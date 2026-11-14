"""Second-pass isolated probes. Uses moto and fake actors; never calls live AWS."""
import base64,contextlib,hashlib,importlib.util,io,json,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from moto import mock_aws
from backend import api,catalog,storage
from backend.domain import RuleError,transition
spec=importlib.util.spec_from_file_location('research_probe_base',Path(__file__).with_name('research-edgecase-probes.py'));base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
M=base.MANAGER;R=base.REPORTER

def new_job(key):return api.create({'machineId':'M-012','title':'Research report','description':'Isolated fictional probe'},R,{'headers':{'idempotency-key':key}})
def run():
    out=[];seen={};collision=None
    for n in range(400000):
        key='round2-'+str(n);prefix=hashlib.sha256((R['id']+':'+key).encode()).hexdigest()[:8]
        if prefix in seen:collision=(seen[prefix],key);break
        seen[prefix]=key
    assert collision,'Increase deterministic local prefix search bound'
    with mock_aws():
        base.setup();a=new_job(collision[0]);b=new_job(collision[1]);out.append({'id':'S01','finding':'Work-order display numbers can collide despite distinct immutable IDs','firstId':a['id'],'secondId':b['id'],'firstNumber':a['number'],'secondNumber':b['number'],'sameDisplayNumber':a['number']==b['number']})
    with mock_aws():
        base.setup()
        with patch.object(api,'now',return_value='2026-11-14T09:00:00Z'):j=storage.get_job(new_job('audit')['id'])
        assigned,reason=transition(j,M,{'action':'approve','version':j['version'],'assigneeId':'worker-A','assigneeName':'Worker A'},'2026-11-14T10:00:00Z');storage.write(assigned,M,'approve',reason,old=j)
        changed,reason=transition(assigned,M,{'action':'reassign','version':assigned['version'],'assigneeId':'worker-B','assigneeName':'Worker B'},'2026-11-14T10:10:00Z');storage.write(changed,M,'reassign',reason,old=assigned)
        events=storage.events(j['id']);event=next(e for e in events if e['action']=='reassign');out.append({'id':'S02','finding':'Assignment audit does not retain old/new assignee or transition version','currentAssignee':storage.get_job(j['id'])['assigneeId'],'reassignmentEvent':event,'earlierWorkerInActivity':any('worker-A' in json.dumps(e) for e in events)})
    with mock_aws():
        base.setup();j=new_job('name');storage.table().put_item(Item={'PK':'USER#worker-A','SK':'PROFILE','displayName':'Current display name','department':'maintenance','machineIds':[]})
        person={'Username':'worker-A','Attributes':[{'Name':'sub','Value':'worker-A'},{'Name':'name','Value':'Original signup name'}]}
        with patch.object(api,'find_user',return_value=person),patch.object(api,'role_for',return_value='worker'):
            result=api.route('POST','/workorders/'+j['id']+'/actions',{'action':'approve','version':1,'assigneeId':'worker-A'},M,{})
        out.append({'id':'S03','finding':'Assigned worker label ignores the current onboarding display name','profileDisplayName':api.profile_for({'id':'worker-A'})['displayName'],'jobAssigneeName':result['assigneeName']})
    with mock_aws():
        base.setup();v=base.make('vendors',name='Supplier');p=base.make('parts',name='High-range part',sku='BOUNDARY',quantity=1000000000);o=base.make('purchases',name='Boundary receipt',partId=p['id'],vendorId=v['id'],quantity=1);catalog.receive(o['id'],{'version':1},M);p=catalog.get('parts',p['id'])
        try:catalog.mutate('parts',{'version':p['version'],'name':'Renamed'},M,p['id']);edit='accepted'
        except RuleError as exc:edit={'status':exc.status,'message':str(exc)}
        out.append({'id':'S04','finding':'Receipt can exceed the quantity cap that later metadata edits enforce','receivedBalance':int(p['quantity']),'renameResult':edit,'boundaryOnly':True})
    with mock_aws():
        base.setup();event={'rawPath':'/workorders','requestContext':{'http':{'method':'POST'},'authorizer':{'jwt':{'claims':{'sub':R['id'],'email_verified':'true'}}}},'headers':{'idempotency-key':'bytes'},'isBase64Encoded':True,'body':base64.b64encode(b'\xff').decode()}
        log=io.StringIO()
        with patch.object(api,'find_user',return_value={'Username':R['id']}),patch.object(api,'role_for',return_value='reporter'),contextlib.redirect_stdout(log):response=api.handler(event,None)
        out.append({'id':'S05','finding':'Malformed UTF-8 is classified as a server error','response':response,'logged':log.getvalue().strip()})
        body=json.dumps({'machineId':'M-012','title':'UTF-8 size probe','description':'Fictional','ignored':'\U0001f642'*17000},ensure_ascii=False);event['body']=body;event['isBase64Encoded']=False
        with patch.object(api,'find_user',return_value={'Username':R['id']}),patch.object(api,'role_for',return_value='reporter'):response=api.handler(event,None)
        out.append({'id':'S06','finding':'Request budget measures decoded characters rather than UTF-8 bytes','characters':len(body),'encodedBytes':len(body.encode()),'configuredComparison':65536,'statusCode':response['statusCode'],'unknownFieldIgnored':True})
    return out
if __name__=='__main__':
    data={'mode':'isolated moto and fake actors only; no live mutations','observations':run()};p=Path('docs/research/2026-11-14-round2-probe-results.json');p.write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2))
