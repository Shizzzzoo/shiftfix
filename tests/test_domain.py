import copy
import pytest
from backend.domain import RuleError, transition

SUP={'id':'s','name':'Supervisor','role':'supervisor'}
TECH={'id':'t','name':'Technician','role':'technician'}
OTHER={'id':'x','name':'Other technician','role':'technician'}
REPORTER={'id':'r','name':'Reporter','role':'operator'}
AT='2026-11-14T10:00:00Z'

def job(**kw):
    return {'id':'one','version':1,'status':'pending_review','assignmentStatus':'unassigned','reporterId':'r','assigneeId':'','deadlineVersion':0,'deadline':'','overdue':False,'attachments':[],**kw}

def apply(j,action,user=SUP,**kw):
    return transition(j,user,{'version':j['version'],'action':action,**kw},AT)[0]

def approved(): return apply(job(),'approve',assigneeId='t',assigneeName='Tech')

def test_approve_requires_supervisor():
    with pytest.raises(RuleError) as e: apply(job(),'approve',REPORTER,assigneeId='t')
    assert e.value.status==403

def test_happy_path_and_rework_preserves_evidence():
    j=approved(); assert j['assignmentStatus']=='awaiting_acceptance'
    j=apply(j,'accept',TECH); assert j['status']=='in_progress'
    j=apply(j,'submit',TECH,reason='Replaced seal',attachments=[{'key':'repair'}])
    assert j['status']=='awaiting_verification'
    j=apply(j,'rework',reason='Leak persists'); assert j['attachments']==[{'key':'repair'}]
    j=apply(j,'submit',TECH,reason='Retested seal')
    j=apply(j,'verify'); assert j['status']=='closed' and j['deadline']==''

def test_return_preserves_fault_and_deadline():
    j=approved(); deadline=j['deadline']; rev=j['deadlineVersion']
    returned=apply(j,'return',TECH,reason='Wrong skill')
    assert returned['status']=='open' and returned['assignmentStatus']=='returned'
    assert returned['deadline']==deadline and returned['deadlineVersion']>rev

def test_old_owner_cannot_write_after_reassignment():
    j=apply(approved(),'reassign',assigneeId='x',assigneeName='Other')
    with pytest.raises(RuleError) as e: apply(j,'accept',TECH)
    assert e.value.status==403
    assert apply(j,'accept',OTHER)['status']=='in_progress'

def test_stale_version_conflicts():
    with pytest.raises(RuleError) as e: transition(approved(),SUP,{'version':1,'action':'reject','reason':'x'})
    assert e.value.status==409

@pytest.mark.parametrize('action',['return','clarify','reject','merge','block','rework','add_note','submit'])
def test_reason_required(action):
    user=TECH if action in {'return','block','submit'} else SUP
    with pytest.raises(RuleError): apply(job(status='in_progress',assigneeId='t',assignmentStatus='accepted'),action,user)

def test_notes_do_not_invalidate_timer():
    j=approved(); out=apply(j,'add_note',reason='Shift handover')
    assert out['deadlineVersion']==j['deadlineVersion'] and out['version']>j['version']

def test_terminal_is_immutable():
    with pytest.raises(RuleError): apply(job(status='closed'),'approve',assigneeId='t')

def test_clarification_returns_to_review_on_reporter_note():
    j=apply(job(),'clarify',reason='Which cylinder?')
    assert apply(j,'add_note',REPORTER,reason='Main cylinder')['status']=='needs_details'
    assert apply(j,'resubmit',REPORTER,reason='Main cylinder')['status']=='pending_review'

def test_transition_does_not_mutate_input():
    j=approved(); snapshot=copy.deepcopy(j)
    apply(j,'accept',TECH)
    assert j==snapshot

def test_cannot_merge_into_self():
    with pytest.raises(RuleError): apply(job(),'merge',reason='same',targetId='one')


def test_keep_separate_clears_only_duplicate_flag():
    j=approved(); j['possibleDuplicate']=True
    out=apply(j,'keep_separate',reason='Different cylinder')
    assert not out['possibleDuplicate']
    assert out['status']==j['status'] and out['deadlineVersion']==j['deadlineVersion']
    with pytest.raises(RuleError) as e: apply(j,'keep_separate',TECH,reason='different')
    assert e.value.status==403

def test_resubmit_requires_reporter_and_reason():
    j=job(status='needs_details')
    with pytest.raises(RuleError): apply(j,'resubmit',REPORTER)
    with pytest.raises(RuleError) as e: apply(j,'resubmit',SUP,reason='updated')
    assert e.value.status==403
    out=apply(j,'resubmit',REPORTER,reason='Updated location',description='The rear cylinder')
    assert out['status']=='pending_review' and out['description']=='The rear cylinder'


def test_submitted_repair_cannot_be_returned_as_assignment():
    j=apply(approved(),'accept',TECH)
    j=apply(j,'submit',TECH,reason='Repaired')
    with pytest.raises(RuleError) as e: apply(j,'return',TECH,reason='Wrong team')
    assert e.value.status==409


def test_supervisor_can_confirm_returned_job_already_resolved():
    j=apply(approved(),'return',TECH,reason='Repair already completed on previous shift')
    with pytest.raises(RuleError): apply(j,'resolve_existing')
    with pytest.raises(RuleError) as e: apply(j,'resolve_existing',TECH,reason='already done')
    assert e.value.status==403
    with pytest.raises(RuleError): apply(approved(),'resolve_existing',reason='already done')
    out=apply(j,'resolve_existing',reason='Verified prior shift repair against machine history')
    assert out['status']=='closed' and out['deadline']==''
    assert out['assignmentStatus']=='returned'
