import pytest
from unittest.mock import Mock
from backend import api,clients,storage
from backend.domain import RuleError
from test_backend import aws,USER


def initial():
    return api.onboard({'displayName':'Team member','department':'maintenance','machineIds':['M-012']},USER)


def edit(version=0,**extra):
    return {'displayName':'Meera Patel','department':'engineering','machineIds':['M-012'],'jobTitle':'Maintenance engineer','phone':'+91 555 0100','shift':'rotating','bio':'Hydraulics and safe handovers.','version':version,**extra}


def test_profile_upgrade_is_private_versioned_and_preserves_authority(aws):
    initial()
    changed=api.route('POST','/profile',edit(),USER,{})
    assert changed['role']=='reporter'
    assert changed['profile']['version']==1 and changed['name']=='Meera Patel'
    assert changed['profile']['jobTitle']=='Maintenance engineer'
    assert api.me(USER)['profile']==changed['profile']
    # The old onboarding path cannot replace an edited profile.
    with pytest.raises(RuleError) as e:initial()
    assert e.value.status==409
    assert api.me(USER)['profile']['bio']=='Hydraulics and safe handovers.'
    other={'id':'other','role':'reporter','name':'Someone else'}
    assert api.me(other)['profile'] is None
    with pytest.raises(RuleError):api.update_profile(edit(),other)


def test_stale_profile_cannot_overwrite_another_session(aws):
    initial();api.update_profile(edit(),USER)
    with pytest.raises(RuleError) as e:api.update_profile(edit(displayName='Old session'),USER)
    assert e.value.status==409
    assert api.me(USER)['name']=='Meera Patel'
    assert api.update_profile(edit(1,displayName='Meera P.'),USER)['profile']['version']==2


@pytest.mark.parametrize('change',[
    {'role':'admin'},{'email':'different@example.test'},{'id':'someone-else'},
    {'version':True},{'version':-1},{'version':1.5},{'version':'0'},
    {'displayName':' '},{'department':[]},{'machineIds':['M-012']*2},
    {'machineIds':['not-registered']},{'machineIds':list('abcde')},
    {'jobTitle':'x'*101},{'phone':'x'*41},{'bio':'x'*601},{'shift':'not-a-shift'},
])
def test_invalid_profile_never_changes_saved_details(aws,change):
    before=initial()['profile']
    with pytest.raises(RuleError):api.update_profile(edit(**change),USER)
    assert api.me(USER)['profile']==before


def test_sdk_pool_reuse_does_not_cache_user_authority(monkeypatch):
    client=Mock();monkeypatch.setenv('USER_POOL_ID','test')
    monkeypatch.setattr(clients.boto3,'client',lambda *a,**kw:client)
    client.admin_list_groups_for_user.side_effect=[{'Groups':[{'GroupName':'manager'}]},{'Groups':[{'GroupName':'reporter'}]}]
    assert api.role_for({'Username':'person'})=='manager'
    assert api.role_for({'Username':'person'})=='reporter'
    assert client.admin_list_groups_for_user.call_count==2
    assert clients.client.cache_info().hits==1


def test_table_pool_keeps_table_identity_separate(aws,monkeypatch):
    first=storage.table()
    assert storage.table() is first
    monkeypatch.setenv('TABLE_NAME','other-table')
    assert storage.table() is not first
