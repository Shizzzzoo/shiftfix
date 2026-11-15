"""Authenticated ShiftFix HTTP API. No credentials or request payloads are logged."""
import base64
import hashlib
import json
import os
import uuid
import time
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from . import storage, catalog, demo, clients
from .domain import MACHINES, TERMINAL, RuleError, now, text, transition, visible, canonical_role, manages

TYPES={'image/jpeg','image/png','image/webp'}


def s3_client():
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION', 'ap-south-1')
    return boto3.client('s3', region_name=region, endpoint_url=f'https://s3.{region}.amazonaws.com', config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'}))


def public(item, user=None):
    hidden = set() if user and manages(user) else {'relatedResolvedIds'}
    return {k:v for k,v in item.items() if k not in hidden and k not in {'PK','SK','GSI1PK','GSI1SK','requestHash'}}


def user_from(event):
    claims=event.get('requestContext',{}).get('authorizer',{}).get('jwt',{}).get('claims',{})
    if not claims.get('sub') or str(claims.get('email_verified')).lower()!='true':
        raise RuleError('Sign in with a verified email address',401)
    groups=claims.get('cognito:groups',[])
    if isinstance(groups,str):
        # API Gateway serializes array claims as bracketed comma-separated strings.
        try: groups=json.loads(groups)
        except ValueError: groups=[x.strip(' \"') for x in groups.strip('[]').split(',')]
    role=role_from_groups(groups, claims.get('email',''), True)
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
        if not isinstance(typ,str) or typ not in TYPES: raise RuleError('Only JPEG, PNG and WebP photos are supported')
        try: info=s3.head_object(Bucket=os.environ['ASSETS_BUCKET'],Key=key)
        except ClientError as exc:
            if exc.response['Error']['Code'] in {'404','NoSuchKey','NotFound'}: raise RuleError('Photo upload is incomplete') from exc
            raise
        if not 0<info['ContentLength']<=5*1024*1024 or info.get('ContentType')!=typ:
            raise RuleError('Invalid photo size or content type')
        prefix=s3.get_object(Bucket=os.environ['ASSETS_BUCKET'],Key=key,Range='bytes=0-15')['Body'].read()
        valid=(typ=='image/jpeg' and prefix.startswith(b'\xff\xd8\xff')) or (typ=='image/png' and prefix.startswith(b'\x89PNG\r\n\x1a\n')) or (typ=='image/webp' and prefix.startswith(b'RIFF') and prefix[8:12]==b'WEBP')
        if not valid: raise RuleError('Photo content does not match a supported image format')
        out.append({'key':key,'name':text(f.get('name'),'Photo name',200),'type':typ,'size':info['ContentLength'],'stage':stage})
    return out


def signed(job,user=None):
    result=public(job,user)
    s3=s3_client()
    result['attachments']=[dict(a,url=s3.generate_presigned_url('get_object',Params={'Bucket':os.environ['ASSETS_BUCKET'],'Key':a['key']},ExpiresIn=900)) for a in job.get('attachments',[])]
    return result


def find_user(id):
    if isinstance(id,str) and id.startswith('demo-person-'):raise RuleError('Demo people are display-only and cannot sign in, receive assignments or have access roles changed',403)
    client=clients.client('cognito-idp',clients.region())
    pages=client.get_paginator('list_users').paginate(UserPoolId=os.environ['USER_POOL_ID'],Filter='sub = "'+text(id,'Worker ID',128)+'"')
    users=[u for p in pages for u in p['Users']]
    if not users: raise RuleError('Worker not found')
    u = users[0]
    attrs = {a['Name']: a['Value'] for a in u['Attributes']}
    if u.get('UserStatus') != 'CONFIRMED' or attrs.get('email_verified') != 'true' or not u.get('Enabled', True):
        raise RuleError('The user must verify their email before receiving a role or assignment')
    return u


def role_from_groups(groups, email='', verified=False):
    if verified and email and email.lower()==os.environ.get('SUPERVISOR_EMAIL','').lower(): return 'admin'
    roles={canonical_role(g) for g in groups}
    return next((r for r in ['admin','manager','worker'] if r in roles),'reporter')


def role_for(user):
    groups=clients.client('cognito-idp',clients.region()).admin_list_groups_for_user(UserPoolId=os.environ['USER_POOL_ID'],Username=user['Username'])['Groups']
    attrs={a['Name']:a['Value'] for a in user.get('Attributes',[])}
    return role_from_groups([g['GroupName'] for g in groups],attrs.get('email',''),attrs.get('email_verified')=='true')


def profile_for(user):
    item=storage.table().get_item(Key={'PK':'USER#'+user['id'],'SK':'PROFILE'},ConsistentRead=True).get('Item')
    return {k:item[k] for k in ['displayName','department','machineIds','jobTitle','phone','shift','bio','version'] if k in item} if item else None


def me(user):
    profile=profile_for(user)
    return dict(user,role=canonical_role(user['role']),name=profile['displayName'] if profile else user['name'],onboardingComplete=bool(profile),profile=profile,demoDataset=demo.manifest())


def onboard(data,user):
    if set(data)!={'displayName','department','machineIds'}: raise RuleError('Provide only displayName, department and machineIds')
    name=text(data.get('displayName'),'Display name',100)
    if len(name)<2: raise RuleError('Display name must contain at least two characters')
    department=data.get('department')
    if not isinstance(department,str) or department not in {'production','maintenance','engineering','quality','operations','other'}: raise RuleError('Choose a valid department')
    ids=data.get('machineIds')
    if not isinstance(ids,list) or len(ids)>4 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids) or any(i not in {m['id'] for m in catalog.machines()} for i in ids): raise RuleError('Choose up to four distinct registered machines')
    old=storage.table().get_item(Key={'PK':'USER#'+user['id'],'SK':'PROFILE'},ConsistentRead=True).get('Item')
    if old:
        if all(old.get(k)==v for k,v in {'displayName':name,'department':department,'machineIds':ids}.items()):return me(user)
        raise RuleError('Your profile is already set up. Use My profile to update it.',409)
    try:
        storage.table().put_item(Item={'PK':'USER#'+user['id'],'SK':'PROFILE','displayName':name,'department':department,'machineIds':ids,'updatedAt':now()},ConditionExpression='attribute_not_exists(PK)')
    except ClientError as exc:
        if exc.response['Error']['Code']=='ConditionalCheckFailedException': raise RuleError('Your profile was set up in another session. Refresh the workspace.',409) from exc
        raise
    return me(user)


def update_profile(data,user):
    required={'displayName','department','machineIds','version'}
    if not required <= set(data) or set(data)-required-{'jobTitle','phone','shift','bio'}:
        raise RuleError('Provide profile details and version only. Access roles and email cannot be changed here.')
    version=data['version']
    if isinstance(version,bool) or not isinstance(version,int) or version<0: raise RuleError('Provide the current profile version')
    old=storage.table().get_item(Key={'PK':'USER#'+user['id'],'SK':'PROFILE'},ConsistentRead=True).get('Item')
    if not old: raise RuleError('Complete first-time setup before editing your profile',409)
    name=text(data['displayName'],'Display name',100)
    if len(name)<2: raise RuleError('Display name must contain at least two characters')
    department=data['department']
    if not isinstance(department,str) or department not in {'production','maintenance','engineering','quality','operations','other'}: raise RuleError('Choose a valid department')
    ids=data['machineIds']
    allowed={m['id'] for m in catalog.machines()}
    if not isinstance(ids,list) or len(ids)>4 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids) or any(i not in allowed for i in ids): raise RuleError('Choose up to four distinct registered machines')
    shift=data.get('shift','unspecified')
    if not isinstance(shift,str) or shift not in {'unspecified','day','evening','night','rotating','flexible'}: raise RuleError('Choose a valid shift')
    cleaned={'displayName':name,'department':department,'machineIds':ids,'shift':shift,
             'jobTitle':text(data.get('jobTitle',''),'Job title',100,False),
             'phone':text(data.get('phone',''),'Contact phone',40,False),
             'bio':text(data.get('bio',''),'About you',600,False),'version':version+1,'updatedAt':now()}
    try:
        storage.table().put_item(Item={**old,**cleaned},
            ConditionExpression='attribute_exists(PK) AND '+('attribute_not_exists(#v)' if version==0 else '#v = :v'),
            ExpressionAttributeNames={'#v':'version'},**({'ExpressionAttributeValues':{':v':version}} if version else {}))
    except ClientError as exc:
        if exc.response['Error']['Code']=='ConditionalCheckFailedException':raise RuleError('Your profile changed in another session. Reload it before saving again.',409) from exc
        raise
    return me(user)


def set_role(target_id,role,user):
    caller=canonical_role(user['role'])
    if caller not in {'admin','manager'}: raise RuleError('Manager access required',403)
    if not isinstance(role,str) or role not in {'manager','worker','reporter'}: raise RuleError('Choose manager, worker or reporter')
    target=find_user(target_id)
    existing=role_for(target)
    if existing=='admin': raise RuleError('The administrator role cannot be changed',403)
    if caller=='manager' and (role=='manager' or existing=='manager'): raise RuleError('Only an administrator can manage managers',403)
    client=clients.client('cognito-idp',clients.region()); args={'UserPoolId':os.environ['USER_POOL_ID'],'Username':target['Username']}
    # Remove canonical and legacy memberships before granting the new role.
    memberships=client.admin_list_groups_for_user(**args)['Groups']
    for group in memberships:
        if group['GroupName'] in {'manager','worker','reporter','supervisor','technician','operator'}:
            client.admin_remove_user_from_group(**args,GroupName=group['GroupName'])
    client.admin_add_user_to_group(**args,GroupName=role)
    return {'id':target_id,'role':role}


def handler(event,context):
    started=time.perf_counter()
    try:
        user=user_from(event)
        current=find_user(user['id'])
        user['role']=role_for(current)
        profile=profile_for(user)
        if profile: user['name']=profile['displayName']
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
        if getattr(exc,'code',None):result['code']=exc.code
        if getattr(exc,'diagnostic',None) and user.get('role')=='admin':result['diagnostic']=exc.diagnostic
    except ClientError as exc:
        # Only operational codes, never request data, tokens, or AWS response bodies.
        print(json.dumps({'awsError':exc.response['Error']['Code']}))
        status=503; result={'message':'Service temporarily unavailable. Please retry.'}
    except Exception as exc:
        print(json.dumps({'errorType':type(exc).__name__}))
        status=500; result={'message':'Something went wrong. Please retry.'}
    response_body=json.dumps(result,default=lambda x:int(x) if isinstance(x,Decimal) and x%1==0 else float(x) if isinstance(x,Decimal) else str(x))
    elapsed=round((time.perf_counter()-started)*1000,1)
    return {'statusCode':status,'headers':{'Content-Type':'application/json','Cache-Control':'no-store','Server-Timing':f'app;dur={elapsed}'},'body':response_body}



def route(method,path,data,user,event):
    user=dict(user,role=canonical_role(user['role']))
    if path.startswith('/assistant/'):
        from . import assistant
        return assistant.route(method,path,data,user)
    if method=='GET' and path=='/me': return me(user)
    if method=='POST' and path=='/onboarding': return onboard(data,user)
    if method=='POST' and path=='/profile': return update_profile(data,user)
    if path=='/catalog' or path.startswith('/catalog/') or path=='/settings/workflow':return catalog.route(method,path,data,user,event)
    if method=='GET' and path=='/machines': return {'items':catalog.machines()}
    if method=='GET' and path=='/workorders':
        return {'items':[public(j,user) for j in storage.list_jobs() if visible(j,user)]}
    if method=='POST' and path=='/uploads':
        files=data.get('files',[])
        if not isinstance(files,list) or not 1<=len(files)<=5: raise RuleError('Choose one to five photos')
        validated=[]
        for f in files:
            if not isinstance(f,dict): raise RuleError('Invalid photo metadata')
            typ=f.get('type'); size=f.get('size')
            if not isinstance(typ,str) or typ not in TYPES or isinstance(size,bool) or not isinstance(size,int) or not 0<size<=5*1024*1024: raise RuleError('Each photo must be JPEG, PNG or WebP and at most 5 MiB')
            validated.append((typ,size,text(f.get('name'),'Photo name',200)))
        if sum(f[1] for f in validated)>25*1024*1024: raise RuleError('Total photos must not exceed 25 MiB')
        result=[]; s3=s3_client()
        for typ,size,name in validated:
            key='uploads/'+user['id']+'/'+str(uuid.uuid4())
            presign=s3.generate_presigned_post(Bucket=os.environ['ASSETS_BUCKET'],Key=key,Fields={'Content-Type':typ},Conditions=[{'Content-Type':typ},['content-length-range',1,5*1024*1024]],ExpiresIn=300)
            result.append({'key':key,'name':name,'type':typ,'size':size,**presign})
        return {'items':result}
    if path=='/users' and method=='GET':
        if not manages(user): raise RuleError('Manager access required',403)
        client=clients.client('cognito-idp',clients.region()); items=[]
        for page in client.get_paginator('list_users').paginate(UserPoolId=os.environ['USER_POOL_ID']):
            for u in page['Users']:
                a={v['Name']:v['Value'] for v in u['Attributes']}
                profile=profile_for({'id':a['sub']})
                items.append({'id':a['sub'],'email':a.get('email',''),'name':profile['displayName'] if profile else a.get('name') or a.get('email','User'),'role':role_for(u),'department':(profile or {}).get('department',''),'jobTitle':(profile or {}).get('jobTitle',''),'shift':(profile or {}).get('shift',''),'emailVerified':a.get('email_verified')=='true','enabled':u.get('Enabled',True)})
        return {'items':items+demo.people()}
    parts=path.strip('/').split('/')
    if len(parts)==3 and parts[0]=='users' and parts[2]=='role' and method=='POST':
        if not manages(user): raise RuleError('Manager access required',403)
        return set_role(parts[1],data.get('role'),user)
    if path=='/workorders' and method=='POST': return create(data,user,event)
    if parts[0]=='workorders' and len(parts)>=2:
        job=storage.get_job(parts[1])
        if not visible(job,user): raise RuleError('You cannot access this work order',403)
        if method=='GET' and len(parts)==2:
            out=signed(job,user); out['activity']=[public(a) for a in storage.events(job['id'])]
            if manages(user):
                out['resolvedCandidates']=[public(j,user) for j in storage.list_jobs() if j['id'] in job.get('relatedResolvedIds',[]) and visible(j,user)]
            if job.get('mergedInto'): out['mergedInto']=job['mergedInto']
            # Linked reports retain their own evidence and authors; don't copy or lose provenance.
            out['linkedReports']=[public(j) for j in storage.list_jobs() if j.get('mergedInto')==job['id'] and visible(j,user)]
            return out
        if method=='POST' and len(parts)==3 and parts[2]=='actions':
            if data.get('action') in {'approve','reassign'}:
                if not manages(user): raise RuleError('Manager access required',403)
                assigned=find_user(data.get('assigneeId',''))
                if role_for(assigned)!='worker': raise RuleError('Assign a user with worker access')
                attrs={a['Name']:a['Value'] for a in assigned['Attributes']}
                assigned_profile=profile_for({'id':attrs['sub']})
                data['assigneeName']=assigned_profile['displayName'] if assigned_profile else attrs.get('name') or attrs.get('email','Worker')
            if data.get('attachments'):
                if data.get('action')!='submit': raise RuleError('Photos can only be added with repair submission')
                data['attachments']=file_metadata(data['attachments'],user,'after')
            target=None
            if data.get('action')=='merge':
                target=storage.get_job(text(data.get('targetId'),'Target work order',128))
                if target['status'] in TERMINAL or target['machineId']!=job['machineId']: raise RuleError('Merge into an active work order for the same machine')
            updated,reason=transition(job,user,data,policy=catalog.workflow())
            extra=[]
            if target:
                # Lock target too: merging into a concurrently closed job must not succeed.
                extra.append({'ConditionCheck':{'TableName':os.environ['TABLE_NAME'],'Key':storage.encode({'PK':target['PK'],'SK':'META'}),'ConditionExpression':'#v = :v','ExpressionAttributeNames':{'#v':'version'},'ExpressionAttributeValues':{':v':storage.SER.serialize(target['version'])}}})
                extra.append({'Put':{'TableName':os.environ['TABLE_NAME'],'Item':storage.encode(storage.activity(dict(target,updatedAt=now()),user,'report_merged',job['number']+': '+reason))}})
            storage.write(updated,user,data['action'],reason,old=job,extra=extra)
            return signed(updated,user)
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
        return signed(previous,user)
    except RuleError as exc:
        if exc.status!=404: raise
    expected_revision=catalog.revision()
    machine=next((m for m in catalog.machines() if m['id']==data.get('machineId')),None)
    if not machine: raise RuleError('Choose a registered machine')
    priority=data.get('priority','medium')
    if not isinstance(priority,str) or priority not in {'low','medium','high','critical'}: raise RuleError('Invalid priority')
    category=text(data.get('category','General'),'Category',100)
    category_id=data.get('categoryId','')
    if category_id:category=catalog.get('categories',category_id)['name']
    at=now()
    related=data.get('relatedId','')
    if related:
        previous=storage.get_job(text(related,'Related work order',128))
        if not visible(previous,user) or previous['machineId']!=machine['id']: raise RuleError('Related work order must be visible and on this machine')
    all_jobs=storage.list_jobs()
    resolved=[j['id'] for j in all_jobs if j['machineId']==machine['id'] and j['category']==category and j['status']=='closed']
    job={**catalog.snapshot(machine),'archived':False,'possibleResolved':bool(resolved),'relatedResolvedIds':resolved,'PK':'WORK#'+id,'SK':'META','GSI1PK':'WORK','GSI1SK':at,'id':id,'number':'WO-'+id[:8].upper(),'machineId':machine['id'],'machineName':machine['name'],'title':text(data.get('title'),'Title',160),'description':text(data.get('description'),'Description',4000),'category':category,'priority':priority,'status':'pending_review','assignmentStatus':'unassigned','assigneeId':'','assigneeName':'','reporterId':user['id'],'reporterName':user['name'],'createdAt':at,'updatedAt':at,'version':1,'deadlineVersion':0,'deadline':'','deadlineKind':'','overdue':False,'blocked':False,'possibleDuplicate':any(j['machineId']==machine['id'] and j['category']==category and j['status'] not in TERMINAL for j in all_jobs),'attachments':file_metadata(data.get('attachments',[]),user,'before'),'relatedId':related,'requestHash':payload_hash}
    if user.get('_assistantDraftId'):job['createdVia']='assistant'
    if category_id:job['categoryId']=category_id
    try: storage.write(job,user,'reported','Created from a human-confirmed assistant draft.' if user.get('_assistantDraftId') else '',extra=[catalog.revision_guard(expected_revision),catalog.work_reference(job)])
    except RuleError as exc:
        if exc.status==409:
            try: previous=storage.get_job(id)
            except RuleError: raise exc
            if previous.get('requestHash')==payload_hash: return signed(previous,user)
        raise
    return signed(job,user)
