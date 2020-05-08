resource ibm_is_image "custom_image" {
  name             = var.image_name
  href             = var.image_url
  operating_system = "centos-7-amd64"
  timeouts {
    create = "30m"
    delete = "10m"
  }
}

output "image_uuid" {
    value = ibm_is_image.custom_image.id
}