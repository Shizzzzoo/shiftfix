# Execute this file through the official AWS MCP run_script tool, not as a local CLI.
# The private artifact is built by build-demo-data.py and uploaded with get_presigned_url.
# MCP invocation: define this function, then result = await import_demo(); result
async def import_demo():
    stack=await call_boto3(service_name='cloudformation',operation_name='DescribeStacks',region_name='ap-south-1',params={'StackName':'shiftfix-live'})
    outputs={o['OutputKey']:o['OutputValue'] for o in stack['Stacks'][0]['Outputs']}
    params={p['ParameterKey']:p['ParameterValue'] for p in stack['Stacks'][0]['Parameters']}
    table=outputs['TableName'];bucket=params['CodeBucket']
    response=await call_boto3(service_name='s3',operation_name='GetObject',region_name='ap-south-1',params={'Bucket':bucket,'Key':'demo/shiftfix-history-v1/import.json'})
    body=response['Body'];payload=json.loads(body if isinstance(body,(str,bytes)) else body.read())
    assert payload['dataset']=='shiftfix-history-v1'
    meta=payload['manifest'];key={k:meta[k] for k in ['PK','SK']}
    existing=await call_boto3(service_name='dynamodb',operation_name='GetItem',region_name='ap-south-1',params={'TableName':table,'Key':key,'ConsistentRead':True})
    if existing.get('Item',{}).get('complete',{}).get('BOOL'):
        result={'alreadyComplete':True,'manifest':existing['Item']}
    else:
        items=payload['items'];written=0;preserved=0
        # Read every import key, honoring unprocessed keys; never overwrite any row.
        known={}
        for start in range(0,len(items),100):
            pending={table:{'Keys':[{k:i[k] for k in ['PK','SK']} for i in items[start:start+100]],'ConsistentRead':True}}
            attempts=0
            while pending:
                r=await call_boto3(service_name='dynamodb',operation_name='BatchGetItem',region_name='ap-south-1',params={'RequestItems':pending})
                for item in r.get('Responses',{}).get(table,[]):known[(item['PK']['S'],item['SK']['S'])]=item
                pending=r.get('UnprocessedKeys',{})
                if pending:
                    attempts+=1
                    if attempts>7:raise Exception('Unprocessed import keys after retries')
                    await asyncio.sleep(min(2**attempts/10,3))
        fresh=[]
        for item in items:
            old=known.get((item['PK']['S'],item['SK']['S']))
            if old:
                assert old.get('demoSeed',{}).get('S')==payload['dataset'], 'Refusing to overwrite non-demo key'
                preserved+=1
            else:fresh.append(item)
        for start in range(0,len(fresh),40):
            chunk=fresh[start:start+40];attempts=0
            while True:
                rev=await call_boto3(service_name='dynamodb',operation_name='GetItem',region_name='ap-south-1',params={'TableName':table,'Key':{'PK':{'S':'CATALOG_REVISION'},'SK':{'S':'META'}},'ConsistentRead':True})
                version=int(rev.get('Item',{}).get('version',{}).get('N','0'))
                guard={'TableName':table,'Key':{'PK':{'S':'CATALOG_REVISION'},'SK':{'S':'META'}},'UpdateExpression':'SET #v = :next','ConditionExpression':'#v = :old' if version else 'attribute_not_exists(#v)','ExpressionAttributeNames':{'#v':'version'},'ExpressionAttributeValues':{':next':{'N':str(version+1)}}}
                if version:guard['ExpressionAttributeValues'][':old']={'N':str(version)}
                writes=[{'Put':{'TableName':table,'Item':i,'ConditionExpression':'attribute_not_exists(PK)'}} for i in chunk]+[{'Update':guard}]
                try:
                    await call_boto3(service_name='dynamodb',operation_name='TransactWriteItems',region_name='ap-south-1',params={'TransactItems':writes})
                    written+=len(chunk);break
                except ClientError as exc:
                    if exc.response['Error']['Code'] not in ['TransactionCanceledException','TransactionConflictException','ProvisionedThroughputExceededException','ThrottlingException']:raise
                    attempts+=1
                    if attempts>6:raise
                    await asyncio.sleep(min(2**attempts/10,3))
        # Complete only after every item is written. Replays preserve this snapshot.
        await call_boto3(service_name='dynamodb',operation_name='PutItem',region_name='ap-south-1',params={'TableName':table,'Item':meta,'ConditionExpression':'attribute_not_exists(PK)'})
        result={'written':written,'preserved':preserved,'manifest':meta}
    return result
