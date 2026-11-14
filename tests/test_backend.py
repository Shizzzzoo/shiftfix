import json
import pytest
import boto3
from moto import mock_aws
from backend import api, storage, deadlines
from backend.domain import RuleError

@pytest.fixture
def aws(monkeypatch):
    monkeypatch.setenv('AWS_DEFAULT_REGION','ap-south-1')
    monkeypatch.setenv('TABLE_NAME','shiftfix-test')
    monkeypatch.setenv('ASSETS_BUCKET','shiftfix-test-assets')
    with mock_aws():
        boto3.client('dynamodb').create_table(TableName='shiftfix-test',BillingMode='PAY_PER_REQUEST',KeySchema=[{'AttributeName':'PK','KeyType':'HASH'},{'AttributeName':'SK','KeyType':'RANGE'}],AttributeDefinitions=[{'AttributeName':'PK','AttributeType':'S'},{'AttributeName':'SK','AttributeType':'S'},{'AttributeName':'GSI1PK','AttributeType':'S'},{'AttributeName':'GSI1SK','AttributeType':'S'}],GlobalSecondaryIndexes=[{'IndexName':'GSI1','KeySchema':[{'AttributeName':'GSI1PK','KeyType':'HASH'},{'AttributeName':'GSI1SK','KeyType':'RANGE'}],'Projection':{'ProjectionType':'ALL'}}])
        boto3.client('s3').create_bucket(Bucket='shiftfix-test-assets',CreateBucketConfiguration={'LocationConstraint':'ap-south-1'})
        yield

USER={'id':'r','name':'Reporter','role':'operator'}

def create(key='a',**kw):
    return api.create({'machineId':'M-012','title':'Oil leak','description':'Oil below press','priority':'high',**kw},USER,{'headers':{'idempotency-key':key}})

def test_create_retry_is_one_job_and_one_event(aws):
    first=create(); second=create()
    assert first['id']==second['id']
    assert len(storage.list_jobs())==1 and len(storage.events(first['id']))==1

def test_idempotency_key_cannot_change_payload(aws):
    create()
    with pytest.raises(RuleError) as e: create(description='Different fault')
    assert e.value.status==409

def test_separate_fault_not_auto_merged(aws):
    create(category='Leak'); second=create('b',category='Leak')
    assert second['possibleDuplicate'] and second['status']=='pending_review'
    assert len(storage.list_jobs())==2

def test_write_conflict_does_not_append_activity(aws):
    j=storage.get_job(create()['id'])
    changed=dict(j,version=2)
    storage.write(changed,USER,'add_note','updated',old=j)
    with pytest.raises(RuleError): storage.write(changed,USER,'add_note','stale',old=j)
    assert len(storage.events(j['id']))==2

def test_stale_deadline_does_not_escalate(aws):
    j=storage.get_job(create()['id'])
    out=deadlines.expire_handler({'workOrderId':j['id'],'deadlineVersion':0,'deadline':'2000-01-01T00:00:00Z'},None)
    assert not out['escalated']
    assert not storage.get_job(j['id'])['overdue']

def test_due_deadline_escalates_once(aws):
    j=storage.get_job(create()['id'])
    j.update(deadline='2000-01-01T00:00:00Z',deadlineKind='repair',deadlineVersion=1)
    storage.table().put_item(Item=j)
    payload={'workOrderId':j['id'],'deadlineVersion':1,'deadline':j['deadline']}
    assert deadlines.expire_handler(payload,None)['escalated']
    assert not deadlines.expire_handler(payload,None)['escalated']
    assert len(storage.events(j['id']))==2

def test_upload_rejects_foreign_prefix(aws):
    with pytest.raises(RuleError) as e: api.file_metadata([{'key':'uploads/other/file','type':'image/jpeg'}],USER,'before')
    assert e.value.status==403

def test_auth_rejects_unverified_and_reads_group(aws):
    claims={'sub':'s','email_verified':'true','cognito:groups':'[supervisor]'}
    event={'requestContext':{'authorizer':{'jwt':{'claims':claims}}}}
    assert api.user_from(event)['role']=='manager'
    claims['email_verified']='false'
    with pytest.raises(RuleError): api.user_from(event)


def test_upload_uses_regional_signature_v4_endpoint(aws):
    out=api.route('POST','/uploads',{'files':[{'name':'fault.jpg','type':'image/jpeg','size':10}]},USER,{})
    photo=out['items'][0]
    assert photo['url']=='https://shiftfix-test-assets.s3.ap-south-1.amazonaws.com/'
    assert photo['fields']['x-amz-algorithm']=='AWS4-HMAC-SHA256'
    assert '/ap-south-1/s3/aws4_request' in photo['fields']['x-amz-credential']
