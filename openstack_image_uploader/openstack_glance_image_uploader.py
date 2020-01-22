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
and then upload to OpenStack Glance Image Service
"""

import os
import sys
import time
import datetime
import logging

from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client

IMAGE_TYPES = ['.qcow2', '.vhd', '.vmdk']

TMOS_IMAGE_DIR = None
OS_PROJECT_DOMAIN_NAME = None
OS_USER_DOMAIN_NAME = None
OS_PROJECT_NAME = None
OS_IMAGE_VISIBILITY = None
OS_USERNAME = None
OS_PASSWORD = None
OS_AUTH_URL = None

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
                    image_filepath = "%s/%s" % (patched_dir_path, patched_image)
                    return_image_files.append(image_filepath)
    return return_image_files


def get_glance_client():
    loader = loading.get_plugin_loader('password')
    auth = loader.load_from_options(
        auth_url=OS_AUTH_URL,
        username=OS_USERNAME,
        password=OS_PASSWORD,
        project_name=OS_PROJECT_NAME,
        user_domain_id=OS_USER_DOMAIN_NAME,
        project_domain_id=OS_PROJECT_DOMAIN_NAME)
    sess = session.Session(auth=auth)
    return Client('2', session=sess)


def get_image_name(image_path):
    return os.path.splitext(os.path.dirname(image_path.replace(TMOS_IMAGE_DIR, '')).replace(os.path.sep, ''))[0]


def assure_glance_image(image_path):
    """check if patched image already exists"""
    image_name = get_image_name(image_path)
    
    try:
        glance = get_glance_client()

        for image in glance.images.list():
            if image.name == image_name:
                LOG.debug('found existing image %s with name %s', image.id, image_name);
                return True
        image = glance.images.create(name=image_name, container_format='bare', disk_format='qcow2', visibility=OS_IMAGE_VISIBILITY)
        LOG.debug('image created with id: %s for name %s', image.id, image_name)
        glance.images.upload(image.id, open(image_path, 'rb'))
        LOG.debug('upload complete image: %s', image_name)
        return True
    except Exception as ex:
        LOG.error('exception occurred assuring glance image for file %s: %s', image_path, ex)
        return False


def upload_patched_images():
    for image_path in get_patched_images(TMOS_IMAGE_DIR):
        assure_glance_image(image_path)


def initialize():
    global TMOS_IMAGE_DIR, OS_PROJECT_DOMAIN_NAME, OS_USER_DOMAIN_NAME, OS_PROJECT_NAME, OS_IMAGE_VISIBILITY, OS_USERNAME, OS_PASSWORD, OS_AUTH_URL
    TMOS_IMAGE_DIR = os.getenv('TMOS_IMAGE_DIR', None)
    OS_PROJECT_DOMAIN_NAME = os.getenv('OS_PROJECT_DOMAIN_NAME', 'default')
    OS_USER_DOMAIN_NAME = os.getenv('OS_USER_DOMAIN_NAME', 'default')
    OS_PROJECT_NAME = os.getenv('OS_PROJECT_NAME', 'admin')
    OS_IMAGE_VISIBILITY = os.getenv('OS_IMAGE_VISIBILITY', 'public')
    OS_USERNAME = os.getenv('OS_USERNAME', None)
    OS_PASSWORD = os.getenv('OS_PASSWORD', None)
    OS_AUTH_URL = os.getenv('OS_AUTH_URL', None)


if __name__ == "__main__":
    START_TIME = time.time()
    LOG.debug('process start time: %s', datetime.datetime.fromtimestamp(
        START_TIME).strftime("%A, %B %d, %Y %I:%M:%S"))
    initialize()
    err_message = ''
    err = False
    if not TMOS_IMAGE_DIR:
        err = True
        err_message += "please set env TMOS_IMAGE_DIR to scan for patched TMOS images\n"
    if not OS_USERNAME:
        err = True
        err_message += "please set env OS_USERNAME to your OpenStack username\n"
    if not OS_PASSWORD:
        err = True
        err_message += "please set env OS_PASSWORD to your OpenStack password\n"
    if not OS_AUTH_URL:
        err = True
        err_message += "please set env OS_AUTH_URL to your OpenStack Keystone endpoint URL\n"
    if err:
        LOG.error('\n\n%s\n', err_message)
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
