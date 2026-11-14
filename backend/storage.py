"""DynamoDB persistence: condition every mutation and append its activity atomically."""
import os
import uuid
import boto3
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError
from .domain import RuleError

SER = TypeSerializer()

def encode(item):
    return {k: SER.serialize(v) for k, v in item.items()}

def table():
    return boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])

def get_job(id):
    job = table().get_item(Key={'PK': 'WORK#' + id, 'SK': 'META'}, ConsistentRead=True).get('Item')
    if not job:
        raise RuleError('Work order not found', 404)
    return job

def list_jobs():
    kwargs = {'IndexName': 'GSI1', 'KeyConditionExpression': 'GSI1PK = :p', 'ExpressionAttributeValues': {':p': 'WORK'}, 'ScanIndexForward': False}
    result = []
    while True:
        page = table().query(**kwargs)
        result.extend(page.get('Items', []))
        if not page.get('LastEvaluatedKey'):
            return result
        kwargs['ExclusiveStartKey'] = page['LastEvaluatedKey']

def events(id):
    kwargs = {'KeyConditionExpression': 'PK = :pk AND begins_with(SK, :event)', 'ExpressionAttributeValues': {':pk': 'WORK#' + id, ':event': 'EVENT#'}, 'ConsistentRead': True}
    result=[]
    while True:
        page=table().query(**kwargs)
        result.extend(page.get('Items', []))
        if not page.get('LastEvaluatedKey'): return result
        kwargs['ExclusiveStartKey']=page['LastEvaluatedKey']

def activity(job, user, action, reason):
    id = str(uuid.uuid4())
    return {'PK': job['PK'], 'SK': 'EVENT#' + job['updatedAt'] + '#' + id, 'id': id, 'at': job['updatedAt'], 'actorId': user['id'], 'actorName': user['name'], 'action': action, 'reason': reason}

def write(job, user, action, reason='', old=None, extra=None):
    name = os.environ['TABLE_NAME']
    put={'TableName': name, 'Item': encode(job), 'ConditionExpression': 'attribute_not_exists(PK)' if old is None else '#v = :v'}
    if old is not None:
        put.update(ExpressionAttributeNames={'#v': 'version'}, ExpressionAttributeValues={':v': SER.serialize(old['version'])})
    writes=[{'Put': put}, {'Put': {'TableName': name, 'Item': encode(activity(job,user,action,reason)), 'ConditionExpression': 'attribute_not_exists(PK)'}}]
    if job.get('deadline') and (old is None or job.get('deadlineVersion') != old.get('deadlineVersion')):
        timer_id=str(uuid.uuid4())
        timer={'PK': 'TIMER#'+timer_id,'SK':'META','id':timer_id,'workOrderId':job['id'],'deadlineVersion':job['deadlineVersion'],'deadline':job['deadline'],'kind':job['deadlineKind']}
        writes.append({'Put': {'TableName':name,'Item':encode(timer),'ConditionExpression':'attribute_not_exists(PK)'}})
    writes.extend(extra or [])
    try:
        boto3.client('dynamodb').transact_write_items(TransactItems=writes)
    except ClientError as exc:
        if exc.response['Error']['Code']=='TransactionCanceledException':
            raise RuleError('This work order changed. Refresh before acting.',409) from exc
        raise
