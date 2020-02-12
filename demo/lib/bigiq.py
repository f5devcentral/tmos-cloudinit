import os
import sys
import time
import datetime
import threading

from urlparse import urlparse

import requests

CONNECT_TIMEOUT = 30


def get_bigiq_session(host, username, password):
    ''' Creates a Requests Session to the BIG-IQ host configured '''
    if requests.__version__ < '2.9.1':
        requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member
    bigiq = requests.Session()
    bigiq.verify = False
    bigiq.headers.update({'Content-Type': 'application/json'})
    bigiq.timeout = CONNECT_TIMEOUT
    token_auth_body = {'username': username,
                       'password': password,
                       'loginProviderName': 'local'}
    login_url = "https://%s/mgmt/shared/authn/login" % (host)
    response = bigiq.post(login_url,
                          json=token_auth_body,
                          verify=False,
                          auth=requests.auth.HTTPBasicAuth(
                              username, password))
    response_json = response.json()
    bigiq.headers.update(
        {'X-F5-Auth-Token': response_json['token']['token']})
    bigiq.base_url = 'https://%s/mgmt/cm/device/licensing/pool' % host
    return bigiq


def get_pools(sess):
    pools_url = '%s/regkey/licenses?$select=id,kind,name' % \
        sess.base_url
    # Now need to check both name and uuid for match. Can't filter.
    # query_filter = '&$filter=name%20eq%20%27'+pool_name+'%27'
    # pools_url = "%s%s" % (pools_url, query_filter)
    response = sess.get(pools_url)
    response.raise_for_status()
    response_json = response.json()
    pools = response_json['items']
    return pools
