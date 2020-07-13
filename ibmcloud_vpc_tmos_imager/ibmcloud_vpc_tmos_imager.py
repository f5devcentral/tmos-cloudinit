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

# ENV INPUTS
API_KEY = None
REGION = None
UPDATE_IMAGES = False
DELETE_ALL = False
DELETE_VPC_IMAGE = True

# CONSTANTS AND CONVENTIONS
COS_STANDARD_PLAN_ID = '744bfc56-d12c-4866-88d5-dac9139e0e5d'  # standard plan ID
COS_RESOURCE_NAME = 'custom-tmos-images'
COS_BUCKET_PREFIX = "c%s" % str(uuid.uuid4())[0:8]
AUTH_ENDPOINT = 'https://iam.cloud.ibm.com/identity/token'

# LOGGING
LOG = logging.getLogger('ibmcloud_vpc_image_importer')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)

# REQUEST SESSION AND RETRIES
SESSION_TOKEN = None
SESSION_TIMESTAMP = 0
SESSION_SECONDS = 1800
REQUEST_RETRIES = 10
REQUEST_DELAY = 10

# STATE
IBM_ACCOUNT_ID = None
RG_UUID = None
RG_CRN = None
COS_RESOURCE_UUID = None
COS_RESOURCE_CRN = None
COS_API_KEY_UUID = None
COS_API_KEY = None
TMOS_IMAGE_CATALOG_URL = None


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
        LOG.error('could not get an access token %d - %s',
                  response.status_code, response.content)
        return None


def get_account_id(token):
    global IBM_ACCOUNT_ID
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "IAM-Apikey": API_KEY,
        "Authorization": "Bearer %s" % token
    }
    ac_url = 'https://iam.cloud.ibm.com/v1/apikeys/details'
    response = requests.get(ac_url, headers=headers)
    if response.status_code < 300:
        IBM_ACCOUNT_ID = response.json()['account_id']
        return True
    else:
        LOG.error('could not retrieve account id: %d - %s',
                  response.status_code, response.content)
        return False


def create_resource_group(token):
    LOG.info('creating resource group for COS resources')
    global RG_UUID, RG_CRN
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = 'https://resource-controller.cloud.ibm.com/v2/resource_groups'
    data = {"name": "rg%s" % COS_BUCKET_PREFIX, "acount_id": IBM_ACCOUNT_ID}
    response = requests.post(rg_url, headers=headers, data=json.dumps(data))
    LOG.info('resource_groups create returned %d' % response.status_code)
    if response.status_code < 300:
        rj = response.json()
        RG_UUID = rj['id']
        RG_CRN = rj['crn']
        LOG.info('resource group crn: %s', RG_CRN)
        return True
    else:
        LOG.info('error creating resource group %d - %s', response.status_code,
                 response.content)
        return False


def create_cos_resource(token):
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
        return True
    else:
        LOG.error('error creating COS resource %d - %s', response.status_code,
                  response.content)
        return False


def create_cos_api_key(token):
    LOG.info('creating COS resources')
    global COS_API_KEY, COS_API_KEY_UUID
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
        return True
    else:
        LOG.error('error creating COS API KEY %d - %s', response.status_code,
                  response.content)
        return False


def delete_cos_api_key(token):
    LOG.info('deleting COS API key %s', COS_API_KEY_UUID)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = "https://resource-controller.cloud.ibm.com/v2/resource_keys/%s" % COS_API_KEY_UUID
    response = requests.delete(rg_url, headers=headers)
    if response.status_code < 300:
        return True
    else:
        LOG.error('error deleting COS API KEY %d - %s', response.status_code,
                  response.content)
        return False


def delete_cos_resource(token):
    LOG.info('deleting COS resource %s', COS_RESOURCE_CRN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = "https://resource-controller.cloud.ibm.com/v2/resource_instances/%s" % COS_RESOURCE_UUID
    response = requests.delete(rg_url, headers=headers)
    if response.status_code < 300:
        return True
    else:
        LOG.error('error deleting COS resource %d - %s', response.status_code,
                  response.content)
        return False


def delete_resource_group(token):
    LOG.info('deleting resource group %s', RG_CRN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    rg_url = "https://resource-controller.cloud.ibm.com/v2/resource_groups/%s" % RG_UUID
    response = requests.delete(rg_url, headers=headers)
    if response.status_code < 300:
        return True
    else:
        LOG.error('error deleting COS resource group %d - %s',
                  response.status_code, response.content)
        return False


def make_request(func, token):
    for i in range(REQUEST_RETRIES):
        if func(token):
            return True
        time.sleep(REQUEST_DELAY)
    return False


def create_cos():
    token = get_iam_token()
    if not token:
        return False
    if not make_request(get_account_id, token):
        return False
    if not make_request(create_resource_group, token):
        return False
    if not make_request(create_cos_resource, token):
        return False
    if not make_request(create_cos_api_key, token):
        return False
    return True


def clean_up_cos():
    token = get_iam_token()
    if not token:
        return False
    if COS_API_KEY_UUID and not make_request(delete_cos_api_key, token):
        return False
    if COS_RESOURCE_UUID and not make_request(delete_cos_resource, token):
        return False
    if RG_UUID and not make_request(delete_resource_group, token):
        return False
    return True


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
    else:
        LOG.error('could not retrieve existing VPC custom images %d - %s',
                  response.status_code, response.content)
    return image_names


def delete_image_by_name(region, image_name):
    token = get_iam_token()
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images?version=2020-04-07&generation=2&visibility=private" % region
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    response = requests.get(image_url, headers=headers)
    if response.status_code < 300:
        images = response.json()
        for image in images['images']:
            if image['name'] == image_name:
                del_url = "https://%s.iaas.cloud.ibm.com/v1/images/%s?version=2020-04-07&generation=2" % (
                    region, image['id'])
                response = requests.delete(del_url, headers=headers)
                if response.status_code < 400:
                    return True
                else:
                    LOG.error('error deleting image %d:%s',
                              response.status_code, response.content)


def get_required_regions():
    global REGION

    # parse regions from environment
    regions = [x.strip() for x in REGION.split(',')]
    # lookup for region from either source (disk or existing)
    name_to_region = {}

    # populate what is need based on TMOS disk images
    required_image_names = []
    for region in regions:
        for image_name in scan_for_disk_images():
            regional_name = "%s-%s" % (image_name, region)
            name_to_region[regional_name] = region
            required_image_names.append(regional_name)

    # populate what VPC images exist in VPCs
    existing_image_names = []
    for region in regions:
        for image_name in get_images(region):
            name_to_region[image_name] = region
            existing_image_names.append(image_name)

    # delete any existing images which are not on disk
    for image_name in existing_image_names:
        if image_name.startswith(
                'bigip') and image_name not in required_image_names:
            if DELETE_VPC_IMAGE:
                LOG.info('image %s in VPC, but not on disk, deleting',
                         image_name)
                delete_image_by_name(name_to_region[image_name], image_name)

    # determine which regions need syncrhonization from disk images
    regions_needed = []
    for image_name in required_image_names:
        # add region to import if disk image does not exist
        if image_name not in existing_image_names:
            LOG.info('adding region %s to COS upload and VPC import',
                     name_to_region[image_name])
            regions_needed.append(name_to_region[image_name])
        # if UPDATE_IMAGE, delete the existing image and add region to update
        elif UPDATE_IMAGES:
            LOG.info('deleting %s to update image', image_name)
            delete_image_by_name(name_to_region[image_name], image_name)
            LOG.info('adding region %s to COS upload and VPC import',
                     name_to_region[image_name])
            regions_needed.append(name_to_region[image_name])
    REGION = ','.join(regions_needed)


def delete_all_images():
    # simply delete all images starting wtih 'bigip' in specified region(s)
    regions = [x.strip() for x in REGION.split(',')]
    for region in regions:
        for image_name in get_images(region):
            if image_name.startswith('bigip'):
                delete_image_by_name(region, image_name)


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
    s_env['COS_IMAGE_LOCATION'] = REGION
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


def initialize():
    global API_KEY, REGION, UPDATE_IMAGES, DELETE_ALL, DELETE_VPC_IMAGE
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

    DELETE_ALL = os.getenv('DELETE_ALL', 'false')
    if DELETE_ALL.lower() == 'true':
        DELETE_ALL = True
    else:
        DELETE_ALL = False
    DELETE_VPC_IMAGE = os.getenv('DELETE_VPC_IMAGE', 'true')
    if DELETE_VPC_IMAGE.lower() == 'true':
        DELETE_VPC_IMAGE = True
    else:
        DELETE_VPC_IMAGE = False
    UPDATE_IMAGES = os.getenv('UPDATE_IMAGES', 'false')
    if UPDATE_IMAGES.lower() == 'true':
        UPDATE_IMAGES = True
    else:
        UPDATE_IMAGES = False
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
    if DELETE_ALL:
        delete_all_images()
    else:
        cos_resources_created = False
        try:
            LOG.info('checking for existing VPC custom images')
            get_required_regions()
            cos_resources_created = create_cos()
            if REGION and cos_resources_created:
                LOG.info('patching TMOS Images')
                patch_images()
                LOG.info('uploading TMOS images to IBM COS')
                upload_images()
                LOG.info('importing COS images to VPC custom images')
                import_images()
        except Exception as ex:
            LOG.error('could not continue: %s', ex)
        if cos_resources_created:
            if not clean_up_cos():
                LOG.error(
                    'could not assue COS resources were deleted properly')
    STOP_TIME = time.time()
    DURATION = STOP_TIME - START_TIME
    LOG.debug(
        'process end time: %s - ran %s (seconds)',
        datetime.datetime.fromtimestamp(STOP_TIME).strftime(
            "%A, %B %d, %Y %I:%M:%S"), DURATION)
