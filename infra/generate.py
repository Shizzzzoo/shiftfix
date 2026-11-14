import json
from pathlib import Path
R={}
def ref(x): return {'Ref':x}
def arn(x): return {'Fn::GetAtt':[x,'Arn']}
def sub(x): return {'Fn::Sub':x}
def add(n,t,p,retain=False):
 R[n]={'Type':t,'Properties':p,'Metadata':{'com.aws.cloudformation.Context':{'why':'ShiftFix maintenance prototype','must':'Private data; role-authorized access; no always-running compute'}}}
 if retain:R[n].update(DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
def role(n,service,statements):
 add(n,'AWS::IAM::Role',{'RoleName':sub('${AWS::StackName}-'+n),'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':service},'Action':'sts:AssumeRole'}]},'Policies':[{'PolicyName':'ScopedRuntime','PolicyDocument':{'Version':'2012-10-17','Statement':statements}}]})
def allow(actions,res):return {'Effect':'Allow','Action':actions,'Resource':res}
logs=allow(['logs:CreateLogStream','logs:PutLogEvents'],sub('arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-*:*'))
for n in ['Assets','Web']:
 add(n,'AWS::S3::Bucket',{'PublicAccessBlockConfiguration':{k:True for k in ['BlockPublicAcls','BlockPublicPolicy','IgnorePublicAcls','RestrictPublicBuckets']},'BucketEncryption':{'ServerSideEncryptionConfiguration':[{'ServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]},'VersioningConfiguration':{'Status':'Enabled'},**({'CorsConfiguration':{'CorsRules':[{'AllowedHeaders':['*'],'AllowedMethods':['GET','POST'],'AllowedOrigins':[sub('https://${Distribution.DomainName}'), 'http://localhost:5173'],'MaxAge':300}]}} if n=='Assets' else {})},True)
add('Table','AWS::DynamoDB::Table',{'BillingMode':'PAY_PER_REQUEST','AttributeDefinitions':[{'AttributeName':k,'AttributeType':'S'} for k in ['PK','SK','GSI1PK','GSI1SK']],'KeySchema':[{'AttributeName':'PK','KeyType':'HASH'},{'AttributeName':'SK','KeyType':'RANGE'}],'GlobalSecondaryIndexes':[{'IndexName':'GSI1','KeySchema':[{'AttributeName':'GSI1PK','KeyType':'HASH'},{'AttributeName':'GSI1SK','KeyType':'RANGE'}],'Projection':{'ProjectionType':'ALL'}}],'StreamSpecification':{'StreamViewType':'NEW_IMAGE'},'SSESpecification':{'SSEEnabled':True},'PointInTimeRecoverySpecification':{'PointInTimeRecoveryEnabled':True}},True)
role('ApiRole','lambda.amazonaws.com',[logs,allow(['dynamodb:GetItem','dynamodb:PutItem','dynamodb:UpdateItem','dynamodb:Query','dynamodb:ConditionCheckItem'],[arn('Table'),sub('${Table.Arn}/index/*')]),allow(['s3:GetObject','s3:PutObject'],sub('${Assets.Arn}/*')),allow(['cognito-idp:ListUsers','cognito-idp:AdminListGroupsForUser','cognito-idp:AdminAddUserToGroup','cognito-idp:AdminRemoveUserFromGroup'],arn('UserPool'))])
role('AuthRole','lambda.amazonaws.com',[logs,allow(['cognito-idp:AdminAddUserToGroup'],sub('arn:${AWS::Partition}:cognito-idp:${AWS::Region}:${AWS::AccountId}:userpool/*'))])
role('TimerRole','lambda.amazonaws.com',[logs,allow(['dynamodb:GetItem','dynamodb:Query','dynamodb:UpdateItem','dynamodb:PutItem'],arn('Table'))])
role('StreamRole','lambda.amazonaws.com',[logs,allow(['dynamodb:DescribeStream','dynamodb:GetRecords','dynamodb:GetShardIterator'],{'Fn::GetAtt':['Table','StreamArn']}),allow(['dynamodb:ListStreams'],'*'),allow(['states:StartExecution'],ref('Workflow')),allow(['sqs:SendMessage'],arn('DeadLetters'))])
def fn(n,handler,rol,env):
 add(n,'AWS::Lambda::Function',{'FunctionName':sub('${AWS::StackName}-'+n),'Runtime':'python3.13','Handler':handler,'Role':arn(rol),'Code':{'S3Bucket':ref('CodeBucket'),'S3Key':ref('CodeKey')},'MemorySize':256,'Timeout':25,'Environment':{'Variables':env}})
 add(n+'Log','AWS::Logs::LogGroup',{'LogGroupName':sub('/aws/lambda/${AWS::StackName}-'+n),'RetentionInDays':7})
fn('Auth','backend.auth.post_confirmation','AuthRole',{'SUPERVISOR_EMAIL':ref('SupervisorEmail')})
add('UserPool','AWS::Cognito::UserPool',{'UserPoolName':sub('${AWS::StackName}-users'),'UsernameAttributes':['email'],'AutoVerifiedAttributes':['email'],'Policies':{'PasswordPolicy':{'MinimumLength':12,'RequireLowercase':True,'RequireUppercase':True,'RequireNumbers':True,'RequireSymbols':True}},'Schema':[{'Name':'email','Required':True,'Mutable':True},{'Name':'name','Required':True,'Mutable':True}],'LambdaConfig':{'PostConfirmation':arn('Auth')}} ,True)
add('AuthPermission','AWS::Lambda::Permission',{'Action':'lambda:InvokeFunction','FunctionName':ref('Auth'),'Principal':'cognito-idp.amazonaws.com','SourceArn':arn('UserPool'),'SourceAccount':ref('AWS::AccountId')})
for name in ['supervisor','technician','operator']:add(name+'Group','AWS::Cognito::UserPoolGroup',{'GroupName':name,'UserPoolId':ref('UserPool')})
add('Client','AWS::Cognito::UserPoolClient',{'UserPoolId':ref('UserPool'),'GenerateSecret':False,'ExplicitAuthFlows':['ALLOW_USER_PASSWORD_AUTH','ALLOW_REFRESH_TOKEN_AUTH'],'PreventUserExistenceErrors':'ENABLED','AccessTokenValidity':1,'IdTokenValidity':1,'RefreshTokenValidity':7,'SupportedIdentityProviders':['COGNITO']})
env={'TABLE_NAME':ref('Table'),'ASSETS_BUCKET':ref('Assets'),'USER_POOL_ID':ref('UserPool'),'SUPERVISOR_EMAIL':ref('SupervisorEmail'),'ACK_SECONDS':'3600','REPAIR_SECONDS':'14400','VERIFY_SECONDS':'7200'}
fn('Api','backend.api.handler','ApiRole',env)
fn('Timer','backend.deadlines.expire_handler','TimerRole',{'TABLE_NAME':ref('Table')})
role('WorkflowRole','states.amazonaws.com',[allow(['lambda:InvokeFunction'],arn('Timer'))])
add('Workflow','AWS::StepFunctions::StateMachine',{'StateMachineName':sub('${AWS::StackName}-deadlines'),'StateMachineType':'STANDARD','RoleArn':arn('WorkflowRole'),'Definition':{'Comment':'Versioned deadline wait; authoritative state checked at execution','StartAt':'WaitForDeadline','States':{'WaitForDeadline':{'Type':'Wait','TimestampPath':'$.deadline','Next':'CheckCurrentAssignment'},'CheckCurrentAssignment':{'Type':'Task','Resource':arn('Timer'),'Retry':[{'ErrorEquals':['Lambda.ServiceException','Lambda.AWSLambdaException','Lambda.SdkClientException','States.TaskFailed'],'IntervalSeconds':2,'MaxAttempts':3,'BackoffRate':2}],'End':True}}}})
add('DeadLetters','AWS::SQS::Queue',{'SqsManagedSseEnabled':True,'MessageRetentionPeriod':1209600})
fn('Stream','backend.deadlines.stream_handler','StreamRole',{'STATE_MACHINE_ARN':ref('Workflow')})
add('StreamMapping','AWS::Lambda::EventSourceMapping',{'EventSourceArn':{'Fn::GetAtt':['Table','StreamArn']},'FunctionName':ref('Stream'),'StartingPosition':'LATEST','BatchSize':10,'FunctionResponseTypes':['ReportBatchItemFailures'],'BisectBatchOnFunctionError':True,'MaximumRetryAttempts':5,'DestinationConfig':{'OnFailure':{'Destination':arn('DeadLetters')}},'FilterCriteria':{'Filters':[{'Pattern':json.dumps({'eventName':['INSERT'],'dynamodb':{'NewImage':{'PK':{'S':[{'prefix':'TIMER#'}]}}}})}]}})
add('HttpApi','AWS::ApiGatewayV2::Api',{'Name':sub('${AWS::StackName}-api'),'ProtocolType':'HTTP','CorsConfiguration':{'AllowOrigins':[sub('https://${Distribution.DomainName}'),'http://localhost:5173'],'AllowHeaders':['Content-Type','Authorization','Idempotency-Key'],'AllowMethods':['GET','POST','OPTIONS']}})
add('Authorizer','AWS::ApiGatewayV2::Authorizer',{'ApiId':ref('HttpApi'),'AuthorizerType':'JWT','IdentitySource':['$request.header.Authorization'],'Name':'Cognito','JwtConfiguration':{'Audience':[ref('Client')],'Issuer':sub('https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPool}')}})
add('Integration','AWS::ApiGatewayV2::Integration',{'ApiId':ref('HttpApi'),'IntegrationType':'AWS_PROXY','IntegrationUri':arn('Api'),'PayloadFormatVersion':'2.0'})
add('Route','AWS::ApiGatewayV2::Route',{'ApiId':ref('HttpApi'),'RouteKey':'ANY /{proxy+}','AuthorizationType':'JWT','AuthorizerId':ref('Authorizer'),'Target':{'Fn::Join':['/',['integrations',ref('Integration')]]}})
add('ApiAccessLog','AWS::Logs::LogGroup',{'RetentionInDays':7})
add('Stage','AWS::ApiGatewayV2::Stage',{'ApiId':ref('HttpApi'),'StageName':'$default','AutoDeploy':True,'DefaultRouteSettings':{'ThrottlingBurstLimit':10,'ThrottlingRateLimit':5},'AccessLogSettings':{'DestinationArn':arn('ApiAccessLog'),'Format':'{"requestId":"$context.requestId","status":"$context.status","route":"$context.routeKey"}'}})
add('ApiPermission','AWS::Lambda::Permission',{'Action':'lambda:InvokeFunction','FunctionName':ref('Api'),'Principal':'apigateway.amazonaws.com','SourceArn':sub('arn:${AWS::Partition}:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*/*/*')})
add('Oac','AWS::CloudFront::OriginAccessControl',{'OriginAccessControlConfig':{'Name':sub('${AWS::StackName}-web'),'OriginAccessControlOriginType':'s3','SigningBehavior':'always','SigningProtocol':'sigv4'}})
add('Distribution','AWS::CloudFront::Distribution',{'DistributionConfig':{'Enabled':True,'DefaultRootObject':'index.html','HttpVersion':'http2','PriceClass':'PriceClass_100','Origins':[{'Id':'web','DomainName':{'Fn::GetAtt':['Web','RegionalDomainName']},'S3OriginConfig':{'OriginAccessIdentity':''},'OriginAccessControlId':ref('Oac')}],'DefaultCacheBehavior':{'TargetOriginId':'web','ViewerProtocolPolicy':'redirect-to-https','AllowedMethods':['GET','HEAD','OPTIONS'],'CachedMethods':['GET','HEAD'],'Compress':True,'ForwardedValues':{'QueryString':False,'Cookies':{'Forward':'none'}},'MinTTL':0,'DefaultTTL':60,'MaxTTL':86400},'CustomErrorResponses':[{'ErrorCode':403,'ResponseCode':200,'ResponsePagePath':'/index.html','ErrorCachingMinTTL':0},{'ErrorCode':404,'ResponseCode':200,'ResponsePagePath':'/index.html','ErrorCachingMinTTL':0}]}})
for n in ['Assets','Web']:
 statements=[{'Effect':'Deny','Principal':'*','Action':'s3:*','Resource':[arn(n),sub('${'+n+'.Arn}/*')],'Condition':{'Bool':{'aws:SecureTransport':'false'}}}]
 if n=='Web':statements.append({'Effect':'Allow','Principal':{'Service':'cloudfront.amazonaws.com'},'Action':'s3:GetObject','Resource':sub('${Web.Arn}/*'),'Condition':{'StringEquals':{'AWS:SourceArn':sub('arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${Distribution}')}}})
 add(n+'Policy','AWS::S3::BucketPolicy',{'Bucket':ref(n),'PolicyDocument':{'Version':'2012-10-17','Statement':statements}})
outputs={'ApiUrl':{'Fn::GetAtt':['HttpApi','ApiEndpoint']},'AppUrl':sub('https://${Distribution.DomainName}'),'UserPoolId':ref('UserPool'),'ClientId':ref('Client'),'AssetsBucket':ref('Assets'),'WebBucket':ref('Web'),'TableName':ref('Table'),'ApiFunction':ref('Api'),'WorkflowArn':ref('Workflow'),'DistributionId':ref('Distribution')}
# Account CloudFront verification restriction: serve static bundle via public Lambda routes.
for key in ['Web','WebPolicy','Oac','Distribution']: R.pop(key,None)
R['Assets']['Properties']['CorsConfiguration']['CorsRules'][0]['AllowedOrigins']=[{'Fn::GetAtt':['HttpApi','ApiEndpoint']},'http://localhost:5173']
R['HttpApi']['Properties']['CorsConfiguration']['AllowOrigins']=['http://localhost:5173']
role('StaticRole','lambda.amazonaws.com',[logs])
fn('Static','backend.static.handler','StaticRole',{})
R['Static']['Properties'].pop('Environment')
add('StaticIntegration','AWS::ApiGatewayV2::Integration',{'ApiId':ref('HttpApi'),'IntegrationType':'AWS_PROXY','IntegrationUri':arn('Static'),'PayloadFormatVersion':'2.0'})
for i,path in enumerate(['/','/config.json','/assets/{proxy+}']):
 add('StaticRoute'+str(i),'AWS::ApiGatewayV2::Route',{'ApiId':ref('HttpApi'),'RouteKey':'GET '+path,'AuthorizationType':'NONE','Target':{'Fn::Join':['/',['integrations',ref('StaticIntegration')]]}})
add('StaticPermission','AWS::Lambda::Permission',{'Action':'lambda:InvokeFunction','FunctionName':ref('Static'),'Principal':'apigateway.amazonaws.com','SourceArn':sub('arn:${AWS::Partition}:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*/GET/*')})
outputs.pop('WebBucket');outputs.pop('DistributionId');outputs['AppUrl']={'Fn::GetAtt':['HttpApi','ApiEndpoint']}
outputs['StaticFunction']=ref('Static')
t={'AWSTemplateFormatVersion':'2010-09-09','Description':'ShiftFix - private factory fault evidence, role-based repair review and durable deadline escalation.','Metadata':{'AWSToolsMetrics':{'AWSAgentToolkit':'aws-cloudformation@3'}},'Parameters':{'CodeBucket':{'Type':'String'},'CodeKey':{'Type':'String'},'SupervisorEmail':{'Type':'String'}},'Resources':R,'Outputs':{k:{'Value':v} for k,v in outputs.items()}}
Path(__file__).with_name('template.json').write_text(json.dumps(t,indent=2))
print(len(json.dumps(t)), 'bytes')
