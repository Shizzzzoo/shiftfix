"""Private, bounded chat documents with fenced generation and content deletion."""
import json
import os
import time
import uuid
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError
from . import storage,clients
from .domain import RuleError,now,manages,visible

MAX_CHATS=50
MAX_TURNS=30
MAX_BYTES=256*1024
TURN_HEADROOM=64*1024
DES=TypeDeserializer()

class ChatError(RuleError):
    def __init__(self,message,status=409,code='CHAT_CHANGED'):
        super().__init__(message,status);self.code=code


def uuid_id(value):
    try:return str(uuid.UUID(value))
    except (ValueError,TypeError,AttributeError):raise RuleError('Provide a valid conversation ID')


def key(user,id):return {'PK':'CHAT#'+user['id'],'SK':'CHAT#'+uuid_id(id)}
def db():return clients.client('dynamodb',clients.region())
def size(value):return len(json.dumps(value,ensure_ascii=False,default=str,separators=(',',':')).encode())


def get(id,user):
    row=storage.table().get_item(Key=key(user,id),ConsistentRead=True).get('Item')
    if not row or row.get('deleted'):raise ChatError('This conversation was deleted or is unavailable.',410,'CHAT_DELETED')
    return row


def assert_live(id,user,scope=None,token=None):
    row=get(id,user)
    if row['role']!=user['role'] or scope is not None and row['scope']!=scope:
        raise ChatError('Your access context changed. Start a new conversation.',403,'ACCESS_CHANGED')
    if token is not None and row.get('leaseToken')!=token:raise ChatError('This conversation changed. Reload it before continuing.')
    return row


def metadata(row,user,scope):
    available=row.get('role')==user['role'] and row.get('scope')==scope
    return {'id':row['id'],'title':row.get('title','New conversation') if available else 'Conversation from previous access',
        'createdAt':row['createdAt'],'updatedAt':row['updatedAt'],'turnCount':int(row.get('turnCount',0)),
        'version':int(row.get('version',1)),'available':available,'full':int(row.get('turnCount',0))>=MAX_TURNS}


def query_rows(pk,prefix,fields=None):
    args={'TableName':os.environ['TABLE_NAME'],'KeyConditionExpression':'PK = :pk AND begins_with(SK, :prefix)',
        'ExpressionAttributeValues':{':pk':pk,':prefix':prefix},'ConsistentRead':True}
    if fields:
        args['ExpressionAttributeNames']={'#f'+str(i):f for i,f in enumerate(fields)}
        args['ProjectionExpression']=','.join(args['ExpressionAttributeNames'])
    rows=[]
    for page in storage.table().meta.client.get_paginator('query').paginate(**args):rows.extend(page.get('Items',[]))
    return rows


def listing(user,scope):
    rows=query_rows('CHAT#'+user['id'],'CHAT#',['id','title','createdAt','updatedAt','turnCount','version','role','scope','deleted'])
    return {'items':[metadata(r,user,scope) for r in sorted(rows,key=lambda r:r['updatedAt'],reverse=True) if not r.get('deleted')],
        'maxConversations':MAX_CHATS,'maxTurns':MAX_TURNS}


def create(data,user,scope):
    if not isinstance(data,dict) or set(data)!={'id'}:raise RuleError('Provide a new conversation ID only')
    id=uuid_id(data['id']);k=key(user,id)
    old=storage.table().get_item(Key=k,ConsistentRead=True).get('Item')
    if old:return {'conversation':metadata(assert_live(id,user,scope),user,scope)}
    at=now();row={**k,'id':id,'title':'New conversation','createdAt':at,'updatedAt':at,'role':user['role'],'scope':scope,'turns':[],'turnCount':0,'version':1}
    writes=[{'Put':{'TableName':os.environ['TABLE_NAME'],'Item':storage.encode(row),'ConditionExpression':'attribute_not_exists(PK)'}},
        {'Update':{'TableName':os.environ['TABLE_NAME'],'Key':storage.encode({'PK':k['PK'],'SK':'LIMIT'}),'UpdateExpression':'ADD activeCount :one',
          'ConditionExpression':'attribute_not_exists(activeCount) OR activeCount < :max','ExpressionAttributeValues':storage.encode({':one':1,':max':MAX_CHATS})}}]
    try:db().transact_write_items(TransactItems=writes)
    except ClientError as exc:
        if exc.response['Error']['Code']!='TransactionCanceledException':raise
        old=storage.table().get_item(Key=k,ConsistentRead=True).get('Item')
        if old:return {'conversation':metadata(assert_live(id,user,scope),user,scope)}
        raise ChatError('You have 50 saved chats. Delete a conversation before starting another.',409,'CHAT_LIMIT') from exc
    return {'conversation':metadata(row,user,scope)}


def job_visibility(turns,user):
    if manages(user):return None
    ids=list({s['id'] for t in turns for s in t.get('result',{}).get('sources',[]) if s.get('kind')=='work_order'})
    allowed=set();name=os.environ['TABLE_NAME']
    for start in range(0,len(ids),100):
        pending={name:{'Keys':[storage.encode({'PK':'WORK#'+id,'SK':'META'}) for id in ids[start:start+100]],'ConsistentRead':True}}
        for attempt in range(4):
            response=db().batch_get_item(RequestItems=pending)
            for raw in response.get('Responses',{}).get(name,[]):
                job={k:DES.deserialize(v) for k,v in raw.items()}
                if visible(job,user):allowed.add(job['id'])
            pending=response.get('UnprocessedKeys',{})
            if not pending:break
            time.sleep(0.05*(2**attempt))
        if pending:raise ChatError('Saved access checks are busy. Please retry.',503,'CHAT_READ_BUSY')
    return allowed


def readable_turns(turns,user):
    allowed=job_visibility(turns,user);out=[]
    for turn in turns:
        denied=allowed is not None and any(s.get('kind')=='work_order' and s.get('id') not in allowed for s in turn.get('result',{}).get('sources',[]))
        out.append({'id':turn['id'],'at':turn['at'],'unavailable':True} if denied else turn)
    return out


def hydrate(result,user):
    from . import assistant_drafts
    out={k:v for k,v in result.items() if k!='drafts'};out['drafts']=[]
    for ref in result.get('drafts',[]):
        try:out['drafts'].append(assistant_drafts.public(assistant_drafts.read(ref['id'],user)))
        except RuleError:out['drafts'].append({**ref,'expired':True})
    return out


def read(id,user,scope):
    row=assert_live(id,user,scope);messages=[]
    for t in readable_turns(row['turns'],user):
        if t.get('unavailable'):
            messages.append({'id':t['id'],'role':'assistant','text':'This exchange is hidden because access to a referenced work order changed.','unavailable':True});continue
        messages.append({'id':t['id']+'-user','role':'user','text':t['question'],'at':t['at']})
        result=hydrate(t['result'],user)
        messages.append({'id':t['id']+'-assistant','role':'assistant','text':result['reply'],'at':t['at'],'sources':result.get('sources',[]),'drafts':result.get('drafts',[])})
    # Authority can change while batches/drafts are being loaded.
    assert_live(id,user,scope)
    return {'conversation':metadata(row,user,scope),'messages':messages}


def begin(id,question,request_id,user,scope):
    row=assert_live(id,user,scope)
    for turn in row['turns']:
        if turn['id']==request_id:
            if turn['question']!=question:raise ChatError('That request ID was used with a different message.')
            checked=readable_turns([turn],user)[0]
            if checked.get('unavailable'):raise ChatError('Referenced work is no longer available. Start a new conversation.',403,'ACCESS_CHANGED')
            return {'replay':{**hydrate(turn['result'],user),**read(id,user,scope)}}
    if len(row['turns'])>=MAX_TURNS or size(row)>MAX_BYTES-TURN_HEADROOM:
        raise ChatError('This saved conversation is full. Start a new conversation to continue.',409,'CHAT_FULL')
    token=str(uuid.uuid4());at=int(time.time())
    try:
        storage.table().update_item(Key=key(user,id),UpdateExpression='SET leaseToken = :token, leaseUntil = :until',
            ConditionExpression='#v = :v AND attribute_not_exists(deleted) AND (attribute_not_exists(leaseUntil) OR leaseUntil < :now)',
            ExpressionAttributeNames={'#v':'version'},ExpressionAttributeValues={':token':token,':until':at+40,':v':row['version'],':now':at})
    except ClientError as exc:
        if exc.response['Error']['Code']=='ConditionalCheckFailedException':raise ChatError('A reply is already running or this chat changed. Reload or try again shortly.',409,'CHAT_BUSY') from exc
        raise
    history=[];history_sources={}
    try:
        for t in readable_turns(row['turns'][-3:],user):
            if not t.get('unavailable'):
                history.extend([{'role':'user','text':t['question'][:1500]},{'role':'assistant','text':t['result']['reply'][:1500]}])
                for source in t['result'].get('sources',[]):
                    if source.get('kind')=='work_order':history_sources[source['id']]=source
    except Exception:
        release(id,token,user);raise
    return {'row':row,'token':token,'history':history,'historySources':list(history_sources.values())}


def finish(context,question,request_id,result,user,scope):
    row=context['row'];id=row['id']
    saved={k:result[k] for k in ['reply','sources','toolsUsed','usage','model'] if k in result}
    # A reply can quote previous context without reading that record again.
    # Carry its dependencies forward so reassignment also hides derived replies.
    sources={s.get('id') or s.get('page'):s for s in context.get('historySources',[])+result.get('sources',[])}
    saved['sources']=list(sources.values())
    saved['drafts']=[{k:d[k] for k in ['id','kind','expiresAt']} for d in result.get('drafts',[])]
    turn={'id':request_id,'at':now(),'question':question,'result':saved};turns=row['turns']+[turn]
    if size(turn)>TURN_HEADROOM or size({**row,'turns':turns})>MAX_BYTES:raise ChatError('This response is too large to save. Start a new conversation with a narrower question.',409,'CHAT_FULL')
    title=row['title'] if row['turns'] else ' '.join(question.split())[:80]
    try:
        storage.table().update_item(Key=key(user,id),UpdateExpression='SET turns = :turns, #title = :title, updatedAt = :at, turnCount = :count, #v = :next REMOVE leaseToken, leaseUntil',
            ConditionExpression='#v = :old AND leaseToken = :token AND attribute_not_exists(deleted)',
            ExpressionAttributeNames={'#v':'version','#title':'title'},ExpressionAttributeValues={':turns':turns,':title':title,':at':turn['at'],':count':len(turns),':next':row['version']+1,':old':row['version'],':token':context['token']})
    except ClientError as exc:
        if exc.response['Error']['Code']=='ConditionalCheckFailedException':raise ChatError('The chat was deleted or changed while replying. It was not recreated.',410,'CHAT_DELETED') from exc
        raise
    saved_read=read(id,user,scope)
    if saved_read['messages'][-1].get('unavailable'):raise ChatError('Referenced work is no longer available. Reload your conversation.',403,'ACCESS_CHANGED')
    return {**result,**saved_read}


def release(id,token,user):
    try:storage.table().update_item(Key=key(user,id),UpdateExpression='REMOVE leaseToken, leaseUntil',ConditionExpression='leaseToken = :token',ExpressionAttributeValues={':token':token})
    except ClientError as exc:
        if exc.response['Error']['Code']!='ConditionalCheckFailedException':print(json.dumps({'chatLeaseReleaseError':exc.response['Error']['Code']}))


def draft_guard(user):
    return {'ConditionCheck':{'TableName':os.environ['TABLE_NAME'],'Key':storage.encode(key(user,user['_conversationId'])),
        'ConditionExpression':'attribute_exists(PK) AND attribute_not_exists(deleted) AND leaseToken = :token',
        'ExpressionAttributeValues':storage.encode({':token':user['_conversationToken']})}}


def strip_drafts(id,user):
    for row in query_rows('AI#'+user['id'],'DRAFT#',['PK','SK','conversationId']):
        if row.get('conversationId')!=id:continue
        try:storage.table().update_item(Key={'PK':row['PK'],'SK':row['SK']},UpdateExpression='SET deleted = :yes, expiresAt = :ttl REMOVE payload, context, confirmedWorkOrder',
            ConditionExpression='conversationId = :id',ExpressionAttributeValues={':yes':True,':ttl':int(time.time())+172800,':id':id})
        except ClientError as exc:
            if exc.response['Error']['Code']!='ConditionalCheckFailedException':raise


def delete(id,user):
    id=uuid_id(id);k=key(user,id)
    for _ in range(3):
        row=storage.table().get_item(Key=k,ConsistentRead=True).get('Item')
        if not row or row.get('deleted'):break
        writes=[{'Update':{'TableName':os.environ['TABLE_NAME'],'Key':storage.encode(k),
            'UpdateExpression':'SET deleted = :yes, expiresAt = :ttl, updatedAt = :at REMOVE turns, #title, leaseToken, leaseUntil ADD #v :one',
            'ConditionExpression':'#v = :v AND attribute_not_exists(deleted)','ExpressionAttributeNames':{'#v':'version','#title':'title'},
            'ExpressionAttributeValues':storage.encode({':yes':True,':ttl':int(time.time())+172800,':at':now(),':one':1,':v':row['version']})}},
            {'Update':{'TableName':os.environ['TABLE_NAME'],'Key':storage.encode({'PK':k['PK'],'SK':'LIMIT'}),
            'UpdateExpression':'ADD activeCount :minus','ConditionExpression':'activeCount > :zero','ExpressionAttributeValues':storage.encode({':minus':-1,':zero':0})}}]
        try:db().transact_write_items(TransactItems=writes);break
        except ClientError as exc:
            if exc.response['Error']['Code']!='TransactionCanceledException':raise
    else:raise ChatError('This chat changed while deleting. Please retry.')
    strip_drafts(id,user)
    return {'deleted':True,'id':id}
