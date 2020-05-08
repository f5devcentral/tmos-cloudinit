provider "ibm" {
#  ibmcloud_api_key      = var.api_key
  generation            = 2
  region                = var.region
  ibmcloud_timeout      = 300
}