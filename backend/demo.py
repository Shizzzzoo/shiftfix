"""Fictional display-only people and dataset disclosure. Never creates identities."""
from . import storage
DATASET='shiftfix-history-v1'

def manifest():
    record=storage.table().get_item(Key={'PK':'DEMO#'+DATASET,'SK':'META'},ConsistentRead=True).get('Item')
    if not record or not record.get('complete'):return None
    return {k:record[k] for k in ['dataset','label','start','end','workOrders']}

def people():
    if not manifest():return []
    args={'KeyConditionExpression':'PK = :p AND begins_with(SK, :s)','ExpressionAttributeValues':{':p':'DEMO#'+DATASET,':s':'PERSON#'},'ConsistentRead':True};out=[]
    while True:
        page=storage.table().query(**args)
        out.extend({k:r[k] for k in ['id','name','email','role','demo','canSignIn']} for r in page.get('Items',[]))
        if not page.get('LastEvaluatedKey'):return out
        args['ExclusiveStartKey']=page['LastEvaluatedKey']
