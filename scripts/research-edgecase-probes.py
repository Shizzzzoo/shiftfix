"""Read-only with respect to AWS: adversarial probes use moto and fake credentials.
Records observed current behavior; these are findings, not passing acceptance tests.
"""
import base64, hashlib, io, json, os, sys
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import boto3
from moto import mock_aws
from PIL import Image
from backend import api,catalog,storage,planning
from backend.domain import RuleError
MANAGER={'id':'manager','name':'Test Manager','role':'manager'}
WORKER={'id':'worker','name':'Test Worker','role':'worker'}
REPORTER={'id':'reporter','name':'Test Reporter','role':'reporter'}

def setup():
    os.environ.update(AWS_DEFAULT_REGION='ap-south-1',AWS_ACCESS_KEY_ID='testing',AWS_SECRET_ACCESS_KEY='testing',TABLE_NAME='research-test',ASSETS_BUCKET='research-test-assets')
    boto3.client('dynamodb').create_table(TableName='research-test',BillingMode='PAY_PER_REQUEST',KeySchema=[{'AttributeName':'PK','KeyType':'HASH'},{'AttributeName':'SK','KeyType':'RANGE'}],AttributeDefinitions=[{'AttributeName':k,'AttributeType':'S'} for k in ['PK','SK','GSI1PK','GSI1SK']],GlobalSecondaryIndexes=[{'IndexName':'GSI1','KeySchema':[{'AttributeName':'GSI1PK','KeyType':'HASH'},{'AttributeName':'GSI1SK','KeyType':'RANGE'}],'Projection':{'ProjectionType':'ALL'}}])
    boto3.client('s3').create_bucket(Bucket='research-test-assets',CreateBucketConfiguration={'LocationConstraint':'ap-south-1'})
def make(kind,**data):return catalog.mutate(kind,data,MANAGER)
def png(color):
    b=io.BytesIO();Image.new('RGB',(1,1),color).save(b,format='PNG');return b.getvalue()
def run():
    findings=[]
    with mock_aws():
        setup();s3=boto3.client('s3');key='uploads/reporter/header-only';fake=b'\x89PNG\r\n\x1a\nnot-a-real-image'
        s3.put_object(Bucket=os.environ['ASSETS_BUCKET'],Key=key,Body=fake,ContentType='image/png')
        accepted=api.file_metadata([{'key':key,'name':'header.png','type':'image/png'}],REPORTER,'before')
        try:Image.open(io.BytesIO(fake)).verify();decoded=True
        except Exception:decoded=False
        findings.append({'id':'R01','finding':'Image header spoof accepted','metadataAccepted':bool(accepted),'imageDecoderAccepted':decoded})
        s3.put_bucket_versioning(Bucket=os.environ['ASSETS_BUCKET'],VersioningConfiguration={'Status':'Enabled'})
        key='uploads/reporter/replay';red=png('red');blue=png('blue')
        s3.put_object(Bucket=os.environ['ASSETS_BUCKET'],Key=key,Body=red,ContentType='image/png')
        committed=api.file_metadata([{'key':key,'name':'evidence.png','type':'image/png'}],REPORTER,'before')[0]
        s3.put_object(Bucket=os.environ['ASSETS_BUCKET'],Key=key,Body=blue,ContentType='image/png')
        latest=s3.get_object(Bucket=os.environ['ASSETS_BUCKET'],Key=key)['Body'].read()
        findings.append({'id':'R02','finding':'Evidence not pinned to reviewed S3 version','committedMetadata':committed,'reviewedHash':hashlib.sha256(red).hexdigest(),'servedLatestHash':hashlib.sha256(latest).hexdigest()})
    with mock_aws():
        setup();meter=make('meters',name='Temperature',assetId='M-012',unit='C',maxValue=80);make('automations',name='High temperature',meterId=meter['id'],enabled=True)
        out=[]
        for n in range(3):out.append(catalog.readings(meter['id'],{'value':90+n},WORKER,{'headers':{'Idempotency-Key':f'probe-{n}'}},True)['workOrderId'])
        findings.append({'id':'R03','finding':'Distinct high readings create repeated active requests','readingCount':3,'distinctWorkOrders':len(set(out)),'duplicateFlags':[w['possibleDuplicate'] for w in storage.list_jobs()]})
    with mock_aws():
        setup();data={'machineId':'M-012','title':'Oil leak','description':'Same observed leak','category':'Hydraulic'}
        first=api.create(data,REPORTER,{'headers':{'idempotency-key':'first'}})
        with patch.object(storage,'list_jobs',return_value=[]):second=api.create(data,REPORTER,{'headers':{'idempotency-key':'second'}})
        findings.append({'id':'R04','finding':'Duplicate advisory misses a lagged GSI','firstExists':bool(storage.get_job(first['id'])),'secondPossibleDuplicate':second['possibleDuplicate'],'actualWorkOrders':len(storage.list_jobs())})
    with mock_aws():
        setup();body={'name':'Supplier timeout replay'};a=make('vendors',**body);b=make('vendors',**body)
        findings.append({'id':'R05','finding':'Catalog create has no logical request idempotency','samePayload':True,'differentIds':a['id']!=b['id'],'vendorCount':len(catalog.records('vendors'))})
        p=make('parts',name='Bearing',sku='BR-01',quantity=3,unit='pieces');p=catalog.adjust(p['id'],{'version':1,'delta':-1,'reason':'Issued'},MANAGER);p=catalog.mutate('parts',{'version':p['version'],'unit':'litres'},MANAGER,p['id'])
        other=make('parts',name='Second bearing record',sku='BR-01',quantity=1)
        findings.append({'id':'R06','finding':'Part unit can change after stock history; duplicate SKU allowed','updatedUnit':p['unit'],'balance':int(p['quantity']),'sameSkuRecords':sum(x['sku']=='BR-01' for x in catalog.records('parts'))})
    with mock_aws():
        setup();template=make('inspection_templates',name='Safety',assetId='M-012',questions=['Old question?']);response=catalog.mutate('inspection_responses',{'templateId':template['id'],'assetId':'M-012','answers':[{'question':'Old question?','answer':'pass'}]},WORKER)
        archived=catalog.archive('inspection_responses',response['id'],{'version':1,'archived':True},MANAGER);catalog.mutate('inspection_templates',{'version':1,'questions':['New question?']},MANAGER,template['id'])
        try:catalog.archive('inspection_responses',response['id'],{'version':archived['version'],'archived':False},MANAGER);restore='restored'
        except RuleError as exc:restore={'status':exc.status,'message':str(exc)}
        findings.append({'id':'R07','finding':'Historical inspection restore depends on current template questions','restoreResult':restore})
    with mock_aws():
        setup();future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat().replace('+00:00','Z');plans=[]
        for n in range(21):
            p=make('plans',name=f'Plan {n}',assetId='M-012',description='Inspect',intervalDays=7,nextRun=future,enabled=True);stored=catalog.get('plans',p['id']);stored['nextRun']=f'2025-01-{n+1:02}T00:00:00Z'
            if n<20:stored['assetId']='fault-injected-missing-asset'
            storage.table().put_item(Item=stored);plans.append(stored)
        first=planning.handler({},None);second=planning.handler({},None)
        findings.append({'id':'R08','finding':'Poison-plan starvation under injected corrupted legacy references','faultInjection':True,'first':first,'second':second,'validPlanId':plans[-1]['id'],'validPlanWorkCreated':any(w.get('planId')==plans[-1]['id'] for w in storage.list_jobs())})
    with mock_aws():
        setup();s3=boto3.client('s3');image=png('red')
        base={'machineId':'M-012','title':'Photo retry','description':'Same report and image'}
        def attachment(suffix):
            key='uploads/reporter/'+suffix;s3.put_object(Bucket=os.environ['ASSETS_BUCKET'],Key=key,Body=image,ContentType='image/png')
            return {'key':key,'name':'photo.png','type':'image/png','size':len(image)}
        first=api.create({**base,'attachments':[attachment('attempt1')]},REPORTER,{'headers':{'idempotency-key':'same-report'}})
        try:api.create({**base,'attachments':[attachment('attempt2')]},REPORTER,{'headers':{'idempotency-key':'same-report'}});retry='succeeded'
        except RuleError as exc:retry={'status':exc.status,'message':str(exc)}
        findings.append({'id':'R09','finding':'Photo reupload changes report payload on response-loss retry','firstCommitted':bool(storage.get_job(first['id'])),'sameImageBytes':True,'retryResult':retry,'workOrders':len(storage.list_jobs())})
    return findings
if __name__=='__main__':
    result={'mode':'isolated moto only; no live mutations','observations':run()};path=Path('docs/research/2026-11-14-edgecase-probe-results.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
