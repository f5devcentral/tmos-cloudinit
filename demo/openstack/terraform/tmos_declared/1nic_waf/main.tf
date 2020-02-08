data "openstack_networking_network_v2" "vip_network" {
  network_id = "${var.vip_network}"
}

data "openstack_networking_subnet_v2" "vip_subnet" {
  network_id = "${var.vip_network}"
}

resource "openstack_networking_port_v2" "vip_port" {
  name           = "${var.server_name}_vip_port"
  network_id     = "${var.vip_network}"
  admin_state_up = "true"
  security_group_ids = [
    "${var.vip_network_security_group}"
  ]
  allowed_address_pairs {
    ip_address = "0.0.0.0/0"
  }
  allowed_address_pairs {
    ip_address = "::/0"
  }
  fixed_ip {
    subnet_id = "${var.vip_subnet}"
  }
}

resource "openstack_networking_floatingip_v2" "vip_floating_ip" {
  port_id = "${openstack_networking_port_v2.vip_port.id}"
  pool    = "${var.external_network_name}"
}

locals {
  dns_assignment = "${element("${openstack_networking_port_v2.vip_port.dns_assignment}", 0)}"
  port_fqdn      = "${replace("${local.dns_assignment.fqdn}", "/\\.$/", "")}"
  port_name      = "${replace("${local.dns_assignment.hostname}", "/^\\.|\\.$/", "")}"
  domain         = "${replace("${local.port_fqdn}", "${local.port_name}.", "")}"
  hostname       = "${var.server_name}.${local.domain}"
}

data "template_file" "user_data" {
  template = "${file("${path.module}/user_data.yaml")}"
  vars = {
    tmos_root_authorized_ssh_key = "${var.tmos_root_authorized_ssh_key}"
    tmos_root_password           = "${var.tmos_root_password}"
    tmos_admin_password          = "${var.tmos_admin_password}"
    do_url                       = "${var.do_url}"
    as3_url                      = "${var.as3_url}"
    waf_policy_url               = "${var.waf_policy_url}"
    license_host                 = "${var.license_host}"
    license_username             = "${var.license_username}"
    license_password             = "${var.license_password}"
    license_pool                 = "${var.license_pool}"
    hostname                     = "${local.hostname}"
    domain                       = "${local.domain}"
    dns_server                   = "${element(sort("${data.openstack_networking_subnet_v2.vip_subnet.dns_nameservers}"), 0)}"
    vip_selfip                   = "${element("${openstack_networking_port_v2.vip_port.all_fixed_ips}", 0)}"
    vip_mask                     = "${element(split("/", "${data.openstack_networking_subnet_v2.vip_subnet.cidr}"), 1)}"
    vip_gateway                  = "${data.openstack_networking_subnet_v2.vip_subnet.gateway_ip}"
    vip_mtu                      = "${data.openstack_networking_network_v2.vip_network.mtu}"
    phone_home_url               = "${var.phone_home_url}"
  }
}

resource "openstack_compute_instance_v2" "adcinstance" {
  name         = "${var.server_name}"
  image_id     = "${var.tmos_image}"
  flavor_id    = "${var.tmos_flavor}"
  key_pair     = "${var.tmos_root_authkey_name}"
  user_data    = "${data.template_file.user_data.rendered}"
  config_drive = true
  network {
    port = "${openstack_networking_port_v2.vip_port.id}"
  }
}

output "hostname" {
  value = "${local.hostname}"
}

output "tmos_management_web_private" {
  value = "https://${element("${openstack_networking_port_v2.vip_port.all_fixed_ips}", 0)}:8443"
}

output "tmos_ssh_private" {
  value = "ssh://root@${element("${openstack_networking_port_v2.vip_port.all_fixed_ips}", 0)}"
}

output "tmos_management_web_public" {
  value = "https://${openstack_networking_floatingip_v2.vip_floating_ip.address}:8443"
}

output "tmos_ssh_public" {
  value = "ssh://root@${openstack_networking_floatingip_v2.vip_floating_ip.address}"
}

output "waf_vip" {
  value = "http://${openstack_networking_floatingip_v2.vip_floating_ip.address}"
}

output "phone_home_url" {
  value = "${var.phone_home_url}"
}
