resource "openstack_networking_port_v2" "management_port" {
  name           = "${var.server_name}_management_port"
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

resource "openstack_networking_floatingip_v2" "management_floating_ip" {
  port_id = "${openstack_networking_port_v2.management_port.id}"
  pool    = "${var.external_network_name}"
}

resource "openstack_networking_port_v2" "cluster_port" {
  name           = "${var.server_name}_cluster_port"
  network_id     = "${var.cluster_network}"
  admin_state_up = "true"
  security_group_ids = [
    "${var.cluster_network_security_group}"
  ]
  allowed_address_pairs {
    ip_address = "0.0.0.0/0"
  }
  allowed_address_pairs {
    ip_address = "::/0"
  }
}

resource "openstack_networking_port_v2" "internal_port" {
  name           = "${var.server_name}_internal_port"
  network_id     = "${var.internal_network}"
  admin_state_up = "true"
  security_group_ids = [
    "${var.internal_network_security_group}"
  ]
  allowed_address_pairs {
    ip_address = "0.0.0.0/0"
  }
  allowed_address_pairs {
    ip_address = "::/0"
  }
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
  fixed_ip {
    subnet_id = "${var.vip_subnet}"
  }
}

resource "openstack_networking_floatingip_v2" "vip_floating_ip" {
  port_id  = "${openstack_networking_port_v2.vip_port.id}"
  fixed_ip = "${element("${openstack_networking_port_v2.vip_port.all_fixed_ips}", 0)}"
  pool     = "${var.external_network_name}"
}

data "template_file" "user_data" {
  template = "${file("${path.module}/user_data.yaml")}"
  vars = {
    tmos_root_password  = "${var.tmos_root_password}"
    tmos_admin_password = "${var.tmos_admin_password}"
    do_url              = "${var.do_url}"
    as3_url             = "${var.as3_url}"
    license_host        = "${var.license_host}"
    license_username    = "${var.license_username}"
    license_password    = "${var.license_password}"
    license_pool        = "${var.license_pool}"
    waf_vip             = "${element("${openstack_networking_port_v2.vip_port.all_fixed_ips}", 0)}"
    waf_policy_url      = "${var.waf_policy_url}"
    pool_member         = "${var.pool_member}"
    pool_member_port    = "${var.pool_member_port}"
    phone_home_url      = "${var.phone_home_url}"
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
    port = "${openstack_networking_port_v2.management_port.id}"
  }
  network {
    port = "${openstack_networking_port_v2.cluster_port.id}"
  }
  network {
    port = "${openstack_networking_port_v2.internal_port.id}"
  }
  network {
    port = "${openstack_networking_port_v2.vip_port.id}"
  }
}


output "tmos_management_web_private" {
  value = "https://${element("${openstack_networking_port_v2.management_port.all_fixed_ips}", 0)}"
}

output "tmos_ssh_private" {
  value = "ssh://root@${element("${openstack_networking_port_v2.management_port.all_fixed_ips}", 0)}"
}

output "tmos_management_web_public" {
  value = "https://${openstack_networking_floatingip_v2.management_floating_ip.address}"
}

output "tmos_ssh_public" {
  value = "ssh://root@${openstack_networking_floatingip_v2.management_floating_ip.address}"
}

output "waf_vip" {
  value = "http://${openstack_networking_floatingip_v2.vip_floating_ip.address}"
}

output "phone_home_url" {
  value = "${var.phone_home_url}"
}
