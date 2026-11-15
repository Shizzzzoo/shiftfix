"""Small typed tool contract exposed to the model; all input is checked again."""
from .assistant_tools import PAGES,STATUSES
S={'type':'string'}
def spec(name,description,properties,required=()):
    return {'toolSpec':{'name':name,'description':description,'inputSchema':{'json':{'type':'object','properties':properties,'required':list(required),'additionalProperties':False}}}}

def configuration():
    return {'tools':[
        spec('workspace_overview','Get computed work-order totals for the current user. Always use live tools for facts.',{}),
        spec('search_work_orders','Search authorized work orders. Totals are exact before the result limit. Dates are created-at UTC dates. Use assigneeId or reporterId me for the current user.',{**{k:S for k in ['query','machineId','assigneeId','reporterId','from','to']},'status':{'type':'string','enum':STATUSES},'priority':{'type':'string','enum':['low','medium','high','critical']},'overdue':{'type':'boolean'},'archived':{'type':'boolean'},'limit':{'type':'integer','minimum':1,'maximum':20}}),
        spec('work_order_details','Read one accessible work order and its recent activity using its ID or WO number.',{'id':S},['id']),
        spec('search_catalog','Search registered assets, inventory, locations, plans, meters or automation rules. lowStock means quantity at or below minQuantity. Search assets first to resolve names to IDs. Access is checked by the server.',{'kind':{'type':'string','enum':list(PAGES)},'query':S,'lowStock':{'type':'boolean'},'limit':{'type':'integer','minimum':1,'maximum':20}},['kind']),
        spec('search_people','Management-only directory search. Returns permitted work metadata; contact phone and biography are excluded.',{'query':S,'limit':{'type':'integer','minimum':1,'maximum':20}}),
        spec('draft_work_order','Prepare a work order for human confirmation. Does not create it. Resolve machineId with search_catalog first; ask for missing fault details.',{'machineId':S,'title':S,'description':S,'priority':{'type':'string','enum':['low','medium','high','critical']},'category':S},['machineId','title','description']),
        spec('draft_rule','Management-only draft for a new paused meter automation or recurring plan. Resolve IDs through search_catalog. A person reviews and saves it in the existing editor. Supported automation fields: name,meterId. Plan fields: name,assetId,description,intervalDays,nextRun (ISO UTC ending Z),priority.',{'kind':{'type':'string','enum':['plans','automations']},'fields':{'type':'object'}},['kind','fields']),
    ]}
