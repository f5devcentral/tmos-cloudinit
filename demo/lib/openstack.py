import os

from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client as glanceClient
from novaclient.client import Client as novaClient
from neutronclient.v2_0.client import Client as neutronClient


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
    nova.flavors.create(name=name, vcpus=vcpus, ram=ram,
                       disk=disk, is_public=True)


def create_standard_f5_flavors(sess):
    """create F5 Compute flavors"""
    standard_flavors = [
        {'name': 'm1.bigip.LTM.1SLOT', 'vcpus': 1, 'ram': 2048, 'disk': 20},
        {'name': 'm1.bigip.ALL.1SLOT', 'vcpus': 2, 'ram': 6144, 'disk': 60},
        {'name': 'm1.bigip.LTM.small', 'vcpus': 2, 'ram': 4096, 'disk': 40},
        {'name': 'm1.bigip.LTM.medium','vcpus': 4, 'ram': 8192, 'disk': 40},
        {'name': 'm1.bigip.ALL.large', 'vcpus': 4, 'ram': 8192, 'disk': 160},
        {'name': 'm1.bigip.ALL.exlarge', 'vcpus': 8, 'ram': 16384, 'disk': 160},
        {'name': 'm1.bigiq.medium', 'vcpus': 4, 'ram': 8192, 'disk': 160},
    ]
    need_to_create = {}
    for flavor in standard_flavors:
        need_to_create[flavor['name']] = flavor
    for existing_flavor in get_nova_flavors(sess):
        if existing_flavor.name in need_to_create.keys():
            del need_to_create[existing_flavor.name]
    for flavor in need_to_create.keys():
        f = need_to_create[flavor]
        create_flavor(
            sess,
            name=f['name'],
            vcpus=f['vcpus'],
            ram=f['ram'],
            disk=f['disk']
        )


def os_session_from_env():
    os_auth_url = os.getenv('OS_AUTH_URL', None)
    os_username = os.getenv('OS_USERNAME', None)
    os_password = os.getenv('OS_PASSWORD', None)
    os_user_domain_name = os.getenv('OS_USER_DOMAIN_NAME', 'default')
    os_project_domain_id = os.getenv('OS_PROJET_DOMAIN_ID', 'default')
    os_project_name = os.getenv('OS_PROJECT_NAME', 'admin')
    if not os_auth_url:
        raise Exception('OpenStack environment variables not set')
    return get_auth_session(os_auth_url, os_username, os_password,
                            os_project_name, os_user_domain_name,
                            os_project_domain_id)
