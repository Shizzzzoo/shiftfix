import pytest
from unittest.mock import Mock
from backend import api, storage
from backend.domain import RuleError, transition
from test_backend import aws, USER, create


def test_legacy_roles_and_verified_owner(monkeypatch):
    monkeypatch.setenv('SUPERVISOR_EMAIL','owner@example.test')
    assert api.role_from_groups(['supervisor'])=='manager'
    assert api.role_from_groups(['technician'])=='worker'
    assert api.role_from_groups(['operator'])=='reporter'
    assert api.role_from_groups(['supervisor'],'OWNER@example.test',True)=='admin'
    assert api.role_from_groups([],'owner@example.test',False)=='reporter'


@pytest.mark.parametrize('caller,target,desired',[
    ('reporter','reporter','worker'),('worker','reporter','manager'),
    ('manager','reporter','manager'),('manager','manager','worker'),
    ('manager','admin','reporter'),('admin','admin','worker'),
    ('admin','reporter','admin')])
def test_role_hierarchy_denials(monkeypatch,caller,target,desired):
    monkeypatch.setattr(api,'find_user',lambda id:{'Username':id})
    monkeypatch.setattr(api,'role_for',lambda u:target)
    with pytest.raises(RuleError):api.set_role('target',desired,{'id':'caller','role':caller})


def test_admin_promotes_manager_and_removes_legacy_groups(monkeypatch):
    client=Mock()
    client.admin_list_groups_for_user.return_value={'Groups':[{'GroupName':'technician'},{'GroupName':'reporter'}]}
    monkeypatch.setenv('USER_POOL_ID','mock')
    monkeypatch.setattr(api,'find_user',lambda id:{'Username':id})
    monkeypatch.setattr(api,'role_for',lambda u:'worker')
    monkeypatch.setattr(api.boto3,'client',lambda *a,**kw:client)
    assert api.set_role('t','manager',{'role':'admin'})=={'id':'t','role':'manager'}
    assert client.admin_remove_user_from_group.call_count==2
    assert client.admin_add_user_to_group.call_args.kwargs['GroupName']=='manager'


def test_manager_can_only_manage_workers_and_reporters(monkeypatch):
    client=Mock();client.admin_list_groups_for_user.return_value={'Groups':[{'GroupName':'reporter'}]}
    monkeypatch.setenv('USER_POOL_ID','mock')
    monkeypatch.setattr(api,'find_user',lambda id:{'Username':id})
    monkeypatch.setattr(api,'role_for',lambda u:'reporter')
    monkeypatch.setattr(api.boto3,'client',lambda *a,**kw:client)
    assert api.set_role('t','worker',{'role':'manager'})['role']=='worker'


def test_onboarding_completion_only_after_valid_save(aws):
    assert api.me(USER)['onboardingComplete'] is False
    data={'displayName':'Meera Patel','department':'production','machineIds':['M-012']}
    result=api.onboard(data,USER)
    assert result['onboardingComplete'] and result['name']=='Meera Patel'
    assert result['profile']==data
    assert result['role']=='reporter'  # onboarding never changes caller's authenticated authority
    assert api.onboard(data,USER)==result


@pytest.mark.parametrize('update',[
    {'displayName':'x'},{'displayName':'x'*101},{'department':'invalid'},
    {'department':[]},{'machineIds':['M-999']},{'machineIds':['M-012']*2},
    {'machineIds':'M-012'},{'role':'admin'}])
def test_invalid_onboarding_never_completes(aws,update):
    data={'displayName':'Meera Patel','department':'production','machineIds':[]}
    data.update(update)
    with pytest.raises(RuleError):api.onboard(data,USER)
    assert api.me(USER)['onboardingComplete'] is False


@pytest.mark.parametrize('size',[500*1024*1024,True,False,0,-1,2.5])
def test_bad_upload_sizes_rejected_before_signing(aws,monkeypatch,size):
    client=Mock();monkeypatch.setattr(api,'s3_client',lambda:client)
    with pytest.raises(RuleError):api.route('POST','/uploads',{'files':[{'name':'ok.jpg','type':'image/jpeg','size':12},{'name':'bad.jpg','type':'image/jpeg','size':size}]},USER,{})
    client.generate_presigned_post.assert_not_called()


def test_svg_masquerading_as_jpeg_rejected(aws):
    s3=api.s3_client();key='uploads/r/not-a-photo'
    s3.put_object(Bucket='shiftfix-test-assets',Key=key,Body=b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',ContentType='image/jpeg')
    with pytest.raises(RuleError,match='content does not match'):
        api.file_metadata([{'key':key,'name':'lie.jpg','type':'image/jpeg','size':42}],USER,'before')


@pytest.mark.parametrize('typ,magic',[('image/jpeg',b'\xff\xd8\xff\xe0more'),('image/png',b'\x89PNG\r\n\x1a\nmore'),('image/webp',b'RIFF0000WEBPmore')])
def test_supported_image_magic_accepted(aws,typ,magic):
    key='uploads/r/photo';api.s3_client().put_object(Bucket='shiftfix-test-assets',Key=key,Body=magic,ContentType=typ)
    assert api.file_metadata([{'key':key,'name':'photo','type':typ}],USER,'before')[0]['size']==len(magic)


def test_closed_recurrence_flag_never_auto_rejects_or_leaks_ids(aws):
    previous=create(category='hydraulic');item=storage.get_job(previous['id']);item['status']='closed'
    storage.table().put_item(Item=item)
    recurring=create('recurrence',category='hydraulic')
    assert recurring['possibleResolved'] and recurring['status']=='pending_review'
    assert 'relatedResolvedIds' not in recurring
    stored=storage.get_job(recurring['id'])
    assert stored['relatedResolvedIds']==[previous['id']]
    assert api.public(stored,{'role':'manager'})['relatedResolvedIds']==[previous['id']]


def test_manager_can_confirm_new_report_already_resolved():
    j={'id':'x','version':1,'status':'pending_review','reporterId':'r','assignmentStatus':'unassigned','deadlineVersion':0}
    out,_=transition(j,{'id':'m','role':'manager'},{'action':'resolve_existing','version':1,'reason':'Verified previous repair with maintenance log'})
    assert out['status']=='closed'
    with pytest.raises(RuleError):transition(j,{'id':'r','role':'reporter'},{'action':'resolve_existing','version':1,'reason':'already done'})


def test_handler_uses_current_authority_not_old_group_claim(monkeypatch):
    monkeypatch.setattr(api,'find_user',lambda id:{'Username':id})
    monkeypatch.setattr(api,'role_for',lambda u:'reporter')
    monkeypatch.setattr(api,'profile_for',lambda u:None)
    event={'requestContext':{'http':{'method':'GET'},'authorizer':{'jwt':{'claims':{'sub':'r','email_verified':'true','cognito:groups':'[manager]'}}}},'rawPath':'/me'}
    import json
    response=api.handler(event,None)
    assert response['statusCode']==200
    assert json.loads(response['body'])['role']=='reporter'


def test_malformed_upload_metadata_rejected_without_signing(aws,monkeypatch):
    client=Mock();monkeypatch.setattr(api,'s3_client',lambda:client)
    for entry in [None, {'name':'bad','type':[], 'size':12}, {'name':5,'type':'image/jpeg','size':12}]:
        with pytest.raises(RuleError):api.route('POST','/uploads',{'files':[entry]},USER,{})
    client.generate_presigned_post.assert_not_called()
