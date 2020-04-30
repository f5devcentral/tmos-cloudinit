variable "region" {
  default     = "eu-de"
  description = "The VPC Region that you want your VPC, networks and the F5 virtual server to be provisioned in. To list available regions, run `ibmcloud is regions`."
}

variable "zone" {
  default     = "eu-de-3"
  description = "The VPC Zone that you want your VPC networks and virtual servers to be provisioned in. To list available zones, run `ibmcloud is zones`."
}

variable "vpc_name" {
  default     = "vpc-frankfurt-3"
  description = "The name of your VPC where F5-BIGIP instance is to be provisioned."
}

variable "resource_group" {
  default     = "default"
  description = "The resource group to use. If unspecified, the account's default resource group is used."
}

variable "tmos_image_name" {
  default     = "bigip-14-1-2-0-0-37-ltm-1slot-us-south"
  description = "TMOS Image name provided by F5"
}

variable "tmos_image_cos_url" {
  default     = "cos://eu-de/bigip-14.1.2-0.0.37.ltm-1slot-eu-de/BIGIP-14.1.2-0.0.37.LTM_1SLOT.qcow2"
  description = "TMOS Image COS SQL URL provided by F5"
}

variable "ssh_key_name" {
  default     = "jgruber"
  description = "The name of the public SSH key to be used when provisining F5-BIGIP VSI."
}

variable "tmos_admin_password" {
  default = "f5C0nfig"
  description = "The password to set for web UI and API access"
}

variable "instance_name" {
  default     = "f5-ve-01"
  description = "The name of your F5-BIGIP Virtual Edition to be provisioned."
}

variable "f5_ve_profile" {
  default     = "cx2-2x4"
  description = "The profile of compute CPU and memory resources to be used when provisioning F5 Virtual Edition. To list available profiles, run `ibmcloud is instance-profiles`."
}

variable "license_basekey" {
  default     = "UUKHD-HPYFM-LSPLZ-SIJRZ-DIEFRUQ"
  description = "The F5 license basekey to apply to the F5 Virtual Edition."
}
