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
This module contains the logic to scan for patched TMOS disk images
and then upload to IBM Cloud Object Storage
"""

import os
import sys
import time
import datetime
import logging
import json
import ibm_boto3
import urlparse
import requests
import re

import concurrent.futures
import threading

from ibm_botocore.client import Config, ClientError

IMAGE_TYPES = ['.qcow2', '.vhd', '.vmdk']
IBM_COS_REGIONS = []

TMOS_IMAGE_DIR = None
COS_UPLOAD_THREADS = 1
COS_API_KEY = None
COS_RESOURCE_CRN = None
COS_IMAGE_LOCATION = None
COS_AUTH_ENDPOINT = None
COS_ENDPOINT = None

COS_BUCKET_PREFIX = 'f5'

IC_API_KEY = None
IC_RESOURCE_GROUP = None
AUTH_ENDPOINT = 'https://iam.cloud.ibm.com/identity/token'
SESSION_TOKEN = None
SESSION_TIMESTAMP = 0
SESSION_SECONDS = 1800
IMAGE_STATUS_PAUSE_SECONDS = 5


IMAGE_MATCH = '^[a-zA-Z]'

UPDATE_IMAGES = None
DELETE_ALL = None
PUBLIC_IMAGES = None
INVENTORY = None

LOG = logging.getLogger('ibmcloud_cos_image_uploader')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)


def get_iam_token():
    global SESSION_TOKEN, SESSION_TIMESTAMP
    now = int(time.time())
    if SESSION_TIMESTAMP > 0 and ((now - SESSION_TIMESTAMP) < SESSION_SECONDS):
        return SESSION_TOKEN
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = "apikey=%s&grant_type=urn:ibm:params:oauth:grant-type:apikey" % IC_API_KEY
    response = requests.post(AUTH_ENDPOINT, headers=headers, data=data)
    if response.status_code < 300:
        SESSION_TIMESTAMP = int(time.time())
        SESSION_TOKEN = response.json()['access_token']
        return SESSION_TOKEN
    else:
        return None


def get_patched_images(tmos_image_dir):
    """get TMOS patched disk images"""
    return_image_files = []
    LOG.debug('searching for images in %s', tmos_image_dir)
    for patched_dir in os.listdir(tmos_image_dir):
        patched_dir_path = "%s/%s" % (tmos_image_dir, patched_dir)
        if os.path.isdir(patched_dir_path):
            for patched_image in os.listdir(patched_dir_path):
                if os.path.splitext(patched_image)[1] in IMAGE_TYPES:
                    image_filepath = "%s/%s" % (patched_dir_path,
                                                patched_image)
                    return_image_files.append(image_filepath)
    return return_image_files


def get_bucket_name(image_path, location):
    """Get bucket for this patched image"""
    return "%s-%s-%s" % (
        COS_BUCKET_PREFIX,
        os.path.splitext(
            os.path.dirname(image_path.replace(TMOS_IMAGE_DIR, '')).replace(
                os.path.sep, ''))[0].replace('_', '-').lower(), location)


def get_object_name(image_path, location):
    """Get object name for this patched image"""
    if 'DATASTOR' in image_path:
        return "%s_DATASTOR" % os.path.dirname(
            image_path.replace(TMOS_IMAGE_DIR, '')).replace(os.path.sep, '')
    else:
        return os.path.dirname(image_path.replace(TMOS_IMAGE_DIR, '')).replace(
            os.path.sep, '')


def get_cos_client(location):
    """return IBM COS client object"""
    cos_endpoint = "https://s3.%s.cloud-object-storage.appdomain.cloud" % location
    return ibm_boto3.client("s3",
                            ibm_api_key_id=COS_API_KEY,
                            ibm_service_instance_id=COS_RESOURCE_CRN,
                            ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                            config=Config(signature_version="oauth"),
                            endpoint_url=cos_endpoint)


def get_cos_resource(location):
    """return IBM COS resource object"""
    cos_endpoint = "https://s3.%s.cloud-object-storage.appdomain.cloud" % location
    return ibm_boto3.resource("s3",
                              ibm_api_key_id=COS_API_KEY,
                              ibm_service_instance_id=COS_RESOURCE_CRN,
                              ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                              config=Config(signature_version="oauth"),
                              endpoint_url=cos_endpoint)


def assure_bucket(bucket_name, location):
    """Make sure bucket exists"""
    cos_res = get_cos_resource(location)
    try:
        for bucket in cos_res.buckets.all():
            if bucket.name == bucket_name:
                LOG.debug('bucket: %s exists', bucket_name)
                return True
        LOG.debug('creating bucket %s', bucket_name)
        cos_res.Bucket(bucket_name).create(ACL='public-read')
        time.sleep(10)
        return True
    except ClientError as client_error:
        # bucket was created, but didn't show up in the list fast
        # enough for the next upload task to see it
        if str(client_error).find('BucketAlreadyExists') > 0:
            return True
        else:
            LOG.error('client error assuring bucket %s: %s', bucket_name,
                      client_error)
            return False
    except Exception as ex:
        LOG.error('exception occurred assuring bucket %s: %s', bucket_name, ex)
        return False


def assure_object(file_path, bucket_name, object_name, location):
    """check if patched image already exists"""
    cos_res = get_cos_resource(location)
    try:
        for obj in cos_res.Bucket(bucket_name).objects.all():
            if obj.key == object_name:
                if UPDATE_IMAGES:
                    obj.delete()
                else:
                    LOG.debug('object: %s/%s exists', bucket_name, object_name)
                    return True
        LOG.debug('starting upload of image %s to %s/%s', file_path,
                  bucket_name, object_name)

        part_size = 1024 * 1024 * 2
        file_threshold = 1024 * 1024 * 1024 * 10

        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold, multipart_chunksize=part_size)

        cos_client = get_cos_client(location)
        transfer_mgr = ibm_boto3.s3.transfer.TransferManager(
            cos_client, config=transfer_config)
        upload = transfer_mgr.upload(file_path,
                                     bucket_name,
                                     object_name,
                                     extra_args={'ACL': 'public-read'})
        upload.result()

        LOG.debug('upload complete for %s/%s', bucket_name, object_name)

        return True

    except ClientError as ce:
        LOG.error('client error assuring object %s/%s: %s', bucket_name,
                  object_name, ce)
        return False
    except Exception as ex:
        LOG.error('exception occurred assuring object %s/%s: %s', bucket_name,
                  object_name, ex)
        return False


def assure_cos_bucket(image_path, location):
    """assure patch image bucket"""
    bucket_name = get_bucket_name(image_path, location)
    object_name = get_object_name(image_path, location)
    if re.search(IMAGE_MATCH, object_name):
        return assure_bucket(bucket_name, location)


def assure_cos_object(image_path, location):
    """assure patch image object"""
    bucket_name = get_bucket_name(image_path, location)
    object_name = get_object_name(image_path, location)
    if re.search(IMAGE_MATCH, object_name):
        md5_path = "%s.md5" % image_path
        if os.path.exists(md5_path):
            md5_object_name = "%s.md5" % object_name
            assure_object(md5_path, bucket_name, md5_object_name, location)
        sig_path = "%s.384.sig" % image_path
        if os.path.exists(sig_path):
            sig_object_name = "%s.384.sig" % object_name
            assure_object(sig_path, bucket_name, sig_object_name, location)
        assure_object(image_path, bucket_name, object_name, location)


def delete_all():
    """delete all files and buckets from the COS resource"""
    LOG.debug('deleting images in: %s', IBM_COS_REGIONS)
    for location in IBM_COS_REGIONS:
        LOG.debug("deleting images in %s region" % location)
        cos_res = get_cos_resource(location)
        try:
            for bucket in cos_res.buckets.all():
                if location in bucket.name:
                    if bucket.name.startswith(COS_BUCKET_PREFIX):
                        delete_bucket = False
                        for obj in cos_res.Bucket(bucket.name).objects.all():
                            if re.search(IMAGE_MATCH, obj.key):
                                LOG.debug('deleting object: %s', obj.key)
                                obj.delete()
                                delete_bucket = True
                            else:
                                LOG.debug(
                                    'leaving object: %s because it did not match %s',
                                    obj.key, IMAGE_MATCH)
                        if delete_bucket:
                            LOG.debug('deleting bucket: %s', bucket.name)
                            bucket.delete()
        except ClientError as client_error:
            LOG.error('client error deleting all resources: %s', client_error)
        except Exception as ex:
            LOG.error('exception occurred deleting all resources: %s', ex)


def upload_patched_images():
    """check for images and assure upload to IBM COS"""
    LOG.debug('uploading images to %s', IBM_COS_REGIONS)
    # Just do an interation to serially create buckets
    image_paths = get_patched_images(TMOS_IMAGE_DIR)
    number_of_uploades = len(image_paths) * len(IBM_COS_REGIONS)
    current_image = 1
    for image_path in image_paths:
        for location in IBM_COS_REGIONS:
            LOG.debug('Processing image %d of %d', current_image,
                      number_of_uploades)
            if assure_cos_bucket(image_path, location):
                assure_cos_object(image_path, location)
            current_image += 1


def get_resource_group_id(token=None):
    if not token:
        token = get_iam_token()
    rg_url = "https://resource-controller.cloud.ibm.com/v2/resource_groups"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    response = requests.get(rg_url, headers=headers)
    if response.status_code < 300:
        rgs = response.json()['resources']
        for rg in rgs:
            if rg['name'] == IC_RESOURCE_GROUP:
                return rg['id']
        return None
    else:
        return None


def get_images(token, region):
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images?version=2020-04-07&generation=2" % region
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    response = requests.get(image_url, headers=headers)
    if response.status_code < 300:
        return response.json()
    else:
        return None


def get_image_id(token, region, image_name):
    if not token:
        token = get_iam_token()
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images?version=2021-09-28&generation=2&name=%s" % (region, image_name)
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
                return image['id']
        return None
    else:
        return None


def get_image_visibility(token, region, image_id):
    if not token:
        token = get_iam_token()
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images/%s?version=2021-09-28&generation=2" % (region, image_id)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    response = requests.get(image_url, headers=headers)
    if response.status_code < 300:
        image = response.json()
        if image['id'] == image_id:
            return image['visibility']
        return None
    else:
        return None


def get_image_status(token, region, image_id):
    if not token:
        token = get_iam_token()
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images/%s?version=2021-09-28&generation=2" % (region, image_id)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    response = requests.get(image_url, headers=headers)
    if response.status_code < 300:
        image = response.json()
        return image['status']
    else:
        return None


def make_image_public(token, region, image_id):
    if not token:
        token = get_iam_token()
    image_visibility = get_image_visibility(token, region, image_id)
    if not image_visibility == 'public':
        image_url = "https://%s.iaas.cloud.ibm.com/v1/images/%s?version=2021-09-28&generation=2" % (region, image_id)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % token
        }
        data = {
            "visibility": "public"
        }
        response = requests.patch(image_url, headers=headers, data=json.dumps(data))
        if response.status_code < 300:
            return True
        else:
            return False
    else:
        return True
        

def delete_image(token, region, image_id):
    if not token:
        token = get_iam_token()
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images/%s?version=2021-09-28&generation=2" % (region, image_id)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    response = requests.delete(image_url, headers=headers)
    if response.status_code < 400:
        return True
    else:
        LOG.error('error deleting image %d:%s',
            response.status_code, response.content)
    return False


def create_public_image(token, region, image_name, cos_url):
    if not token:
        token = get_iam_token()
    image_id = get_image_id(token, region, image_name)
    if UPDATE_IMAGES:
        if image_id:
            delete_image(token, region, )
    if not image_id:
        LOG.debug('Creating %s in %s' % (image_name, region))
        image_url = "https://%s.iaas.cloud.ibm.com/v1/images/%s?version=2021-09-28&generation=2" % region
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % token
        }
        data = {
            "name": image_name,
            "file": {
                "href": cos_url
            },
            "operating_system": {
                "name": "centos-7-amd64"
            },
            "resource_group": {
                "id": get_resource_group_id(token)
            }
        }
        response = requests.post(image_url, headers=headers, data=json.dumps(data))
        if response.status_code < 400:
            image = response.json()
            is_available = False
            while not is_available:
                state_of_image = get_image_status(token, region, image['id'])
                if state_of_image == 'available':
                    is_available = True
                else:
                    time.sleep(IMAGE_STATUS_PAUSE_SECONDS)
            if not make_image_public(token, region, image['id']):
                LOG.error('image %s could not be made public, permissions?', image['id'])
                return None
            return image['id']
        else:
            LOG.error('error creating image %s from cos_url: %s - %d:%s',
                image_name, cos_url, response.status_code, response.content)
        return None
    else:
        if not make_image_public(token, region, image_id):
            LOG.error('image %s could not be made public, permissions?', image_id)
            return None
        return image_id


def create_public_images():
    """got through published COS images and create public VPC images"""
    if not IC_API_KEY:
        LOG.info('no env variable found IC_API_KEY, so no public images will be created')
        return
    LOG.debug('create public images to %s', IBM_COS_REGIONS)
    token = get_iam_token()
    for location in IBM_COS_REGIONS:
        cos_res = get_cos_resource(location)
        try:
            for bucket in cos_res.buckets.all():
                if location in bucket.name:
                    for obj in cos_res.Bucket(bucket.name).objects.all():
                        if os.path.splitext(obj.key)[1] in IMAGE_TYPES:
                            image_name = bucket.name.replace("%s-" % COS_BUCKET_PREFIX,'').replace('.', '-')
                            cos_url = "cos://%s/%s/%s" % (location, bucket.name, obj.key)
                            LOG.debug('Creating public image %s in %s from url %s' % (image_name, location, cos_url))
                            create_public_image(token, location, image_name, cos_url)
        except ClientError as client_error:
            LOG.error('client error creating inventory of resources: %s',
                      client_error)
        except Exception as ex:
            LOG.error('exception creating inventory of resources: %s', ex)                  


def inventory():
    """create inventory JSON"""
    global UPDATE_IMAGES
    inventory_file = "%s/ibmcos_images.json" % (TMOS_IMAGE_DIR)
    if os.path.exists(inventory_file):
        os.unlink(inventory_file)
    inventory = {}
    for location in IBM_COS_REGIONS:
        inventory[location] = []
        cos_res = get_cos_resource(location)
        try:
            token = get_iam_token()
            for bucket in cos_res.buckets.all():
                if location in bucket.name:
                    for obj in cos_res.Bucket(bucket.name).objects.all():
                        LOG.debug('inventory add %s/%s', bucket.name, obj.key)
                        if os.path.splitext(obj.key)[1] in IMAGE_TYPES:
                            image_name = bucket.name.replace("%s-" % COS_BUCKET_PREFIX,'').replace('.', '-')
                            cos_url = "cos://%s/%s/%s" % (location, bucket.name, obj.key)
                            cos_md5_url = "cos://%s/%s/%s.md5" % (location, bucket.name, obj.key)
                            image_id = get_image_id(token, location, image_name)
                            inv_obj = {
                                'image_name': image_name,
                                'image_sql_url': cos_url,
                                'md5_sql_url': cos_md5_url,
                                'image_id': image_id
                            }
                            inventory[location].append(inv_obj)
        except ClientError as client_error:
            LOG.error('client error creating inventory of resources: %s',
                      client_error)
        except Exception as ex:
            LOG.error('exception creating inventory of resources: %s', ex)
    # write it locally
    with open(inventory_file, 'w') as ivf:
        ivf.write(json.dumps(inventory))
    # store in each location
    old_update_images = UPDATE_IMAGES
    UPDATE_IMAGES = True
    for location in IBM_COS_REGIONS:
        bucket_name = "%s-%s" % (COS_BUCKET_PREFIX, location)
        public_url = "https://%s.s3.%s.cloud-object-storage.appdomain.cloud/f5-image-catalog.json" % (
            bucket_name, location)
        LOG.debug('writing image catalog to: %s', public_url)
        assure_bucket(bucket_name, location)
        assure_object(inventory_file, bucket_name, "f5-image-catalog.json",
                      location)
    UPDATE_IMAGES = old_update_images


def initialize():
    """initialize configuration from environment variables"""
    global TMOS_IMAGE_DIR, IBM_COS_REGIONS, COS_UPLOAD_THREADS, \
           COS_API_KEY, COS_RESOURCE_CRN, COS_IMAGE_LOCATION, \
           COS_AUTH_ENDPOINT, UPDATE_IMAGES, DELETE_ALL, \
           COS_BUCKET_PREFIX, IC_API_KEY, IC_RESOURCE_GROUP, \
           IMAGE_MATCH, PUBLIC_IMAGES, INVENTORY
    TMOS_IMAGE_DIR = os.getenv('TMOS_IMAGE_DIR', None)
    COS_UPLOAD_THREADS = os.getenv('COS_UPLOAD_THREADS', 1)
    COS_API_KEY = os.getenv('COS_API_KEY', None)
    COS_RESOURCE_CRN = os.getenv('COS_RESOURCE_CRN', None)
    COS_IMAGE_LOCATION = os.getenv('COS_IMAGE_LOCATION', 'us-south')
    COS_BUCKET_PREFIX = os.getenv('COS_BUCKET_PREFIX', 'f5-image-catalog')
    IMAGE_MATCH = os.getenv('IMAGE_MATCH', '^[a-zA-Z]')
    IBM_COS_REGIONS = [x.strip() for x in COS_IMAGE_LOCATION.split(',')]
    COS_AUTH_ENDPOINT = os.getenv('COS_AUTH_ENDPOINT',
                                  'https://iam.cloud.ibm.com/identity/token')
    # KEY TO MAKE PUBIC IMAGES
    IC_API_KEY = os.getenv('IC_API_KEY', None)
    IC_RESOURCE_GROUP = os.getenv('IC_RESOURCE_GROUP', 'default')
    UPDATE_IMAGES = os.getenv('UPDATE_IMAGES', 'false')
    if UPDATE_IMAGES.lower() == 'true':
        UPDATE_IMAGES = True
    else:
        UPDATE_IMAGES = False
    DELETE_ALL = os.getenv('DELETE_ALL', 'false')
    if DELETE_ALL.lower() == 'true':
        DELETE_ALL = True
    else:
        DELETE_ALL = False
    PUBLIC_IMAGES = os.getenv('PUBLIC_IMAGES', 'true')
    if PUBLIC_IMAGES.lower() == 'true':
        PUBLIC_IMAGES = True
    else:
        PUBLIC_IMAGES = False    
    INVENTORY = os.getenv('INVENTORY', 'true')
    if INVENTORY.lower() == 'true':
        INVENTORY = True
    else:
        INVENTORY = False


if __name__ == "__main__":
    START_TIME = time.time()
    LOG.debug(
        'process start time: %s',
        datetime.datetime.fromtimestamp(START_TIME).strftime(
            "%A, %B %d, %Y %I:%M:%S"))
    initialize()
    ERROR_MESSAGE = ''
    ERROR = False
    if not COS_API_KEY:
        ERROR = True
        ERROR_MESSAGE += "please set env COS_API_KEY for your IBM COS resource\n"
    if not COS_RESOURCE_CRN:
        ERROR = True
        ERROR_MESSAGE += "please set env COS_RESOURCE_CRN for your IBM COS resource\n"
    if not TMOS_IMAGE_DIR and not DELETE_ALL:
        ERROR = True
        ERROR_MESSAGE += "please set env TMOS_IMAGE_DIR to scan for patched TMOS images\n"

    if ERROR:
        LOG.error('\n\n%s\n', ERROR_MESSAGE)
        sys.exit(1)
    LOG.info('uploading images into %s with COS_BUCKET_PREFIX %s',
             COS_RESOURCE_CRN, COS_BUCKET_PREFIX)
    if DELETE_ALL:
        delete_all()
    else:
        upload_patched_images()
    if PUBLIC_IMAGES:
        create_public_images()
    if INVENTORY:
        inventory()
    STOP_TIME = time.time()
    DURATION = STOP_TIME - START_TIME
    LOG.debug(
        'process end time: %s - ran %s (seconds)',
        datetime.datetime.fromtimestamp(STOP_TIME).strftime(
            "%A, %B %d, %Y %I:%M:%S"), DURATION)
