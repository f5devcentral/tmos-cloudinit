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
import ibm_boto3

from ibm_botocore.client import Config, ClientError

IMAGE_TYPES = ['.qcow2', '.vhd', '.vmdk']

TMOS_IMAGE_DIR = None
COS_API_KEY = None
COS_RESOURCE_CRN = None
COS_IMAGE_LOCATION = None
COS_AUTH_ENDPOINT = None
COS_ENDPOINT = None
UPDATE_IMAGES = False

LOG = logging.getLogger('tmos_image_patcher')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)


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


def get_bucket_name(image_path):
    """Get bucket for this patched image"""
    return "%s-%s" % (os.path.splitext(os.path.dirname(image_path.replace(TMOS_IMAGE_DIR, '')).replace(os.path.sep, ''))[0].replace('_', '-').lower(), COS_IMAGE_LOCATION)


def get_object_name(image_path):
    """Get object name for this patched image"""
    if 'DATASTOR' in image_path:
        return "%s_DATASTOR" % os.path.dirname(image_path.replace(TMOS_IMAGE_DIR, '')).replace(os.path.sep, '')
    else:
        return os.path.dirname(image_path.replace(TMOS_IMAGE_DIR, '')).replace(os.path.sep, '')


def get_cos_client():
    """return IBM COS client object"""
    return ibm_boto3.client("s3",
                            ibm_api_key_id=COS_API_KEY,
                            ibm_service_instance_id=COS_RESOURCE_CRN,
                            ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                            config=Config(signature_version="oauth"),
                            endpoint_url=COS_ENDPOINT)


def get_cos_resource():
    """return IBM COS resource object"""
    return ibm_boto3.resource("s3",
                              ibm_api_key_id=COS_API_KEY,
                              ibm_service_instance_id=COS_RESOURCE_CRN,
                              ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                              config=Config(signature_version="oauth"),
                              endpoint_url=COS_ENDPOINT)


def assure_bucket(bucket_name):
    """Make sure bucket exists"""
    cos_res = get_cos_resource()
    try:
        for bucket in cos_res.buckets.all():
            if bucket.name == bucket_name:
                return True
        LOG.debug('creating bucket %s', bucket_name)
        cos_res.Bucket(bucket_name).create(
            ACL='public-read',
            CreateBucketConfiguration={
                "LocationConstraint": COS_IMAGE_LOCATION
            }
        )
        return True
    except ClientError as client_error:
        LOG.error('client error assuring bucket %s: %s',
                  bucket_name, client_error)
        return False
    except Exception as ex:
        LOG.error('exception occurred assuring bucket %s: %s', bucket_name, ex)
        return False


def assure_object(file_path, bucket_name, object_name):
    """check if patched image already exists"""
    cos_res = get_cos_resource()
    try:
        for obj in cos_res.Bucket(bucket_name).objects.all():
            if obj.key == object_name:
                if UPDATE_IMAGES:
                    obj.delete()
                else:
                    return True
        LOG.debug('starting upload of image %s to %s/%s',
                  file_path, bucket_name, object_name)

        part_size = 1024 * 1024 * 2
        file_threshold = 1024 * 1024 * 1024 * 10

        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )

        cos_client = get_cos_client()
        transfer_mgr = ibm_boto3.s3.transfer.TransferManager(
            cos_client, config=transfer_config)
        upload = transfer_mgr.upload(file_path, bucket_name, object_name)
        upload.result()

        LOG.debug('upload complete for %s/%s', bucket_name, object_name)

        return True

    except ClientError as ce:
        LOG.error('client error assuring object %s/%s: %s',
                  bucket_name, object_name, ce)
        return False
    except Exception as ex:
        LOG.error('exception occurred assuring object %s/%s: %s',
                  bucket_name, object_name, ex)
        return False


def assure_cos_image(image_path):
    """assure patch image object"""
    bucket_name = get_bucket_name(image_path)
    object_name = get_object_name(image_path)
    LOG.debug('checking IBM COS Object: %s/%s exists',
              bucket_name, object_name)
    if assure_bucket(bucket_name):
        assure_object(image_path, bucket_name, object_name)
    md5_path = "%s.md5" % image_path
    if os.path.exists(md5_path):
        md5_object_name = "%s.md5" % object_name
        assure_object(md5_path, bucket_name, md5_object_name)
    sig_path = "%s.384.sig" % image_path
    if os.path.exists(sig_path):
        sig_object_name = "%s.384.sig" % object_name
        assure_object(sig_path, bucket_name, sig_object_name)


def upload_patched_images():
    """check for iamges and assure upload to IBM COS"""
    for image_path in get_patched_images(TMOS_IMAGE_DIR):
        assure_cos_image(image_path)


def initialize():
    """initialize configuration from environment variables"""
    global TMOS_IMAGE_DIR, COS_API_KEY, COS_RESOURCE_CRN, COS_IMAGE_LOCATION, COS_AUTH_ENDPOINT, COS_ENDPOINT, UPDATE_IMAGES
    TMOS_IMAGE_DIR = os.getenv('TMOS_IMAGE_DIR', None)
    COS_API_KEY = os.getenv('COS_API_KEY', None)
    COS_RESOURCE_CRN = os.getenv('COS_RESOURCE_CRN', None)
    COS_IMAGE_LOCATION = os.getenv('COS_IMAGE_LOCATION', 'us-south')
    COS_AUTH_ENDPOINT = os.getenv(
        'COS_AUTH_ENDPOINT', 'https://iam.cloud.ibm.com/identity/token')
    COS_ENDPOINT = os.getenv(
        'COS_ENDPOINT', 'https://s3.us-west.cloud-object-storage.appdomain.cloud')
    UPDATE_IMAGES = os.getenv('UPDATE_IMAGES', False)
    if UPDATE_IMAGES.lower() == 'true':
        UPDATE_IMAGES = True


if __name__ == "__main__":
    START_TIME = time.time()
    LOG.debug('process start time: %s', datetime.datetime.fromtimestamp(
        START_TIME).strftime("%A, %B %d, %Y %I:%M:%S"))
    initialize()
    ERROR_MESSAGE = ''
    ERROR = False
    if not TMOS_IMAGE_DIR:
        ERROR = True
        ERROR_MESSAGE += "please set env TMOS_IMAGE_DIR to scan for patched TMOS images\n"
    if not COS_API_KEY:
        ERROR = True
        ERROR_MESSAGE += "please set env COS_API_KEY for your IBM COS resource\n"
    if not COS_RESOURCE_CRN:
        ERROR = True
        ERROR_MESSAGE += "please set env COS_RESOURCE_CRN for your IBM COS resource\n"
    if ERROR:
        LOG.error('\n\n%s\n', ERROR_MESSAGE)
        sys.exit(1)
    upload_patched_images()
    STOP_TIME = time.time()
    DURATION = STOP_TIME - START_TIME
    LOG.debug(
        'process end time: %s - ran %s (seconds)',
        datetime.datetime.fromtimestamp(
            STOP_TIME).strftime("%A, %B %d, %Y %I:%M:%S"),
        DURATION
    )
