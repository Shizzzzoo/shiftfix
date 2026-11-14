import importlib.util
from datetime import datetime,timezone
from pathlib import Path
import pytest
from backend import api,catalog,demo,storage
from backend.domain import RuleError
from test_backend import aws,USER

spec=importlib.util.spec_from_file_location('demo_builder',Path(__file__).parents[1]/'scripts/build-demo-data.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def test_demo_graph_integrity_and_side_effect_free_import():
    rows,manifest,cat,jobs,people=builder.build(datetime(2026,11,14,15,tzinfo=timezone.utc))
    assert manifest['start']=='2026-09-14T00:00:00Z'
    assert len(jobs)>150 and len({w['createdAt'][:10] for w in jobs})==62
    assert all(w['demo'] and w['demoSeed']==builder.DATASET for w in jobs)
    assert all(not r['PK'].startswith('TIMER#') for r in rows)
    assert all(not p['enabled'] for p in cat['plans']+cat['automations'])
    assert all(p['demo'] and not p['canSignIn'] and p['email'].endswith('@example.invalid') for p in people)
    keys=[(r['PK'],r['SK']) for r in rows];assert len(keys)==len(set(keys))
    ids={r['id'] for kind in cat.values() for r in kind}|{p['id'] for p in people}
    assert all(w['machineId'] in ids and w['teamId'] in ids for w in jobs)
    assert all(w['assigneeId'] in ids for w in jobs if w['assigneeId'])
    for p in cat['parts']:
        movements=[r for r in rows if r['PK']==p['PK'] and r.get('delta') is not None and r['SK'].startswith('AUDIT#'+p['id'])]
        assert sum(r['delta'] for r in movements)==p['quantity']>=0
    for w in jobs:
        assert any(r['PK']==w['PK'] and r['SK'].startswith('EVENT#') for r in rows)
        assert ('ASSETWORK#'+w['machineId'],'WORK#'+w['id']) in keys
        assert w['createdAt']<=w['updatedAt']<=manifest['end']
    rows2,_,_,_,_=builder.build(datetime(2026,11,14,15,tzinfo=timezone.utc))
    assert rows==rows2

def test_demo_people_never_authenticate_or_receive_roles(aws):
    for id in ['demo-person-ravi','demo-person-fake']:
        with pytest.raises(RuleError) as e:api.find_user(id)
        assert e.value.status==403
        with pytest.raises(RuleError):api.set_role(id,'worker',dict(USER,role='admin'))

def test_demo_disclosure_requires_completed_manifest(aws):
    assert api.me(USER)['demoDataset'] is None
    storage.table().put_item(Item={'PK':'DEMO#'+demo.DATASET,'SK':'META','complete':False})
    assert demo.people()==[]
    rows,manifest,_,_,people=builder.build(datetime(2026,11,14,15,tzinfo=timezone.utc))
    for p in people:storage.table().put_item(Item=p)
    storage.table().put_item(Item=manifest)
    assert api.me(USER)['demoDataset']['workOrders']==len([r for r in rows if r['PK'].startswith('WORK#') and r['SK']=='META'])
    assert len(demo.people())==8
    assert all(p['canSignIn'] is False for p in demo.people())
