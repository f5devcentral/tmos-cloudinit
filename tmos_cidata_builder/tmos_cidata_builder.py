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
This module contains the logic to create a cidata compliant ISO image
provided either user-data, meta-data, and vendor-data or else SSH public 
key file to embed in the default user.
"""

import os
import sys
import logging
import tempfile
import json
import uuid
import yaml

import pycdlib

from jinja2 import Template

LOG = logging.getLogger('tmos_cidata_builder')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)


def create_configdrive(userdata=None,
                       metatdata=None,
                       vendordata=None,
                       cidata_file=None):
    """ create the ISO9660 cidata containing only the user-data """
    if not userdata:
        LOG.error('can not create a ISO9660 ci-data without userdata')
        return False
    if not cidata_file:
        LOG.error(
            'can not create tmos_declared configdrive wihtout output file')
        return False
    tmpdir = tempfile.mkdtemp()
    try:
        iso = pycdlib.PyCdlib()
        iso.new(interchange_level=3,
                joliet=True,
                sys_ident='LINUX',
                pub_ident_str='F5 Application and Orchestration PM Team',
                app_ident_str='tmos_cidata_builder',
                rock_ridge='1.09',
                vol_ident='cidata')
        with open('%s/user_data' % tmpdir, 'w+') as ud_file:
            ud_file.write(userdata)
        iso.add_file('%s/user_data' % tmpdir,
                     '/USER_DAT.;1',
                     rr_name='user-data')
        if metatdata:
            with open('%s/meta-data' % tmpdir, 'w+') as md_file:
                md_file.write(metatdata)
            iso.add_file('%s/meta-data' % tmpdir,
                         '/META_DAT.;1',
                         rr_name='meta-data')
        if vendordata:
            with open('%s/vendor-data' % tmpdir, 'w+') as vd_file:
                vd_file.write(vendordata)
            iso.add_file('%s/vendor-data' % tmpdir,
                         '/VEND_DAT.;1',
                         rr_name='vendor-data')
        iso.write(cidata_file)
        iso.close()
        clean_tmpdir(tmpdir)
    except TypeError as type_error:
        LOG.error('error creating ISO file: %s', type_error)
        clean_tmpdir(tmpdir)
        return False
    return True


def clean_tmpdir(tmpdir):
    """ clean out temporary directory """
    for tmp_file in os.listdir(tmpdir):
        os.remove('%s/%s' % (tmpdir, tmp_file))
    system_temp_dir = tempfile.gettempdir()
    path, directory = os.path.split(tmpdir)
    while not path == system_temp_dir:
        os.rmdir("%s" % os.path.join(path, directory))
        path, directory = os.path.split(path)
    os.rmdir("%s" % os.path.join(path, directory))


def load_declaration(string):
    """ loads the declaration """
    try:
        obj = yaml.safe_load(string)
        return obj
    except ValueError:
        return False


def to_yaml(obj):
    """ creates a YAML document from an object """
    try:
        return yaml.dump(obj, default_flow_style=False, width=float("inf"))
    except ValueError:
        return False


if __name__ == "__main__":
    USERDATA_FILE = os.getenv('USERDATA_FILE', '/declarations/user-data')
    METADATA_FILE = os.getenv('METADATA_FILE', '/declarations/meta-data')
    VENDORDATA_FILE = os.getenv('VENDORDATA_FILE', '/declarations/vendor-data')
    SSH_PUBKEY_FILE = os.getenv('SSH_PUBKEY_FILE', '/declarations/id_rsa.pub')
    HOSTNAME = os.getenv('HOSTNAME', 'localhost.local')
    INSTANCE_ID = os.getenv('INSTANCE_ID', uuid.uuid4())
    CIDATA_FILE = os.getenv('CIDATA_FILE', '/configdrives/cidata.iso')
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

    user_data = ""
    if os.path.exists(USERDATA_FILE):
        LOG.info('building ISO9660 cidata user-data from %s', USERDATA_FILE)
        with open(USERDATA_FILE, 'r') as ud:
            user_data = ud.read()
    else:
        with open("%s/user-data.j2" % SCRIPT_DIR, 'r') as udt:
            t = Template(udt.read())
            ssh_public_key = "null"
            if os.path.exists(SSH_PUBKEY_FILE):
                with open(SSH_PUBKEY_FILE, 'r') as sk:
                    ssh_public_key = sk.read()
                LOG.info('injecting SSH key from %s', SSH_PUBKEY_FILE)
            user_data = t.render({'ssh_public_key': ssh_public_key})

    meta_data = ""
    if os.path.exists(METADATA_FILE):
        LOG.info('building ISO9660 cidata meta-data from %s', METADATA_FILE)
        with open(METADATA_FILE, 'r') as md:
            meta_data = md.read()
    else:
        with open("%s/meta-data.j2" % SCRIPT_DIR, 'r') as mdt:
            t = Template(mdt.read())
            LOG.info('injecting instance id: %s', INSTANCE_ID)
            LOG.info('injecting hostname: %s', HOSTNAME)
            meta_data = t.render({
                'instanceid': INSTANCE_ID,
                'hostname': HOSTNAME
            })

    vendor_data = None
    if os.path.exists(VENDORDATA_FILE):
        LOG.info('building ISO9660 cidata vendor-data from %s',
                 VENDORDATA_FILE)
        with open(VENDORDATA_FILE, 'r') as vd:
            vendor_data = vd.read()

    BUILT = create_configdrive(user_data, meta_data, vendor_data, CIDATA_FILE)
    if not BUILT:
        LOG.error('could not build ISO9660 cidata')
        if os.path.exists(CIDATA_FILE):
            os.remove(CIDATA_FILE)
        sys.exit(1)
    LOG.info('output IS09660 file: %s', CIDATA_FILE)
