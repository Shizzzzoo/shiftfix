"""Transactional outbox dispatch and stale-safe deadline escalation."""
import os
import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError
from . import storage
from .domain import TERMINAL, RuleError, now


def stream_handler(event,context):
    failures=[]
    decode=TypeDeserializer()
    for record in event.get('Records',[]):
        if record.get('eventName')!='INSERT': continue
        item={k:decode.deserialize(v) for k,v in record['dynamodb'].get('NewImage',{}).items()}
        if not item.get('PK','').startswith('TIMER#'): continue
        try:
            import json
            payload={k:item[k] for k in ['workOrderId','deadlineVersion','deadline','kind']}
            boto3.client('stepfunctions').start_execution(stateMachineArn=os.environ['STATE_MACHINE_ARN'],name='timer-'+item['id'],input=json.dumps(payload,default=int))
        except ClientError as exc:
            if exc.response['Error']['Code']!='ExecutionAlreadyExists': failures.append({'itemIdentifier':record['dynamodb']['SequenceNumber']})
        except Exception:
            failures.append({'itemIdentifier':record['dynamodb']['SequenceNumber']})
    return {'batchItemFailures':failures}


def expire_handler(event,context):
    try: job=storage.get_job(event['workOrderId'])
    except RuleError as exc:
        if exc.status==404: return {'escalated':False,'reason':'missing'}
        raise
    if job['status'] in TERMINAL or not job.get('deadline') or int(job['deadlineVersion'])!=int(event['deadlineVersion']) or job['deadline']!=event['deadline'] or job.get('overdue'):
        return {'escalated':False,'reason':'stale_or_complete'}
    if now()<job['deadline']: return {'escalated':False,'reason':'not_due'}
    updated=dict(job,overdue=True,version=job['version']+1,updatedAt=now())
    try:
        storage.write(updated,{'id':'system','name':'ShiftFix automation'},'deadline_missed',job['deadlineKind']+' deadline missed',old=job)
    except RuleError as exc:
        if exc.status==409: raise RuntimeError('Concurrent update; retry deadline check') from exc
        raise
    return {'escalated':True}
