##################################################################################
# region - The VPC region to instatiate the F5 BIG-IP instance
##################################################################################
variable "region" {
  type        = string
  default     = "us-south"
  description = "The VPC region to instatiate the F5 BIG-IP instance"
}
# Present for CLI testng
#variable "api_key" {
#  type        = string
#  default     = ""
#  description = "IBM Public Cloud API KEY"
#}

##################################################################################
# instance_name - The name of the F5 BIG-IP instance
##################################################################################
variable "instance_name" {
  type        = string
  default     = "f5-ve-01"
  description = "The VPC Instance name"
}

##################################################################################
# tmos_image_name - The name of VPC image to use for the F5 BIG-IP instnace
##################################################################################
variable "tmos_image_name" {
  type        = string
  default     = "bigip-15-1-0-4-0-0-6-ltm-1slot"
  description = "The image to be used when provisioning the F5 BIG-IP instance"
}

##################################################################################
# instance_profile - The name of the VPC profile to use for the F5 BIG-IP instnace
##################################################################################
variable "instance_profile" {
  type        = string
  default     = "cx2-2x4"
  description = "The resource profile to be used when provisioning the F5 BIG-IP instance"
}

##################################################################################
# ssh_key_name - The name of the public SSH key to be used when provisining F5 BIG-IP
##################################################################################
variable "ssh_key_name" {
  type        = string
  default     = ""
  description = "The name of the public SSH key (VPC Gen 2 SSH Key) to be used when provisioning the F5 BIG-IP instance"
}

##################################################################################
# tmos_license_basekey - The F5 BIG-IP license basekey to activate against activate.f5.com
##################################################################################
variable "license_type" {
  type        = string
  default     = "none"
  description = "How to license, may be 'none','byol','regkeypool','utilitypool'"
}
variable "byol_license_basekey" {
  type        = string
  default     = "none"
  description = "Bring your own license registration key for the F5 BIG-IP instance"
}
variable "license_host" {
  type        = string
  default     = "none"
  description = "BIGIQ IP or hostname to use for pool based licensing of the F5 BIG-IP instance"
}
variable "license_username" {
  type        = string
  default     = "none"
  description = "BIGIQ username to use for the pool based licensing of the F5 BIG-IP instance"
}
variable "license_password" {
  type        = string
  default     = "none"
  description = "BIGIQ password to use for the pool based licensing of the F5 BIG-IP instance"
}
variable "license_pool" {
  type        = string
  default     = "none"
  description = "BIGIQ license pool name of the pool based licensing of the F5 BIG-IP instance"
}
variable "license_sku_keyword_1" {
  type        = string
  default     = "none"
  description = "BIGIQ primary SKU for ELA utility licensing of the F5 BIG-IP instance"
}
variable "license_sku_keyword_2" {
  type        = string
  default     = "none"
  description = "BIGIQ secondary SKU for ELA utility licensing of the F5 BIG-IP instance"
}
variable "license_unit_of_measure" {
  type        = string
  default     = "hourly"
  description = "BIGIQ utility pool unit of measurement"
}


##################################################################################
# tmos_admin_password - The password for the built-in admin F5 BIG-IP user
##################################################################################
variable "tmos_admin_password" {
  type        = string
  default     = ""
  description = "admin account password for the F5 BIG-IP instance"
}

##################################################################################
# management_subnet_id - The VPC subnet ID for the F5 BIG-IP management interface
##################################################################################
variable "management_subnet_id" {
  type        = string
  default     = null
  description = "Required VPC Gen2 subnet ID for the F5 BIG-IP management network"
}

##################################################################################
# data_1_1_subnet_id - The VPC subnet ID for the F5 BIG-IP 1.1 data interface
##################################################################################
variable "data_1_1_subnet_id" {
  type        = string
  default     = ""
  description = "Optional VPC Gen2 subnet ID for the F5 BIG-IP 1.1 data network"
}

##################################################################################
# data_1_2_subnet_id - The VPC subnet ID for the F5 BIG-IP 1.2 data interface
##################################################################################
variable "data_1_2_subnet_id" {
  type        = string
  default     = ""
  description = "Optional VPC Gen2 subnet ID for the F5 BIG-IP 1.2 data network"
}

##################################################################################
# data_1_3_subnet_id - The VPC subnet ID for the F5 BIG-IP 1.3 data interface
##################################################################################
variable "data_1_3_subnet_id" {
  type        = string
  default     = ""
  description = "Optional VPC Gen2 subnet ID for the F5 BIG-IP 1.3 data network"
}

##################################################################################
# data_1_4_subnet_id - The VPC subnet ID for the F5 BIG-IP 1.4 data interface
##################################################################################
variable "data_1_4_subnet_id" {
  type        = string
  default     = ""
  description = "Optional VPC Gen2 subnet ID for the F5 BIG-IP 1.4 data network"
}

##################################################################################
# phone_home_url - The web hook URL to POST status to when F5 BIG-IP onboarding completes
##################################################################################
variable "phone_home_url" {
  type        = string
  default     = ""
  description = "The URL to POST status when BIG-IP is finished onboarding"
}

##################################################################################
# schematic template for phone_home_url_metadata
##################################################################################
variable "template_source" {
  default     = "f5devcentral/tmos-cloudinit/demo/ibmcloud_vpc_gen2/schematics/tmos_multi_nic"
  description = "The terraform template source for phone_home_url_metadata"
}
variable "template_version" {
  default     = "20200825"
  description = "The terraform template version for phone_home_url_metadata"
}
variable "app_id" {
  default     = "undefined"
  description = "The terraform application id for phone_home_url_metadata"
}
