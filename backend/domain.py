"""Pure work-order rules. API and deadline workers use the same state model."""
import copy
import os
from datetime import datetime, timedelta, timezone

TERMINAL = {'closed', 'rejected', 'merged', 'skipped'}
MACHINES = [
    {'id': 'M-012', 'name': 'Hydraulic press', 'location': 'Assembly · Bay 01'},
    {'id': 'M-008', 'name': 'Conveyor belt', 'location': 'Packaging · Line 02'},
    {'id': 'M-004', 'name': 'Drive motor', 'location': 'Assembly · Bay 03'},
    {'id': 'M-019', 'name': 'Proximity sensor', 'location': 'Packaging · Line 01'},
]

class RuleError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def text(value, label, maximum=2000, required=True):
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > maximum:
        raise RuleError(f'{label} must be text between {1 if required else 0} and {maximum} characters')
    return value.strip()


def schedule(job, kind, seconds, at):
    job['deadlineVersion'] = job.get('deadlineVersion', 0) + 1
    job['deadlineKind'] = kind
    job['deadline'] = (datetime.fromisoformat(at.replace('Z', '+00:00')) + timedelta(seconds=seconds)).isoformat().replace('+00:00', 'Z')
    job['overdue'] = False


def clear_deadline(job):
    job['deadlineVersion'] = job.get('deadlineVersion', 0) + 1
    job['deadline'] = ''
    job['deadlineKind'] = ''
    job['overdue'] = False


def canonical_role(role):
    return {'supervisor': 'manager', 'technician': 'worker', 'operator': 'reporter'}.get(role, role if role in {'admin', 'manager', 'worker', 'reporter'} else 'reporter')

def manages(user):
    return canonical_role(user['role']) in {'admin', 'manager'}

def visible(job, user):
    return manages(user) or job['reporterId'] == user['id'] or job.get('assigneeId') == user['id']


def transition(original, user, data, at=None, policy=None):
    at = at or now()
    policy = policy or {}
    action = data.get('action')
    if data.get('version') != original['version']:
        raise RuleError('This work order changed. Refresh before acting.', 409)
    supervisor = manages(user)
    owner = canonical_role(user['role']) == 'worker' and user['id'] == original.get('assigneeId')
    if not visible(original, user):
        raise RuleError('You cannot access this work order', 403)
    if action in {'approve', 'reassign', 'clarify', 'reject', 'merge', 'verify', 'rework', 'keep_separate', 'resolve_existing','skip'} and not supervisor:
        raise RuleError('Manager access required', 403)
    if action in {'accept', 'return', 'start', 'block', 'submit'} and not owner:
        raise RuleError('Only the currently assigned worker can do that', 403)
    if action in {'archive','restore'}:
        if not supervisor:raise RuleError('Manager access required',403)
        if original['status'] not in TERMINAL:raise RuleError('Only terminal work orders can be archived or restored',409)
        job=copy.deepcopy(original)
        job.update(archived=action=='archive',version=original['version']+1,updatedAt=at)
        return job,text(data.get('reason',''),'Reason',2000,False)
    if original.get('archived'):raise RuleError('Restore this work order before acting',409)
    if original['status'] in TERMINAL:
        raise RuleError('This work order is already closed, rejected or merged', 409)
    reason = data.get('reason', '')
    if action in {'return', 'clarify', 'reject', 'merge', 'block', 'rework', 'add_note', 'submit', 'keep_separate', 'resubmit', 'resolve_existing','skip'}:
        reason = text(reason, 'Reason')
    elif reason:
        reason = text(reason, 'Reason')
    job = copy.deepcopy(original)
    if action in {'approve', 'reassign'}:
        if action == 'approve' and job['status'] not in {'pending_review', 'needs_details'}:
            raise RuleError('Only new reports can be approved', 409)
        if action == 'reassign' and job['status'] not in {'open', 'in_progress'}:
            raise RuleError('This work order cannot be reassigned yet', 409)
        job.update(status='open', assignmentStatus='awaiting_acceptance',
                   assigneeId=text(data.get('assigneeId'), 'Worker', 128),
                   assigneeName=text(data.get('assigneeName', data.get('assigneeId')), 'Worker name', 200), blocked=False)
        schedule(job, 'acknowledgment', int(policy.get('ackMinutes',int(os.environ.get('ACK_SECONDS','3600'))//60))*60, at)
    elif action in {'accept', 'start'}:
        if job['status'] != 'open' or job['assignmentStatus'] != 'awaiting_acceptance':
            raise RuleError('Assignment is not awaiting acceptance', 409)
        job.update(status='in_progress', assignmentStatus='accepted', blocked=False)
        schedule(job, 'repair', int(policy.get('repairMinutes',int(os.environ.get('REPAIR_SECONDS','14400'))//60))*60, at)
    elif action == 'return':
        if job['status'] not in {'open', 'in_progress'} or job['assignmentStatus'] not in {'awaiting_acceptance', 'accepted'}:
            raise RuleError('Assignment cannot be returned', 409)
        job.update(status='open', assignmentStatus='returned', blocked=False)
        # Preserve the original deadline, but invalidate old owner callbacks.
        job['deadlineVersion'] += 1
    elif action == 'block':
        if job['status'] != 'in_progress':
            raise RuleError('Only repairs in progress can be blocked', 409)
        job['blocked'] = True
    elif action == 'submit':
        if job['status'] != 'in_progress' or job['assignmentStatus'] != 'accepted':
            raise RuleError('Start the assigned repair before submitting', 409)
        job.update(status='awaiting_verification', blocked=False)
        job['attachments'].extend(data.get('attachments', []))
        schedule(job, 'verification', int(policy.get('verifyMinutes',int(os.environ.get('VERIFY_SECONDS','7200'))//60))*60, at)
    elif action == 'verify':
        if job['status'] != 'awaiting_verification':
            raise RuleError('Repair is not awaiting verification', 409)
        job['status'] = 'closed'
        job['closedAt'] = at
        clear_deadline(job)
    elif action == 'rework':
        if job['status'] != 'awaiting_verification':
            raise RuleError('Repair is not awaiting verification', 409)
        job['status'] = 'in_progress'
        schedule(job, 'repair', int(policy.get('repairMinutes',int(os.environ.get('REPAIR_SECONDS','14400'))//60))*60, at)
    elif action == 'clarify':
        if job['status'] not in {'pending_review', 'needs_details'}:
            raise RuleError('Only pending reports can request clarification', 409)
        job['status'] = 'needs_details'
    elif action == 'reject':
        if job['status'] not in {'pending_review', 'needs_details'}:
            raise RuleError('Only pending reports can be rejected', 409)
        job['status'] = 'rejected'
        clear_deadline(job)
    elif action == 'merge':
        if job['status'] not in {'pending_review', 'needs_details', 'open'}:
            raise RuleError('Only unstarted work can be merged', 409)
        if data.get('targetId') == job['id']:
            raise RuleError('Cannot merge a report into itself')
        job.update(status='merged', mergedInto=text(data.get('targetId'), 'Target work order', 128))
        clear_deadline(job)
    elif action == 'resolve_existing':
        if job['status'] not in {'pending_review', 'needs_details'} and not (job['status'] == 'open' and job['assignmentStatus'] == 'returned'):
            raise RuleError('Only a new report or returned assignment can be confirmed already resolved', 409)
        job['status'] = 'closed'
        job['closedAt'] = at
        clear_deadline(job)
    elif action == 'skip':
        if not job.get('planId') or job['status'] not in {'pending_review','open'}:raise RuleError('Only unstarted planned work can be skipped',409)
        job['status']='skipped'
        clear_deadline(job)
    elif action == 'keep_separate':
        if not job.get('possibleDuplicate'):
            raise RuleError('No duplicate flag to dismiss', 409)
        job['possibleDuplicate'] = False
    elif action == 'resubmit':
        if user['id'] != job['reporterId']:
            raise RuleError('Only the original reporter can resubmit', 403)
        if job['status'] != 'needs_details':
            raise RuleError('This report is not awaiting clarification', 409)
        if data.get('description'):
            job['description'] = text(data['description'], 'Description', 4000)
        job['status'] = 'pending_review'
    elif action == 'add_note':
        pass
    else:
        raise RuleError('Unknown action')
    job.update(version=original['version'] + 1, updatedAt=at)
    return job, reason
