# lookup SSH public keys by name
data "ibm_is_ssh_key" "ssh_pub_key" {
  name = "${var.ssh_key_name}"
}

# lookup compute profile by name
data "ibm_is_instance_profile" "instance_profile" {
  name = "${var.instance_profile}"
}

# create a random password if we need it
resource "random_password" "password" {
  length           = 16
  special          = true
  override_special = "_%@"
}

# lookup image name for a custom image in region if we need it
data "ibm_is_image" "tmos_custom_image" {
  name = "${var.tmos_image_name}"
}

locals {
  # use the public image if the name is found
  public_image_map = {
    bigip-14-1-2-6-0-0-2-all-1slot = {
      "us-south" = "r006-f0a8cba9-1e9e-4771-87ba-20b7fd33b16a"
      "us-east"  = "r014-eccb5c62-82d9-438c-b81e-716f3506700f"
      "eu-gb"    = "r018-72ee97b8-ffeb-4427-bd2a-fc60e4d2b6b5"
      "eu-de"    = "r010-cf56a548-d5ca-4833-b0a6-bde256140d93"
      "jp-tok"   = "r022-44656c7d-427c-4e06-9253-3224cd1df827"
    }
    bigip-14-1-2-6-0-0-2-ltm-1slot = {
      "us-south" = "r006-1ca34358-b1f0-44b1-bf9a-a8bd9837a672"
      "us-east"  = "r014-3c86e0bf-1026-4400-91f6-b4256d972ed5"
      "eu-gb"    = "r018-e717281f-5bd7-4e08-8d54-7b45ddfb12c7"
      "eu-de"    = "r010-e8022107-fea9-471b-ba6c-8b8f8e130ab9"
      "jp-tok"   = "r022-c7377896-c997-495a-88f7-033f827d6d8b"
    }
    bigip-15-1-0-4-0-0-6-all-1slot = {
      "us-south" = "r006-654bca9e-8e4d-46c2-980b-c52fdd2237f4"
      "us-east"  = "r014-d73926e1-3b82-413f-aecc-36710b59cf4b"
      "eu-gb"    = "r018-e02a17f1-90bc-494b-ab66-4f3e03c08b7d"
      "eu-de"    = "r010-3a06e044-56e8-4d45-a5c2-535a7b673a94"
      "jp-tok"   = "r022-a65002eb-ad05-4d56-bcb8-2d3fa14f9834"
    }
    bigip-15-1-0-4-0-0-6-ltm-1slot = {
      "us-south" = "r006-c176a319-39e3-4f24-82a1-6dd4f2fa58dc"
      "us-east"  = "r014-e2a4cc82-d935-4f3f-9042-21f64d18232c"
      "eu-gb"    = "r018-859e47fb-40db-4d72-9da7-2de4fc78d64c"
      "eu-de"    = "r010-cd996cda-53ce-4783-9e3a-03a18b9162ff"
      "jp-tok"   = "r022-36b57097-deba-49c2-bffb-f37c61c8e713"
    }
  }
}

locals {
  # set the user_data YAML template for each license type
  license_map = {
    "none"        = "${file("${path.module}/user_data_no_license.yaml")}"
    "byol"        = "${file("${path.module}/user_data_byol_license.yaml")}"
    "regkeypool"  = "${file("${path.module}/user_data_regkey_pool_license.yaml")}"
    "utilitypool" = "${file("${path.module}/user_data_utility_pool_license.yaml")}"
  }
}

locals {
  # custom image takes priority over public image
  image_id = data.ibm_is_image.tmos_custom_image.id == null ? lookup(local.public_image_map[var.tmos_image_name], var.region) : data.ibm_is_image.tmos_custom_image.id
  # public image takes priority over custom image
  # image_id = lookup(lookup(local.public_image_map, var.tmos_image_name, {}), var.region, data.ibm_is_image.tmos_custom_image.id)
  template_file = lookup(local.license_map, var.license_type, local.license_map["none"])
  # user admin_password if supplied, else set a random password
  admin_password = var.tmos_admin_password == "" ? random_password.password.result : var.tmos_admin_password
  # set user_data YAML values or else set them to null for templating
  phone_home_url          = var.phone_home_url == "" ? "null" : var.phone_home_url
  byol_license_basekey    = var.byol_license_basekey == "none" ? "null" : var.byol_license_basekey
  license_host            = var.license_host == "none" ? "null" : var.license_host
  license_username        = var.license_username == "none" ? "null" : var.license_username
  license_password        = var.license_password == "none" ? "null" : var.license_password
  license_pool            = var.license_pool == "none" ? "null" : var.license_pool
  license_sku_keyword_1   = var.license_sku_keyword_1 == "none" ? "null" : var.license_sku_keyword_1
  license_sku_keyword_2   = var.license_sku_keyword_2 == "none" ? "null" : var.license_sku_keyword_2
  license_unit_of_measure = var.license_unit_of_measure == "none" ? "null" : var.license_unit_of_measure
}

data "template_file" "user_data" {
  template = local.template_file
  vars = {
    tmos_admin_password     = local.admin_password
    tmos_license_basekey    = local.byol_license_basekey
    license_host            = local.license_host
    license_username        = local.license_username
    license_password        = local.license_password
    license_pool            = local.license_pool
    license_sku_keyword_1   = local.license_sku_keyword_1
    license_sku_keyword_2   = local.license_sku_keyword_2
    license_unit_of_measure = local.license_unit_of_measure
    phone_home_url          = local.phone_home_url
    template_source         = var.template_source
    template_version        = var.template_version
    zone                    = data.ibm_is_subnet.f5_managment_subnet.zone
    vpc                     = data.ibm_is_subnet.f5_managment_subnet.vpc
    app_id                  = var.app_id
  }
}

# create compute instance
resource "ibm_is_instance" "f5_ve_instance" {
  name    = var.instance_name
  image   = local.image_id
  profile = data.ibm_is_instance_profile.instance_profile.id
  primary_network_interface {
    name            = "management"
    subnet          = data.ibm_is_subnet.f5_managment_subnet.id
    security_groups = [ibm_is_security_group.f5_open_sg.id]
  }
  dynamic "network_interfaces" {
    for_each = local.secondary_subnets
    content {
      name            = format("data-1-%d", (network_interfaces.key + 1))
      subnet          = network_interfaces.value
      security_groups = [ibm_is_security_group.f5_open_sg.id]
    }

  }
  vpc        = data.ibm_is_subnet.f5_managment_subnet.vpc
  zone       = data.ibm_is_subnet.f5_managment_subnet.zone
  keys       = [data.ibm_is_ssh_key.ssh_pub_key.id]
  user_data  = data.template_file.user_data.rendered
  depends_on = [ibm_is_security_group_rule.f5_allow_outbound]
  timeouts {
    create = "60m"
    delete = "120m"
  }
}

# create floating IP for management access
resource "ibm_is_floating_ip" "f5_management_floating_ip" {
  name   = "f0-${random_uuid.namer.result}"
  target = ibm_is_instance.f5_ve_instance.primary_network_interface.0.id
  timeouts {
    create = "60m"
    delete = "60m"
  }
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

output "image_id" {
  value = local.image_id
}

output "instance_id" {
  value = ibm_is_instance.f5_ve_instance.id
}

output "profile_id" {
  value = data.ibm_is_instance_profile.instance_profile.id
}

output "f5_shell_access" {
  value = "ssh://root@${ibm_is_floating_ip.f5_management_floating_ip.address}"
}

output "f5_phone_home_url" {
  value = var.phone_home_url
}
