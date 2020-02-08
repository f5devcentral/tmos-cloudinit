variable "tmos_image" {
  default = "8cc8f40c-e8e1-414a-885d-555875748d10"
}

variable "tmos_flavor" {
  default = "6e03a841-e852-480d-a616-8b6578c64443"
}

variable "tmos_root_authkey_name" {
  default = "johntgruber"
}

variable "tmos_root_authorized_ssh_key" {
  default = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC9OJ+5GlA0AkOi7FNtRxabTvMGP20rAVnJSaV64GKqiu6EOhGm/wUyFrZ2vJxMwTp3KOeRqm7EmPTxIwh0zTlRoJhC+zqa+P6IAmLUq8oW99hzZ1nd3eAQ4nwPlfTDLbYTPOTB2ymc7hd5XRwXvnrl5P7KCI2RlItKDwufLYjO3gvWHNjqQIxPq8MwL7VYRcddfOqwJYbGPL+um9Kzhz4A/mgo++G65QnEsdcy6MV0Wp+l3rf9Z9TvrslMii45OTFkLtPzmqR0FSqTdC3kfP4jrepad2VLeeCml8KFYf6AYY8V5hhzFlI/SFdt0kaIpeULFEsMXKVYwcv6H2ZHS8Mp john.t.gruber@gmail.com"
}

variable "tmos_root_password" {
  default = "f5c0nfig"
}

variable "tmos_admin_password" {
  default = "f5c0nfig"
}

variable "license_host" {
  default = "172.13.1.108"
}

variable "license_username" {
  default = "admin"
}

variable "license_password" {
  default = "admin"
}

variable "license_pool" {
  default = "BIGIPVEREGKEYS"
}

variable "do_url" {
  default = "https://github.com/F5Networks/f5-declarative-onboarding/releases/download/v1.10.0/f5-declarative-onboarding-1.10.0-2.noarch.rpm"
}

variable "as3_url" {
  default = "https://github.com/F5Networks/f5-appsvcs-extension/releases/download/v3.17.0/f5-appsvcs-3.17.0-3.noarch.rpm"
}

variable "phone_home_url" {
  default = "https://webhook.site/8d37382d-c793-46ba-8103-d8576baaae4e"
}

variable "external_network" {
  default = "ec61b30a-1922-45cb-b71f-ddb77e28b353"
}

variable "external_network_name" {
  default = "public"
}

variable "management_network" {
  default = "4de5a047-e16f-4cd4-a34b-a9b42f3fd02e"
}

variable "management_network_security_group" {
  default = "3fbdd3a4-8223-4817-b05c-92dcd2f91f81"
}

variable "cluster_network" {
  default = "5356ac62-5fc8-4481-a098-8af85442f62f"
}

variable "cluster_network_security_group" {
  default = "3fbdd3a4-8223-4817-b05c-92dcd2f91f81"
}

variable "internal_network" {
  default = "ac1b436d-0931-48da-95f1-5e3ee889cb87"
}

variable "internal_network_security_group" {
  default = "3fbdd3a4-8223-4817-b05c-92dcd2f91f81"
}

variable "vip_network" {
  default = "a3d921f5-4860-4954-a492-ad85f7a0020c"
}

variable "vip_network_security_group" {
  default = "3fbdd3a4-8223-4817-b05c-92dcd2f91f81"
}

variable "vip_subnet" {
  default = "34427dd9-9d39-4c4d-9530-ff253fe20640"
}

variable "server_name" {
  default = "adc4nic"
}