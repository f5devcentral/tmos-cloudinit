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
This module contains the logic to create VPC images from
F5 public COS image URLs.
"""

import os
import json
import logging
import requests
import sys
import datetime
import time
import re
import subprocess
import uuid

API_KEY = None
REGION = None

COS_RESOURCE_NAME = 'custom-tmos-images'
COS_BUCKET_PREFIX = "c%s" % str(uuid.uuid4())[0:8]

TMOS_IMAGE_CATALOG_URL = None

AUTH_ENDPOINT = 'https://iam.cloud.ibm.com/identity/token'

LOG = logging.getLogger('ibmcloud_vpc_image_importer')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)

SESSION_TOKEN = None
SESSION_TIMESTAMP = 0
SESSION_SECONDS = 1800

RG_UUID = None
RG_CRN = None
COS_RESOURCE_UUID = None
COS_RESOURCE_CRN = None
COS_API_KEY_UUID = None
COS_API_KEY = None

COS_STANDARD_PLAN_ID = '744bfc56-d12c-4866-88d5-dac9139e0e5d'


def get_iam_token():
    global SESSION_TOKEN, SESSION_TIMESTAMP
    now = int(time.time())
    if SESSION_TIMESTAMP > 0 and ((now - SESSION_TIMESTAMP) < SESSION_SECONDS):
        return SESSION_TOKEN
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = "apikey=%s&grant_type=urn:ibm:params:oauth:grant-type:apikey" % API_KEY
    response = requests.post(AUTH_ENDPOINT, headers=headers, data=data)
    if response.status_code < 300:
        SESSION_TIMESTAMP = int(time.time())
        SESSION_TOKEN = response.json()['access_token']
        return SESSION_TOKEN
    else:
        return None


def get_account_id():
    token = get_iam_token()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "IAM-Apikey": API_KEY,
        "Authorization": "Bearer %s" % token
    }
    ac_url = 'https://iam.cloud.ibm.com/v1/apikeys/details'
    response = requests.get(ac_url, headers=headers)
    if response.status_code < 300:
        return response.json()['account_id']
    else:
        return None


def create_resource_group():
    LOG.info('creating resource group for COS resources')
    global RG_UUID, RG_CRN
    token = get_iam_token()
    account_id = get_account_id()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = 'https://resource-controller.cloud.ibm.com/v2/resource_groups'
    data = {"name": "rg%s" % COS_BUCKET_PREFIX, "acount_id": account_id}
    response = requests.post(rg_url, headers=headers, data=json.dumps(data))
    LOG.info('resource_groups create returned %d' % response.status_code)
    if response.status_code < 300:
        rj = response.json()
        RG_UUID = rj['id']
        RG_CRN = rj['crn']
        LOG.info('resource group crn: %s', RG_CRN)


def create_cos_resource():
    LOG.info('createing COS resource instance')
    if not RG_UUID:
        create_resource_group()
    global COS_RESOURCE_CRN, COS_RESOURCE_UUID
    token = get_iam_token()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = 'https://resource-controller.cloud.ibm.com/v2/resource_instances'
    data = {
        "name": "cosr%s" % COS_BUCKET_PREFIX,
        "target": "bluemix-global",
        "resource_group": RG_UUID,
        "resource_plan_id": COS_STANDARD_PLAN_ID
    }
    response = requests.post(rg_url, headers=headers, data=json.dumps(data))
    LOG.info('resource_instances create returned %d' % response.status_code)
    if response.status_code < 300:
        rj = response.json()
        COS_RESOURCE_CRN = rj['id']
        COS_RESOURCE_UUID = rj['guid']
        LOG.info('resource crn: %s', COS_RESOURCE_CRN)


def create_cos_api_key():
    LOG.info('creating COS API key')
    global COS_API_KEY, COS_API_KEY_UUID
    if not COS_RESOURCE_UUID:
        create_cos_resource()
    token = get_iam_token()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = 'https://resource-controller.cloud.ibm.com/v2/resource_keys'
    data = {
        "name": "cosk%s" % COS_BUCKET_PREFIX,
        "source": COS_RESOURCE_UUID,
        "role": "Manager"
    }
    response = requests.post(rg_url, headers=headers, data=json.dumps(data))
    LOG.info('resource_keys create returned %d' % response.status_code)
    if response.status_code < 300:
        rj = response.json()
        COS_API_KEY = rj['credentials']['apikey']
        COS_API_KEY_UUID = rj['guid']
        LOG.info('COS API KEY guid: %s', COS_API_KEY_UUID)


def delete_cos_api_key():
    LOG.info('deleting COS API key %s', COS_API_KEY_UUID)
    token = get_iam_token()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = "https://resource-controller.cloud.ibm.com/v2/resource_keys/%s" % COS_API_KEY_UUID
    requests.delete(rg_url, headers=headers)


def delete_cos_resource():
    LOG.info('deleting COS resource %s', COS_RESOURCE_CRN)
    token = get_iam_token()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = "https://resource-controller.cloud.ibm.com/v2/resource_instances/%s" % COS_RESOURCE_UUID
    requests.delete(rg_url, headers=headers)


def delete_resource_group():
    LOG.info('deleting resource group %s', RG_CRN)
    token = get_iam_token()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = "https://resource-controller.cloud.ibm.com/v2/resource_groups/%s" % RG_UUID
    requests.delete(rg_url, headers=headers)


def scan_for_disk_images():
    """Scan for TMOS disk images"""
    tmos_image_dir = os.getenv('TMOS_IMAGE_DIR', '/TMOSImages')
    images_names = []
    for image_file in os.listdir(tmos_image_dir):
        filepath = "%s/%s" % (tmos_image_dir, image_file)
        if os.path.isfile(filepath) and image_file.find('qcow2') > 0:
            image_name = os.path.splitext(image_file)[0].replace(
                '.qcow2', '').replace('.', '-').replace('_', '-').lower()
            images_names.append(image_name)
    return images_names


def get_images(region):
    token = get_iam_token()
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images?version=2020-04-07&generation=2&visibility=private" % region
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    response = requests.get(image_url, headers=headers)
    image_names = []
    if response.status_code < 300:
        images = response.json()
        for image in images['images']:
            image_names.append(image['name'])
    return image_names


def get_required_regions():
    global REGION
    image_names = scan_for_disk_images()
    if image_names:
        regions_needed = []
        LOG.debug('searching for regional images for %s', image_names)
        regions = [x.strip() for x in REGION.split(',')]
        LOG.debug('searching regions %s', regions)
        
        for region in regions:
            existing_images = get_images(region)
            LOG.debug('found %s in region %s', existing_images, region)
            for image_name in image_names:
                regional_name = "%s-%s" % (image_name, region)
                if regional_name in existing_images:
                    LOG.debug('%s already exists', regional_name)
                else:
                    LOG.debug('need to create VPC image %s', regional_name)
                    regions_needed.append(region)
        REGION = ','.regions_needed
    else:
        REGION = ''


def patch_images():
    s_env = os.environ.copy()
    s_env['TMOS_CLOUDINIT_CONFIG_TEMPLATE'] = os.path.join(
        os.path.dirname(__file__), '..',
        'image_patch_files/cloudinit_configs/ibmcloud_vpc_gen2/cloud-init.tmpl'
    )
    cmd = os.path.join(os.path.dirname(__file__), '..', 'tmos_image_patcher',
                       'tmos_image_patcher.py')
    proc = subprocess.Popen(cmd,
                            env=s_env,
                            stdout=sys.stdout,
                            stderr=sys.stderr)
    proc.wait()


def upload_images():
    global TMOS_IMAGE_CATALOG_URL
    if not COS_API_KEY:
        create_cos_api_key()
    s_env = os.environ.copy()
    s_env['COS_RESOURCE_CRN'] = COS_RESOURCE_CRN
    s_env['COS_API_KEY'] = COS_API_KEY
    s_env['COS_IMAGE_LOCATION'] = s_env['REGION']
    s_env['COS_BUCKET_PREFIX'] = COS_BUCKET_PREFIX
    cmd = os.path.join(os.path.dirname(__file__), '..',
                       'ibmcloud_image_uploader',
                       'ibmcloud_cos_image_uploader.py')
    proc = subprocess.Popen(cmd,
                            env=s_env,
                            stdout=sys.stdout,
                            stderr=sys.stderr)
    proc.wait()
    regions = [x.strip() for x in REGION.split(',')]
    TMOS_IMAGE_CATALOG_URL = "https://%s-%s.s3.%s.cloud-object-storage.appdomain.cloud/f5-image-catalog.json" % (
        COS_BUCKET_PREFIX, regions[0], regions[0])
    LOG.info('populating TMOS_IMAGE_CATALOG_URL for import phase as: %s',
             TMOS_IMAGE_CATALOG_URL)


def import_images():
    s_env = os.environ.copy()
    s_env['TMOS_IMAGE_CATALOG_URL'] = TMOS_IMAGE_CATALOG_URL
    s_env['REGION'] = REGION
    cmd = os.path.join(os.path.dirname(__file__), '..',
                       'ibmcloud_vpc_image_importer',
                       'ibmcloud_vpc_image_importer.py')
    proc = subprocess.Popen(cmd,
                            env=s_env,
                            stdout=sys.stdout,
                            stderr=sys.stderr)
    proc.wait()


def clean_up():
    delete_cos_api_key()
    delete_cos_resource()
    delete_resource_group()


def initialize():
    global API_KEY, REGION
    error = False
    API_KEY = os.getenv('API_KEY', None)
    if not API_KEY:
        LOG.error(
            'please specify an API_KEY evironment variable to use to create IBM Cloud resources'
        )
        error = True
    REGION = os.getenv('REGION', None)
    if not REGION:
        LOG.error(
            'please specify a REGION enivornment varibale to use to create IBM Cloud resources'
        )
        error = True
    if error:
        sys.exit(1)


if __name__ == "__main__":
    if not os.environ['USER'] == 'root':
        print "Please run this script as sudo"
        sys.exit(1)
    START_TIME = time.time()
    LOG.debug(
        'process start time: %s',
        datetime.datetime.fromtimestamp(START_TIME).strftime(
            "%A, %B %d, %Y %I:%M:%S"))
    initialize()
    try:
        LOG.info('checking for existing VPC custom images')
        get_required_regions()
        if REGION:
            create_cos_api_key()
            LOG.info('patching TMOS Images')
            patch_images()
            LOG.info('uploading TMOS images to IBM COS')
            upload_images()
            LOG.info('importing COS images to VPC custom images')
            import_images()
    except Exception as ex:
        LOG.error('could not continue: %s', ex)
    clean_up()
    STOP_TIME = time.time()
    DURATION = STOP_TIME - START_TIME
    LOG.debug(
        'process end time: %s - ran %s (seconds)',
        datetime.datetime.fromtimestamp(STOP_TIME).strftime(
            "%A, %B %d, %Y %I:%M:%S"), DURATION)
