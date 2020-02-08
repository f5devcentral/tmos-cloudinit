resource "openstack_networking_port_v2" "management_port_primary" {
  name           = "${var.server_name}_management_port_primary"
  network_id     = "${var.management_network}"
  admin_state_up = "true"
  security_group_ids = [
    "${var.management_network_security_group}"
  ]
  allowed_address_pairs {
    ip_address = "0.0.0.0/0"
  }
  allowed_address_pairs {
    ip_address = "::/0"
  }
}

resource "openstack_networking_floatingip_v2" "management_floating_ip_primary" {
  port_id = "${openstack_networking_port_v2.management_port_primary.id}"
  pool    = "${var.external_network_name}"
}

resource "openstack_networking_port_v2" "vip_port_primary" {
  name           = "${var.server_name}_vip_port_primary"
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

resource "openstack_networking_port_v2" "management_port_secondary" {
  name           = "${var.server_name}_management_port_secondary"
  network_id     = "${var.management_network}"
  admin_state_up = "true"
  security_group_ids = [
    "${var.management_network_security_group}"
  ]
  allowed_address_pairs {
    ip_address = "0.0.0.0/0"
  }
  allowed_address_pairs {
    ip_address = "::/0"
  }
}

resource "openstack_networking_floatingip_v2" "management_floating_ip_secondary" {
  port_id = "${openstack_networking_port_v2.management_port_secondary.id}"
  pool    = "${var.external_network_name}"
}

resource "openstack_networking_port_v2" "vip_port_secondary" {
  name           = "${var.server_name}_vip_port_secondary"
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
  fixed_ip {
    subnet_id = "${var.vip_subnet}"
  }
}

resource "openstack_networking_floatingip_v2" "vip_floating_ip_secondary" {
  port_id  = "${openstack_networking_port_v2.vip_port_secondary.id}"
  fixed_ip = "${element("${openstack_networking_port_v2.vip_port_secondary.all_fixed_ips}", 0)}"
  pool     = "${var.external_network_name}"
}

locals {
  dns_assignment     = "${element("${openstack_networking_port_v2.management_port_primary.dns_assignment}", 0)}"
  port_fqdn          = "${replace("${local.dns_assignment.fqdn}", "/\\.$/", "")}"
  port_name          = "${replace("${local.dns_assignment.hostname}", "/^\\.|\\.$/", "")}"
  domain             = "${replace("${local.port_fqdn}", "${local.port_name}.", "")}"
  hostname_primary   = "${var.server_name}-primary.${local.domain}"
  hostname_secondary = "${var.server_name}-secondary.${local.domain}"
}

data "template_file" "user_data_primary" {
  template = "${file("${path.module}/user_data_primary.yaml")}"
  vars = {
    tmos_root_password   = "${var.tmos_root_password}"
    tmos_admin_password  = "${var.tmos_admin_password}"
    do_url               = "${var.do_url}"
    as3_url              = "${var.as3_url}"
    license_host         = "${var.license_host}"
    license_username     = "${var.license_username}"
    license_password     = "${var.license_password}"
    license_pool         = "${var.license_pool}"
    hostname_primary     = "${local.hostname_primary}"
    hostname_secondary   = "${local.hostname_secondary}"
    secondary_cluster_ip = "${element("${openstack_networking_port_v2.vip_port_secondary.all_fixed_ips}", 1)}"
    waf_vip              = "${element("${openstack_networking_port_v2.vip_port_secondary.all_fixed_ips}", 0)}"
    waf_policy_url       = "${var.waf_policy_url}"
    phone_home_url       = "${var.phone_home_url}"
  }
}

data "template_file" "user_data_secondary" {
  template = "${file("${path.module}/user_data_secondary.yaml")}"
  vars = {
    tmos_root_password   = "${var.tmos_root_password}"
    tmos_admin_password  = "${var.tmos_admin_password}"
    do_url               = "${var.do_url}"
    as3_url              = "${var.as3_url}"
    license_host         = "${var.license_host}"
    license_username     = "${var.license_username}"
    license_password     = "${var.license_password}"
    license_pool         = "${var.license_pool}"
    hostname_primary     = "${local.hostname_primary}"
    hostname_secondary   = "${local.hostname_secondary}"
    secondary_cluster_ip = "${element("${openstack_networking_port_v2.vip_port_secondary.all_fixed_ips}", 1)}"
    waf_vip              = "${element("${openstack_networking_port_v2.vip_port_secondary.all_fixed_ips}", 0)}"
    waf_policy_url       = "${var.waf_policy_url}"
    phone_home_url       = "${var.phone_home_url}"
  }
}

resource "openstack_compute_instance_v2" "adcinstance_primary" {
  name         = "${var.server_name}-primary"
  image_id     = "${var.tmos_image}"
  flavor_id    = "${var.tmos_flavor}"
  key_pair     = "${var.tmos_root_authkey_name}"
  user_data    = "${data.template_file.user_data_primary.rendered}"
  config_drive = true
  network {
    port = "${openstack_networking_port_v2.management_port_primary.id}"
  }
  network {
    port = "${openstack_networking_port_v2.vip_port_primary.id}"
  }
}

resource "openstack_compute_instance_v2" "adcinstance_secondary" {
  name         = "${var.server_name}-secondary"
  image_id     = "${var.tmos_image}"
  flavor_id    = "${var.tmos_flavor}"
  key_pair     = "${var.tmos_root_authkey_name}"
  user_data    = "${data.template_file.user_data_secondary.rendered}"
  config_drive = true
  network {
    port = "${openstack_networking_port_v2.management_port_secondary.id}"
  }
  network {
    port = "${openstack_networking_port_v2.vip_port_secondary.id}"
  }
}

output "tmos_management_web_private_primary" {
  value = "https://${element("${openstack_networking_port_v2.management_port_primary.all_fixed_ips}", 0)}"
}

output "tmos_ssh_private_primary" {
  value = "ssh://root@${element("${openstack_networking_port_v2.management_port_primary.all_fixed_ips}", 0)}"
}

output "tmos_management_web_public_primary" {
  value = "https://${openstack_networking_floatingip_v2.management_floating_ip_primary.address}"
}

output "tmos_ssh_public_primary" {
  value = "ssh://root@${openstack_networking_floatingip_v2.management_floating_ip_primary.address}"
}

output "tmos_management_web_private_secondary" {
  value = "https://${element("${openstack_networking_port_v2.management_port_secondary.all_fixed_ips}", 0)}"
}

output "tmos_ssh_private_secondary" {
  value = "ssh://root@${element("${openstack_networking_port_v2.management_port_secondary.all_fixed_ips}", 0)}"
}

output "tmos_management_web_public_secondary" {
  value = "https://${openstack_networking_floatingip_v2.management_floating_ip_secondary.address}"
}

output "tmos_ssh_public_secondary" {
  value = "ssh://root@${openstack_networking_floatingip_v2.management_floating_ip_secondary.address}"
}

output "waf_vip" {
  value = "http://${openstack_networking_floatingip_v2.vip_floating_ip_secondary.address}"
}

output "phone_home_url" {
  value = "${var.phone_home_url}"
}
