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

TMOS_IMAGE_CATALOG_URL = None
API_KEY = None
IMAGE_MATCH = '^[a-zA-Z]'
REGION = 'us-south'
UPDATE_IMAGES = None
DRY_RUN = None
DELETE_ALL = None
AUTH_ENDPOINT = 'https://iam.cloud.ibm.com/identity/token'

LOG = logging.getLogger('tmos_image_patcher')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)

SESSION_TOKEN = None
SESSION_TIMESTAMP = 0
SESSION_SECONDS = 1800


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


def get_existing_vpcs(token, region):
    vpc_url = "https://%s.iaas.cloud.ibm.com/v1/vpcs?version=2020-04-07&generation=2" % region
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    response = requests.get(vpc_url, headers=headers)
    if response.status_code < 300:
        return response.json()
    else:
        return None


def get_images(token, region):
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images?version=2020-04-07&generation=2&visibility=private" % region
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


def import_image(token, region, name, cos_url):
    image_url = "https://%s.iaas.cloud.ibm.com/v1/images?version=2020-04-07&generation=2" % region
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    data = {
        "name": name,
        "file": {
            "href": cos_url
        },
        "operating_system": {
            "name": "centos-7-amd64"
        }
    }
    response = requests.post(image_url, headers=headers, data=json.dumps(data))
    return response


def image_exists(image_name, region=None):
    token = get_iam_token()
    existing_images = get_images(token, region)
    if existing_images:
        for image in existing_images['images']:
            if image_name == image['name']:
                return True
    return False


def delete_image(image_name, region=None):
    token = get_iam_token()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token
    }
    existing_images = get_images(token, region)
    if existing_images:
        for image in existing_images['images']:
            if image_name == image['name']:
                del_url = "https://%s.iaas.cloud.ibm.com/v1/images/%s?version=2020-04-07&generation=2" % (region, image['id'])    
                response = requests.delete(del_url, headers=headers)
                if response.status_code < 400:
                    return True
                else:
                    LOG.error('error deleting image %d:%s', response.status_code, response.content)
    return False


def dry_run(catalog_db):
    for region in REGION:
        if region in catalog_db:
            for image in catalog_db[region]:
                if re.search(IMAGE_MATCH, image['image_name']):
                    if DELETE_ALL:
                        LOG.info('dry run - would delete %s in %s if exists', image['image_name'], region)
                    elif UPDATE_IMAGES:
                        LOG.info('dry run - would update %s in %s if exists', image['image_name'], region)
                    else:
                        LOG.info('dry run - would import custom image %s in %s if it does not exists', image['image_name'], region)


def delete_all_images():
    token = get_iam_token()
    for region in REGION:
        existing_images = get_images(token, region)
        for image in existing_images['images']:
            if re.search(IMAGE_MATCH, image['name']):
                LOG.info('deleting image %s', image['name'])
                if not delete_image(image['name'], region):
                    LOG.error('image deletion failed for image %s', image['name'])


def import_images(catalog_db):
    token = get_iam_token()
    for region in REGION:
        if region in catalog_db:
            for image in catalog_db[region]:
                if re.search(IMAGE_MATCH, image['image_name']):
                    exists = image_exists(image['image_name'], region)
                    if exists and UPDATE_IMAGES:
                        LOG.info('deleting image %s to force update', image['image_name'])
                        if delete_image(image['image_name'], region):
                            exists = False
                    if exists:
                        LOG.info('image %s already exists', image['image_name'])
                    else:
                        response = import_image(
                            token, region, image['image_name'],
                            image['image_sql_url'])
                        if response.status_code > 300:
                            LOG.error('could not import %s: %d - %s', 
                                      image['image_name'],
                                      response.status_code, response.content)
                        else:
                            LOG.info('imported image %s', image['image_name'])


def get_tmos_image_catalog():
    """get TMOS catalog JSON"""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.get(TMOS_IMAGE_CATALOG_URL, headers=headers)
    if response.status_code > 400:
        LOG.error('could not retrieve F5 TMOS image catalog %d:%s' % (response.status_code, response.content))
        return None
    else:
        return response.json()


def initialize():
    """initialize configuration from environment variables"""
    global TMOS_IMAGE_CATALOG_URL, API_KEY, IMAGE_MATCH, REGION, UPDATE_IMAGES, DRY_RUN, DELETE_ALL, AUTH_ENDPOINT
    TMOS_IMAGE_CATALOG_URL = os.getenv(
        'TMOS_IMAGE_CATALOG_URL',
        'https://f5-image-catalog-us-south.s3.us-south.cloud-object-storage.appdomain.cloud/f5-image-catalog.json'
    )
    API_KEY = os.getenv('API_KEY', None)
    IMAGE_MATCH = os.getenv('IMAGE_MATCH', '^[a-zA-Z]')
    REGION = os.getenv('REGION', 'us-south')
    REGION = [ x.strip() for x in REGION.split(',') ]
    DRY_RUN = os.getenv('DRY_RUN', 'false')
    if DRY_RUN.lower() == 'true':
        DRY_RUN = True
    else:
        DRY_RUN = False
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
    LOG.debug('processing images in %s', REGION)
    AUTH_ENDPOINT = os.getenv(
        'AUTH_ENDPOINT', 'https://iam.cloud.ibm.com/identity/token')
    

if __name__ == "__main__":
    START_TIME = time.time()
    LOG.debug('process start time: %s', datetime.datetime.fromtimestamp(
        START_TIME).strftime("%A, %B %d, %Y %I:%M:%S"))
    initialize()
    ERROR_MESSAGE = ''
    ERROR = False
    if not API_KEY:
        ERROR = True
        ERROR_MESSAGE += "please set env API_KEY for your IBM IaaS Account\n"
    catalog_db = get_tmos_image_catalog()
    if not catalog_db:
        ERROR = True
        ERROR_MESSAGE += "could not read TMOS image catalog\n"
    if ERROR:
        LOG.error('\n\n%s\n', ERROR_MESSAGE)
        sys.exit(1)
    if DRY_RUN:
        dry_run(catalog_db)
    else:
        if DELETE_ALL:
            delete_all_images()
        else:
            import_images(catalog_db)
    STOP_TIME = time.time()
    DURATION = STOP_TIME - START_TIME
    LOG.debug(
        'process end time: %s - ran %s (seconds)',
        datetime.datetime.fromtimestamp(
            STOP_TIME).strftime("%A, %B %d, %Y %I:%M:%S"),
        DURATION
    )



