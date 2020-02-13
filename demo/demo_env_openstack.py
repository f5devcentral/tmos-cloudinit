#!/usr/bin/env python
import os
import sys
import json
import requests
import pystache

import lib.screen as screen
import lib.environment as env
import lib.openstack as openstack
import lib.bigiq as bigiq

HEADER = '\n\nOpenStack Demonstration Environment\n\n'


def create_webhook_site_token_url():
    web_hook_url = 'https://webhook.site/token'
    resp = requests.post(web_hook_url, data={'default_status': 200, 'default_content': {
    }, 'default_content_type': 'application/json', 'timeout': 0})
    return 'https://webhook.site/%s' % resp.json()['uuid']


def populate():
    """initialize OpenStack demo environment"""

    screen.print_screen(
        HEADER,
        message='Please wait while we evaluate your OpenStack environemnt'
    )

    try:
        sess = openstack.os_session_from_env()
    except:
        screen.print_screen(
            HEADER,
            message='Please source your OpenStack RC and run this application again', exit=True
        )
    
    # load demo defaults into environment
    env.load_demo_defaults()
    env.load_locals(HEADER)

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
    pool_member = os.getenv('pool_member', None)
    pool_member_port = os.getenv('pool_member_port', 80)

    screen.print_screen(
        HEADER,
        message='Resolving resources from your OpenStack environment, please wait..'
    )
    # resource discovery from environment
    images = openstack.get_glance_images(sess)
    for image in images:
        if image.name == tmos_all_image_name:
            tmos_all_image_uuid = image.id
        if image.name == tmos_ltm_image_name:
            tmos_ltm_image_uuid = image.id
    flavors = openstack.get_nova_flavors(sess)
    if os.getenv('OS_PROJECT_NAME', 'admin') == 'admin':
        found_big_flavors = False
        for flavor in flavors:
            if 'big' in flavor.name:
                found_big_flavors = True
        if not found_big_flavors:
            y_n = screen.print_screen(
                HEADER,
                prompt="Should new TMOS flavors be create for demos? (Y/N): "
            )
            if y_n.lower() == 'y':
                create_standard_f5_flavors(sess)
                flavors = get_nova_flavors(sess)
    for flavor in flavors:
        if flavor.name == tmos_all_flavor_name:
            tmos_all_flavor_uuid = flavor.id
        if flavor.name == tmos_ltm_flavor_name:
            tmos_ltm_flavor_uuid = flavor.id
    authkeys = openstack.get_nova_authkeys(sess)
    for authkey in authkeys:
        if authkey.id == tmos_root_authkey_name:
            tmos_root_authorized_ssh_key = authkey.public_key.rstrip()
    networks = openstack.get_neutron_networks(sess)
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
    for ext_net in external_networks:
        if ext_net['name'] == external_network_name:
            external_network_uuid = ext_net['id']
    subnets = openstack.get_neutron_subnets(sess)
    for subnet in subnets:
        if subnet['name'] == vip_subnet_name:
            vip_subnet_uuid = subnet['id']
    security_groups = openstack.get_neutron_security_groups(sess)

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
        screen.print_screen(HEADER, message=error_messages, exit=True)
        sys.exit(1)

    # if not populated from env, prompt for discovery

    while not tmos_ltm_image_uuid:
        image_names = []
        for image in images:
            image_names.append(image.name)
        image_indx = screen.print_screen(
            HEADER,
            message='Which LTM image should we use?',
            menu={'prompt': 'Enter number: ', 'items': image_names}
        )
        if len(images) >= int(image_indx):
            tmos_ltm_image_name = images[image_indx].name
            tmos_ltm_image_uuid = images[image_indx].id

    while not tmos_ltm_flavor_uuid:
        flavor_names = []
        for flavor in flavors:
            flavor_names.append(flavor.name)
        flavor_indx = screen.print_screen(
            HEADER,
            message='Which LTM flavor should we use?',
            menu={'prompt': 'Enter number: ', 'items': flavor_names}
        )
        tmos_ltm_flavor_name = flavors[flavor_indx].name
        tmos_ltm_flavor_uuid = flavors[flavor_indx].id

    while not tmos_all_image_uuid:
        image_names = []
        for image in images:
            image_names.append(image.name)
        image_indx = screen.print_screen(
            HEADER,
            message='Which ALL image should we use?',
            menu={'prompt': 'Enter number: ', 'items': image_names}
        )
        if len(images) >= int(image_indx):
            tmos_all_image_name = images[image_indx].name
            tmos_all_image_uuid = images[image_indx].id

    while not tmos_all_flavor_uuid:
        flavor_names = []
        for flavor in flavors:
            flavor_names.append(flavor.name)
        flavor_indx = screen.print_screen(
            HEADER,
            message='Which ALL flavor should we use?',
            menu={'prompt': 'Enter number: ', 'items': flavor_names}
        )
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
            sg_indx = screen.print_screen(
                HEADER,
                message='Which security group should we use for TMOS interfaces?',
                menu={'prompt': 'Enter number: ',
                      'items': security_group_names}
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
                key_names.append(kn.id)
            authkey_indx = screen.print_screen(
                HEADER,
                message='Which auth key should be injected into your TMOS instances?',
                menu={'prompt': 'Enter number: ', 'items': key_names}
            )
            tmos_root_authkey_name = authkeys[authkey_indx].id
            tmos_root_authorized_ssh_key = authkeys[authkey_indx].public_key.rstrip(
            )

    while not external_network_name:
        if len(external_networks) == 1:
            external_network_name = external_networks[0]['name']
            external_network_uuid = external_networks[0]['id']
        else:
            ext_net_names = []
            for en in external_networks:
                ext_net_names.append(en['name'])
            net_indx = screen.print_screen(
                HEADER,
                message='Which external network should we use to create Floating IPs?',
                menu={'prompt': 'Enter number: ', 'items': ext_net_names}
            )
            external_network_name = external_networks[net_indx]['name']
            external_network_uuid = external_networks[net_indx]['id']

    if not management_network_name or len(networks) < 2:
        y_n = screen.print_screen(
            HEADER,
            prompt='Should we just create new tenant networks for demos? (Y/N): ')
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
        net_indx = screen.print_screen(
            HEADER,
            message='Which network should we use for TMOS management interfaces?',
            menu={'prompt': 'Enter number: ', 'items': network_names}
        )
        management_network_name = networks[net_indx]['name']
        management_network_uuid = networks[net_indx]['id']
        management_network_mtu = networks[net_indx]['mtu']

    while not cluster_network_name:
        net_indx = screen.print_screen(
            HEADER,
            message='Which network should we use for TMOS cluster sync interfaces?',
            menu={'prompt': 'Enter number: ', 'items': network_names}
        )
        cluster_network_name = networks[net_indx]['name']
        cluster_network_uuid = networks[net_indx]['id']
        cluster_network_mtu = networks[net_indx]['mtu']

    while not internal_network_name:
        net_indx = screen.print_screen(
            HEADER,
            message='Which network should we use for TMOS internal only interfaces?',
            menu={'prompt': 'Enter number: ', 'items': network_names}
        )
        internal_network_name = networks[net_indx]['name']
        internal_network_uuid = networks[net_indx]['id']
        internal_network_mtu = networks[net_indx]['mtu']

    while not (vip_network_name and vip_subnet_uuid):
        net_indx = screen.print_screen(
            HEADER,
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
            net_indx = screen.print_screen(
                HEADER,
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
        license_host = screen.print_screen(
            HEADER,
            prompt='What is the IP or hostname of the BIG-IQ license server?: ')
    while not license_username:
        license_username = screen.print_screen(
            HEADER,
            prompt='What BIG-IQ username should we use?: ')
    while not license_password:
        license_password = screen.print_screen(
            HEADER,
            prompt='What BIG-IQ password should we use?: ')
    while not license_pool:
        try:
            sess = bigiq.get_bigiq_session(license_host, license_username, license_password)
            pools = bigiq.get_pools(sess)
            if len(pools) < 1:
                raise Exception('no RegKey pools found')
            pool_names = []
            for pool in pools:
                pool_names.append(pool['name'])
            pool_indx = screen.print_screen(
                HEADER,
                message='Which BIG-IQ RegKey license pool should we use?',
                menu={'prompt': 'Enter number: ', 'items': pool_names}
            )
            license_pool = pools[pool_indx]['name']
        except:
            license_pool = screen.print_screen(
                HEADER,
                prompt='What BIG-IQ RegKey license pool should we use?: '
            )
    while not do_url:
        do_url = screen.print_screen(
            HEADER,
            prompt='What f5-declarative-onboarding RPM download URL should we use?: ')
    while not as3_url:
        as3_url = screen.print_screen(
            HEADER,
            prompt='What f5-appsvcs-extension RPM download URL should we use?: ')
    while not waf_policy_url:
        waf_policy_url = screen.print_screen(
            HEADER,
            prompt='What is the URL to download your exported WAF policy XML file?: ')
    while not phone_home_url:
        phone_home_url = create_webhook_site_token_url()
    while not pool_member:
        pool_member = screen.print_screen(
            HEADER,
            prompt='What should be the IP address of the pool member behind the WAF?: '
        )
        pool_member_port = screen.print_screen(
            HEADER,
            prompt='What TCP port is the WAF pool member listing on? [i.e. 80]: '
        )
        pool_member_port = int(pool_member_port)

    # save locals for next run
    env.save_locals({
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
            'waf_policy_url': waf_policy_url,
            'pool_member': pool_member,
            'pool_member_port': pool_member_port
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
        'pool_member': pool_member,
        'pool_member_port': pool_member_port,
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

    screen.clear_screen()


if __name__ == "__main__":
    populate()
