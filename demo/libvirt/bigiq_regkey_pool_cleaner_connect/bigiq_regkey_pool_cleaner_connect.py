#!/usr/bin/env python

# coding=utf-8
# pylint: disable=broad-except,unused-argument,line-too-long, unused-variable
# Copyright (c) 2016-2018, F5 Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
This module contains the process to scan BIG-IQ for regkey license
allocations and matches those to Neutron ports by MAC address. It
revokes any license allocations for IP addresses and MAC addresses
which are not present in OpenStack.
"""

import argparse
import logging
import os
import sys
import time
import datetime
import threading
import socket

from urlparse import urlparse

import requests

CONNECT_TIMEOUT = 30

LOG = logging.getLogger('bigiq_regkey_pool_cleaner')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)


def _get_bigiq_session(ctx, reuse=True):
    ''' Creates a Requests Session to the BIG-IQ host configured '''
    if reuse and hasattr(ctx, 'bigiq'):
        return ctx.bigiq
    if requests.__version__ < '2.9.1':
        requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member
    bigiq = requests.Session()
    bigiq.ctx = ctx
    bigiq.verify = False
    bigiq.headers.update({'Content-Type': 'application/json'})
    bigiq.timeout = CONNECT_TIMEOUT
    token_auth_body = {'username': ctx.bigiqusername,
                       'password': ctx.bigiqpassword,
                       'loginProviderName': 'local'}
    login_url = "https://%s/mgmt/shared/authn/login" % (ctx.bigiqhost)
    response = bigiq.post(login_url,
                          json=token_auth_body,
                          verify=False,
                          auth=requests.auth.HTTPBasicAuth(
                              ctx.bigiqusername, ctx.bigiqpassword))
    response_json = response.json()
    bigiq.headers.update(
        {'X-F5-Auth-Token': response_json['token']['token']})
    bigiq.base_url = 'https://%s/mgmt/cm/device/licensing/pool' % ctx.bigiqhost
    ctx.bigiq = bigiq
    return bigiq


def _get_pool_id(ctx):
    ''' Get a BIG-IQ license pool by its pool name. Returns first
        match of the specific pool type.
    :param: bigiq_session: BIG-IQ session object
    :param: pool_name: BIG-IQ pool name
    :returns: Pool ID string
    '''
    LOG.debug('finding pool %s', ctx.licensepool)
    bigiq_session = _get_bigiq_session(ctx)
    pools_url = '%s/regkey/licenses?$select=id,kind,name' % \
        bigiq_session.base_url
    # Now need to check both name and uuid for match. Can't filter.
    # query_filter = '&$filter=name%20eq%20%27'+pool_name+'%27'
    # pools_url = "%s%s" % (pools_url, query_filter)
    response = bigiq_session.get(pools_url)
    response.raise_for_status()
    response_json = response.json()
    pools = response_json['items']
    for pool in pools:
        if pool['name'] == ctx.licensepool or pool['id'] == ctx.licensepool:
            if str(pool['kind']).find('pool:regkey') > 1:
                return pool['id']
    return None


def _get_active_members(ctx):
    ''' Get regkey, member_id tuple by management IP address
    :param: ctx:: application context
    :returns: list of regkey pool members with active keys
    '''
    LOG.debug(
        'querying pools %s: %s for active licenses', ctx.licensepool, ctx.bigiq_pool_id)
    bigiq_session = _get_bigiq_session(ctx)
    pools_url = '%s/regkey/licenses' % bigiq_session.base_url
    offerings_url = '%s/%s/offerings' % (pools_url, ctx.bigiq_pool_id)
    response = bigiq_session.get(offerings_url)
    response.raise_for_status()
    response_json = response.json()
    offerings = response_json['items']
    return_members = []
    for offering in offerings:
        members_url = '%s/%s/members' % (
            offerings_url, offering['regKey'])
        response = bigiq_session.get(members_url)
        response.raise_for_status()
        response_json = response.json()
        members = response_json['items']
        for member in members:
            return_members.append(member)
    return return_members


def _get_members_to_revoke(ctx, license_pool_members):
    if not license_pool_members:
        return []
    members_to_revoke = []
    members_to_test = []
    for member in license_pool_members:
        if (not ctx.device_name_includes and not ctx.device_address_prefix):
            members_to_test.append(member)
        elif (ctx.device_address_prefix and member['deviceAddress'].startswith(ctx.device_address_prefix)):
            if (ctx.device_name_includes and member['deviceName'].find(ctx.device_name_includes) > -1):
                members_to_test.append(member)
            else:
                members_to_test.append(member)
        elif (ctx.device_name_includes and member['deviceName'].find(ctx.device_name_includes) > -1):
            if (ctx.device_address_prefix and member['deviceAddress'].startswith(ctx.device_address_prefix)):
                members_to_test.append(member)
            else:
                members_to_test.append(member)
    LOG.debug(
        'Testing TCP connections to %d active license members', len(members_to_test))
    for member in members_to_test:
        if ( not _test_tcp_connection(member['deviceAddress'], member['httpsPort']) ):
            LOG.info('Device %s:%s did not connect' % (member['deviceAddress'], member['httpsPort']))
            members_to_revoke.append(member);
    return members_to_revoke


def _test_tcp_connection(address, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    LOG.debug('Testing TCP connection to %s:%s' % (address, port))
    try:
        s.connect((address, port))
        return True
    except Exception as e:
        return False
    finally:
        s.close()


def _report(license_members, members_to_revoke):
    if not license_members:
        return []
    return_records = []
    now = datetime.datetime.utcnow()
    fmt_ts = now.strftime('%Y-%m-%dT%H:%M:%S') + \
        ('.%03dZ' % (now.microsecond / 10000))
    for member in license_members:
        preserve_member = True
        for revoke in members_to_revoke:
            if member['id'] == revoke['id']:
                preserve_member = False
                return_records.append(
                    "OFF,%s,%s,%s" % (
                        fmt_ts,
                        member['macAddress'],
                        member['deviceAddress']
                    )
                )
        if preserve_member:
            return_records.append(
                "ON,%s,%s,%s" % (
                    fmt_ts,
                    member['macAddress'],
                    member['deviceAddress']
                )
            )
    return return_records


def _revoke(ctx, member):
    bigiq_session = _get_bigiq_session(ctx, reuse=False)
    session_urlp = urlparse(bigiq_session.base_url)
    member_urlp = urlparse(member['selfLink'])
    member_url = '%s://%s%s' % (
        member_urlp.scheme, session_urlp.netloc, member_urlp.path)
    delete_body = {'id': member['id'],
                   'username': 'admin',
                   'password': 'revoke'}
    LOG.debug('revoking license for member %s : %s',
              member['id'], member['macAddress'])
    response = bigiq_session.delete(member_url,
                                    json=delete_body,
                                    verify=False)
    if response.status_code > 399:
        LOG.error(
            'could not revoke license for member: %s - %s', member['id'], response.text)


def reconcile(ctx, license_members, members_to_revoke):
    ''' print out a report for all active license members and revoke missing ports '''
    if not license_members:
        return
    reports = _report(license_members, members_to_revoke)
    if ctx.report_file:
        with open(ctx.report_file, 'a+') as report_file:
            for report in reports:
                report_file.write(report + '\n')
    else:
        for report in reports:
            LOG.info('report record: %s', report)
    for revoke in members_to_revoke:
        try:
            thread = threading.Thread(target=_revoke, args=(ctx, revoke))
            thread.start()
        except Exception as ex:
            LOG.error("error revoking member %s - %s", revoke['id'], ex)


def main(ctx):
    ''' main entry point '''

    log_level_dict = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARN': logging.WARN,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'FATAL': logging.FATAL
    }

    LOG.setLevel(log_level_dict[ctx.log_level])

    if ctx.daemon:
        LOG.debug('Running in daemon mode, polling every %d seconds',
                  ctx.poll_cycle)
        while True:
            # Get a new session every pool cycle
            _get_bigiq_session(ctx, reuse=False)
            # resolve the Pool ID from pool name
            try:
                ctx.bigiq_pool_id = _get_pool_id(ctx)
            except KeyboardInterrupt:
                LOG.info('Existing..')
                sys.exit(1)
            except Exception as ex:
                if 'Unauthorized' in str(ex):
                    LOG.error('BIG-IQ session expited')
                    ctx.bigiq = None
                    ctx.bigiq_pool_id = _get_pool_id(ctx)   
                else:
                    LOG.error("Pool %s not found - %s", ctx.licensepool, ex)
                time.sleep(ctx.poll_cycle)
                continue
            try:
                LOG.debug('Polling licenses in %s pool', ctx.licensepool)
                # find active licenses
                license_pool_members = _get_active_members(ctx)
                # find active licenses which do not have Neutron ports for their MAC address
                revoke_members = _get_members_to_revoke(
                    ctx, license_pool_members)
                # report and revoke
                reconcile(ctx, license_pool_members, revoke_members)
                time.sleep(ctx.poll_cycle)
            except KeyboardInterrupt:
                LOG.info('Existing..')
                sys.exit(1)
            except Exception as ex:
                if 'Unauthorized' in str(ex):
                    LOG.error('BIG-IQ session expited')
                else:
                    LOG.error("Error reconciling licenses %s", ex)
                ctx.bigiq = None
                ctx.openstack = None
                time.sleep(ctx.poll_cycle)
    else:
        # resolve the Pool ID from pool name
        try:
            ctx.bigiq_pool_id = _get_pool_id(ctx)
        except KeyboardInterrupt:
            LOG.info('Existing..')
            sys.exit(1)
        except Exception as ex:
            LOG.error("Pool %s not found - %s", ctx.licensepool, ex)
            return False
        try:
            # find active licenses
            LOG.debug('Polling licenses in %s pool', ctx.licensepool)
            license_pool_members = _get_active_members(ctx)
            # find active licenses which do not have Neutron ports for their MAC address
            revoke_members = _get_members_to_revoke(ctx, license_pool_members)
            # report and revoke
            reconcile(ctx, license_pool_members, revoke_members)
        except Exception as ex:
            LOG.error("Error reconciling licenses %s", ex)
            return False
        return True


if __name__ == "__main__":
    ARGPARSE = argparse.ArgumentParser()
    ARGPARSE.add_argument('-l', '--log-level', help='set logging level',
                          choices=['DEBUG', 'INFO', 'WARN',
                                   'ERROR', 'CRITICAL', 'FATAL'],
                          default=os.getenv('LOGLEVEL', 'INFO'))
    ARGPARSE.add_argument(
        '-d', '--daemon', help='Run in deamon mode', action='store_true')
    ARGPARSE.add_argument('-p', '--poll-cycle', help='How often to report and revoke, default 5 minutes',
                          default=os.getenv('LICENSEPOOLINTERVAL', 300), type=int)
    ARGPARSE.add_argument('-r', '--report-file',
                          help='the report log file', default=os.getenv('LICENSEREPORTFILE', None))
    ARGPARSE.add_argument('--bigiqhost', help='BIG-IQ hostname or IP address',
                          default=os.getenv('BIGIQHOST', '192.168.245.1'))
    ARGPARSE.add_argument('--bigiqusername', help='BIG-IQ username',
                          default=os.getenv('BIGIQUSERNAME', 'admin'))
    ARGPARSE.add_argument('--bigiqpassword', help='BIG-IQ password',
                          default=os.getenv('BIGIQPASSWORD', 'admin'))
    ARGPARSE.add_argument('--licensepool', help='BIG-IQ license pool name',
                          default=os.getenv('LICENSEPOOL'))
    ARGPARSE.add_argument('--device-address-prefix', help='consider only devices with the following deviceAddress prefix',
                          default=os.getenv('DEVICE_ADDRESS_PREFIX'))
    ARGPARSE.add_argument('--device-name-includes', help='consider only devices which include this string in their device name',
                          default=os.getenv('DEVICE_NAME_INCLUDES'))
    if main(ARGPARSE.parse_args()):
        sys.exit(0)
    else:
        sys.exit(1)
