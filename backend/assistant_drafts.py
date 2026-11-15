"""Private, expiring drafts. A model can propose; only a person can confirm."""
import hashlib
import json
import os
import time
import uuid
from . import catalog, storage, clients
from .domain import RuleError, manages, text
from botocore.exceptions import ClientError


def store(kind, payload, user, request_id, context=None):
    digest=hashlib.sha256(json.dumps([user['id'],request_id,kind,payload],sort_keys=True).encode()).hexdigest()
    id=str(uuid.UUID(digest[:32]))
    item={'PK':'AI#'+user['id'],'SK':'DRAFT#'+id,'id':id,'kind':kind,'payload':payload,'role':user['role'],'context':context or {},'expiresAt':int(time.time())+900}
    if user.get('_conversationId'):
        from . import conversations
        conversations.assert_live(user['_conversationId'],user,user['_conversationScope'],user['_conversationToken'])
        item['conversationId']=user['_conversationId']
    # A repeated model tool call produces the same reviewed draft and expiry.
    old=storage.table().get_item(Key={'PK':item['PK'],'SK':item['SK']},ConsistentRead=True).get('Item')
    if not old:
        try:
            if user.get('_conversationId'):
                clients.client('dynamodb',clients.region()).transact_write_items(TransactItems=[
                    {'Put':{'TableName':os.environ['TABLE_NAME'],'Item':storage.encode(item),'ConditionExpression':'attribute_not_exists(PK)'}},conversations.draft_guard(user)])
            else:storage.table().put_item(Item=item,ConditionExpression='attribute_not_exists(PK)')
        except ClientError as exc:
            if exc.response['Error']['Code'] not in ['ConditionalCheckFailedException','TransactionCanceledException']:raise
            if user.get('_conversationId'):conversations.assert_live(user['_conversationId'],user,user['_conversationScope'],user['_conversationToken'])
            item=storage.table().get_item(Key={'PK':item['PK'],'SK':item['SK']},ConsistentRead=True).get('Item')
            if not item:raise RuleError('The draft could not be saved. Please retry.',409) from exc
    else:item=old
    return public(item)


def public(item):
    return {k:item[k] for k in ['id','kind','payload','expiresAt','context','confirmedWorkOrder'] if k in item}


def read(id,user):
    try:uuid.UUID(id)
    except (ValueError,TypeError,AttributeError):raise RuleError('Invalid draft ID')
    item=storage.table().get_item(Key={'PK':'AI#'+user['id'],'SK':'DRAFT#'+id},ConsistentRead=True).get('Item')
    if not item:raise RuleError('Draft not found',404)
    if item.get('deleted'):raise RuleError('This draft was deleted with its conversation.',410)
    if item.get('conversationId'):
        from . import conversations,assistant
        conversations.assert_live(item['conversationId'],user,'demo' if assistant.demo_only() else 'workspace')
    if item['expiresAt']<=int(time.time()):raise RuleError('This draft expired. Ask for a new draft.',410)
    if item['role']!=user['role']:raise RuleError('Your role changed. Ask for a new draft with your current access.',403)
    return item


def work_order(data,user,request_id):
    allowed={'machineId','title','description','priority','category'}
    if not isinstance(data,dict) or set(data)-allowed:raise RuleError('Invalid work-order draft fields')
    machine=next((m for m in catalog.machines() if m['id']==data.get('machineId')),None)
    if not machine:raise RuleError('Choose a registered machine ID; search assets first')
    priority=data.get('priority','medium')
    if priority not in ['low','medium','high','critical']:raise RuleError('Choose a valid priority')
    payload={'machineId':machine['id'],'title':text(data.get('title'),'Title',160),'description':text(data.get('description'),'Description',4000),'priority':priority,'category':text(data.get('category','General'),'Category',100)}
    return store('work_order',payload,user,request_id,{'machineName':machine['name'],'machineCode':machine.get('code') or machine['id'],'location':machine.get('locationName') or machine.get('location','')})


def rule(data,user,request_id):
    if not manages(user):raise RuleError('Manager access required to draft plans or automation rules',403)
    if not isinstance(data,dict) or set(data)!={'kind','fields'} or data['kind'] not in ['plans','automations']:raise RuleError('Choose plans or automations')
    fields=data['fields']
    if not isinstance(fields,dict) or 'version' in fields:raise RuleError('Provide fields for a new rule')
    fields=catalog.validate(data['kind'],{**fields,'enabled':False})
    context={'meterName':catalog.get('meters',fields['meterId'])['name']} if data['kind']=='automations' else {'assetName':catalog.asset(fields['assetId'])['name']}
    return store(data['kind'],fields,user,request_id,context)


def confirm(data,user):
    if not isinstance(data,dict) or set(data)!={'draftId'}:raise RuleError('Confirm only the reviewed draft ID')
    draft=read(data['draftId'],user)
    if draft['kind']!='work_order':raise RuleError('Review planning and automation drafts in their normal editor')
    from . import api
    # The normal report API provides authorization, fresh asset checks, duplicate
    # advisories, an audit event and atomic idempotency for double-clicks/retries.
    job=api.create(draft['payload'],dict(user,_assistantDraftId=draft['id']),{'headers':{'idempotency-key':'assistant:'+draft['id']}})
    summary={k:job[k] for k in ['id','number','title','status','possibleDuplicate','possibleResolved']}
    try:storage.table().update_item(Key={'PK':draft['PK'],'SK':draft['SK']},UpdateExpression='SET confirmedWorkOrder = :job',ConditionExpression='attribute_not_exists(deleted)',ExpressionAttributeValues={':job':summary})
    except ClientError as exc:
        if exc.response['Error']['Code']!='ConditionalCheckFailedException':raise
    return {'workOrder':summary,'message':'Work order created and sent for manager review.'}
