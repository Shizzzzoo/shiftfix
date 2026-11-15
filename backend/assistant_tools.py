"""Allowlisted, role-scoped data tools. No arbitrary API paths or database queries."""
from collections import Counter
from datetime import date
from . import catalog, storage
from .domain import RuleError, manages, text, visible
from . import assistant_drafts as drafts

PAGES={'assets':'Assets','asset_types':'Asset types','categories':'Categories','locations':'Locations','zones':'Zones','subzones':'Sub-zones','teams':'Teams','vendors':'Vendors','part_types':'Part types','part_locations':'Part locations','parts':'Parts','purchases':'Purchase management','meters':'Meters','inspection_templates':'Inspection templates','inspection_responses':'Inspection responses','plans':'Recurrence','automations':'Automations','life_tracking':'Life tracking'}
JOB_FIELDS=['id','number','title','machineId','machineName','status','priority','assigneeName','assigneeId','reporterName','createdAt','deadline','overdue','archived','version']
CAT_FIELDS=['id','name','code','sku','description','typeId','categoryId','locationId','zoneId','subzoneId','teamId','partId','meterId','assetId','quantity','minQuantity','unit','enabled','nextRun','intervalDays','minValue','maxValue','lastValue','status','version']
STATUSES=['pending_review','needs_details','open','in_progress','awaiting_verification','closed','rejected','merged','skipped']


def checked(data,allowed):
    if not isinstance(data,dict) or set(data)-set(allowed):raise RuleError('Unknown tool fields')
    return data


def query(data):return text(data.get('query',''),'Search',200,False).casefold()
def limit(data):
    n=data.get('limit',10)
    if isinstance(n,bool) or not isinstance(n,int) or not 1<=n<=20:raise RuleError('Limit must be 1 to 20')
    return n

def job_public(j,demo_only=False):
    out={k:j[k] for k in JOB_FIELDS if k in j}
    if demo_only:
        # A demo job may have been reassigned to a genuine account after import.
        # Never export that person's identity through the free provider.
        if not str(j.get('assigneeId','')).startswith('demo-person-'):
            out.pop('assigneeId',None);out.pop('assigneeName',None)
        if not str(j.get('reporterId','')).startswith('demo-person-'):out.pop('reporterName',None)
    return out
def reference(j):return {'kind':'work_order','id':j['id'],'label':j['number']+' · '+j['title'][:70]}
def page_reference(kind):return {'kind':'page','page':PAGES[kind],'label':PAGES[kind]}


class WorkspaceTools:
    def __init__(self,user,request_id,demo_only=False):
        self.demo_only=demo_only;self.user=user;self.request_id=request_id;self.sources={};self.drafts=[];self._jobs=None

    def jobs(self):
        if self._jobs is None:
            rows=[j for j in storage.list_jobs() if visible(j,self.user)]
            # Recheck non-management candidates with strong reads so a stale GSI
            # assignment cannot expose a work order after reassignment.
            if not manages(self.user):rows=[storage.get_job(j['id']) for j in rows]
            self._jobs=[j for j in rows if visible(j,self.user) and (not self.demo_only or j.get('demo') is True)]
        return self._jobs

    def add_sources(self,rows):
        for source in rows:
            key=source.get('id') or source.get('page')
            if len(self.sources)<20:self.sources[key]=source

    def execute(self,name,data):
        if name=='workspace_overview':
            checked(data,[]);jobs=self.jobs()
            return {'accessibleWorkOrders':len(jobs),'byStatus':dict(Counter(j['status'] for j in jobs)),'overdue':sum(bool(j.get('overdue')) for j in jobs if j['status'] not in ['closed','rejected','merged','skipped']),'role':self.user['role']}
        if name=='search_work_orders':return self.search_jobs(data)
        if name=='work_order_details':return self.details(data)
        if name=='search_catalog':return self.search_catalog(data)
        if name=='search_people':return self.people(data)
        if name=='draft_work_order':
            if self.demo_only:
                checked(data,['machineId','title','description','priority','category'])
                self.demo_reference('assets',data.get('machineId'))
            draft=drafts.work_order(data,self.user,self.request_id);self.drafts.append(draft)
            return {'draft':draft,'instruction':'Draft only. Nothing was created. The person must review and press Confirm create.'}
        if name=='draft_rule':
            if self.demo_only:
                checked(data,['kind','fields'])
                fields=data.get('fields',{})
                if not isinstance(fields,dict):raise RuleError('Invalid rule fields')
                self.demo_reference('meters' if data.get('kind')=='automations' else 'assets',fields.get('meterId') if data.get('kind')=='automations' else fields.get('assetId'))
            draft=drafts.rule(data,self.user,self.request_id);self.drafts.append(draft)
            return {'draft':draft,'instruction':'Draft only, paused. Open the regular editor to review and save. No rule was created or enabled.'}
        raise RuleError('This tool is not available',403)

    def demo_reference(self,kind,id):
        record=catalog.asset(id) if kind=='assets' else catalog.get(kind,id)
        if record.get('demo') is not True:raise RuleError('This assistant mode supports fictional demo equipment only. Use the normal editor for workspace records.',403)

    def search_jobs(self,data):
        checked(data,['query','status','priority','machineId','assigneeId','reporterId','overdue','from','to','archived','limit'])
        for k in ['machineId','assigneeId','reporterId']:
            if k in data and (not isinstance(data[k],str) or not 1<=len(data[k])<=128):raise RuleError('Invalid '+k)
        data=dict(data)
        for k in ['assigneeId','reporterId']:
            if data.get(k) in ['me','self']:data[k]=self.user['id']
            if data.get(k) and not manages(self.user) and data[k]!=self.user['id']:raise RuleError('You may search your own accessible work only',403)
        for k,choices in [('status',STATUSES),('priority',['low','medium','high','critical'])]:
            if k in data and data[k] not in choices:raise RuleError('Invalid '+k)
        for k in ['overdue','archived']:
            if k in data and not isinstance(data[k],bool):raise RuleError(k+' must be true or false')
        for k in ['from','to']:
            if k in data:
                try:date.fromisoformat(data[k])
                except (ValueError,TypeError):raise RuleError('Dates must use YYYY-MM-DD (UTC)')
        if data.get('from') and data.get('to') and data['from']>data['to']:raise RuleError('End date must follow start date')
        needle=query(data);n=limit(data)
        rows=[j for j in self.jobs() if bool(j.get('archived'))==data.get('archived',False)]
        for k in ['status','priority','machineId','assigneeId','reporterId','overdue']:
            if k in data:rows=[j for j in rows if j.get(k)==data[k]]
        if data.get('from'):rows=[j for j in rows if j['createdAt'][:10]>=data['from']]
        if data.get('to'):rows=[j for j in rows if j['createdAt'][:10]<=data['to']]
        if needle:rows=[j for j in rows if needle in ' '.join(str(j.get(k,'')) for k in ['number','title','description','machineName','machineId','assigneeName','reporterName','locationName','category']).casefold()]
        picked=rows[:n];self.add_sources([reference(j) for j in picked])
        return {'totalMatches':len(rows),'returned':len(picked),'byStatus':dict(Counter(j['status'] for j in rows)),'items':[job_public(j,self.demo_only) for j in picked],'scope':'Only records this user may access; totalMatches is computed before limiting.'}

    def details(self,data):
        checked(data,['id']);id=text(data.get('id'),'Work order ID',128)
        matches=[j for j in self.jobs() if j['id']==id or j['number'].casefold()==id.casefold()]
        if len(matches)!=1:raise RuleError('Work order unavailable or ambiguous in your accessible records',404)
        j=matches[0];self.add_sources([reference(j)])
        return {**job_public(j,self.demo_only),'description':j.get('description','')[:2000],'attachmentCount':len(j.get('attachments',[])),'activity':[{k:str(e.get(k,''))[:500] for k in ['action','at','actorName','reason']} for e in storage.events(j['id'])[-10:] if not self.demo_only or e.get('demo') is True]}

    def search_catalog(self,data):
        checked(data,['kind','query','lowStock','limit']);kind=data.get('kind')
        if not isinstance(kind,str):raise RuleError('Choose a catalog kind')
        catalog.permitted(self.user,kind)
        needle=query(data);n=limit(data)
        if 'lowStock' in data and not isinstance(data['lowStock'],bool):raise RuleError('lowStock must be true or false')
        if data.get('lowStock') and kind!='parts':raise RuleError('lowStock is supported for parts only')
        rows=catalog.machines() if kind=='assets' else catalog.records(kind,True)
        if self.demo_only:rows=[r for r in rows if r.get('demo') is True]
        if needle:rows=[r for r in rows if needle in ' '.join(str(r.get(k,'')) for k in ['id','name','code','sku','description']).casefold()]
        if data.get('lowStock'):rows=[r for r in rows if r.get('quantity',0)<=r.get('minQuantity',0)]
        self.add_sources([page_reference(kind)])
        return {'kind':kind,'totalMatches':len(rows),'items':[{k:(v[:500] if isinstance(v,str) else v) for k,v in r.items() if k in CAT_FIELDS} for r in rows[:n]]}

    def people(self,data):
        checked(data,['query','limit'])
        if not manages(self.user):raise RuleError('Only Admins and Managers may search the people directory',403)
        from . import api
        needle=query(data);n=limit(data)
        rows=api.route('GET','/users',{},self.user,{})['items']
        if self.demo_only:rows=[r for r in rows if r.get('demo') is True]
        if needle:rows=[r for r in rows if needle in ' '.join(str(r.get(k,'')) for k in ['id','name','department','jobTitle','role']).casefold()]
        self.add_sources([{'kind':'page','page':'Users','label':'People & access'}])
        return {'totalMatches':len(rows),'items':[{k:r[k] for k in ['id','name','role','department','jobTitle','shift','demo'] if k in r} for r in rows[:n]]}
