"""Typed operational catalog and atomic inventory/measurement transactions."""
import copy
import hashlib
import json
import math
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from . import storage
from .domain import MACHINES, RuleError, canonical_role, manages, now, text

SIMPLE={'asset_types','categories','locations','part_types'}
KINDS=SIMPLE|{'assets','zones','subzones','teams','vendors','part_locations','parts','purchases','meters','inspection_templates','inspection_responses','plans','automations','life_tracking'}
REPORTER_READ={'assets','asset_types','categories','locations','zones','subzones'}
WORKER_READ=KINDS-{'vendors','purchases'}
FIELDS={k:{'name','description'} for k in SIMPLE}
FIELDS.update({
'assets':{'name','code','typeId','categoryId','locationId','zoneId','subzoneId','teamId','serial','description'},
'zones':{'name','locationId','description'},'subzones':{'name','zoneId','description'},
'teams':{'name','memberIds','description'},'vendors':{'name','email','phone','description'},
'part_locations':{'name','locationId','description'},
'parts':{'name','sku','typeId','locationId','vendorId','quantity','minQuantity','unit'},
'purchases':{'name','partId','vendorId','quantity','unitCost','currency'},
'meters':{'name','assetId','unit','minValue','maxValue'},
'inspection_templates':{'name','assetId','questions'},
'inspection_responses':{'templateId','assetId','answers','notes'},
'plans':{'name','assetId','description','intervalDays','nextRun','priority','enabled'},
'automations':{'name','meterId','enabled'},
'life_tracking':{'name','partId','assetId','installedOn','expectedLifeDays','notes'}})
REFS={'assets':{'typeId':'asset_types','categoryId':'categories','locationId':'locations','zoneId':'zones','subzoneId':'subzones','teamId':'teams'},'zones':{'locationId':'locations'},'subzones':{'zoneId':'zones'},'part_locations':{'locationId':'locations'},'parts':{'typeId':'part_types','locationId':'part_locations','vendorId':'vendors'},'purchases':{'partId':'parts','vendorId':'vendors'},'meters':{'assetId':'assets'},'inspection_templates':{'assetId':'assets'},'inspection_responses':{'templateId':'inspection_templates','assetId':'assets'},'plans':{'assetId':'assets'},'automations':{'meterId':'meters'},'life_tracking':{'partId':'parts','assetId':'assets'}}
REQUIRED={'assets':{'code'},'zones':{'locationId'},'subzones':{'zoneId'},'parts':{'sku'},'purchases':{'partId','vendorId','quantity'},'meters':{'assetId','unit'},'inspection_templates':{'questions'},'inspection_responses':{'templateId','assetId','answers'},'plans':{'assetId','description','intervalDays','nextRun'},'automations':{'meterId'},'life_tracking':{'partId','assetId','installedOn','expectedLifeDays'}}


def public(item): return {k:v for k,v in item.items() if k not in {'PK','SK','GSI1PK','GSI1SK','requestHash'}}

def permitted(user,kind,write=False):
    if kind not in KINDS: raise RuleError('Unknown catalog',404)
    if manages(user): return
    role=canonical_role(user['role'])
    if write:
        if role=='worker' and kind=='inspection_responses': return
        raise RuleError('Manager access required',403)
    if kind not in (WORKER_READ if role=='worker' else REPORTER_READ): raise RuleError('This catalog is not available to your role',403)


def records(kind,active=False):
    result=[];args={'KeyConditionExpression':'PK = :pk AND begins_with(SK, :sk)','ExpressionAttributeValues':{':pk':'CAT#'+kind,':sk':'ITEM#'},'ConsistentRead':True}
    while True:
        page=storage.table().query(**args);result.extend(page.get('Items',[]))
        if not page.get('LastEvaluatedKey'):break
        args['ExclusiveStartKey']=page['LastEvaluatedKey']
    return [r for r in result if not active or not r.get('archived')]


def get(kind,id,active=True):
    if not isinstance(id,str) or not id or len(id)>128: raise RuleError('Invalid reference')
    record=storage.table().get_item(Key={'PK':'CAT#'+kind,'SK':'ITEM#'+id},ConsistentRead=True).get('Item')
    if not record or active and record.get('archived'): raise RuleError(f'{kind} reference not found or archived',404)
    return record


def machines():
    return MACHINES+[public(a) for a in records('assets',True)]


def asset(id):
    found=next((m for m in MACHINES if m['id']==id),None)
    return found or get('assets',id)


def integer(value,label,minimum=0,maximum=1000000000):
    if isinstance(value,bool) or not isinstance(value,(int,Decimal)) or value!=int(value) or not minimum<=value<=maximum: raise RuleError(f'{label} must be an integer from {minimum} to {maximum}')
    return int(value)


def number(value,label,minimum=None):
    if isinstance(value,bool) or not isinstance(value,(int,float,Decimal)) or not math.isfinite(float(value)) or minimum is not None and value<minimum: raise RuleError(f'{label} must be a finite number'+(' >= '+str(minimum) if minimum is not None else ''))
    return Decimal(str(value))


def utc(value,label='Next run'):
    try:
        if not isinstance(value,str) or not value.endswith('Z'): raise ValueError()
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo!=timezone.utc: raise ValueError()
        return parsed.replace(microsecond=0).isoformat().replace('+00:00','Z')
    except ValueError as e: raise RuleError(label+' must be an ISO UTC timestamp ending Z') from e


def validate(kind,data,old=None):
    if not isinstance(data,dict) or set(data)-FIELDS[kind]-{'version'}: raise RuleError('Unknown fields in '+kind)
    out={k:v for k,v in data.items() if k!='version'}
    if old:
        out={**{k:v for k,v in old.items() if k in FIELDS[kind]},**out}
    for field in REQUIRED.get(kind,set()):
        if field not in out or out[field] in ('',None): raise RuleError(field+' is required')
    if kind!='inspection_responses':out['name']=text(out.get('name'),'Name',200)
    if kind=='parts':
        out['unit']=out.get('unit') or 'pieces'
        for f in ['quantity','minQuantity']:
            if out.get(f) in ('',None):out[f]=0
    for field in {'description','serial','email','phone','notes','sku','code','unit'} & out.keys(): out[field]=text(out[field],field,4000 if field in {'description','notes'} else 200,field in {'sku','code','unit'})
    for field,target in REFS.get(kind,{}).items():
        value=out.get(field,'')
        if value:
            asset(value) if target=='assets' else get(target,value)
        elif value not in ('',None):raise RuleError('Invalid '+field)
        out[field]=value or ''
    if kind=='assets':
        if out.get('zoneId') and get('zones',out['zoneId'])['locationId']!=out.get('locationId'):raise RuleError('Zone must belong to the selected location')
        if out.get('subzoneId') and get('subzones',out['subzoneId'])['zoneId']!=out.get('zoneId'):raise RuleError('Sub-zone must belong to the selected zone')
    if kind=='teams':
        ids=out.get('memberIds',[])
        if not isinstance(ids,list) or len(ids)>50 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):raise RuleError('Choose at most 50 distinct users')
        from .api import find_user
        from . import demo
        fictional={p['id'] for p in demo.people()}
        for id in ids:
            if id not in fictional:find_user(id)
        out['memberIds']=ids
    if kind=='parts':
        for f in ['quantity','minQuantity']:out[f]=integer(out.get(f,0),f)
        if old and out['quantity']!=old['quantity']:raise RuleError('Use a stock adjustment to change quantity')
        out['unit']=text(out.get('unit') or 'pieces','Unit',100)
    if kind=='purchases':
        out['quantity']=integer(out['quantity'],'Quantity',1)
        if out.get('unitCost') not in (None,''):out['unitCost']=number(out['unitCost'],'Unit cost',0)
        else:out.pop('unitCost',None)
        out['currency']=out.get('currency') or 'INR'
        if out['currency'] not in ['INR','USD','EUR']:raise RuleError('Choose INR, USD or EUR')
    if kind=='meters':
        for f in ['minValue','maxValue']:
            if out.get(f) not in (None,''):out[f]=number(out[f],f)
            else:out.pop(f,None)
        if 'minValue' in out and 'maxValue' in out and out['minValue']>=out['maxValue']:raise RuleError('Minimum threshold must be below maximum')
    if kind=='inspection_templates':
        q=out['questions']
        if not isinstance(q,list) or not 1<=len(q)<=20:raise RuleError('Provide 1 to 20 checklist questions')
        out['questions']=[text(x,'Question',300) for x in q]
        if len(set(out['questions']))!=len(out['questions']):raise RuleError('Checklist questions must be distinct')
    if kind=='inspection_responses':
        template=get('inspection_templates',out['templateId']);answers=out['answers']
        if template.get('assetId') and template['assetId']!=out['assetId']:raise RuleError('This template is for a different asset')
        if not isinstance(answers,list) or len(answers)!=len(template['questions']):raise RuleError('Answer every checklist item')
        cleaned=[]
        for question,answer in zip(template['questions'],answers):
            if not isinstance(answer,dict) or set(answer)-{'question','answer','note'} or answer.get('question')!=question or answer.get('answer') not in ['pass','fail','na']:raise RuleError('Checklist answers must match the template in order')
            cleaned.append({'question':question,'answer':answer['answer'],'note':text(answer.get('note',''),'Note',1000,False)})
        out.update(answers=cleaned,name=template['name']+' inspection')
    if kind=='plans':
        out['intervalDays']=integer(out['intervalDays'],'Interval days',1,365)
        out['nextRun']=utc(out['nextRun']);out['priority']=out.get('priority') or 'medium'
        if out['priority'] not in ['low','medium','high','critical']:raise RuleError('Invalid priority')
    if kind in {'plans','automations'}:
        out.setdefault('enabled',False)
        if not isinstance(out['enabled'],bool):raise RuleError('Enabled must be true or false')
    if kind=='life_tracking':
        out['expectedLifeDays']=integer(out['expectedLifeDays'],'Expected life days',1,36500)
        try:
            if not isinstance(out['installedOn'],str) or len(out['installedOn'])!=10:raise ValueError()
            datetime.strptime(out['installedOn'],'%Y-%m-%d')
        except ValueError as e:raise RuleError('Installed on must be YYYY-MM-DD') from e
    return out


def audit(record,user,action,reason='',**extra):
    at=now();id=str(uuid.uuid4())
    return {'PK':record['PK'],'SK':'AUDIT#'+record['id']+'#'+at+'#'+id,'id':id,'at':at,'actorId':user['id'],'actorName':user['name'],'action':action,'reason':reason,**extra}


def put(record,old=None):
    operation={'TableName':os.environ['TABLE_NAME'],'Item':storage.encode(record),'ConditionExpression':'#v = :v' if old else 'attribute_not_exists(PK)'}
    if old:operation.update(ExpressionAttributeNames={'#v':'version'},ExpressionAttributeValues={':v':storage.SER.serialize(old['version'])})
    return {'Put':operation}


def revision():
    """Read before any dependency snapshot; serialize catalog writes optimistically."""
    item=storage.table().get_item(Key={'PK':'CATALOG_REVISION','SK':'META'},ConsistentRead=True).get('Item')
    return int(item['version']) if item else 0


def revision_guard(expected):
    update={'TableName':os.environ['TABLE_NAME'],'Key':storage.encode({'PK':'CATALOG_REVISION','SK':'META'}),'UpdateExpression':'SET #v = :next','ConditionExpression':'#v = :old' if expected else 'attribute_not_exists(#v)','ExpressionAttributeNames':{'#v':'version'},'ExpressionAttributeValues':{':next':storage.SER.serialize(expected+1)}}
    if expected:update['ExpressionAttributeValues'][':old']=storage.SER.serialize(expected)
    return {'Update':update}


def work_reference(job):
    return put({'PK':'ASSETWORK#'+job['machineId'],'SK':'WORK#'+job['id'],'workOrderId':job['id']})


def active_asset_work(id):
    """Strong reads avoid a freshly created job being absent from the GSI."""
    args={'KeyConditionExpression':'PK = :pk','ExpressionAttributeValues':{':pk':'ASSETWORK#'+id},'ConsistentRead':True}
    while True:
        page=storage.table().query(**args)
        for reference in page.get('Items',[]):
            job=storage.get_job(reference['workOrderId'])
            if job['status'] not in {'closed','rejected','merged','skipped'}:return True
        if not page.get('LastEvaluatedKey'):break
        args['ExclusiveStartKey']=page['LastEvaluatedKey']
    # Legacy jobs predate the reference partition. New jobs always add a row.
    return any(w['machineId']==id and w['status'] not in {'closed','rejected','merged','skipped'} for w in storage.list_jobs())


def transaction(writes):
    try:boto3.client('dynamodb').transact_write_items(TransactItems=writes)
    except ClientError as e:
        if e.response['Error']['Code']=='TransactionCanceledException':raise RuleError('Record changed or operation already processed. Refresh before retrying.',409) from e
        raise


def mutate(kind,data,user,id=None):
    permitted(user,kind,True)
    expected_revision=revision()
    old=get(kind,id,False) if id else None
    if old:
        if kind=='inspection_responses':raise RuleError('Inspection responses are immutable')
        if old.get('archived'):raise RuleError('Restore this record before editing',409)
        if kind=='purchases' and old.get('status')=='received':raise RuleError('Received purchases are immutable',409)
        if data.get('version')!=old['version']:raise RuleError('Record changed. Refresh before editing.',409)
    out=validate(kind,data,old)
    if kind=='plans' and (not old or old['nextRun']!=out['nextRun']) and out['nextRun']<=now():raise RuleError('Next run must be in the future')
    id=id or str(uuid.uuid4());at=now()
    record={**(old or {}),**out,'PK':'CAT#'+kind,'SK':'ITEM#'+id,'id':id,'version':int(old['version'])+1 if old else 1,'archived':False,'createdAt':old['createdAt'] if old else at,'createdBy':old['createdBy'] if old else user['id'],'updatedAt':at}
    if old and kind in {'zones','subzones'}:
        field='locationId' if kind=='zones' else 'zoneId'
        child_field='zoneId' if kind=='zones' else 'subzoneId'
        if out[field]!=old[field] and any(a.get(child_field)==id for a in records('assets',True)):raise RuleError('Move referencing assets before changing this parent',409)
    if kind=='purchases':record['status']='draft'
    if kind=='assets':
        if out['code'].upper() in {m['id'] for m in MACHINES}:raise RuleError('Asset code conflicts with a built-in machine')
        if old and old['code'].casefold()!=out['code'].casefold():raise RuleError('Asset code is immutable; create another asset instead')
    writes=[put(record,old),put(audit(record,user,'updated' if old else 'created'))]
    if kind=='parts' and not old:writes[-1]=put(audit(record,user,'opening_stock',delta=out['quantity'],balance=out['quantity']))
    if kind=='assets':
        token=out['code'].casefold()
        lock={'PK':'UNIQUE#ASSETCODE','SK':token,'ownerId':id}
        if not old or old['code'].casefold()!=token:
            writes.append(put(lock))

    transaction(writes+[revision_guard(expected_revision)])
    return public(record)


def archive(kind,id,data,user):
    if not manages(user):raise RuleError('Manager access required',403)
    expected_revision=revision()
    old=get(kind,id,False)
    if data.get('version')!=old['version']:raise RuleError('Record changed. Refresh before archiving.',409)
    value=data.get('archived')
    if not isinstance(value,bool):raise RuleError('Archived must be true or false')
    if value==old.get('archived',False):return public(old)
    if value:
        if kind=='assets':
            if active_asset_work(id):raise RuleError('Asset has unresolved work orders',409)
        for child,refs in REFS.items():
            for field,target in refs.items():
                if target==kind and any(r.get(field)==id for r in records(child,True)):raise RuleError('Active '+child+' records still reference this record',409)
    else:
        validate(kind,{k:v for k,v in old.items() if k in FIELDS[kind]})
    record={**old,'archived':value,'version':old['version']+1,'updatedAt':now()}
    transaction([put(record,old),put(audit(record,user,'archived' if value else 'restored')),revision_guard(expected_revision)])
    return public(record)


def history(kind,id):
    args={'KeyConditionExpression':'PK = :pk AND begins_with(SK, :sk)','ExpressionAttributeValues':{':pk':'CAT#'+kind,':sk':'AUDIT#'+id+'#'},'ConsistentRead':True};items=[]
    while True:
        page=storage.table().query(**args);items.extend(public(i) for i in page.get('Items',[]))
        if not page.get('LastEvaluatedKey'):return items
        args['ExclusiveStartKey']=page['LastEvaluatedKey']


def adjust(id,data,user):
    if not manages(user):raise RuleError('Manager access required',403)
    expected_revision=revision()
    old=get('parts',id)
    if data.get('version')!=old['version']:raise RuleError('Stock record changed',409)
    delta=integer(data.get('delta'),'Stock delta',-1000000000)
    if not delta:raise RuleError('Stock delta cannot be zero')
    reason=text(data.get('reason'),'Stock reason',1000)
    balance=int(old['quantity'])+delta
    if balance<0:raise RuleError('Insufficient stock',409)
    record=dict(old,quantity=balance,version=old['version']+1,updatedAt=now())
    transaction([put(record,old),put(audit(record,user,'stock_adjustment',reason,delta=delta,balance=balance)),revision_guard(expected_revision)])
    return public(record)


def receive(id,data,user):
    if not manages(user):raise RuleError('Manager access required',403)
    expected_revision=revision()
    old=get('purchases',id)
    if old.get('status')!='draft' or data.get('version')!=old['version']:raise RuleError('Purchase already received or changed',409)
    part=get('parts',old['partId']);get('vendors',old['vendorId'])
    received=dict(old,status='received',receivedAt=now(),updatedAt=now(),version=old['version']+1)
    stock=dict(part,quantity=int(part['quantity'])+int(old['quantity']),updatedAt=now(),version=part['version']+1)
    transaction([put(received,old),put(stock,part),put(audit(received,user,'received')),put(audit(stock,user,'purchase_received',old['name'],delta=int(old['quantity']),balance=stock['quantity'])),revision_guard(expected_revision)])
    return public(received)


def snapshot(machine):
    result={k:machine.get(k,'') for k in ['code','typeId','categoryId','locationId','zoneId','subzoneId','teamId']}
    for field,kind in [('typeId','asset_types'),('categoryId','categories'),('locationId','locations'),('zoneId','zones'),('subzoneId','subzones'),('teamId','teams')]:
        if result[field]:
            try:result[field[:-2]+'Name']=get(kind,result[field],False)['name']
            except RuleError:pass
    return result


def request_job(machine, title, description, priority, user, id, **extra):
    at=now()
    source='planId' if extra.get('planId') else 'meterId'
    possible_duplicate=bool(extra.get(source)) and any(w['machineId']==machine['id'] and w.get(source)==extra[source] and w['status'] not in {'closed','rejected','merged','skipped'} for w in storage.list_jobs())
    return {'PK':'WORK#'+id,'SK':'META','GSI1PK':'WORK','GSI1SK':at,'id':id,'number':'WO-'+id[:8].upper(),'machineId':machine['id'],'machineName':machine['name'],'title':title,'description':description,'category':'Preventive' if extra.get('planId') else 'Meter threshold','priority':priority,'status':'pending_review','assignmentStatus':'unassigned','assigneeId':'','assigneeName':'','reporterId':user['id'],'reporterName':user['name'],'createdAt':at,'updatedAt':at,'version':1,'deadlineVersion':0,'deadline':'','deadlineKind':'','overdue':False,'blocked':False,'possibleDuplicate':possible_duplicate,'possibleResolved':False,'attachments':[],'archived':False,**snapshot(machine),**extra}


def readings(id,data,user,event,write):
    if canonical_role(user['role']) not in {'admin','manager','worker'}:raise RuleError('Worker access required',403)
    expected_revision=revision() if write else None
    meter=get('meters',id)
    if not write:
        args={'KeyConditionExpression':'PK = :pk AND begins_with(SK, :sk)','ExpressionAttributeValues':{':pk':'METER#'+id,':sk':'READING#'},'ConsistentRead':True};items=[]
        while True:
            page=storage.table().query(**args);items.extend(public(i) for i in page.get('Items',[]))
            if not page.get('LastEvaluatedKey'):return {'items':sorted(items,key=lambda i:i['at'],reverse=True)}
            args['ExclusiveStartKey']=page['LastEvaluatedKey']
    if set(data)-{'value','note'}:raise RuleError('Provide only value and note')
    value=number(data.get('value'),'Reading');note=text(data.get('note',''),'Note',1000,False)
    headers={k.lower():v for k,v in event.get('headers',{}).items()}
    key=text(headers.get('idempotency-key'),'Idempotency-Key',128)
    digest=hashlib.sha256((user['id']+':'+id+':'+key).encode()).hexdigest()
    pk={'PK':'METER#'+id,'SK':'READING#'+digest}
    request_hash=hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()
    existing=storage.table().get_item(Key=pk,ConsistentRead=True).get('Item')
    if existing:
        if existing['requestHash']!=request_hash:raise RuleError('Idempotency key used for a different reading',409)
        return {'reading':public(existing),'meter':public(meter),'workOrderId':existing.get('workOrderId','')}
    breached=('minValue' in meter and value<meter['minValue']) or ('maxValue' in meter and value>meter['maxValue'])
    reading={**pk,'id':digest,'value':value,'note':note,'at':now(),'actorId':user['id'],'actorName':user['name'],'breached':breached,'requestHash':request_hash}
    updated={**meter,'latestReading':value,'latestReadAt':reading['at'],'version':meter['version']+1,'updatedAt':now()}
    rules=[r for r in records('automations',True) if r['meterId']==id and r.get('enabled')]
    writes=[put(updated,meter),put(reading),put(audit(meter,user,'reading_recorded',note)),revision_guard(expected_revision)]
    if breached and rules:
        machine=asset(meter['assetId']);job_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'meter:'+id+':'+digest))
        job=request_job(machine,meter['name']+' outside threshold',f"Manual reading {value} {meter['unit']} is outside configured thresholds. {note}",'high',user,job_id,meterId=id,readingId=digest)
        reading['workOrderId']=job_id;writes[1]=put(reading)
        storage.write(job,user,'meter_threshold_reported',extra=writes+[work_reference(job)])
    else:transaction(writes)
    return {'reading':public(reading),'meter':public(updated),'workOrderId':reading.get('workOrderId','')}


def workflow(data=None,user=None):
    key={'PK':'SETTINGS','SK':'WORKFLOW'};old=storage.table().get_item(Key=key,ConsistentRead=True).get('Item')
    defaults={'ackMinutes':int(os.environ.get('ACK_SECONDS',3600))//60,'repairMinutes':int(os.environ.get('REPAIR_SECONDS',14400))//60,'verifyMinutes':int(os.environ.get('VERIFY_SECONDS',7200))//60,'version':0}
    if data is None:return {k:old[k] for k in defaults} if old else defaults
    if not manages(user):raise RuleError('Manager access required',403)
    if set(data)!={'ackMinutes','repairMinutes','verifyMinutes','version'}:raise RuleError('Provide ackMinutes, repairMinutes, verifyMinutes and version')
    if data['version']!=(old['version'] if old else 0):raise RuleError('Workflow settings changed',409)
    out={k:integer(data[k],k,1,525600) for k in ['ackMinutes','repairMinutes','verifyMinutes']}
    record={**key,**out,'version':data['version']+1,'updatedAt':now()}
    transaction([put(record,old),put({'PK':'SETTINGS','SK':'AUDIT#'+now()+'#'+str(uuid.uuid4()),'actorId':user['id'],'action':'workflow_updated','at':now()})])
    return {k:record[k] for k in defaults}


def route(method,path,data,user,event):
    parts=path.strip('/').split('/')
    if path=='/catalog' and method=='GET':
        allowed=KINDS if manages(user) else WORKER_READ if canonical_role(user['role'])=='worker' else REPORTER_READ
        return {'catalog':{kind:[public(i) for i in records(kind,not manages(user))] for kind in sorted(allowed)}}
    if path=='/settings/workflow':
        if not manages(user):raise RuleError('Manager access required',403)
        if method=='GET':return workflow()
        if method=='POST':return workflow(data,user)
        raise RuleError('Endpoint not found',404)
    if len(parts)<2 or parts[0]!='catalog':raise RuleError('Endpoint not found',404)
    kind=parts[1];permitted(user,kind)
    if len(parts)==2:
        if method=='GET':return {'items':[public(i) for i in records(kind,not manages(user))]}
        if method=='POST':return mutate(kind,data,user)
    if len(parts)==3 and method=='POST':return mutate(kind,data,user,parts[2])
    if len(parts)==4:
        id=parts[2];action=parts[3]
        if action=='archive' and method=='POST':return archive(kind,id,data,user)
        if kind=='parts' and action=='adjust' and method=='POST':return adjust(id,data,user)
        if kind=='parts' and action=='history' and method=='GET':get(kind,id,False);return {'items':history(kind,id)}
        if kind=='purchases' and action=='receive' and method=='POST':return receive(id,data,user)
        if kind=='meters' and action=='readings' and method in {'GET','POST'}:return readings(id,data,user,event,method=='POST')
    raise RuleError('Endpoint not found',404)
