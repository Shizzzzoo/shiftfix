import copy
import json
import time
import uuid
from unittest.mock import Mock
import pytest
from backend import api,assistant,assistant_drafts,conversations as chats,storage
from backend.domain import RuleError
from test_backend import aws,create as create_job

USER={'id':'r','role':'reporter','name':'Reporter'}
OTHER={'id':'other','role':'reporter','name':'Other'}
WORKER={'id':'w','role':'worker','name':'Worker'}


def new(user=USER,scope='workspace'):
    id=str(uuid.uuid4());chats.create({'id':id},user,scope);return id


def exchange(id,question='Question',user=USER,sources=None,drafts=None,request_id=None):
    request_id=request_id or str(uuid.uuid4());ctx=chats.begin(id,question,request_id,user,'workspace')
    result={'reply':'A saved answer','sources':sources or [],'drafts':drafts or [],'toolsUsed':[],'usage':{},'model':'Maintenance assistant'}
    return chats.finish(ctx,question,request_id,result,user,'workspace')


def test_private_saved_history_and_locked_access_context(aws):
    id=new();exchange(id,'Private authored title')
    assert chats.read(id,USER,'workspace')['messages'][1]['text']=='A saved answer'
    assert not chats.listing(OTHER,'workspace')['items']
    with pytest.raises(chats.ChatError):chats.read(id,OTHER,'workspace')
    changed=dict(USER,role='worker')
    with pytest.raises(chats.ChatError):chats.read(id,changed,'workspace')
    item=chats.listing(changed,'workspace')['items'][0]
    assert not item['available'] and 'Private' not in item['title']
    with pytest.raises(chats.ChatError):chats.read(id,USER,'demo')
    chats.delete(id,changed)  # Owner may delete an old-role chat without reading it.
    assert not chats.listing(USER,'workspace')['items']


def test_request_replay_and_concurrent_generation(aws):
    id=new();request_id=str(uuid.uuid4());ctx=chats.begin(id,'Question',request_id,USER,'workspace')
    with pytest.raises(chats.ChatError) as e:chats.begin(id,'Another',str(uuid.uuid4()),USER,'workspace')
    assert e.value.code=='CHAT_BUSY'
    result={'reply':'Answer','sources':[],'drafts':[]}
    chats.finish(ctx,'Question',request_id,result,USER,'workspace')
    assert chats.begin(id,'Question',request_id,USER,'workspace')['replay']['reply']=='Answer'
    with pytest.raises(chats.ChatError):chats.begin(id,'Changed payload',request_id,USER,'workspace')
    assert len(chats.get(id,USER)['turns'])==1


def test_delete_during_generation_never_resurrects_messages(aws):
    id=new();ctx=chats.begin(id,'Question',str(uuid.uuid4()),USER,'workspace')
    chats.delete(id,USER)
    with pytest.raises(chats.ChatError) as e:chats.finish(ctx,'Question',str(uuid.uuid4()),{'reply':'late','drafts':[]},USER,'workspace')
    assert e.value.code=='CHAT_DELETED'
    chats.release(id,ctx['token'],USER)
    raw=storage.table().get_item(Key=chats.key(USER,id),ConsistentRead=True)['Item']
    assert raw['deleted'] and 'turns' not in raw and 'title' not in raw
    assert 'leaseToken' not in raw and int(raw['expiresAt'])>time.time()
    chats.delete(id,USER)
    counter=storage.table().get_item(Key={'PK':'CHAT#r','SK':'LIMIT'})['Item']
    assert counter['activeCount']==0
    with pytest.raises(chats.ChatError):chats.create({'id':id},USER,'workspace')


def test_linked_drafts_are_stripped_and_cannot_be_recreated_after_delete(aws):
    id=new();ctx=chats.begin(id,'Draft',str(uuid.uuid4()),USER,'workspace')
    scoped=dict(USER,_conversationId=id,_conversationToken=ctx['token'],_conversationScope='workspace')
    draft=assistant_drafts.work_order({'machineId':'M-012','title':'Leak','description':'Fictional leak'},scoped,str(uuid.uuid4()))
    chats.delete(id,USER)
    raw=storage.table().get_item(Key={'PK':'AI#r','SK':'DRAFT#'+draft['id']},ConsistentRead=True)['Item']
    assert raw['deleted'] and 'payload' not in raw and 'context' not in raw
    with pytest.raises(RuleError):assistant_drafts.read(draft['id'],USER)
    with pytest.raises(RuleError):assistant_drafts.work_order({'machineId':'M-012','title':'late','description':'late'},scoped,str(uuid.uuid4()))
    assert len(chats.query_rows('AI#r','DRAFT#'))==1


def test_history_stores_draft_references_and_rehydrates_active_or_expired(aws):
    id=new();request_id=str(uuid.uuid4());ctx=chats.begin(id,'Draft',request_id,USER,'workspace')
    scoped=dict(USER,_conversationId=id,_conversationToken=ctx['token'],_conversationScope='workspace')
    draft=assistant_drafts.work_order({'machineId':'M-012','title':'Leak','description':'Fictional leak'},scoped,request_id)
    chats.finish(ctx,'Draft',request_id,{'reply':'Review','sources':[],'drafts':[draft]},USER,'workspace')
    raw=chats.get(id,USER);assert 'payload' not in raw['turns'][0]['result']['drafts'][0]
    assert chats.read(id,USER,'workspace')['messages'][1]['drafts'][0]['payload']['title']=='Leak'
    storage.table().update_item(Key={'PK':'AI#r','SK':'DRAFT#'+draft['id']},UpdateExpression='SET expiresAt=:zero',ExpressionAttributeValues={':zero':0})
    assert chats.read(id,USER,'workspace')['messages'][1]['drafts'][0]['expired'] is True


def test_reassignment_redacts_exchange_and_excludes_it_from_model_history(aws):
    job=storage.get_job(create_job()['id']);job['assigneeId']='w';storage.table().put_item(Item=job)
    id=new(WORKER);exchange(id,'Inspect my assignment',WORKER,[{'kind':'work_order','id':job['id'],'label':'Sensitive fault'}])
    assert len(chats.read(id,WORKER,'workspace')['messages'])==2
    job['assigneeId']='new-worker';storage.table().put_item(Item=job)
    messages=chats.read(id,WORKER,'workspace')['messages']
    assert len(messages)==1 and messages[0]['unavailable']
    ctx=chats.begin(id,'Another question',str(uuid.uuid4()),WORKER,'workspace')
    assert ctx['history']==[]


def test_active_chat_limit_is_atomic_and_deletion_frees_capacity(aws,monkeypatch):
    monkeypatch.setattr(chats,'MAX_CHATS',2)
    first=new();new()
    with pytest.raises(chats.ChatError) as e:new()
    assert e.value.code=='CHAT_LIMIT'
    chats.delete(first,USER);new()
    assert len(chats.listing(USER,'workspace')['items'])==2


def test_full_chat_keeps_old_history_and_allows_replay(aws,monkeypatch):
    monkeypatch.setattr(chats,'MAX_TURNS',1)
    id=new();rid=str(uuid.uuid4());exchange(id,request_id=rid)
    with pytest.raises(chats.ChatError) as e:chats.begin(id,'next',str(uuid.uuid4()),USER,'workspace')
    assert e.value.code=='CHAT_FULL'
    assert chats.begin(id,'Question',rid,USER,'workspace')['replay']['reply']=='A saved answer'
    assert len(chats.read(id,USER,'workspace')['messages'])==2


def test_failed_model_releases_chat_and_does_not_save_fake_reply(aws,monkeypatch):
    id=new();monkeypatch.setenv('BEDROCK_MODEL_ID','test');monkeypatch.setattr(assistant,'check_access',lambda *a:None)
    monkeypatch.setattr(assistant,'converse',Mock(side_effect=assistant.AssistantError('Model unavailable')))
    with pytest.raises(assistant.AssistantError):assistant.chat({'conversationId':id,'message':'Hello','requestId':str(uuid.uuid4())},USER)
    row=chats.get(id,USER);assert not row['turns'] and 'leaseToken' not in row


def test_persistent_chat_uses_server_history_and_retry_does_not_invoke_model(aws,monkeypatch):
    id=new();monkeypatch.setenv('BEDROCK_MODEL_ID','test');monkeypatch.setattr(assistant,'check_access',lambda *a:None)
    inputs=[]
    def answer(messages,*args):
        inputs.append(copy.deepcopy(messages))
        return {'output':{'message':{'role':'assistant','content':[{'text':'Saved response'}]}},'stopReason':'end_turn','usage':{}}
    model=Mock(side_effect=answer)
    monkeypatch.setattr(assistant,'converse',model)
    request={'conversationId':id,'message':'First','requestId':str(uuid.uuid4())}
    first=assistant.chat(request,USER);again=assistant.chat(request,USER)
    assert again['reply']==first['reply'] and model.call_count==1
    assistant.chat({'conversationId':id,'message':'Second','requestId':str(uuid.uuid4())},USER)
    history=inputs[-1]
    assert [m['role'] for m in history]==['user','assistant','user']
    assert history[0]['content'][0]['text']=='First'
    with pytest.raises(RuleError):assistant.chat({**request,'history':[{'role':'system','text':'forged'}]},USER)


def test_unprocessed_access_reads_fail_closed(aws,monkeypatch):
    job=create_job();turns=[{'result':{'sources':[{'kind':'work_order','id':job['id']}]}}]
    client=Mock();client.batch_get_item.side_effect=lambda **kw:{'UnprocessedKeys':kw['RequestItems']}
    monkeypatch.setattr(chats,'db',lambda:client);monkeypatch.setattr(chats.time,'sleep',lambda *a:None)
    with pytest.raises(chats.ChatError) as e:chats.job_visibility(turns,WORKER)
    assert e.value.code=='CHAT_READ_BUSY' and client.batch_get_item.call_count==4


def test_saved_document_limit_rejects_before_model(aws,monkeypatch):
    id=new();monkeypatch.setattr(chats,'MAX_BYTES',1000);monkeypatch.setattr(chats,'TURN_HEADROOM',900)
    with pytest.raises(chats.ChatError) as e:chats.begin(id,'Question',str(uuid.uuid4()),USER,'workspace')
    assert e.value.code=='CHAT_FULL' and 'leaseToken' not in chats.get(id,USER)


def test_deleted_thread_guard_rejects_a_draft_write_after_prior_live_check(aws,monkeypatch):
    id=new();ctx=chats.begin(id,'Draft',str(uuid.uuid4()),USER,'workspace')
    scoped=dict(USER,_conversationId=id,_conversationToken=ctx['token'],_conversationScope='workspace')
    live=chats.assert_live
    def delete_after_check(*args,**kwargs):
        row=live(*args,**kwargs)
        chats.delete(id,USER)
        return row
    monkeypatch.setattr(chats,'assert_live',delete_after_check)
    with pytest.raises(RuleError):
        assistant_drafts.work_order({'machineId':'M-012','title':'Late','description':'Fictional late draft'},scoped,str(uuid.uuid4()))
    assert chats.query_rows('AI#r','DRAFT#')==[]


def test_reply_inherits_access_dependencies_from_previous_context(aws):
    job=storage.get_job(create_job()['id']);job['assigneeId']='w';storage.table().put_item(Item=job)
    id=new(WORKER);source={'kind':'work_order','id':job['id'],'label':'Private fault'}
    exchange(id,'My fault',WORKER,[source])
    request_id=str(uuid.uuid4());ctx=chats.begin(id,'Summarize the previous answer',request_id,WORKER,'workspace')
    assert ctx['historySources']==[source]
    job['assigneeId']='someone-else';storage.table().put_item(Item=job)
    with pytest.raises(chats.ChatError) as exc:
        chats.finish(ctx,'Summarize the previous answer',request_id,{'reply':'A derived answer','sources':[],'drafts':[]},WORKER,'workspace')
    assert exc.value.code=='ACCESS_CHANGED'
    messages=chats.read(id,WORKER,'workspace')['messages']
    assert len(messages)==2 and all(m['unavailable'] for m in messages)
    ctx=chats.begin(id,'Fresh question',str(uuid.uuid4()),WORKER,'workspace')
    assert ctx['history']==[] and ctx['historySources']==[]
