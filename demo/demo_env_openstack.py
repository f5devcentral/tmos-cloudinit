#!/usr/bin/env python
import os
import sys
import json
import requests
import pystache

from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client as glanceClient
from novaclient.client import Client as novaClient
from neutronclient.v2_0.client import Client as neutronClient

HEADER = '\n\nOpenStack Demonstration Environment\n\n'

def load_demo_defaults():
    env_json_path = "%s/demo_defaults.json" % os.path.dirname(
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


def load_locals():
    env_json_path = "%s/local_defaults.json" % os.path.dirname(
        os.path.realpath(__file__))
    if os.path.exists(env_json_path):
        y_n = print_screen(prompt='Discovered a previous demo environment. Should we reuse it? (Y/N): ')
        if not y_n.lower() == 'y':
            return
        print_screen(message='Loading previous environment settings.. please wait.')
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
    env_json_path = "%s/local_defaults.json" % os.path.dirname(
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


def get_auth_session(auth_url, username, password,
                     project_name, user_domain_name,
                     project_domain_id):
    """get OpenStack client session"""
    loader = loading.get_plugin_loader('password')
    auth = loader.load_from_options(
        auth_url=auth_url,
        username=username,
        password=password,
        project_name=project_name,
        user_domain_id=user_domain_name,
        project_domain_id=project_domain_id)
    return session.Session(auth=auth)


def get_glance_client(sess):
    """get OpenStack glance client"""
    return glanceClient('2', session=sess)


def get_glance_images(sess):
    """get OpenStack glance images"""
    glance = get_glance_client(sess)
    images_dict = {}
    for image in glance.images.list():
        images_dict[image.name] = image
    image_keys = images_dict.keys()
    image_keys.sort()
    images = []
    for image in image_keys:
        images.append(images_dict[image])
    return images


def get_nova_client(sess):
    """get OpenStack nova client"""
    return novaClient('2', session=sess)


def get_nova_flavors(sess):
    """get OpenStack nova flavors, optionally filtered"""
    nova = get_nova_client(sess)
    flavors_dict = {}
    for flavor in nova.flavors.list():
        flavors_dict[flavor.name] = flavor
    flavor_keys = flavors_dict.keys()
    flavor_keys.sort()
    flavors = []
    for flavor in flavor_keys:
        flavors.append(flavors_dict[flavor])
    return flavors


def get_nova_authkeys(sess):
    """get OpenStack nova flavors, optionally filtered"""
    nova = get_nova_client(sess)
    authkeys_dict = {}
    for authkey in nova.keypairs.list():
        authkeys_dict[authkey.id] = authkey
    authkeys_keys = authkeys_dict.keys()
    authkeys_keys.sort()
    authkeys = []
    for authkey in authkeys_keys:
        authkeys.append(authkeys_dict[authkey])
    return authkeys


def get_neutron_client(sess):
    """get OpenStack neutron client"""
    return neutronClient(session=sess)


def get_neutron_networks(sess):
    """get OpenStack networks"""
    neutron = get_neutron_client(sess)
    networks_dict = {}
    for network in neutron.list_networks()['networks']:
        networks_dict[network['name']] = network
    network_keys = networks_dict.keys()
    network_keys.sort()
    networks = []
    for network in network_keys:
        networks.append(networks_dict[network])
    return networks


def create_neutron_network(sess, network_name):
    """create OpenStack tenant network"""
    neutron = get_neutron_client(sess)
    return neutron.create_network({'network': {'name': network_name}})['network']


def create_neutron_dhcp_subnet(sess, network_uuid, subnet_name,
                               subnet_cidr, subnet_gateway, dns_server, start_address, end_address):
    neutron = get_neutron_client(sess)
    subnet = {
        'network_id': network_uuid,
        'name': subnet_name,
        'ip_version': 4,
        'cidr': subnet_cidr,
        'gateway_ip': subnet_gateway,
        'dns_nameservers': [dns_server],
        'allocation_pools': [{'start': start_address, 'end': end_address}]
    }
    return neutron.create_subnet({'subnet': subnet})['subnet']


def create_neutron_router(sess, external_network_uuid):
    neutron = get_neutron_client(sess)
    router = {
        "name": "demo_router",
        "admin_state_up": True,
        "external_gateway_info": {
            "network_id": external_network_uuid,
            "enable_snat": True
        }
    }
    return neutron.create_router({'router': router})['router']


def add_interface_to_neutron_router(sess, router_uuid, subnet_uuid):
    neutron = get_neutron_client(sess)
    return neutron.add_interface_router(router_uuid, {'subnet_id': subnet_uuid})


def get_neutron_subnets(sess):
    """get OpenStack subnets"""
    neutron = get_neutron_client(sess)
    subnets_dict = {}
    for subnet in neutron.list_subnets()['subnets']:
        subnets_dict[subnet['name']] = subnet
    subnet_keys = subnets_dict.keys()
    subnet_keys.sort()
    subnets = []
    for subnet in subnet_keys:
        subnets.append(subnets_dict[subnet])
    return subnets


def get_neutron_security_groups(sess):
    """get OpenStack security groups"""
    neutron = get_neutron_client(sess)
    security_groups_dict = {}
    project_id = sess.get_project_id()
    for sg in neutron.list_security_groups()['security_groups']:
        if sg['project_id'] == project_id:
            security_groups_dict[sg['name']] = sg
    sg_keys = security_groups_dict.keys()
    sg_keys.sort()
    security_groups = []
    for sg in sg_keys:
        security_groups.append(security_groups_dict[sg])
    return security_groups


def create_flavor(sess, name, vcpus, ram, disk):
    """create flavor """
    nova = get_nova_client(sess)
    nova.flavor.create(name=name, vcpus=vcpus, ram=ram, disk=disk, is_public=True)


def create_standard_f5_flavors(sess):
    """create F5 Compute flavors"""
    create_flavor(sess, 'm1.bigip.LTM_1SLOT', 1, 2, 20)
    create_flavor(sess, 'm1.bigip.ALL_1SLOT', 2, 6, 60)
    create_flavor(sess, 'm1.bigip.LTM.small', 2, 4, 40)
    create_flavor(sess, 'm1.bigip.LTM.medium', 4, 8, 40)
    create_flavor(sess, 'm1.bigip.ALL.large', 4, 8, 160)
    create_flavor(sess, 'm1.bigip.ALL.exlarge', 8, 16, 160)
    create_flavor(sess, 'm1.bigiq.medium', 4, 8, 160)


def create_webhook_site_token_url():
    web_hook_url = 'https://webhook.site/token'
    resp = requests.post(web_hook_url, data={'default_status': 200, 'default_content': {
    }, 'default_content_type': 'application/json', 'timeout': 0})
    return 'https://webhook.site/%s' % resp.json()['uuid']


def os_session_from_env():
    os_auth_url = os.getenv('OS_AUTH_URL', None)
    os_username = os.getenv('OS_USERNAME', None)
    os_password = os.getenv('OS_PASSWORD', None)
    os_user_domain_name = os.getenv('OS_USER_DOMAIN_NAME', 'default')
    os_project_domain_id = os.getenv('OS_PROJET_DOMAIN_ID', 'default')
    os_project_name = os.getenv('OS_PROJECT_NAME', 'admin')
    if not os_auth_url:
        print('\nplease source your OpenStack RC file before populating demo variables.\n')
        sys.exit(1)
    return get_auth_session(os_auth_url, os_username, os_password,
                            os_project_name, os_user_domain_name,
                            os_project_domain_id)


def print_screen(message=None, prompt=None, menu=None, exit=False):
    os.system('clear')
    print(HEADER)
    if message:
        print(message)
        print('\n')
    if exit:
        sys.exit(1)
    if menu:
        for index, item in enumerate(menu['items']):
            print("\t%d) %s" % (index + 1, item))
        print('\n')
        menu_indx = input(menu['prompt'])      
        if len(menu['items']) >= int(menu_indx):
            return (menu_indx-1)
    elif(prompt):
        return raw_input(prompt)


def populate():
    """initialize OpenStack demo environment"""

    print_screen(message='Please wait while we evaluate your OpenStack environemnt')

    # laod OpenStack standard environment variables for AAA
    os_auth_url = os.getenv('OS_AUTH_URL', None)
    os_username = os.getenv('OS_USERNAME', None)
    os_password = os.getenv('OS_PASSWORD', None)
    os_user_domain_name = os.getenv('OS_USER_DOMAIN_NAME', 'default')
    os_project_domain_id = os.getenv('OS_PROJET_DOMAIN_ID', 'default')
    os_project_name = os.getenv('OS_PROJECT_NAME', 'admin')
    if not os_auth_url:
        print_screen(message='Please source your OpenStack RC and run this application again', exit=True)
    # load demo defaults into environment
    load_demo_defaults()
    load_locals()

    sess = get_auth_session(os_auth_url, os_username, os_password,
                            os_project_name, os_user_domain_name,
                            os_project_domain_id)

    # template resource values, attempt to get them from env first
    tmos_ltm_image_name = os.getenv('tmos_ltm_image_name', None)
    tmos_ltm_image_uuid = os.getenv('tmos_ltm_image_uuid', None)
    tmos_ltm_flavor_name = os.getenv('tmos_ltm_flavor_name', None)
    tmos_ltm_flavor_uuid = os.getenv('tmos_ltm_flavor_uuid', None)
    tmos_all_image_name = os.getenv('tmos_all_image_name', None)
    tmos_all_image_uuid = os.getenv('tmos_all_image_uuid', None)
    tmos_all_flavor_name = os.getenv('tmos_all_flavor_name', None)
    tmos_all_flavor_uuid = os.getenv('tmos_all_flavor_uuid', None)
    tmos_root_password = os.getenv('tmos_root_password', None)
    tmos_admin_password = os.getenv('tmos_admin_password', None)
    tmos_root_authkey_name = os.getenv('tmos_root_authkey_name', None)
    tmos_root_authorized_ssh_key = os.getenv(
        'tmos_root_authorized_ssh_key', None)
    license_host = os.getenv('license_host', None)
    license_username = os.getenv('license_username', None)
    license_password = os.getenv('license_password', None)
    license_pool = os.getenv('license_pool', None)
    do_url = os.getenv('do_url', None)
    as3_url = os.getenv('as3_url', None)
    waf_policy_url = os.getenv('waf_policy_url', None)
    phone_home_url = os.getenv(
        'phone_home_url', create_webhook_site_token_url())
    external_network_name = os.getenv('external_network_name', None)
    external_network_uuid = os.getenv('external_network_uuid', None)
    management_network_name = os.getenv('management_network_name', None)
    management_network_uuid = os.getenv('management_network_uuid', None)
    management_network_mtu = int(os.getenv('management_network_mtu', 1450))
    cluster_network_name = os.getenv('cluster_network_name', None)
    cluster_network_uuid = os.getenv('cluster_network_uuid', None)
    cluster_network_mtu = int(os.getenv('cluster_network_mtu', 1450))
    internal_network_name = os.getenv('internal_network_name', None)
    internal_network_uuid = os.getenv('internal_network_uuid', None)
    internal_network_mtu = int(os.getenv('internal_network_mtu', 1450))
    vip_network_name = os.getenv('vip_network_name', None)
    vip_network_uuid = os.getenv('vip_network_uuid', None)
    vip_network_mtu = int(os.getenv('vip_network_mtu', 1450))
    vip_subnet_name = os.getenv('vip_subnet_name', None)
    vip_subnet_uuid = os.getenv('vip_subnet_uuid', None)
    security_group_name = os.getenv('security_group_name', None)
    security_group_uuid = os.getenv('security_group_uuid', None)
    heat_timeout = os.getenv('heat_timeout', 1800)

    print_screen(message='Resolving resources from your OpenStack environment, please wait..')
    # resource discovery from environment
    images = get_glance_images(sess)
    for image in images:
        if image.name == tmos_all_image_name:
            tmos_all_image_uuid = image.id
        if image.name == tmos_ltm_image_name:
            tmos_ltm_image_uuid = image.id
    flavors = get_nova_flavors(sess)
    if os_project_name == 'admin':
        found_big_flavors = False
        for flavor in flavors:
            if 'big' in flavor:
                found_big_flavors = True
        if not found_big_flavors:
            y_n = print_screen(prompt="Should new TMOS flavors be create for demos? (Y/N): ")
            if y_n.lower() == 'y':
                create_standard_f5_flavors(sess)
                flavors = get_nova_flavors(sess)
    for flavor in flavors:
        if flavor.name == tmos_all_flavor_name:
            tmos_all_flavor_uuid = flavor.id
        if flavor.name == tmos_ltm_flavor_name:
            tmos_ltm_flavor_uuid = flavor.id
    authkeys = get_nova_authkeys(sess)
    for authkey in authkeys:
        if authkey.id == tmos_root_authkey_name:
            tmos_root_authorized_ssh_key = authkey.public_key.rstrip()
    networks = get_neutron_networks(sess)
    external_networks = []
    for network in networks:
        if network['router:external']:
            external_networks.append(network)
        if network['name'] == management_network_name:
            management_network_uuid = network['id']
            management_network_mtu = network['mtu']
        if network['name'] == cluster_network_name:
            cluster_network_uuid = network['id']
            cluster_network_mtu = network['mtu']
        if network['name'] == internal_network_name:
            internal_network_uuid = network['id']
            internal_network_mtu = network['mtu']
        if network['name'] == vip_network_name:
            vip_network_uuid = network['id']
            vip_network_mtu = network['mtu']
    external_networks = external_networks
    for ext_net in external_networks:
        if ext_net['name'] == external_network_name:
            external_network_uuid = ext_net['id']
    subnets = get_neutron_subnets(sess)
    for subnet in subnets:
        if subnet['name'] == vip_subnet_name:
            vip_subnet_uuid = subnet['id']
    security_groups = get_neutron_security_groups(sess)

    req_errors = False
    error_messages = ''

    if len(images) == 0:
        error_messages += 'No compute images found.\n\n'
        req_errors = True

    if len(flavors) == 0:
        error_messages += 'No compute flavors found.\n\n'
        req_errors = True

    if len(authkeys) == 0:
        error_messages += 'No compute authentication SSH keys found.\n\n'
        req_errors = True

    if len(external_networks) == 0:
        error_messages += 'No external networks found. Demos create Floating IPs.\n\n'
        req_errors = True

    if req_errors:
        print_screen(message=error_messages, exit=True)
        sys.exit(1)

    # if not populated from env, prompt for discovery

    while not tmos_ltm_image_uuid:
        image_names = []
        for image in images:
            image_names.append(image.name)
        image_indx = print_screen(message='Which LTM image should we use?', menu={'prompt': 'Enter number: ', 'items': image_names})
        if len(images) >= int(image_indx):
            tmos_ltm_image_name = images[image_indx].name
            tmos_ltm_image_uuid = images[image_indx].id

    while not tmos_ltm_flavor_uuid:
        flavor_names = []
        for flavor in flavors:
            flavor_names.append(flavor.name)
        flavor_indx = print_screen(message='Which LTM flavor should we use?', menu={'prompt': 'Enter number: ', 'items': flavor_names})
        tmos_ltm_flavor_name = flavors[flavor_indx].name
        tmos_ltm_flavor_uuid = flavors[flavor_indx].id

    while not tmos_all_image_uuid:
        image_names = []
        for image in images:
            image_names.append(image.name)
        image_indx = print_screen(message='Which ALL image should we use?', menu={'prompt': 'Enter number: ', 'items': image_names})
        if len(images) >= int(image_indx):
            tmos_all_image_name = images[image_indx].name
            tmos_all_image_uuid = images[image_indx].id

    while not tmos_all_flavor_uuid:
        flavor_names = []
        for flavor in flavors:
            flavor_names.append(flavor.name)
        flavor_indx = print_screen(message='Which ALL flavor should we use?', menu={'prompt': 'Enter number: ', 'items': flavor_names})
        tmos_all_flavor_name = flavors[flavor_indx].name
        tmos_all_flavor_uuid = flavors[flavor_indx].id


    while not security_group_uuid:
        if len(security_groups) == 1:
            security_group_name = security_groups[0]['name']
            security_group_uuid = security_groups[0]['id']
        else:
            security_group_names = []
            
            for sg in security_groups:
                security_group_names.append(sg['name'])
            sg_indx = print_screen(
                message='Which security group should we use for TMOS interfaces?',
                menu={'prompt': 'Enter number: ', 'items': security_group_names}
            )
            security_group_name = security_groups[sg_indx]['name']
            security_group_uuid = security_groups[sg_indx]['id']

    while not tmos_root_authkey_name:
        if len(authkeys) == 1:
            tmos_root_authkey_name = authkeys[0].id
            tmos_root_authorized_ssh_key = authkeys[0].public_key.rstrip()
        else:
            key_names = []
            for kn in authkeys:
                key_names.append(kn)
            authkey_indx = print_screen(
                message='Which auth key should be injected into your TMOS instances?',
                menu={'prompt': 'Enter number: ', 'items': key_names}
            )
            tmos_root_authkey_name = authkeys[authkey_indx].id
            tmos_root_authorized_ssh_key = authkeys[authkey_indx].public_key.rstrip()

    while not external_network_name:
        if len(external_networks) == 1:
            external_network_name = external_networks[0]['name']
            external_network_uuid = external_networks[0]['id']
        else:
            ext_net_names = []
            for en in external_networks:
                ext_net_names.append(en['name'])
            net_indx = print_screen(
                message='Which external network should we use to create Floating IPs?',
                menu={'prompt': 'Enter number: ', 'items': ext_net_names}
            )
            external_network_name = external_networks[net_indx]['name']
            external_network_uuid = external_networks[net_indx]['id']

    if not management_network_name or len(networks) < 2:
        y_n = print_screen(prompt='Should we just create new tenant networks for demos? (Y/N): ')
        if y_n.lower() == 'y':
            management = create_neutron_network(
                sess, 'tmos_demo_management')
            management_network_name = management['name']
            management_network_uuid = management['id']
            management_network_mtu = management['mtu']
            management_subnet = create_neutron_dhcp_subnet(
                sess, management_network_uuid, 'tmos_demo_management',
                '192.168.245.0/24', '192.168.245.1', '8.8.8.8', '192.168.245.20', '192.168.245.200'
            )
            cluster = create_neutron_network(sess, 'tmos_demo_HA')
            cluster_network_name = cluster['name']
            cluster_network_uuid = cluster['id']
            cluster_network_mtu = cluster['mtu']
            cluster_subnet = create_neutron_dhcp_subnet(
                sess, cluster_network_uuid, 'tmos_demo_HA',
                '1.1.1.0/24', '1.1.1.1', '8.8.8.8', '1.1.1.20', '1.1.1.200'
            )
            internal = create_neutron_network(sess, 'tmos_demo_internal')
            internal_network_name = internal['name']
            internal_network_uuid = internal['id']
            internal_network_mtu = internal['mtu']
            internal_subnet = create_neutron_dhcp_subnet(
                sess, internal_network_uuid, 'tmos_demo_internal',
                '192.168.40.0/24', '192.168.40.1', '8.8.8.8', '192.168.40.20', '192.168.40.200'
            )
            external = create_neutron_network(sess, 'tmos_demo_external')
            vip_network_name = external['name']
            vip_network_uuid = external['id']
            vip_network_mtu = external['mtu']
            vip_subnet = create_neutron_dhcp_subnet(
                sess, vip_network_uuid, 'tmos_demo_external',
                '192.168.80.0/24', '192.168.80.1', '8.8.8.8', '192.168.80.20', '192.168.80.200'
            )
            vip_subnet_name = vip_subnet['name']
            vip_subnet_uuid = vip_subnet['id']
            networks = [management_network_uuid, cluster_network_uuid,
                        internal_network_uuid, external_network_uuid]
            router = create_neutron_router(sess, external_network_uuid)
            add_interface_to_neutron_router(
                sess, router['id'], management_subnet['id'])
            add_interface_to_neutron_router(
                sess, router['id'], cluster_subnet['id'])
            add_interface_to_neutron_router(
                sess, router['id'], internal_subnet['id'])
            add_interface_to_neutron_router(
                sess, router['id'], vip_subnet['id'])
    
    network_names = []
    for net in networks:
        network_names.append(net['name'])

    while not management_network_name:
        net_indx = print_screen(
            message='Which network should we use for TMOS management interfaces?',
            menu={'prompt': 'Enter number: ', 'items': network_names}
        )
        management_network_name = networks[net_indx]['name']
        management_network_uuid = networks[net_indx]['id']
        management_network_mtu = networks[net_indx]['mtu']

    while not cluster_network_name:
        net_indx = print_screen(
            message='Which network should we use for TMOS cluster sync interfaces?',
            menu={'prompt': 'Enter number: ', 'items': network_names}
        )
        cluster_network_name = networks[net_indx]['name']
        cluster_network_uuid = networks[net_indx]['id']
        cluster_network_mtu = networks[net_indx]['mtu']

    while not internal_network_name:
        net_indx = print_screen(
            message='Which network should we use for TMOS internal only interfaces?',
            menu={'prompt': 'Enter number: ', 'items': network_names}
        )
        internal_network_name = networks[net_indx]['name']
        internal_network_uuid = networks[net_indx]['id']
        internal_network_mtu = networks[net_indx]['mtu']

    while not (vip_network_name and vip_subnet_uuid):
        net_indx = print_screen(
            message='Which network should we use for TMOS Virtual Servers?',
            menu={'prompt': 'Enter number: ', 'items': network_names}
        )
        vip_network_name = networks[net_indx]['name']
        vip_network_uuid = networks[net_indx]['id']
        vip_network_mtu = networks[net_indx]['mtu']
        
        candidate_subnets = []
        for subnet in subnets:
            if subnet['network_id'] == vip_network_uuid:
                candidate_subnets.append(subnet)
        if len(candidate_subnets) == 1:
            vip_subnet_name = candidate_subnets[0]['name']
            vip_subnet_uuid = candidate_subnets[0]['id']
        else:
            subnet_names = []
            for sn in candidate_subnets:
                subnet_names.append(sn['name'])
            net_indx = print_screen(
                message='Which subnet should we use for TMOS Virtual Servers?',
                menu={'prompt': 'Enter number: ', 'items': subnet_names}
            )
            vip_subnet_name = networks[net_indx]['name']
            vip_subnet_uuid = networks[net_indx]['id']

    while not tmos_root_password:
        tmos_root_password = 'f5c0nfig'
    while not tmos_admin_password:
        tmos_admin_password = 'f5c0nfig'
    while not license_host:
        license_host = print_screen(prompt='What is the IP or hostname of the BIG-IQ license server?: ')
    while not license_username:
        license_username = print_screen(prompt='What BIG-IQ username should we use?: ')
    while not license_password:
        license_password = print_screen(prompt='What BIG-IQ password should we use?: ')
    while not license_pool:
        license_pool = print_screen(prompt='What BIG-IQ RegKey license pool should we use?: ')
    while not do_url:
        do_url = print_screen(prompt='What f5-declarative-onboarding RPM download URL should we use?: ')
    while not as3_url:
        as3_url = print_screen(prompt='What f5-appsvcs-extension RPM download URL should we use?: ')
    while not waf_policy_url:
        waf_policy_url = print_screen('What is the URL to download your exported WAF policy XML file?: ')
    while not phone_home_url:
        phone_home_url = create_webhook_site_token_url()

    # save locals for next run
    save_locals({
        'globals': {
            'tmos_root_password': tmos_root_password,
            'tmos_admin_password': tmos_admin_password,
            'tmos_root_authorized_ssh_key': tmos_root_authorized_ssh_key.rstrip(),
            'license_host': license_host,
            'license_username': license_username,
            'license_password': license_password,
            'license_pool': license_pool,
            'do_url': do_url,
            'as3_url': as3_url,
            'waf_policy_url': waf_policy_url
        },
        'openstack': {
            'tmos_ltm_image_name': tmos_ltm_image_name,
            'tmos_ltm_image_uuid': tmos_ltm_image_uuid,
            'tmos_ltm_flavor_name': tmos_ltm_flavor_name,
            'tmos_ltm_flavor_uuid': tmos_ltm_flavor_uuid,
            'tmos_all_image_name': tmos_all_image_name,
            'tmos_all_image_uuid': tmos_all_image_uuid,
            'tmos_all_flavor_name': tmos_all_flavor_name,
            'tmos_all_flavor_uuid': tmos_all_flavor_uuid,
            'tmos_root_authkey_name': tmos_root_authkey_name,
            'external_network_name': external_network_name,
            'external_network_uuid': external_network_uuid,
            'management_network_name': management_network_name,
            'management_network_uuid': management_network_uuid,
            'management_network_mtu': management_network_mtu,
            'management_security_group_name': security_group_name,
            'management_security_group_uuid': security_group_uuid,
            'cluster_network_name': cluster_network_name,
            'cluster_network_uuid': cluster_network_uuid,
            'cluster_network_mtu': cluster_network_mtu,
            'cluster_security_group_name': security_group_name,
            'cluster_security_group_uuid': security_group_uuid,
            'internal_network_name': internal_network_name,
            'internal_network_uuid': internal_network_uuid,
            'internal_network_mtu': internal_network_mtu,
            'internal_security_group_name': security_group_name,
            'internal_security_group_uuid': security_group_uuid,
            'vip_network_name': vip_network_name,
            'vip_network_uuid': vip_network_uuid,
            'vip_network_mtu': vip_network_mtu,
            'vip_network_security_group_name': security_group_name,
            'vip_network_security_group_uuid': security_group_uuid,
            'vip_subnet_name': vip_subnet_name,
            'vip_subnet_uuid': vip_subnet_uuid,
            'heat_timeout': heat_timeout
        }
    })

    answers = {
        'tmos_ltm_image_name': tmos_ltm_image_name,
        'tmos_ltm_image_uuid': tmos_ltm_image_uuid,
        'tmos_ltm_flavor_name': tmos_ltm_flavor_name,
        'tmos_ltm_flavor_uuid': tmos_ltm_flavor_uuid,
        'tmos_all_image_name': tmos_all_image_name,
        'tmos_all_image_uuid': tmos_all_image_uuid,
        'tmos_all_flavor_name': tmos_all_flavor_name,
        'tmos_all_flavor_uuid': tmos_all_flavor_uuid,
        'tmos_root_password': tmos_root_password,
        'tmos_admin_password': tmos_admin_password,
        'tmos_root_authkey_name': tmos_root_authkey_name,
        'tmos_root_authorized_ssh_key': tmos_root_authorized_ssh_key.rstrip(),
        'license_host': license_host,
        'license_username': license_username,
        'license_password': license_password,
        'license_pool': license_pool,
        'do_url': do_url,
        'as3_url': as3_url,
        'waf_policy_url': waf_policy_url,
        'phone_home_url': phone_home_url,
        'external_network_name': external_network_name,
        'external_network_uuid': external_network_uuid,
        'management_network_name': management_network_name,
        'management_network_uuid': management_network_uuid,
        'management_network_mtu': management_network_mtu,
        'management_network_security_group_name': security_group_name,
        'management_network_security_group_uuid': security_group_uuid,
        'cluster_network_name': cluster_network_name,
        'cluster_network_uuid': cluster_network_uuid,
        'cluster_network_mtu': cluster_network_mtu,
        'cluster_network_security_group_name': security_group_name,
        'cluster_network_security_group_uuid': security_group_uuid,
        'internal_network_name': internal_network_name,
        'internal_network_uuid': internal_network_uuid,
        'internal_network_mtu': internal_network_mtu,
        'internal_network_security_group_name': security_group_name,
        'internal_network_security_group_uuid': security_group_uuid,
        'vip_network_name': vip_network_name,
        'vip_network_uuid': vip_network_uuid,
        'vip_network_mtu': vip_network_mtu,
        'vip_network_security_group_name': security_group_name,
        'vip_network_security_group_uuid': security_group_uuid,
        'vip_subnet_name': vip_subnet_name,
        'vip_subnet_uuid': vip_subnet_uuid,
        'heat_timeout': heat_timeout
    }

    # write out HEAT env YAML files
    heat_tld = "%s/openstack/heat" % os.path.dirname(
        os.path.realpath(__file__))
    templates = []
    for root, dirs, files in os.walk(heat_tld):
        for f_n in files:
            if f_n.endswith('.mst'):
                templates.append(os.path.join(root, f_n))
    for template in templates:
        env_path = "%s.yaml" % os.path.splitext(template)[0]
        with open(template, 'r') as t_f:
            with open(env_path, 'w+') as e_f:
                e_f.write(pystache.render(t_f.read(), answers))
    # write out Ansible config file
    ansible_tld = "%s/openstack/ansible" % os.path.dirname(
        os.path.realpath(__file__))
    templates = []
    for root, dirs, files in os.walk(ansible_tld):
        for f_n in files:
            if f_n.endswith('.mst'):
                templates.append(os.path.join(root, f_n))
    for template in templates:
        env_path = "%s.yaml" % os.path.splitext(template)[0]
        with open(template, 'r') as t_f:
            with open(env_path, 'w+') as e_f:
                e_f.write(pystache.render(t_f.read(), answers))
    # write out terraform config files
    terraform_tld = "%s/openstack/terraform" % os.path.dirname(
        os.path.realpath(__file__))
    templates = []
    for root, dirs, files in os.walk(terraform_tld):
        for f_n in files:
            if f_n.endswith('.mst'):
                templates.append(os.path.join(root, f_n))
    for template in templates:
        var_path = "%s.tf" % os.path.splitext(template)[0]
        with open(template, 'r') as t_f:
            with open(var_path, 'w+') as v_f:
                v_f.write(pystache.render(t_f.read(), answers))

    os.system('clear')

if __name__ == "__main__":
    populate()
