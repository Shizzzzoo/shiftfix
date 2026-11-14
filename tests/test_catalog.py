import copy
import json
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import pytest
from backend import api,catalog,storage,planning
from backend.domain import RuleError,transition
from test_backend import aws,USER

MANAGER={'id':'m','name':'Manager','role':'manager'}
WORKER={'id':'w','name':'Worker','role':'worker'}
REPORTER={'id':'r','name':'Reporter','role':'reporter'}

def make(kind,**data):return catalog.mutate(kind,data,MANAGER)

def inventory():
    vendor=make('vendors',name='Supply Co')
    part=make('parts',name='Seal',sku='SEAL-1',quantity=5,minQuantity=2)
    return vendor,part


def test_scoped_bootstrap_and_mutation_matrix(aws):
    make('locations',name='Workshop');make('vendors',name='Private Supplier')
    for user in [REPORTER,WORKER]:
        data=catalog.route('GET','/catalog',{},user,{})['catalog']
        assert 'locations' in data and 'vendors' not in data
        with pytest.raises(RuleError) as e:catalog.mutate('locations',{'name':'Unauthorized'},user)
        assert e.value.status==403
    assert 'vendors' in catalog.route('GET','/catalog',{},MANAGER,{})['catalog']
    with pytest.raises(RuleError):catalog.route('GET','/catalog/parts',{},REPORTER,{})


def test_parent_hierarchy_and_dynamic_asset_snapshot(aws):
    location=make('locations',name='Factory floor')
    zone=make('zones',name='Bay A',locationId=location['id'])
    sub=make('subzones',name='Cell 1',zoneId=zone['id'])
    other=make('locations',name='Wrong location')
    with pytest.raises(RuleError):make('assets',name='Press',code='P-1',locationId=other['id'],zoneId=zone['id'])
    asset=make('assets',name='Press',code='P-1',locationId=location['id'],zoneId=zone['id'],subzoneId=sub['id'])
    assert any(m['id']==asset['id'] for m in catalog.machines())
    job=api.create({'machineId':asset['id'],'title':'Leak','description':'Oil on floor','priority':'high'},REPORTER,{'headers':{'idempotency-key':'dyn'}})
    assert job['locationId']==location['id'] and job['zoneName']=='Bay A'
    with pytest.raises(RuleError):catalog.archive('locations',location['id'],{'version':1,'archived':True},MANAGER)
    with pytest.raises(RuleError):catalog.archive('assets',asset['id'],{'version':1,'archived':True},MANAGER)


def test_foreign_reference_rejected(aws):
    with pytest.raises(RuleError):make('zones',name='Orphan',locationId='missing')
    with pytest.raises(RuleError):make('parts',name='Part',sku='P',vendorId='missing')


def test_unique_asset_codes_and_archive_restore(aws):
    asset=make('assets',name='Pump',code='PUMP')
    with pytest.raises(RuleError):make('assets',name='Other',code='pump')
    archived=catalog.archive('assets',asset['id'],{'version':asset['version'],'archived':True},MANAGER)
    assert archived['archived']
    assert not any(a['id']==asset['id'] for a in catalog.machines())
    restored=catalog.archive('assets',asset['id'],{'version':archived['version'],'archived':False},MANAGER)
    assert not restored['archived']


def test_stock_adjustment_prevents_negative_and_stale(aws):
    _,part=inventory()
    changed=catalog.adjust(part['id'],{'version':1,'delta':-3,'reason':'Issued for repair'},MANAGER)
    assert changed['quantity']==2
    with pytest.raises(RuleError) as e:catalog.adjust(part['id'],{'version':1,'delta':1,'reason':'Old view'},MANAGER)
    assert e.value.status==409
    with pytest.raises(RuleError):catalog.adjust(part['id'],{'version':2,'delta':-3,'reason':'Insufficient'},MANAGER)
    with pytest.raises(RuleError):catalog.mutate('parts',{'version':2,'quantity':999},MANAGER,part['id'])
    assert len(catalog.history('parts',part['id']))==2
    assert catalog.get('parts',part['id'])['quantity']==2


def test_receiving_is_atomic_and_once(aws):
    vendor,part=inventory()
    order=make('purchases',name='Seal restock',partId=part['id'],vendorId=vendor['id'],quantity=10,unitCost=1.25)
    received=catalog.receive(order['id'],{'version':1},MANAGER)
    assert received['status']=='received' and catalog.get('parts',part['id'])['quantity']==15
    with pytest.raises(RuleError):catalog.receive(order['id'],{'version':1},MANAGER)
    assert catalog.get('parts',part['id'])['quantity']==15
    assert any(e['action']=='purchase_received' and e['delta']==10 for e in catalog.history('parts',part['id']))


def test_archived_reference_prevents_new_child(aws):
    vendor=make('vendors',name='Archived Vendor')
    catalog.archive('vendors',vendor['id'],{'version':1,'archived':True},MANAGER)
    with pytest.raises(RuleError):make('parts',name='Seal',sku='S',vendorId=vendor['id'])


def test_inspection_exact_questions_and_worker_permission(aws):
    template=make('inspection_templates',name='Safety round',assetId='M-012',questions=['Guard intact?','No leak?'])
    data={'templateId':template['id'],'assetId':'M-012','answers':[{'question':'Guard intact?','answer':'pass'},{'question':'No leak?','answer':'fail','note':'Small leak'}]}
    result=catalog.mutate('inspection_responses',data,WORKER)
    assert result['name']=='Safety round inspection'
    with pytest.raises(RuleError):catalog.mutate('inspection_responses',data,REPORTER)
    bad=copy.deepcopy(data);bad['answers'][0]['question']='Changed'
    with pytest.raises(RuleError):catalog.mutate('inspection_responses',bad,WORKER)
    with pytest.raises(RuleError):catalog.mutate('inspection_responses',{**data,'version':1},MANAGER,result['id'])


def test_meter_threshold_workorder_atomic_idempotency(aws):
    meter=make('meters',name='Press temperature',assetId='M-012',unit='C',minValue=10,maxValue=80)
    make('automations',name='Temperature fault',meterId=meter['id'],enabled=True)
    event={'headers':{'Idempotency-Key':'reading-1'}}
    result=catalog.readings(meter['id'],{'value':90,'note':'Manual round'},WORKER,event,True)
    assert result['reading']['breached'] and result['workOrderId']
    again=catalog.readings(meter['id'],{'value':90,'note':'Manual round'},WORKER,event,True)
    assert again['workOrderId']==result['workOrderId'] and len(storage.list_jobs())==1
    assert len(catalog.readings(meter['id'],{},WORKER,{},False)['items'])==1
    with pytest.raises(RuleError):catalog.readings(meter['id'],{'value':91},WORKER,event,True)
    with pytest.raises(RuleError):catalog.readings(meter['id'],{'value':90},REPORTER,event,True)


def test_disabled_meter_automation_does_not_create_fault(aws):
    meter=make('meters',name='Temperature',assetId='M-012',unit='C',maxValue=80)
    make('automations',name='Paused fault',meterId=meter['id'],enabled=False)
    assert not catalog.readings(meter['id'],{'value':90},WORKER,{'headers':{'Idempotency-Key':'paused'}},True)['workOrderId']
    assert not storage.list_jobs()


def test_workflow_settings_apply_future_transitions(aws):
    assert catalog.workflow()['ackMinutes']==60
    settings=catalog.workflow({'ackMinutes':10,'repairMinutes':20,'verifyMinutes':30,'version':0},MANAGER)
    j={'id':'w','version':1,'status':'pending_review','reporterId':'r','deadlineVersion':0,'assignmentStatus':'unassigned'}
    updated,_=transition(j,MANAGER,{'action':'approve','version':1,'assigneeId':'w','assigneeName':'Worker'},'2026-11-14T10:00:00Z',policy=settings)
    assert updated['deadline']=='2026-11-14T10:10:00Z'
    with pytest.raises(RuleError):catalog.workflow({'ackMinutes':1,'repairMinutes':1,'verifyMinutes':1,'version':0},MANAGER)
    with pytest.raises(RuleError):catalog.workflow({'ackMinutes':1,'repairMinutes':1,'verifyMinutes':1,'version':1},REPORTER)


def test_hourly_plan_occurrence_once_and_next_future(aws):
    future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat().replace('+00:00','Z')
    plan=make('plans',name='Weekly press inspection',assetId='M-012',description='Inspect seals',intervalDays=7,nextRun=future,priority='medium',enabled=True)
    stored=catalog.get('plans',plan['id']);stored['nextRun']='2025-01-01T10:00:00Z';storage.table().put_item(Item=stored)
    first=planning.handler({},None);second=planning.handler({},None)
    assert len(first['processed'])==1 and not second['processed']
    jobs=storage.list_jobs();assert len(jobs)==1 and jobs[0]['planId']==plan['id']
    assert catalog.get('plans',plan['id'])['nextRun']>datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def test_planned_skip_and_terminal_archive(aws):
    j={'id':'x','version':1,'status':'pending_review','reporterId':'r','assignmentStatus':'unassigned','deadlineVersion':0}
    with pytest.raises(RuleError):transition(j,MANAGER,{'action':'skip','version':1,'reason':'Scheduled outage postponed'})
    j['planId']='plan'
    skipped,_=transition(j,MANAGER,{'action':'skip','version':1,'reason':'Scheduled outage postponed'})
    assert skipped['status']=='skipped'
    archived,_=transition(skipped,MANAGER,{'action':'archive','version':2})
    assert archived['archived']
    restored,_=transition(archived,MANAGER,{'action':'restore','version':3})
    assert not restored['archived']
    with pytest.raises(RuleError):transition(j,MANAGER,{'action':'archive','version':1})


def test_onboarding_accepts_dynamic_asset_and_life_tracking(aws):
    machine=make('assets',name='Pump',code='P-2')
    result=api.onboard({'displayName':'Reporter','department':'production','machineIds':[machine['id']]},REPORTER)
    assert result['profile']['machineIds']==[machine['id']]
    _,part=inventory()
    life=make('life_tracking',name='Pump seal life',partId=part['id'],assetId=machine['id'],installedOn='2026-11-14',expectedLifeDays=365)
    assert life['expectedLifeDays']==365
    with pytest.raises(RuleError):make('life_tracking',name='Bad date',partId=part['id'],assetId=machine['id'],installedOn='not-date',expectedLifeDays=365)


def test_scheduler_stale_snapshot_cannot_duplicate_occurrence(aws,monkeypatch):
    future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat().replace('+00:00','Z')
    plan=make('plans',name='Daily inspection',assetId='M-012',description='Inspect motor',intervalDays=1,nextRun=future,priority='medium',enabled=True)
    old=catalog.get('plans',plan['id']);old['nextRun']='2025-01-01T00:00:00Z';storage.table().put_item(Item=old)
    original_records=catalog.records
    monkeypatch.setattr(catalog,'records',lambda kind,active=False:[copy.deepcopy(old)] if kind=='plans' else original_records(kind,active))
    assert len(planning.handler({},None)['processed'])==1
    assert not planning.handler({},None)['processed']
    assert len(storage.list_jobs())==1


def test_receive_stock_race_rolls_back_purchase_and_audit(aws,monkeypatch):
    vendor,part=inventory()
    order=make('purchases',name='Restock',partId=part['id'],vendorId=vendor['id'],quantity=2)
    original_transaction=catalog.transaction
    def race(writes):
        # A second receiver/adjuster changes stock between read and transaction.
        record=catalog.get('parts',part['id']);record['version']+=1;record['quantity']=4
        storage.table().put_item(Item=record)
        return original_transaction(writes)
    monkeypatch.setattr(catalog,'transaction',race)
    with pytest.raises(RuleError) as exc:catalog.receive(order['id'],{'version':1},MANAGER)
    assert exc.value.status==409
    assert catalog.get('purchases',order['id'])['status']=='draft'
    assert catalog.get('parts',part['id'])['quantity']==4
    assert all(a['action']!='received' for a in catalog.history('purchases',order['id']))


def test_bad_catalog_inputs_do_not_create_records(aws):
    cases=[('parts',{'name':'Seal','sku':'S','quantity':True}),('meters',{'name':'Bad','assetId':'M-012','unit':'C','minValue':100,'maxValue':10}),('plans',{'name':'Past','assetId':'M-012','description':'Inspect','nextRun':'2025-01-01T00:00:00Z','intervalDays':1}),('plans',{'name':'No UTC','assetId':'M-012','description':'Inspect','nextRun':'2099-01-01T00:00:00','intervalDays':1}),('asset_types',{'name':'Leak','role':'admin'})]
    for kind,fields in cases:
        with pytest.raises(RuleError):make(kind,**fields)
        assert catalog.records(kind)==[]


def test_archived_meter_cannot_accept_reading(aws):
    meter=make('meters',name='Temperature',assetId='M-012',unit='C')
    catalog.archive('meters',meter['id'],{'version':1,'archived':True},MANAGER)
    with pytest.raises(RuleError):catalog.readings(meter['id'],{'value':12},WORKER,{'headers':{'Idempotency-Key':'x'}},True)


def test_worker_cannot_archive_or_adjust_inventory(aws):
    _,part=inventory()
    with pytest.raises(RuleError):catalog.adjust(part['id'],{'version':1,'delta':1,'reason':'Fake'},WORKER)
    with pytest.raises(RuleError):catalog.archive('parts',part['id'],{'version':1,'archived':True},WORKER)


def test_optional_blank_fields_and_exact_workflow_response(aws):
    part=make('parts',name='Seal',sku='S',unit='',quantity='',minQuantity='',vendorId='',locationId='')
    assert part['unit']=='pieces' and part['quantity']==0 and part['minQuantity']==0
    meter=make('meters',name='Temperature',assetId='M-012',unit='C',minValue='',maxValue='')
    assert 'minValue' not in meter and 'maxValue' not in meter
    payload={'ackMinutes':1,'repairMinutes':2,'verifyMinutes':3,'version':0}
    saved=catalog.workflow(payload,MANAGER)
    assert set(saved)==set(payload)
    assert catalog.workflow()==saved
    assert catalog.workflow({**saved,'repairMinutes':4},MANAGER)['version']==2


def test_archive_wins_race_against_child_create(aws,monkeypatch):
    location=make('locations',name='Plant')
    original=catalog.transaction
    fired=False
    def race(writes):
        nonlocal fired
        if not fired:
            fired=True
            catalog.archive('locations',location['id'],{'version':1,'archived':True},MANAGER)
        return original(writes)
    monkeypatch.setattr(catalog,'transaction',race)
    with pytest.raises(RuleError) as exc:make('zones',name='Bay',locationId=location['id'])
    assert exc.value.status==409
    assert catalog.get('locations',location['id'],False)['archived']
    assert not catalog.records('zones')


def test_child_create_wins_race_against_archive(aws,monkeypatch):
    location=make('locations',name='Plant')
    original=catalog.transaction
    fired=False
    def race(writes):
        nonlocal fired
        if not fired:
            fired=True
            make('zones',name='Bay',locationId=location['id'])
        return original(writes)
    monkeypatch.setattr(catalog,'transaction',race)
    with pytest.raises(RuleError) as exc:catalog.archive('locations',location['id'],{'version':1,'archived':True},MANAGER)
    assert exc.value.status==409
    assert not catalog.get('locations',location['id'])['archived']
    assert len(catalog.records('zones'))==1


def test_asset_archive_wins_race_against_new_work(aws,monkeypatch):
    asset=make('assets',name='Pump',code='PUMP-RACE')
    original=storage.write
    def race(job,*args,**kwargs):
        catalog.archive('assets',asset['id'],{'version':1,'archived':True},MANAGER)
        return original(job,*args,**kwargs)
    monkeypatch.setattr(storage,'write',race)
    with pytest.raises(RuleError) as exc:api.create({'machineId':asset['id'],'title':'Leak','description':'Oil leak'},REPORTER,{'headers':{'Idempotency-Key':'race-work'}})
    assert exc.value.status==409
    assert catalog.get('assets',asset['id'],False)['archived']
    assert not storage.list_jobs()


def test_new_work_wins_archive_and_strong_refs_survive_gsi_lag(aws,monkeypatch):
    asset=make('assets',name='Pump',code='PUMP-WORK-WINS')
    original=catalog.transaction
    fired=False
    def race(writes):
        nonlocal fired
        if not fired:
            fired=True
            api.create({'machineId':asset['id'],'title':'Leak','description':'Oil leak'},REPORTER,{'headers':{'Idempotency-Key':'work-first'}})
        return original(writes)
    monkeypatch.setattr(catalog,'transaction',race)
    with pytest.raises(RuleError) as exc:catalog.archive('assets',asset['id'],{'version':1,'archived':True},MANAGER)
    assert exc.value.status==409
    assert not catalog.get('assets',asset['id'])['archived']
    monkeypatch.setattr(catalog,'transaction',original)
    monkeypatch.setattr(storage,'list_jobs',lambda:[])  # simulate delayed GSI visibility
    with pytest.raises(RuleError,match='unresolved work'):catalog.archive('assets',asset['id'],{'version':1,'archived':True},MANAGER)


def test_repeated_threshold_breach_advisory_duplicate_without_auto_merge(aws):
    meter=make('meters',name='Temperature',assetId='M-012',unit='C',maxValue=80)
    make('automations',name='Threshold report',meterId=meter['id'],enabled=True)
    first=catalog.readings(meter['id'],{'value':90},WORKER,{'headers':{'Idempotency-Key':'first-breach'}},True)
    second=catalog.readings(meter['id'],{'value':95},WORKER,{'headers':{'Idempotency-Key':'second-breach'}},True)
    assert first['workOrderId']!=second['workOrderId']
    candidate=storage.get_job(second['workOrderId'])
    assert candidate['possibleDuplicate'] and candidate['status']=='pending_review'
    refs=storage.table().query(KeyConditionExpression='PK = :pk',ExpressionAttributeValues={':pk':'ASSETWORK#M-012'},ConsistentRead=True)['Items']
    assert {r['workOrderId'] for r in refs}=={first['workOrderId'],second['workOrderId']}
