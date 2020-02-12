import os
import json
import screen


def load_demo_defaults():
    env_json_path = "%s/../demo_defaults.json" % os.path.dirname(
        os.path.realpath(__file__))
    if os.path.exists(env_json_path):
        j_f = open(env_json_path, 'r')
        demo_vars = json.load(j_f)
        if 'globals' in demo_vars:
            for var in demo_vars['globals'].keys():
                if not var in os.environ:
                    os.environ[var] = str(demo_vars['globals'][var])
        if 'openstack' in demo_vars:
            for var in demo_vars['openstack'].keys():
                if not var in os.environ:
                    os.environ[var] = str(demo_vars['openstack'][var])


def load_locals(HEADER):
    env_json_path = "%s/../local_defaults.json" % os.path.dirname(
        os.path.realpath(__file__))
    if os.path.exists(env_json_path):
        y_n = screen.print_screen(
            HEADER,
            prompt='Discovered a previous demo environment. Should we reuse it? (Y/N): ')
        if not y_n.lower() == 'y':
            return
        screen.print_screen(
            HEADER,
            message='Loading previous environment settings.. please wait.')
        j_f = open(env_json_path, 'r')
        local_vars = json.load(j_f)
        if 'globals' in local_vars:
            for var in local_vars['globals'].keys():
                if not var in os.environ:
                    os.environ[var] = str(local_vars['globals'][var])
        if 'openstack' in local_vars:
            for var in local_vars['openstack'].keys():
                if not var in os.environ:
                    os.environ[var] = str(local_vars['openstack'][var])


def save_locals(answers=None):
    env_json_path = "%s/../local_defaults.json" % os.path.dirname(
        os.path.realpath(__file__))
    if answers:
        with open(env_json_path, 'w+') as j_f:
            json.dump(answers, j_f)
    else:
        locals_json = {
            'globals': {},
            'openstack': {},
        }
        if os.path.exists(env_json_path):
            with open(env_json_path, 'r') as j_f:
                locals_json = json.load(j_f)
        else:
            globals_vars = [
                'tmos_root_password',
                'tmos_admin_password',
                'license_host',
                'license_username',
                'license_password',
                'license_pool',
                'do_url',
                'as3_url',
                'waf_policy_url'
            ]
            openstack_vars = [
                'tmos_ltm_image_name',
                'tmos_ltm_flavor_name',
                'tmos_all_image_name',
                'tmos_all_flavor_name',
                'external_network_name',
                'management_network_name',
                'cluster_network_name',
                'internal_network_name',
                'vip_network_name',
                'vip_subnet_name'
            ]
            for var in globals_vars:
                if os.environ.get(var):
                    locals_json['globals'][var] = os.environ.get(var)
                else:
                    locals_json['globals'][var] = None
            for var in openstack_vars:
                if os.environ.get(var):
                    locals_json['openstack'][var] = os.environ.get(var)
                else:
                    locals_json['openstack'][var] = None
        with open(env_json_path, 'w+') as j_f:
            json.dump(locals_json, j_f)
