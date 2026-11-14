"""Build a reproducible, additive demo import. No AWS calls or credentials.
The import uses conditional writes; stable keys make re-runs non-destructive.
"""
import argparse, calendar, collections, copy, json, random, uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path

DATASET='shiftfix-history-v1'
NS=uuid.UUID('7b4d7004-8552-4628-9442-aa732681785a')
def ident(value):return 'demo-'+str(uuid.uuid5(NS,value))
def stamp(at):return at.replace(microsecond=0).isoformat().replace('+00:00','Z')
def typed(v):
    if v is None:return {'NULL':True}
    if isinstance(v,bool):return {'BOOL':v}
    if isinstance(v,str):return {'S':v}
    if isinstance(v,(int,float)):return {'N':str(v)}
    if isinstance(v,list):return {'L':[typed(x) for x in v]}
    if isinstance(v,dict):return {'M':{k:typed(x) for k,x in v.items()}}
    raise TypeError(type(v))

def build(as_of):
    rng=random.Random(43);rows=[];catalog=collections.defaultdict(list)
    month=as_of.month-2;year=as_of.year
    if month<1:month+=12;year-=1
    start=as_of.replace(year=year,month=month,day=min(as_of.day,calendar.monthrange(year,month)[1]),hour=0,minute=0,second=0,microsecond=0)
    people=[]
    for slug,name,role in [('anika','Anika Rao','manager'),('omar','Omar Khan','manager'),('ravi','Ravi Kumar','worker'),('meera','Meera Patel','worker'),('arjun','Arjun Singh','worker'),('farah','Farah Ali','worker'),('priya','Priya Nair','reporter'),('dev','Dev Shah','reporter')]:
        p={'PK':'DEMO#'+DATASET,'SK':'PERSON#'+slug,'id':'demo-person-'+slug,'name':name+' (Demo)','email':slug+'@example.invalid','role':role,'demo':True,'canSignIn':False,'demoSeed':DATASET};rows.append(p);people.append(p)
    manager=people[0];workers=people[2:6];reporters=people[6:]
    def cat(kind,slug,name,**extra):
        r={'PK':'CAT#'+kind,'SK':'ITEM#'+ident(kind+':'+slug),'id':ident(kind+':'+slug),'name':name,'version':1,'archived':False,'createdAt':stamp(start),'updatedAt':stamp(start),'createdBy':manager['id'],'demo':True,'demoSeed':DATASET,**extra};rows.append(r);catalog[kind].append(r);return r
    def audit(r,at,action,delta=None,balance=None,reason='Simulated maintenance record'):
        a={'PK':r['PK'],'SK':'AUDIT#'+r['id']+'#'+stamp(at)+'#'+ident(r['id']+action+stamp(at)),'id':ident(r['id']+action+stamp(at)),'at':stamp(at),'actorId':manager['id'],'actorName':manager['name'],'action':action,'reason':reason,'demo':True,'demoSeed':DATASET}
        if delta is not None:a.update(delta=delta,balance=balance)
        rows.append(a)
    locations=[cat('locations',x,x+' · Demo',description='Fictional factory location') for x in ['Assembly hall','Packaging hall','Utilities building']]
    zones=[cat('zones',str(i),name+' · Demo',locationId=locations[i//2]['id']) for i,name in enumerate(['Press bay','Motor cell','Conveyor line','Pallet cell','Compressor room','Electrical room'])]
    subs=[cat('subzones',str(i),'Cell '+str(i+1)+' · Demo',zoneId=z['id']) for i,z in enumerate(zones)]
    types=[cat('asset_types',str(i),n+' · Demo') for i,n in enumerate(['Press','Conveyor','Motor','Compressor'])]
    cats=[cat('categories',str(i),n+' · Demo') for i,n in enumerate(['Mechanical','Electrical','Hydraulic','Preventive'])]
    teams=[cat('teams',str(i),n+' · Demo',memberIds=[workers[i%4]['id'],workers[(i+1)%4]['id']],description='Fictional roster; no login access') for i,n in enumerate(['Mechanical crew','Electrical crew','Utility crew'])]
    assets=[]
    specs=[('Hydraulic press A',0,0,2),('Hydraulic press B',0,0,2),('Drive motor A',1,2,1),('Drive motor B',1,2,1),('Packaging conveyor A',2,1,0),('Packaging conveyor B',3,1,0),('Air compressor A',4,3,0),('Air compressor B',4,3,3),('Pallet conveyor',3,1,3),('Utility pump',5,2,1)]
    for i,(name,z,t,c) in enumerate(specs):
        a=cat('assets',str(i),name+' · Demo',code=f'DEMO-{i+1:03}',typeId=types[t]['id'],categoryId=cats[c]['id'],locationId=zones[z]['locationId'],zoneId=zones[z]['id'],subzoneId=subs[z]['id'],teamId=teams[i%3]['id'],serial=f'SIM-2024-{i+1:04}',description='Fictional equipment for the ShiftFix demo')
        rows.append({'PK':'UNIQUE#ASSETCODE','SK':a['code'].casefold(),'ownerId':a['id'],'demoSeed':DATASET});assets.append(a)
    retired=cat('assets','retired','Retired training motor · Demo',code='DEMO-RETIRED',archived=True,description='Archived example; never installed')
    rows.append({'PK':'UNIQUE#ASSETCODE','SK':'demo-retired','ownerId':retired['id'],'demoSeed':DATASET})
    vendors=[cat('vendors',str(i),n+' · Demo',email=f'supplier{i+1}@example.invalid',phone='',description='Fictional supplier; no order or message is sent') for i,n in enumerate(['Precision Spares','Motion Supply','Fluid Power Co','Industrial Sensors'])]
    parttypes=[cat('part_types',str(i),n+' · Demo') for i,n in enumerate(['Bearings','Seals','Electrical','Consumables'])]
    bins=[cat('part_locations',str(i),n+' · Demo',locationId=locations[i%3]['id']) for i,n in enumerate(['Stores rack A','Tool crib B','Utilities cabinet'])]
    parts=[]
    for i,name in enumerate(['6205 bearing','Press seal kit','Contactor 24V','Drive belt','Hydraulic filter','Proximity sensor','Compressor oil','Safety relay']):
        opening=4 if i==0 else 20+i*3
        p=cat('parts',str(i),name+' · Demo',sku=f'DEMO-SKU-{i+1:03}',typeId=parttypes[i%4]['id'],locationId=bins[i%3]['id'],vendorId=vendors[i%4]['id'],quantity=opening,minQuantity=5 if i==0 else 12,unit='litres' if i==6 else 'pieces');parts.append(p);audit(p,start,'opening_stock',opening,opening)
    for i in range(12):
        p=parts[(i%7)+1];date=start+timedelta(days=4+i*4);received=i<8;quantity=8+(i%4)*3
        o=cat('purchases',str(i),f'Spare replenishment {i+1:02} · Demo',partId=p['id'],vendorId=vendors[i%4]['id'],quantity=quantity,unitCost=450+i*75,currency='INR',status='received' if received else 'draft',createdAt=stamp(date),updatedAt=stamp(date+timedelta(days=2)) if received else stamp(date),version=2 if received else 1)
        if received:
            o['receivedAt']=o['updatedAt'];p['quantity']+=quantity;p['version']+=1;p['updatedAt']=o['updatedAt'];audit(p,date+timedelta(days=2),'purchase_received',quantity,p['quantity'],o['name']);audit(o,date+timedelta(days=2),'received')
    for i,p in enumerate(parts):
        for j in range(3 if i else 1):
            at=start+timedelta(days=18+j*14+i);amount=2 if i==0 else 3+j;p['quantity']-=amount;p['version']+=1;p['updatedAt']=stamp(at);audit(p,at,'stock_adjustment',-amount,p['quantity'],'Simulated issue to maintenance job')
    templates=[cat('inspection_templates',str(i),n+' · Demo',assetId=assets[i*2]['id'],questions=['Guards secure and access clear?','No oil or air leaks?','Emergency stop checked?']) for i,n in enumerate(['Press start-up','Motor condition','Conveyor safety','Compressor daily'])]
    for i in range(28):
        t=templates[i%4];at=start+timedelta(days=2+i*2,hours=8)
        if at>as_of:continue
        cat('inspection_responses',str(i),t['name']+' inspection',templateId=t['id'],assetId=t['assetId'],answers=[{'question':q,'answer':'fail' if i%9==0 and j==1 else 'pass','note':'Simulated minor seepage; raised for review' if i%9==0 and j==1 else 'Simulated inspection observation'} for j,q in enumerate(t['questions'])],notes='Fictional inspection round',createdAt=stamp(at),updatedAt=stamp(at),createdBy=workers[i%4]['id'])
    meters=[]
    for i in range(6):
        m=cat('meters',str(i),('Oil temperature' if i%2==0 else 'Motor vibration')+' · Demo',assetId=assets[i]['id'],unit='°C' if i%2==0 else 'mm/s',minValue=10 if i%2==0 else 0,maxValue=75 if i%2==0 else 6);meters.append(m)
        for j in range(9):
            at=min(start+timedelta(days=j*7,hours=9),as_of-timedelta(minutes=10));value=round((54+rng.random()*18) if i%2==0 else (2+rng.random()*3),1)
            if j in [3,7] and i in [0,3]:value=82 if i==0 else 7.2
            r={'PK':'METER#'+m['id'],'SK':'READING#'+ident(f'meter{i}:{j}'),'id':ident(f'meter{i}:{j}'),'value':value,'note':'Fictional historical reading','at':stamp(at),'actorId':workers[i%4]['id'],'actorName':workers[i%4]['name'],'breached':value<m['minValue'] or value>m['maxValue'],'demo':True,'demoSeed':DATASET};rows.append(r);m.update(latestReading=value,latestReadAt=r['at'],updatedAt=r['at'],version=j+2)
    plans=[cat('plans',str(i),name+' · Demo',assetId=assets[i]['id'],description='Demo preventive instructions: isolate equipment, inspect, record findings and seek manager review.',intervalDays=[7,14,30][i%3],nextRun=stamp(as_of+timedelta(days=i+1)),priority='medium',enabled=False) for i,name in enumerate(['Press seal inspection','Press lubrication','Motor alignment','Motor thermal check','Conveyor tension','Conveyor guarding'])]
    for i in range(3):cat('automations',str(i),'Threshold review '+str(i+1)+' · Demo',meterId=meters[i]['id'],enabled=False)
    for i in range(6):cat('life_tracking',str(i),'Installed '+parts[i]['name'],partId=parts[i]['id'],assetId=assets[i]['id'],installedOn=(as_of-timedelta(days=20+i*14)).date().isoformat(),expectedLifeDays=[30,60,90][i%3],notes='Fictional installation; calendar estimate only')
    jobs=[];day=start;sequence=0
    fault_titles=['Seal seepage at coupling','Intermittent drive trip','Conveyor belt tracking drift','Unusual bearing vibration','Loose guard fastener','Slow return stroke','Sensor alignment drift','Planned lubrication round','Warm electrical terminal','Air pressure fluctuation']
    while day.date()<=as_of.date():
        count=1 if day.weekday()>=5 else 3+(day.day%2)
        for j in range(count):
            sequence+=1;created=day+timedelta(hours=6+j*2,minutes=sequence%37)
            if created>as_of:continue
            age=(as_of-created).total_seconds()/86400
            if age>10:status=rng.choices(['closed','rejected','merged','skipped'],[80,7,6,7])[0]
            else:status=rng.choices(['closed','pending_review','needs_details','open','in_progress','awaiting_verification'],[27,17,10,17,19,10])[0]
            a=assets[sequence%len(assets)];w=workers[sequence%4];reporter=reporters[sequence%2];id=ident('work:'+str(sequence));approved=created+timedelta(minutes=20);accepted=created+timedelta(hours=1);submitted=created+timedelta(hours=3);closed=created+timedelta(hours=4)
            if status=='closed' and closed>as_of:status='pending_review'
            assigned=status in ['open','in_progress','awaiting_verification','closed'];deadline=(approved+timedelta(hours=2)) if status=='open' else (accepted+timedelta(hours=8)) if status=='in_progress' else (submitted+timedelta(hours=4)) if status=='awaiting_verification' else None
            updated=closed if status=='closed' else submitted if status=='awaiting_verification' else accepted if status=='in_progress' else approved if status in ['open','rejected','merged','skipped','needs_details'] else created
            updated=min(updated,as_of);archived=status in ['closed','rejected','merged','skipped'] and sequence%13==0
            job={'PK':'WORK#'+id,'SK':'META','GSI1PK':'WORK','GSI1SK':stamp(created),'id':id,'number':f'DEMO-{sequence:04}','title':fault_titles[sequence%len(fault_titles)],'description':'Fictional maintenance history for the ShiftFix demo. '+a['name']+': '+fault_titles[sequence%len(fault_titles)]+'. Operator observed the condition during the shift walk-through.','machineId':a['id'],'machineName':a['name'],'category':cats[sequence%4]['name'],'priority':rng.choices(['low','medium','high','critical'],[15,50,28,7])[0],'status':status,'assignmentStatus':'accepted' if status in ['in_progress','awaiting_verification','closed'] else 'awaiting_acceptance' if status=='open' else 'unassigned','assigneeId':w['id'] if assigned else '','assigneeName':w['name'] if assigned else '','reporterId':reporter['id'],'reporterName':reporter['name'],'createdAt':stamp(created),'updatedAt':stamp(updated),'version':5 if status=='closed' else 3 if assigned else 1,'deadlineVersion':1 if deadline else 0,'deadline':stamp(deadline) if deadline else '','deadlineKind':'acknowledgment' if status=='open' else 'repair' if status=='in_progress' else 'verification' if status=='awaiting_verification' else '','overdue':bool(deadline and deadline<as_of),'blocked':status=='in_progress' and sequence%3==0,'possibleDuplicate':status=='pending_review' and sequence%3==0,'possibleResolved':status=='pending_review' and sequence%5==0,'relatedResolvedIds':[],'attachments':[],'archived':archived,'demo':True,'demoSeed':DATASET,'timersSuppressed':True}
            for field,kind in [('typeId','asset_types'),('categoryId','categories'),('locationId','locations'),('zoneId','zones'),('subzoneId','subzones'),('teamId','teams')]:job[field]=a[field];job[field[:-2]+'Name']=next(r['name'] for r in catalog[kind] if r['id']==a[field])
            if status=='closed':job['closedAt']=stamp(closed)
            if status=='skipped' or sequence%10==0:job['planId']=plans[sequence%6]['id'];job['scheduledFor']=job['createdAt']
            if status=='open' and sequence%4==0:job['assignmentStatus']='returned'
            if status=='merged':job['status']='rejected';status='rejected' # no dangling merge target
            if sequence%6==0:
                f=Path('public/assets/factory-floor.jpg');job['attachments']=[{'key':'demo/'+DATASET+'/factory-context.jpg','name':'Illustrative demo factory photo.jpg','type':'image/jpeg','size':f.stat().st_size,'stage':'before'}]
            rows.append(job);jobs.append(job);rows.append({'PK':'ASSETWORK#'+a['id'],'SK':'WORK#'+id,'workOrderId':id,'demoSeed':DATASET})
            events=[('reported',created,reporter,'Simulated report recorded')]
            if assigned:events.append(('approve',approved,manager,'Simulated review and assignment'))
            if status in ['in_progress','awaiting_verification','closed']:events.append(('start',accepted,w,'Simulated lockout and repair start'))
            if status in ['awaiting_verification','closed']:events.append(('submit',submitted,w,'Simulated repair complete; function check passed'))
            if status=='closed':events.append(('verify',closed,manager,'Simulated supervisor verification'))
            if status in ['rejected','skipped','needs_details']:events.append(({'rejected':'reject','skipped':'skip','needs_details':'clarify'}[status],updated,manager,'Simulated '+('out-of-scope report' if status=='rejected' else 'planned task deferred' if status=='skipped' else 'request for clearer fault description')))
            for n,(action,at,actor,reason) in enumerate(events):
                rows.append({'PK':job['PK'],'SK':'EVENT#'+stamp(min(at,as_of))+'#'+ident(id+str(n)),'id':ident(id+str(n)),'at':stamp(min(at,as_of)),'actorId':actor['id'],'actorName':actor['name'],'action':action,'reason':reason,'demo':True,'demoSeed':DATASET})
        day+=timedelta(days=1)
    # Explicit merged duplicate reports link to an actual active same-machine job.
    for n,target in enumerate([w for w in jobs if w['status'] in ['open','in_progress']][:3]):
        duplicate=copy.deepcopy(target);id=ident('merged:'+str(n));at=min(as_of,datetime.fromisoformat(target['createdAt'].replace('Z','+00:00'))+timedelta(minutes=5))
        duplicate.update(PK='WORK#'+id,id=id,number=f'DEMO-M{n+1:03}',title='Duplicate: '+target['title'],status='merged',mergedInto=target['id'],assignmentStatus='unassigned',assigneeId='',assigneeName='',deadline='',deadlineKind='',overdue=False,blocked=False,archived=False,possibleDuplicate=False,possibleResolved=False,version=2,createdAt=stamp(at),updatedAt=stamp(at+timedelta(minutes=2)),GSI1SK=stamp(at))
        duplicate.pop('closedAt',None);rows.append(duplicate);jobs.append(duplicate)
        rows.append({'PK':'ASSETWORK#'+duplicate['machineId'],'SK':'WORK#'+id,'workOrderId':id,'demoSeed':DATASET})
        for i,action in enumerate(['reported','merge']):
            rows.append({'PK':'WORK#'+id,'SK':'EVENT#'+stamp(at+timedelta(minutes=i*2))+'#'+ident(id+str(i)),'id':ident(id+str(i)),'at':stamp(at+timedelta(minutes=i*2)),'actorId':manager['id'],'actorName':manager['name'],'action':action,'reason':'Fictional duplicate linked to '+target['number'],'demo':True,'demoSeed':DATASET})
    # Link advisory requests to actual matching historical repairs.
    for job in jobs:
        if job['possibleResolved']:
            matches=[w['id'] for w in jobs if w['machineId']==job['machineId'] and w['status']=='closed' and w['createdAt']<job['createdAt']]
            job['relatedResolvedIds']=matches[-2:];job['possibleResolved']=bool(matches)
    manifest={'PK':'DEMO#'+DATASET,'SK':'META','dataset':DATASET,'label':'Fictional factory demo','start':stamp(start),'end':stamp(as_of),'workOrders':len(jobs),'complete':True,'demo':True,'counts':{k:len(v) for k,v in catalog.items()},'people':len(people)}
    return rows,manifest,catalog,jobs,people

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--as-of');a=p.parse_args();as_of=datetime.fromisoformat(a.as_of.replace('Z','+00:00')) if a.as_of else datetime.now(timezone.utc)
    rows,manifest,catalog,jobs,people=build(as_of);path=Path('.deploy');path.mkdir(exist_ok=True)
    payload={'dataset':DATASET,'manifest':{k:typed(v) for k,v in manifest.items()},'items':[{k:typed(v) for k,v in r.items()} for r in rows]}
    (path/'demo-import.json').write_text(json.dumps(payload,separators=(',',':')))
    (path/'demo-fixture.json').write_text(json.dumps({'manifest':manifest,'catalog':catalog,'items':jobs,'users':people,'rows':rows},separators=(',',':')))
    print(json.dumps({'manifest':manifest,'rows':len(rows),'statuses':dict(collections.Counter(w['status'] for w in jobs))},indent=2))
