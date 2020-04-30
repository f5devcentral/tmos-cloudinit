# populate region from var name
data "ibm_is_region" "region" {
  name = var.region
}

# populate zone from var name
data "ibm_is_zone" "zone" {
  name   = var.zone
  region = data.ibm_is_region.region.name
}

# populate VPC from var name
data "ibm_is_vpc" "f5_vpc" {
  name = var.vpc_name
}

# populate resource group from var name
data "ibm_resource_group" "rg" {
  name = var.resource_group
}

# populate ssh key from var name
data "ibm_is_ssh_key" "f5_ssh_pub_key" {
  name = var.ssh_key_name
}

# populate compute profile from var name
data "ibm_is_instance_profile" "f5_ve_profile" {
  name = var.f5_ve_profile
}

# populate user_data template from vars
data "template_file" "user_data" {
  template = "${file("${path.module}/user_data.yaml")}"
  vars = {
    tmos_admin_password = var.tmos_admin_password
    license_basekey     = var.license_basekey
  }
}

# import custom image from public COS SQL URL
resource "ibm_is_image" "tmos_image" {
  name             = var.tmos_image_name
  href             = var.tmos_image_cos_url
  operating_system = "centos-7-amd64"
  timeouts {
    create = "30m"
    delete = "10m"
  }
}

# wait for image import to complete
data "ibm_is_image" "tmos_image" {
  name       = var.tmos_image_name
  depends_on = [ibm_is_image.tmos_image]
}

# create VPC Subnets and Security Groups
resource "ibm_is_subnet" "f5_management_subnet" {
  name                     = "f5-management"
  vpc                      = data.ibm_is_vpc.f5_vpc.id
  zone                     = data.ibm_is_zone.zone.name
  total_ipv4_address_count = "256"
}

# create F5 control plane firewalling
# https://support.f5.com/csp/article/K46122561
resource "ibm_is_security_group" "f5_management_sg" {
  name = "f5-management-sg"
  vpc  = data.ibm_is_vpc.f5_vpc.id
}

resource "ibm_is_security_group_rule" "f5_management_in_icmp" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "inbound"
  icmp {
    type = 8
  }
}

resource "ibm_is_security_group_rule" "f5_management_in_ssh" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "inbound"
  tcp {
    port_min = 22
    port_max = 22
  }
}
resource "ibm_is_security_group_rule" "f5_management_in_https" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "inbound"
  tcp {
    port_min = 443
    port_max = 443
  }
}
resource "ibm_is_security_group_rule" "f5_management_in_snmp_tcp" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "inbound"
  tcp {
    port_min = 161
    port_max = 161
  }
}
resource "ibm_is_security_group_rule" "f5_management_in_snmp_udp" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "inbound"
  udp {
    port_min = 161
    port_max = 161
  }
}
resource "ibm_is_security_group_rule" "f5_management_in_ha" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "inbound"
  udp {
    port_min = 1026
    port_max = 1026
  }
}

resource "ibm_is_security_group_rule" "f5_management_in_iquery" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "inbound"
  tcp {
    port_min = 4353
    port_max = 4353
  }
}

// allow all outbound on control plane
// all TCP
resource "ibm_is_security_group_rule" "f5_management_out_tcp" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "outbound"
  tcp {
    port_min = 1
    port_max = 65535
  }
}

// all outbound UDP
resource "ibm_is_security_group_rule" "f5_management_out_udp" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "outbound"
  udp {
    port_min = 1
    port_max = 65535
  }
}

// all ICMP
resource "ibm_is_security_group_rule" "f5_management_out_icmp" {
  group     = ibm_is_security_group.f5_management_sg.id
  direction = "outbound"
  icmp {
    type = 0
  }
}

// allow all traffic to data plane interfaces
// TMM is the firewall
resource "ibm_is_security_group" "f5_tmm_sg" {
  name = "f5-tmm-sg"
  vpc  = data.ibm_is_vpc.f5_vpc.id
}

// all TCP
resource "ibm_is_security_group_rule" "f5_tmm_in_tcp" {
  group     = ibm_is_security_group.f5_tmm_sg.id
  direction = "inbound"
  tcp {
    port_min = 1
    port_max = 65535
  }
}

resource "ibm_is_security_group_rule" "f5_tmm_out_tcp" {
  group     = ibm_is_security_group.f5_tmm_sg.id
  direction = "outbound"
  tcp {
    port_min = 1
    port_max = 65535
  }
}

// all UDP
resource "ibm_is_security_group_rule" "f5_tmm_in_udp" {
  group     = ibm_is_security_group.f5_tmm_sg.id
  direction = "inbound"
  udp {
    port_min = 1
    port_max = 65535
  }
}

resource "ibm_is_security_group_rule" "f5_tmm_out_udp" {
  group     = ibm_is_security_group.f5_tmm_sg.id
  direction = "outbound"
  udp {
    port_min = 1
    port_max = 65535
  }
}

// all ICMP
resource "ibm_is_security_group_rule" "f5_tmm_in_icmp" {
  group     = ibm_is_security_group.f5_tmm_sg.id
  direction = "inbound"
  icmp {
    type = 8
  }
}

resource "ibm_is_security_group_rule" "f5_tmm_out_icmp" {
  group     = ibm_is_security_group.f5_tmm_sg.id
  direction = "outbound"
  icmp {
    type = 0
  }
}

// data plane subnets
resource "ibm_is_subnet" "f5_cluster_subnet" {
  name                     = "f5-cluster"
  vpc                      = data.ibm_is_vpc.f5_vpc.id
  zone                     = data.ibm_is_zone.zone.name
  total_ipv4_address_count = "256"
  depends_on               = [ibm_is_subnet.f5_management_subnet]
}
resource "ibm_is_subnet" "f5_internal_subnet" {
  name                     = "f5-internal"
  vpc                      = data.ibm_is_vpc.f5_vpc.id
  zone                     = data.ibm_is_zone.zone.name
  total_ipv4_address_count = "256"
  depends_on               = [ibm_is_subnet.f5_cluster_subnet]
}
resource "ibm_is_subnet" "f5_external_subnet" {
  name                     = "f5-external"
  vpc                      = data.ibm_is_vpc.f5_vpc.id
  zone                     = data.ibm_is_zone.zone.name
  total_ipv4_address_count = "256"
  depends_on               = [ibm_is_subnet.f5_internal_subnet]
}

# create instance
resource "ibm_is_instance" "f5_ve_instance" {
  name    = var.instance_name
  image   = data.ibm_is_image.tmos_image.id
  profile = var.f5_ve_profile
  primary_network_interface {
    name            = "management"
    subnet          = ibm_is_subnet.f5_management_subnet.id
    security_groups = [ibm_is_security_group.f5_management_sg.id]
  }
  network_interfaces {
    name            = "tmm-1-1-cluster"
    subnet          = ibm_is_subnet.f5_cluster_subnet.id
    security_groups = [ibm_is_security_group.f5_tmm_sg.id]
  }
  network_interfaces {
    name            = "tmm-1-2-internal"
    subnet          = ibm_is_subnet.f5_internal_subnet.id
    security_groups = [ibm_is_security_group.f5_tmm_sg.id]
  }
  network_interfaces {
    name            = "tmm-1-3-external"
    subnet          = ibm_is_subnet.f5_external_subnet.id
    security_groups = [ibm_is_security_group.f5_tmm_sg.id]
  }
  vpc       = data.ibm_is_vpc.f5_vpc.id
  zone      = data.ibm_is_zone.zone.name
  keys      = [data.ibm_is_ssh_key.f5_ssh_pub_key.id]
  user_data = data.template_file.user_data.rendered
}

# create floating IPs
resource "ibm_is_floating_ip" "f5_management_floating_ip" {
  name   = "management-floating-ip"
  target = ibm_is_instance.f5_ve_instance.primary_network_interface.0.id
}

resource "ibm_is_floating_ip" "f5_external_floating_ip" {
  name   = "external-floating-ip"
  target = ibm_is_instance.f5_ve_instance.network_interfaces.2.id
}

