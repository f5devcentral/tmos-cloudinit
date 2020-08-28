data "ibm_is_image" "tmos_image" {
   name = "${var.tmos_image_name}"
}

data "ibm_is_ssh_key" "ssh_pub_key" {
  name = "${var.ssh_key_name}"
}

data "ibm_is_instance_profile" "instance_profile" {
  name = "${var.instance_profile}"
}

resource "random_password" "password" {
  length = 16
  special = true
  override_special = "_%@"
}

locals {
   template = lookup({"none"="${file("${path.module}/user_data_no_license.yaml")}",
                      "byol"="${file("${path.module}/user_data_byol_license.yaml")}", 
                      "regkeypool"="${file("${path.module}/user_data_regkey_pool_license.yaml")}",
                      "utilitypool"="${file("${path.module}/user_data_utility_pool_license.yaml")}"}, 
                     var.license_type,
                     "${file("${path.module}/user_data_no_license.yaml")}")
   admin_password = var.tmos_admin_password == "" ? random_password.password.result : var.tmos_admin_password
   phone_home_url = var.phone_home_url == "" ? "null" : var.phone_home_url
   byol_license_basekey = var.byol_license_basekey == "none" ? "null" : var.byol_license_basekey
   license_host = var.license_host == "none" ? "null" : var.license_host
   license_username = var.license_username == "none" ? "null" : var.license_username
   license_password = var.license_password == "none" ? "null" : var.license_password
   license_pool = var.license_pool == "none" ? "null" : var.license_pool
   license_sku_keyword_1 = var.license_sku_keyword_1 == "none" ? "null": var.license_sku_keyword_1
   license_sku_keyword_2 = var.license_sku_keyword_2 == "none" ? "null": var.license_sku_keyword_2
   license_unit_of_measure = var.license_unit_of_measure == "none" ? "null": var.license_unit_of_measure
}

data "template_file" "user_data" {
  template = local.template
  vars = {
    tmos_admin_password = local.admin_password
    tmos_license_basekey = local.byol_license_basekey
    license_host = local.license_host
    license_username = local.license_username
    license_password = local.license_password
    license_pool = local.license_pool
    license_sku_keyword_1 = local.license_sku_keyword_1
    license_sku_keyword_2 = local.license_sku_keyword_2
    license_unit_of_measure = local.license_unit_of_measure
    phone_home_url = local.phone_home_url
    template_source = var.template_source
    template_version = var.template_version
    zone = data.ibm_is_subnet.f5_managment_subnet.zone
    vpc = data.ibm_is_subnet.f5_managment_subnet.vpc
    app_id = var.app_id
  }
}

resource "ibm_is_instance" "f5_ve_instance" {
  name    = var.instance_name
  image   = data.ibm_is_image.tmos_image.id
  profile = data.ibm_is_instance_profile.instance_profile.id
  primary_network_interface {
    name            = "management"
    subnet          = data.ibm_is_subnet.f5_managment_subnet.id
    security_groups = [ibm_is_security_group.f5_open_sg.id]
  }
  dynamic "network_interfaces" {
      for_each = local.secondary_subnets
      content {
          name = format("data-1-%d", (network_interfaces.key+1))
          subnet = network_interfaces.value
          security_groups = [ibm_is_security_group.f5_open_sg.id]
      }

  }
  vpc  = data.ibm_is_subnet.f5_managment_subnet.vpc
  zone = data.ibm_is_subnet.f5_managment_subnet.zone
  keys = [data.ibm_is_ssh_key.ssh_pub_key.id]
  user_data = data.template_file.user_data.rendered
  depends_on = [ibm_is_security_group_rule.f5_allow_outbound]
}

# create floating IPs
resource "ibm_is_floating_ip" "f5_management_floating_ip" {
  name   = "f0-${random_uuid.namer.result}"
  target = ibm_is_instance.f5_ve_instance.primary_network_interface.0.id
}

# create 1:1 floating IPs to vNICs - Not supported by IBM yet
#resource "ibm_is_floating_ip" "f5_data_floating_ips" {
#  count = length(local.secondary_subnets)
#  name   = format("f%d-%s", (count.index+1), random_uuid.namer.result)
#  target = ibm_is_instance.f5_ve_instance.network_interfaces[count.index].id
#}

output "resource_name" {
  value = ibm_is_instance.f5_ve_instance.name
}

output "resource_status" {
  value = ibm_is_instance.f5_ve_instance.status
}

output "VPC" {
  value = ibm_is_instance.f5_ve_instance.vpc
}

output "f5_shell_access" {
  value = "ssh://root@${ibm_is_floating_ip.f5_management_floating_ip.address}"
}

output "f5_phone_home_url" {
    value = var.phone_home_url
}