#!/usr/bin/python

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
module: f5_bigiq_revoke_license_by_mac
short_description: Revoke BIG-IQ pool license by device MAC address
description:
  - Revoke BIG-IQ pool license by device MAC address
author:
  - John Gruber (@jgruberf5)
notes:
  - Required BIG-IQ with license pool
options:
  bigiqhost:
    description:
      - The BIG-IQ host
    required: true
    default: None
    choices: []
    aliases: []
  bigiqusername:
    description:
      - The BIG-IQ Username
    required: true
    default: None
    choices: []
    aliases: []
  bigiqpassword:
    description:
      - The BIG-IQ Password
    required: true
    default: None
    choices: []
    aliases: []
  bigiqpool
    description:
      - The BIG-IQ Pool Name
    required: true
    default: None
    choices: []
    aliases: []
  devicemac
    description:
      - The MAC address associated with the activated license
    required: true
    default: None
    choices: []
    aliases: []
'''

EXAMPLES = '''
- name Revoke Device License
  f5_bigiq_revoke_license_by_mac:
    bigiqhost: 192.168.245.111
    bigiqusername: admin
    bigiqpassword: admin
    bigiqpool: BIGIPVEREGKEYS
    devicemac: '02:16:3e:7a:c9:d4'
'''

from ansible.module_utils.basic import AnsibleModule

import requests

CONNECT_TIMEOUT = 30


def _get_bigiq_session(bigiqhost, bigiqusername, bigiqpassword):
    ''' Creates a Requests Session to the BIG-IQ host configured '''
    if requests.__version__ < '2.9.1':
        requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member
    bigiq = requests.Session()
    bigiq.verify = False
    bigiq.headers.update({'Content-Type': 'application/json'})
    bigiq.timeout = CONNECT_TIMEOUT
    token_auth_body = {'username': bigiqusername,
                       'password': bigiqpassword,
                       'loginProviderName': 'local'}
    login_url = "https://%s/mgmt/shared/authn/login" % (bigiqhost)
    response = bigiq.post(login_url,
                          json=token_auth_body,
                          verify=False,
                          auth=requests.auth.HTTPBasicAuth(
                            bigiqusername, bigiqpassword))
    response_json = response.json()
    bigiq.headers.update(
        {'X-F5-Auth-Token': response_json['token']['token']})
    bigiq.base_url = 'https://%s/mgmt/cm/device/licensing/pool' % bigiqhost
    bigiq = bigiq
    return bigiq


def _get_pool_id(bigiq, bigiqpool):
    ''' Get a BIG-IQ license pool by its pool name. Returns first
        match of the specific pool type.
    :param: bigiq: BIG-IQ session object
    :param: bigiqpool: BIG-IQ pool name
    :returns: Pool ID string
    '''
    pools_url = '%s/regkey/licenses?$select=id,kind,name' % \
        bigiq.base_url
    # Now need to check both name and uuid for match. Can't filter.
    # query_filter = '&$filter=name%20eq%20%27'+pool_name+'%27'
    # pools_url = "%s%s" % (pools_url, query_filter)
    response = bigiq.get(pools_url)
    response.raise_for_status()
    response_json = response.json()
    pools = response_json['items']
    for pool in pools:
        if pool['name'] == bigiqpool or pool['id'] == bigiqpool:
            if str(pool['kind']).find('pool:regkey') > 1:
                return pool['id']
    return None


def _revoke_devicemac(bigiq, poolname, devicemac):
    ''' Get regkey, member_id tuple by management IP address
    :param: bigiq: BIG-IQ session object
    :param: bigiqpool: BIG-IQ pool name
    :param: devicemac: Device MAC address to check for
    :returns: list of regkey pool members with active keys
    '''
    pool_id = _get_pool_id(bigiq, poolname)
    pools_url = '%s/regkey/licenses' % bigiq.base_url
    offerings_url = '%s/%s/offerings' % (pools_url, pool_id)
    response = bigiq.get(offerings_url)
    response.raise_for_status()
    response_json = response.json()
    offerings = response_json['items']
    delete_url = None
    for offering in offerings:
        members_url = '%s/%s/members' % (
            offerings_url, offering['regKey'])
        response = bigiq.get(members_url)
        response.raise_for_status()
        response_json = response.json()
        members = response_json['items']
        for member in members:
            if member['macAddress'].lower() == devicemac:
                delete_url = '%s/%s' %  (members_url, member['id'])
    if delete_url:
        response = bigiq.delete(delete_url)
        response.raise_for_status()
        return True
    else:
        return False


def run_module():
    module_args = dict(
        bigiqhost=dict(type='str', required=True),
        bigiqusername=dict(type='str', required=True),
        bigiqpassword=dict(type='str', required=True),
        bigiqpool=dict(type='str', required=True),
        devicemac=dict(type='str', required=True)
    )

    result = dict(
        changed = False
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    try:
        bigiq = _get_bigiq_session(
            module.params['bigiqhost'],
            module.params['bigiqusername'],
            module.params['bigiqpassword']
        )
        revoked = _revoke_devicemac(
            bigiq,
            module.params['bigiqpool'],
            module.params['devicemac']
        )
        if (revoked):
            result['changed'] = True
        module.exit_json(**result)
    except Exception as ex:
        module.fail_json(msg="%s" % ex)


def main():
    run_module()

if __name__ == '__main__':
    main()