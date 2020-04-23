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
import base64
import time
import datetime
import logging
import json
import uuid

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
UPDATE_IMAGES = None
DELETE_ALL = None

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
    """get OpenStack glance client"""
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
    """get image name formatted string"""
    if 'DATASTOR' in image_path:
        return "%s_DATASTOR" % os.path.splitext(os.path.dirname(image_path.replace(TMOS_IMAGE_DIR, '')).replace(os.path.sep, ''))[0]
    else:
        return os.path.splitext(os.path.dirname(image_path.replace(TMOS_IMAGE_DIR, '')).replace(os.path.sep, ''))[0]


def assure_glance_image(image_path):
    """check if patched image already exists"""
    image_name = get_image_name(image_path)

    try:
        glance = get_glance_client()
        exist_image_id = None
        for image in glance.images.list():
            if image.name == image_name:
                LOG.debug('found existing image %s with name %s', image.id, image_name)
                if UPDATE_IMAGES:
                    LOG.debug('deleting existing image %s', image.id)
                    glance.images.delete(image.id)
                    exist_image_id = image.id
                else:
                    return True
        if not exist_image_id:
            exist_image_id = str(uuid.uuid4())
        image = glance.images.create(name=image_name, id=exist_image_id, container_format='bare', disk_format='qcow2', visibility=OS_IMAGE_VISIBILITY)
        LOG.debug('image created with id: %s for name %s', image.id, image_name)
        glance.images.upload(image.id, open(image_path, 'rb'))
        LOG.debug('upload complete image: %s', image_name)
        kwargs = {'owner_specified.uploader_managed':'true'}
        glance.images.update(image.id, **kwargs)
        md5sum_path = "%s.md5" % image_path
        if os.path.exists(md5sum_path):
            with open(md5sum_path, 'r') as md5sum_file:
                kwargs = {'owner_specified.shade.md5':str(md5sum_file.read())}
                glance.images.update(image.id, **kwargs)
        sig_path = "%s.384.sig" % image_path
        if os.path.exists(sig_path):
            with open(sig_path, 'r') as sig_file:
                b64sig = base64.b64encode(sig_file.read())
                kwargs = {'owner_specified.shade.base64.sha384.sig':str(b64sig)}
                glance.images.update(image.id, **kwargs)
        return True
    except Exception as ex:
        LOG.error('exception occurred assuring glance image for file %s: %s', image_path, ex)
        return False


def upload_patched_images():
    """upload discovered images to OpenStack glance"""
    for image_path in get_patched_images(TMOS_IMAGE_DIR):
        assure_glance_image(image_path)


def delete_image(image_id):
    """delete a glance image by id"""
    glance = get_glance_client()
    glance.images.delete(image_id)


def delete_all():
    """delete all uploader managed images"""
    glance = get_glance_client()
    for image in glance.images.list():
        if 'owner_specified.uploader_managed' in image:
            glance.images.delete(id)


def inventory():
    """create inventory JSON"""
    inventory_file = "%s/openstack_images.json" % TMOS_IMAGE_DIR
    if os.path.exists(inventory_file):
        os.unlink(inventory_file)
    glance = get_glance_client()
    images = []
    for image in glance.images.list():
        if 'owner_specified.uploader_managed' in image:
            images.append(image)
    if images:
        with open(inventory_file, 'w') as ivf:
            ivf.write(json.dumps(images))


def initialize():
    """initialize configuration from environment"""
    global TMOS_IMAGE_DIR, OS_PROJECT_DOMAIN_NAME, OS_USER_DOMAIN_NAME, OS_PROJECT_NAME, OS_IMAGE_VISIBILITY, OS_USERNAME, OS_PASSWORD, OS_AUTH_URL, UPDATE_IMAGES, DELETE_ALL
    TMOS_IMAGE_DIR = os.getenv('TMOS_IMAGE_DIR', None)
    OS_PROJECT_DOMAIN_NAME = os.getenv('OS_PROJECT_DOMAIN_NAME', 'default')
    OS_USER_DOMAIN_NAME = os.getenv('OS_USER_DOMAIN_NAME', 'default')
    OS_PROJECT_NAME = os.getenv('OS_PROJECT_NAME', 'admin')
    OS_IMAGE_VISIBILITY = os.getenv('OS_IMAGE_VISIBILITY', 'public')
    OS_USERNAME = os.getenv('OS_USERNAME', None)
    OS_PASSWORD = os.getenv('OS_PASSWORD', None)
    OS_AUTH_URL = os.getenv('OS_AUTH_URL', None)
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


if __name__ == "__main__":
    START_TIME = time.time()
    LOG.debug('process start time: %s', datetime.datetime.fromtimestamp(
        START_TIME).strftime("%A, %B %d, %Y %I:%M:%S"))
    initialize()
    ERROR_MESSAGE = ''
    ERRPR = False
    if not TMOS_IMAGE_DIR:
        ERRPR = True
        ERROR_MESSAGE += "please set env TMOS_IMAGE_DIR to scan for patched TMOS images\n"
    if not OS_USERNAME:
        ERRPR = True
        ERROR_MESSAGE += "please set env OS_USERNAME to your OpenStack username\n"
    if not OS_PASSWORD:
        ERRPR = True
        ERROR_MESSAGE += "please set env OS_PASSWORD to your OpenStack password\n"
    if not OS_AUTH_URL:
        ERRPR = True
        ERROR_MESSAGE += "please set env OS_AUTH_URL to your OpenStack Keystone endpoint URL\n"
    if ERRPR:
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
