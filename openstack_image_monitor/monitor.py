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
This module runs both the image patcher and openstack image
uploader on a regular basis.
"""
import os
import sys
import time
import logging
import subprocess
import signal

KEEP_RUNNING = True
IN_PROCESS = False

LOG = logging.getLogger('openstack_image_monitor')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)


def run(image_patcher, openstack_uploader):
    global IN_PROCESS
    if not IN_PROCESS:
        IN_PROCESS = True
        subprocess.Popen(image_patcher).wait()
        subprocess.Popen(openstack_uploader).wait()
        IN_PROCESS = False


def sig_exit():
    global KEEP_RUNNING
    KEEP_RUNNING = False


if __name__ == "__main__":
    if not os.environ['USER'] == 'root':
        print "Please run this script as sudo"
        sys.exit(1)
    INTERVAL = int(os.getenv('INTERVAL', 1800))
    IMAGE_PATCHER = os.getenv('IMAGE_PATCHER', '/tmos-cloudinit/tmos_image_patcher/tmos_image_patcher.py')
    OPENSTACK_IMAGE_UPLOADER = os.getenv('OPENSTACK_IMAGE_UPLOADER', '/tmos-cloudinit/openstack_image_uploader/openstack_glance_image_uploader.py')
    LOG.info('running monitor every %d seconds' % INTERVAL)
    while KEEP_RUNNING:
        try:
            run(IMAGE_PATCHER, OPENSTACK_IMAGE_UPLOADER)
        except Exception as error:
            LOG.error('error running image monitor: %s' % error)
        time.sleep(INTERVAL)
