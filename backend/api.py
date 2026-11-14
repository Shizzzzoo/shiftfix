"""Authenticated ShiftFix HTTP API. No credentials or request payloads are logged."""
import base64
import hashlib
import json
import os
import uuid
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from . import storage
from .domain import MACHINES, TERMINAL, RuleError, now, text, transition, visible

TYPES={'image/jpeg','image/png','image/webp'}


def s3_client():
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION', 'ap-south-1')
    return boto3.client('s3', region_name=region, endpoint_url=f'https://s3.{region}.amazonaws.com', config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'}))


def public(item):
    return {k:v for k,v in item.items() if k not in {'PK','SK','GSI1PK','GSI1SK','requestHash'}}


def user_from(event):
    claims=event.get('requestContext',{}).get('authorizer',{}).get('jwt',{}).get('claims',{})
    if not claims.get('sub') or str(claims.get('email_verified')).lower()!='true':
        raise RuleError('Sign in with a verified email address',401)
    groups=claims.get('cognito:groups',[])
    if isinstance(groups,str):
        # API Gateway serializes array claims as bracketed comma-separated strings.
        try: groups=json.loads(groups)
        except ValueError: groups=[x.strip(' \"') for x in groups.strip('[]').split(',')]
    role=next((r for r in ['supervisor','technician'] if r in groups),'operator')
    return {'id':claims['sub'],'email':claims.get('email',''),'name':claims.get('name') or claims.get('email','User'),'role':role}


def file_metadata(files,user,stage):
    if not isinstance(files,list) or len(files)>5: raise RuleError('Attach at most five photos per update')
    out=[]
    s3=s3_client()
    for f in files:
        if not isinstance(f,dict): raise RuleError('Invalid attachment')
        key=f.get('key','')
        if not isinstance(key,str) or not key.startswith('uploads/'+user['id']+'/') or '..' in key:
            raise RuleError('Attachment does not belong to your upload',403)
        typ=f.get('type')
        if typ not in TYPES: raise RuleError('Only JPEG, PNG and WebP photos are supported')
        try: info=s3.head_object(Bucket=os.environ['ASSETS_BUCKET'],Key=key)
        except ClientError as exc:
            if exc.response['Error']['Code'] in {'404','NoSuchKey','NotFound'}: raise RuleError('Photo upload is incomplete') from exc
            raise
        if not 0<info['ContentLength']<=5*1024*1024 or info.get('ContentType')!=typ:
            raise RuleError('Invalid photo size or content type')
        out.append({'key':key,'name':text(f.get('name'),'Photo name',200),'type':typ,'size':info['ContentLength'],'stage':stage})
    return out


def signed(job):
    result=public(job)
    s3=s3_client()
    result['attachments']=[dict(a,url=s3.generate_presigned_url('get_object',Params={'Bucket':os.environ['ASSETS_BUCKET'],'Key':a['key']},ExpiresIn=900)) for a in job.get('attachments',[])]
    return result


def find_user(id):
    client=boto3.client('cognito-idp')
    pages=client.get_paginator('list_users').paginate(UserPoolId=os.environ['USER_POOL_ID'],Filter='sub = "'+text(id,'Technician ID',128)+'"')
    users=[u for p in pages for u in p['Users']]
    if not users: raise RuleError('Technician not found')
    u = users[0]
    attrs = {a['Name']: a['Value'] for a in u['Attributes']}
    if u.get('UserStatus') != 'CONFIRMED' or attrs.get('email_verified') != 'true' or not u.get('Enabled', True):
        raise RuleError('The user must verify their email before receiving a role or assignment')
    return u


def role_for(user):
    groups=boto3.client('cognito-idp').admin_list_groups_for_user(UserPoolId=os.environ['USER_POOL_ID'],Username=user['Username'])['Groups']
    names={g['GroupName'] for g in groups}
    return next((r for r in ['supervisor','technician'] if r in names),'operator')


def handler(event,context):
    try:
        user=user_from(event)
        method=event['requestContext']['http']['method']
        path=event.get('rawPath','').rstrip('/')
        body=event.get('body') or '{}'
        if event.get('isBase64Encoded'): body=base64.b64decode(body).decode()
        if len(body)>65536: raise RuleError('Request too large',413)
        try: data=json.loads(body)
        except (ValueError,UnicodeDecodeError) as exc: raise RuleError('Invalid JSON') from exc
        if not isinstance(data,dict): raise RuleError('Request must be an object')
        result=route(method,path,data,user,event)
        status=200
    except RuleError as exc:
        status=exc.status; result={'message':str(exc)}
    except ClientError as exc:
        # Only operational codes, never request data, tokens, or AWS response bodies.
        print(json.dumps({'awsError':exc.response['Error']['Code']}))
        status=503; result={'message':'Service temporarily unavailable. Please retry.'}
    except Exception as exc:
        print(json.dumps({'errorType':type(exc).__name__}))
        status=500; result={'message':'Something went wrong. Please retry.'}
    return {'statusCode':status,'headers':{'Content-Type':'application/json','Cache-Control':'no-store'},'body':json.dumps(result,default=lambda x:int(x) if isinstance(x,Decimal) and x%1==0 else float(x) if isinstance(x,Decimal) else str(x))}


def route(method,path,data,user,event):
    if method=='GET' and path=='/me': return user
    if method=='GET' and path=='/machines': return {'items':MACHINES}
    if method=='GET' and path=='/workorders':
        return {'items':[public(j) for j in storage.list_jobs() if visible(j,user)]}
    if method=='POST' and path=='/uploads':
        files=data.get('files',[])
        if not isinstance(files,list) or not 1<=len(files)<=5: raise RuleError('Choose one to five photos')
        result=[]; s3=s3_client()
        for f in files:
            typ=f.get('type'); size=f.get('size')
            if typ not in TYPES or not isinstance(size,int) or not 0<size<=5*1024*1024: raise RuleError('Each photo must be JPEG, PNG or WebP and at most 5 MiB')
            name=text(f.get('name'),'Photo name',200)
            key='uploads/'+user['id']+'/'+str(uuid.uuid4())
            presign=s3.generate_presigned_post(Bucket=os.environ['ASSETS_BUCKET'],Key=key,Fields={'Content-Type':typ},Conditions=[{'Content-Type':typ},['content-length-range',1,5*1024*1024]],ExpiresIn=300)
            result.append({'key':key,'name':name,'type':typ,'size':size,**presign})
        return {'items':result}
    if path=='/users' and method=='GET':
        if user['role']!='supervisor': raise RuleError('Supervisor access required',403)
        client=boto3.client('cognito-idp'); items=[]
        for page in client.get_paginator('list_users').paginate(UserPoolId=os.environ['USER_POOL_ID']):
            for u in page['Users']:
                a={v['Name']:v['Value'] for v in u['Attributes']}
                items.append({'id':a['sub'],'email':a.get('email',''),'name':a.get('name') or a.get('email','User'),'role':role_for(u)})
        return {'items':items}
    parts=path.strip('/').split('/')
    if len(parts)==3 and parts[0]=='users' and parts[2]=='role' and method=='POST':
        if user['role']!='supervisor': raise RuleError('Supervisor access required',403)
        role=data.get('role')
        if role not in {'technician','operator'}: raise RuleError('Choose technician or operator')
        u=find_user(parts[1])
        if role_for(u)=='supervisor': raise RuleError('Cannot change supervisor role')
        client=boto3.client('cognito-idp')
        args={'UserPoolId':os.environ['USER_POOL_ID'],'Username':u['Username'],'GroupName':'technician'}
        if role=='technician': client.admin_add_user_to_group(**args)
        else: client.admin_remove_user_from_group(**args)
        return {'id':parts[1],'role':role}
    if path=='/workorders' and method=='POST': return create(data,user,event)
    if parts[0]=='workorders' and len(parts)>=2:
        job=storage.get_job(parts[1])
        if not visible(job,user): raise RuleError('You cannot access this work order',403)
        if method=='GET' and len(parts)==2:
            out=signed(job); out['activity']=[public(a) for a in storage.events(job['id'])]
            if job.get('mergedInto'): out['mergedInto']=job['mergedInto']
            # Linked reports retain their own evidence and authors; don't copy or lose provenance.
            out['linkedReports']=[public(j) for j in storage.list_jobs() if j.get('mergedInto')==job['id'] and visible(j,user)]
            return out
        if method=='POST' and len(parts)==3 and parts[2]=='actions':
            if data.get('action') in {'approve','reassign'}:
                if user['role']!='supervisor': raise RuleError('Supervisor access required',403)
                assigned=find_user(data.get('assigneeId',''))
                if role_for(assigned)!='technician': raise RuleError('Assign a user with technician access')
                attrs={a['Name']:a['Value'] for a in assigned['Attributes']}
                data['assigneeName']=attrs.get('name') or attrs.get('email','Technician')
            if data.get('attachments'):
                if data.get('action')!='submit': raise RuleError('Photos can only be added with repair submission')
                data['attachments']=file_metadata(data['attachments'],user,'after')
            target=None
            if data.get('action')=='merge':
                target=storage.get_job(text(data.get('targetId'),'Target work order',128))
                if target['status'] in TERMINAL or target['machineId']!=job['machineId']: raise RuleError('Merge into an active work order for the same machine')
            updated,reason=transition(job,user,data)
            extra=[]
            if target:
                # Lock target too: merging into a concurrently closed job must not succeed.
                extra.append({'ConditionCheck':{'TableName':os.environ['TABLE_NAME'],'Key':storage.encode({'PK':target['PK'],'SK':'META'}),'ConditionExpression':'#v = :v','ExpressionAttributeNames':{'#v':'version'},'ExpressionAttributeValues':{':v':storage.SER.serialize(target['version'])}}})
                extra.append({'Put':{'TableName':os.environ['TABLE_NAME'],'Item':storage.encode(storage.activity(dict(target,updatedAt=now()),user,'report_merged',job['number']+': '+reason))}})
            storage.write(updated,user,data['action'],reason,old=job,extra=extra)
            return signed(updated)
    raise RuleError('Endpoint not found',404)


def create(data,user,event):
    key=event.get('headers',{}).get('idempotency-key') or event.get('headers',{}).get('Idempotency-Key')
    key=text(key,'Idempotency-Key',128)
    digest=hashlib.sha256((user['id']+':'+key).encode()).hexdigest()
    id=str(uuid.UUID(digest[:32]))
    payload_hash=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    try:
        previous=storage.get_job(id)
        if previous.get('requestHash')!=payload_hash: raise RuleError('Idempotency key already used for a different report',409)
        return signed(previous)
    except RuleError as exc:
        if exc.status!=404: raise
    machine=next((m for m in MACHINES if m['id']==data.get('machineId')),None)
    if not machine: raise RuleError('Choose a registered machine')
    priority=data.get('priority','medium')
    if priority not in {'low','medium','high','critical'}: raise RuleError('Invalid priority')
    category=text(data.get('category','General'),'Category',100)
    at=now()
    related=data.get('relatedId','')
    if related:
        previous=storage.get_job(text(related,'Related work order',128))
        if not visible(previous,user) or previous['machineId']!=machine['id']: raise RuleError('Related work order must be visible and on this machine')
    job={'PK':'WORK#'+id,'SK':'META','GSI1PK':'WORK','GSI1SK':at,'id':id,'number':'WO-'+id[:8].upper(),'machineId':machine['id'],'machineName':machine['name'],'title':text(data.get('title'),'Title',160),'description':text(data.get('description'),'Description',4000),'category':category,'priority':priority,'status':'pending_review','assignmentStatus':'unassigned','assigneeId':'','assigneeName':'','reporterId':user['id'],'reporterName':user['name'],'createdAt':at,'updatedAt':at,'version':1,'deadlineVersion':0,'deadline':'','deadlineKind':'','overdue':False,'blocked':False,'possibleDuplicate':any(j['machineId']==machine['id'] and j['category']==category and j['status'] not in TERMINAL for j in storage.list_jobs()),'attachments':file_metadata(data.get('attachments',[]),user,'before'),'relatedId':related,'requestHash':payload_hash}
    try: storage.write(job,user,'reported')
    except RuleError as exc:
        if exc.status==409:
            previous=storage.get_job(id)
            if previous.get('requestHash')==payload_hash: return signed(previous)
        raise
    return signed(job)
