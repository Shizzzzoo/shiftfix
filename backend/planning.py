"""Hourly recurring maintenance: one auditable request, atomic schedule advancement."""
from datetime import datetime,timedelta,timezone
import uuid
from . import catalog,storage
from .domain import RuleError,now


def handler(event,context):
    at=now();processed=[];skipped=[]
    for plan in sorted(catalog.records('plans',True),key=lambda p:p['nextRun']):
        if len(processed)+len(skipped)>=20:break
        if not plan.get('enabled') or plan['nextRun']>at:continue
        try:
            expected_revision=catalog.revision()
            current=catalog.get('plans',plan['id'])
            if current['version']!=plan['version'] or not current.get('enabled') or current['nextRun']>at:continue
            plan=current
            machine=catalog.asset(plan['assetId'])
            scheduled=plan['nextRun'];instant=datetime.fromisoformat(at.replace('Z','+00:00'));due=datetime.fromisoformat(scheduled.replace('Z','+00:00'))
            interval=int(plan['intervalDays']);steps=(instant-due).days//interval+1
            next_run=(due+timedelta(days=interval*steps)).isoformat().replace('+00:00','Z')
            user={'id':plan['createdBy'],'name':'Preventive maintenance schedule','role':'manager'}
            id=str(uuid.uuid5(uuid.NAMESPACE_URL,'shiftfix-plan:'+plan['id']+':'+scheduled))
            job=catalog.request_job(machine,plan['name'],plan['description'],plan['priority'],user,id,planId=plan['id'],scheduledFor=scheduled)
            updated=dict(plan,nextRun=next_run,version=plan['version']+1,updatedAt=at,lastRun=at)
            storage.write(job,user,'planned_request_created',extra=[catalog.put(updated,plan),catalog.put(catalog.audit(plan,user,'scheduled_request_created',id)),catalog.revision_guard(expected_revision),catalog.work_reference(job)])
            processed.append({'planId':plan['id'],'workOrderId':id})
        except RuleError as exc:
            skipped.append({'planId':plan['id'],'reason':str(exc)})
    return {'processed':processed,'skipped':skipped}
