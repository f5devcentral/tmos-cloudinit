#!/usr/bin/env python
import os
import sys

import lib.openstack as openstack

os_project_name = os.getenv('OS_PROJECT_NAME', None)


if os_project_name and os_project_name == 'admin':
    sess = openstack.os_session_from_env()
    openstack.create_standard_f5_flavors(sess)
else:
    print('please source your OpenStack admin RC file\n')
    sys.exit(1)