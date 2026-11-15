import copy
import io
import json
import uuid
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
import pytest
from backend import assistant,gemini,storage,catalog,api
from backend.assistant_tools import WorkspaceTools
from backend.domain import RuleError
from test_backend import aws,create

MANAGER={'id':'manager','role':'manager','name':'Private Real Person'}


def test_adapter_translates_schema_and_preserves_native_signature():
    native={'role':'model','parts':[{'functionCall':{'id':'call-1','name':'search_catalog','args':{'kind':'assets'}},'thoughtSignature':'OPAQUE_SIGNATURE'}]}
    first=gemini.normalized({'candidates':[{'content':native,'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':11,'candidatesTokenCount':5,'thoughtsTokenCount':2}})
    assert first['usage']=={'inputTokens':11,'outputTokens':7}
    messages=[{'role':'user','content':[{'text':'Find presses'}]},first['output']['message'],{'role':'user','content':[{'toolResult':{'toolUseId':'call-1','content':[{'json':{'items':[]}}],'status':'success'}}]}]
    saved=copy.deepcopy(messages)
    data=gemini.body(messages,'system',{'tools':[{'toolSpec':{'name':'search_catalog','description':'Search','inputSchema':{'json':{'type':'object','additionalProperties':False}}}}]})
    assert data['contents'][1]==native
    assert data['contents'][2]['parts']==[{'functionResponse':{'name':'search_catalog','id':'call-1','response':{'items':[]}}}]
    assert data['tools'][0]['functionDeclarations'][0]['parametersJsonSchema']['additionalProperties'] is False
    assert data['generationConfig']['maxOutputTokens']==1024
    assert messages==saved


def test_generated_internal_ids_are_not_sent_as_provider_ids():
    output=gemini.normalized({'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'functionCall':{'name':'workspace_overview','args':{}}}]}}]})['output']['message']
    id=output['content'][0]['toolUse']['toolUseId']
    result={'role':'user','content':[{'toolResult':{'toolUseId':id,'content':[{'json':{}}]}}]}
    assert 'id' not in gemini.contents([output,result])[1]['parts'][0]['functionResponse']


@pytest.mark.parametrize('response',[
    {'promptFeedback':{'blockReason':'SAFETY'}},
    {'candidates':[{'finishReason':'SAFETY','content':{'parts':[]}}]},
    {'candidates':[{'finishReason':'STOP','content':{'parts':[]}}]},
    {'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'functionCall':{'name':'draft_work_order','args':{}}}]}}]},
])
def test_blocked_empty_or_truncated_function_output_is_not_executed(response):
    with pytest.raises(assistant.AssistantError):gemini.normalized(response)


def test_thought_text_is_not_a_user_reply():
    response={'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'thought':True,'text':'private reasoning'},{'text':'Visible answer'}]}}]}
    assert gemini.normalized(response)['output']['message']['content']==[{'text':'Visible answer'}]


@pytest.mark.parametrize('status,code',[(400,'AI_UNAVAILABLE'),(401,'AI_ACCESS_DENIED'),(403,'AI_ACCESS_DENIED'),(404,'AI_MODEL_UNAVAILABLE'),(429,'AI_BUSY'),(500,'AI_UNAVAILABLE'),(302,'AI_UNAVAILABLE')])
def test_http_failures_do_not_expose_key_provider_error_or_request_body(monkeypatch,capsys,status,code):
    monkeypatch.setenv('GEMINI_API_KEY','LOCAL_TEST_KEY_ONLY')
    opener=Mock();opener.open.side_effect=HTTPError('https://example.invalid',status,'provider body contains sensitive input',{},io.BytesIO(b'LOCAL_TEST_KEY_ONLY private input'))
    monkeypatch.setattr(gemini.request,'build_opener',lambda *a:opener)
    with pytest.raises(assistant.AssistantError) as e:gemini.converse([{'role':'user','content':[{'text':'question'}]}],'system',{'tools':[]})
    assert e.value.code==code
    assert 'LOCAL_TEST_KEY_ONLY' not in str(e.value)+capsys.readouterr().out
    assert 'private input' not in str(e.value)
    req=opener.open.call_args.args[0]
    assert req.full_url.startswith('https://generativelanguage.googleapis.com/v1beta/models/')
    assert 'LOCAL_TEST_KEY_ONLY' not in req.full_url
    assert opener.open.call_args.kwargs['timeout']==6


def test_provider_timeout_missing_key_invalid_model_and_oversized_response(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    with pytest.raises(assistant.AssistantError) as e:gemini.converse([],'',{'tools':[]})
    assert e.value.code=='AI_NOT_CONFIGURED'
    monkeypatch.setenv('GEMINI_API_KEY','LOCAL_TEST_KEY_ONLY');monkeypatch.setenv('GEMINI_MODEL_ID','https://untrusted.invalid/model')
    with pytest.raises(assistant.AssistantError):gemini.converse([],'',{'tools':[]})
    monkeypatch.setenv('GEMINI_MODEL_ID','gemini-3.5-flash-lite')
    opener=Mock();opener.open.side_effect=URLError('sensitive provider details')
    monkeypatch.setattr(gemini.request,'build_opener',lambda *a:opener)
    with pytest.raises(assistant.AssistantError) as e:gemini.converse([],'',{'tools':[]})
    assert e.value.code=='AI_TIMEOUT'
    opener.open.side_effect=None;opener.open.return_value.__enter__=Mock(return_value=Mock(read=lambda n:b'x'*n));opener.open.return_value.__exit__=Mock(return_value=False)
    with pytest.raises(assistant.AssistantError) as e:gemini.converse([],'',{'tools':[]})
    assert e.value.code=='AI_INVALID_RESPONSE'


def test_redirect_cannot_forward_key():
    assert gemini.NoRedirect().redirect_request(None,None,302,'',{},'https://other.invalid') is None


def test_demo_scope_excludes_real_jobs_and_identity_after_demo_reassignment(aws):
    real=create();j=storage.get_job(create('demo')['id']);j.update(demo=True,assigneeId='real-worker',assigneeName='Private Real Worker',reporterName='Private Real Reporter');storage.table().put_item(Item=j)
    tool=WorkspaceTools(MANAGER,str(uuid.uuid4()),demo_only=True)
    result=tool.execute('search_work_orders',{})
    assert result['totalMatches']==1
    assert 'Private Real' not in json.dumps(assistant.plain(result))
    assert 'assigneeId' not in result['items'][0]
    with pytest.raises(RuleError):tool.execute('work_order_details',{'id':real['id']})
    assert tool.execute('workspace_overview',{})['accessibleWorkOrders']==1


def test_demo_directory_and_catalog_exclude_genuine_records(aws,monkeypatch):
    real=catalog.mutate('parts',{'name':'Private Real Part','sku':'R1','quantity':1,'minQuantity':2},MANAGER)
    fake=catalog.mutate('parts',{'name':'Fictional spare','sku':'D1','quantity':2,'minQuantity':3},MANAGER)
    row=catalog.get('parts',fake['id']);row['demo']=True;storage.table().put_item(Item=row)
    original=api.route
    def route(method,path,data,user,event):
        if path=='/users':return {'items':[MANAGER,{'id':'demo-person-a','name':'Fictional Person','demo':True,'role':'worker'}]}
        return original(method,path,data,user,event)
    monkeypatch.setattr(api,'route',route)
    tool=WorkspaceTools(MANAGER,str(uuid.uuid4()),demo_only=True)
    assert tool.execute('search_catalog',{'kind':'parts'})['totalMatches']==1
    assert tool.execute('search_people',{})['items']==[{'id':'demo-person-a','name':'Fictional Person','demo':True,'role':'worker'}]
    with pytest.raises(RuleError):tool.execute('draft_work_order',{'machineId':'M-012','title':'Test','description':'Test'})
    with pytest.raises(RuleError):tool.execute('draft_rule',{'kind':'plans','fields':{'assetId':'M-012'}})


def test_demo_details_exclude_new_real_activity(aws):
    j=storage.get_job(create()['id']);j['demo']=True;storage.table().put_item(Item=j)
    result=WorkspaceTools(MANAGER,str(uuid.uuid4()),demo_only=True).execute('work_order_details',{'id':j['id']})
    assert result['activity']==[]


def test_provider_selection_defaults_to_restricted_demo_and_manual_search_stays_live(aws,monkeypatch):
    monkeypatch.setenv('ASSISTANT_PROVIDER','gemini');monkeypatch.setenv('GEMINI_API_KEY','LOCAL_TEST_KEY_ONLY');monkeypatch.delenv('GEMINI_DATA_MODE',raising=False);monkeypatch.setattr(assistant,'check_access',lambda *a:None)
    assert assistant.demo_only()
    status=assistant.route('GET','/assistant/status',{},MANAGER)
    assert status['configured'] and status['dataScope']=='demo' and 'Gemini' not in status['model']
    create()
    assert assistant.route('POST','/assistant/search',{'tool':'search_work_orders','input':{}},MANAGER)['result']['totalMatches']==1
    monkeypatch.setenv('GEMINI_DATA_MODE','paid');assert not assistant.demo_only()
    monkeypatch.setenv('ASSISTANT_PROVIDER','unrecognized')
    with pytest.raises(assistant.AssistantError):assistant.configured()


def test_complete_gemini_tool_loop_drafts_without_creating(aws,monkeypatch):
    monkeypatch.setenv('ASSISTANT_PROVIDER','gemini');monkeypatch.setenv('GEMINI_DATA_MODE','paid');monkeypatch.setenv('GEMINI_API_KEY','LOCAL_TEST_KEY_ONLY');monkeypatch.setattr(assistant,'check_access',lambda *a:None)
    responses=[{'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'functionCall':{'id':'call1','name':'draft_work_order','args':{'machineId':'M-012','title':'Oil leak','description':'Fictional oil below press'}}}]}}]}, {'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'text':'Review the draft and confirm to create it.'}]}}]}]
    def open(req,**kw):
        response=Mock();response.__enter__=Mock(return_value=Mock(read=lambda n:json.dumps(responses.pop(0)).encode()));response.__exit__=Mock(return_value=False);return response
    monkeypatch.setattr(gemini.request,'build_opener',lambda *a:Mock(open=open))
    result=assistant.chat({'message':'Draft an oil leak report','history':[],'requestId':str(uuid.uuid4())},MANAGER)
    assert len(result['drafts'])==1 and not storage.list_jobs()
    assert '_geminiContent' not in json.dumps(result)
    assert 'LOCAL_TEST_KEY_ONLY' not in json.dumps(result)


def test_helper_verifies_login_before_prompting_for_a_secret(monkeypatch):
    import runpy
    from pathlib import Path
    from botocore.exceptions import MissingDependencyException
    helper=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/configure-gemini-secret.py'))
    session=Mock();session.client.side_effect=MissingDependencyException(msg='CRT required')
    monkeypatch.setattr(helper['boto3'],'Session',lambda **kw:session)
    prompt=Mock();monkeypatch.setattr(helper['getpass'],'getpass',prompt)
    monkeypatch.setattr(helper['sys'],'argv',['configure-gemini-secret.py'])
    with pytest.raises(MissingDependencyException):helper['main']()
    prompt.assert_not_called()


def test_helper_check_never_reads_or_writes_a_secret(monkeypatch):
    import runpy
    from pathlib import Path
    helper=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/configure-gemini-secret.py'))
    session=Mock();monkeypatch.setattr(helper['boto3'],'Session',lambda **kw:session)
    prompt=Mock();monkeypatch.setattr(helper['getpass'],'getpass',prompt)
    monkeypatch.setattr(helper['sys'],'argv',['configure-gemini-secret.py','--check'])
    helper['main']();prompt.assert_not_called()
    session.client.return_value.get_caller_identity.assert_called_once()
    for name in ['get_secret_value','put_secret_value','create_secret']:getattr(session.client.return_value,name).assert_not_called()


def test_admin_service_diagnostic_redacts_credentials_and_request_text(monkeypatch,capsys):
    key='LOCAL_TEST_KEY_ONLY';prompt='This is the entire private user request'
    monkeypatch.setenv('GEMINI_API_KEY',key)
    error_body={'error':{'status':'INVALID_ARGUMENT','message':'Unsupported option; '+key+' '+prompt+' private@example.invalid','details':[{'reason':'API_KEY_INVALID'},{'reason':key}]}}
    opener=Mock();opener.open.side_effect=HTTPError('https://example.invalid',400,'invalid',{},io.BytesIO(json.dumps(error_body).encode()))
    monkeypatch.setattr(gemini.request,'build_opener',lambda *a:opener)
    with pytest.raises(assistant.AssistantError) as e:gemini.converse([{'role':'user','content':[{'text':prompt}]}],'system',{'tools':[]})
    result=json.dumps(e.value.diagnostic)
    assert e.value.diagnostic['status']=='INVALID_ARGUMENT'
    assert e.value.diagnostic['reasons']==['API_KEY_INVALID']
    for private in [key,prompt,'private@example.invalid']:assert private not in result
    assert 'Unsupported option' in result
    assert 'Unsupported option' not in capsys.readouterr().out


def test_unresolved_secret_reference_is_not_sent_to_google(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','{{resolve:secretsmanager:example:SecretString:api_key}}')
    opener=Mock();monkeypatch.setattr(gemini.request,'build_opener',opener)
    with pytest.raises(assistant.AssistantError) as e:gemini.converse([],'system',{'tools':[]})
    assert e.value.code=='AI_NOT_CONFIGURED';opener.assert_not_called()


def test_invalid_google_key_400_has_explicit_access_error(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','LOCAL_TEST_KEY_ONLY')
    body={'error':{'status':'INVALID_ARGUMENT','message':'API key not valid. Please pass a valid API key.'}}
    opener=Mock();opener.open.side_effect=HTTPError('https://example.invalid',400,'invalid',{},io.BytesIO(json.dumps(body).encode()))
    monkeypatch.setattr(gemini.request,'build_opener',lambda *a:opener)
    with pytest.raises(assistant.AssistantError) as e:gemini.converse([],'system',{'tools':[]})
    assert e.value.code=='AI_ACCESS_DENIED'


def test_helper_google_rejection_leaves_existing_secret_untouched(monkeypatch,capsys):
    import runpy
    from pathlib import Path
    helper=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/configure-gemini-secret.py'))
    session=Mock();monkeypatch.setattr(helper['boto3'],'Session',lambda **kw:session)
    monkeypatch.setattr(helper['getpass'],'getpass',Mock(side_effect=['LOCAL_TEST_KEY_ONLY']*2))
    monkeypatch.setattr(helper['sys'],'argv',['configure-gemini-secret.py'])
    monkeypatch.setattr(helper['sys'].stdin,'isatty',lambda:True)
    body={'error':{'message':'do not echo LOCAL_TEST_KEY_ONLY','details':[{'reason':'API_KEY_INVALID'}]}}
    opener=Mock();opener.open.side_effect=HTTPError('https://example.invalid',400,'invalid',{},io.BytesIO(json.dumps(body).encode()))
    monkeypatch.setattr(helper['urlrequest'],'build_opener',lambda *a:opener)
    with pytest.raises(SystemExit) as e:helper['main']()
    assert 'API_KEY_INVALID' in str(e.value) and 'LOCAL_TEST_KEY_ONLY' not in str(e.value)
    for name in ['get_secret_value','put_secret_value','create_secret']:getattr(session.client.return_value,name).assert_not_called()


def test_helper_success_requires_no_identifier_handoff(monkeypatch,capsys):
    import runpy
    from pathlib import Path
    helper=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/configure-gemini-secret.py'))
    session=Mock();session.client.return_value.describe_secret.return_value={'ARN':'arn:aws:secretsmanager:ap-south-1:123456789012:secret:test'}
    monkeypatch.setattr(helper['boto3'],'Session',lambda **kw:session)
    monkeypatch.setattr(helper['getpass'],'getpass',Mock(side_effect=['LOCAL_TEST_KEY_ONLY']*2))
    monkeypatch.setattr(helper['sys'],'argv',['configure-gemini-secret.py'])
    monkeypatch.setattr(helper['sys'].stdin,'isatty',lambda:True)
    response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
    monkeypatch.setattr(helper['urlrequest'],'build_opener',lambda *a:Mock(open=Mock(return_value=response)))
    helper['main']()
    session.client.return_value.put_secret_value.assert_called_once()
    session.client.return_value.get_secret_value.assert_not_called()
    out=capsys.readouterr().out
    assert 'Key stored successfully. You are finished' in out
    assert 'arn:aws:' not in out and 'LOCAL_TEST_KEY_ONLY' not in out
