data "ibm_is_subnet" "f5_managment_subnet" {
  identifier = "${var.management_subnet_id}"
}

locals {
  secondary_subnets = compact(list(var.data_1_1_subnet_id, var.data_1_2_subnet_id, var.data_1_3_subnet_id, var.data_1_4_subnet_id))
}

resource "random_uuid" "namer" {}

// open up port security security group
resource "ibm_is_security_group" "f5_open_sg" {
  name           = "sg-${random_uuid.namer.result}"
  vpc            = data.ibm_is_subnet.f5_managment_subnet.vpc
  resource_group = data.ibm_is_subnet.f5_managment_subnet.resource_group
}

// allow all inbound
resource "ibm_is_security_group_rule" "f5_allow_inbound" {
  depends_on = [ibm_is_security_group.f5_open_sg]
  group      = ibm_is_security_group.f5_open_sg.id
  direction  = "inbound"
  remote     = "0.0.0.0/0"
}

// all all outbound
resource "ibm_is_security_group_rule" "f5_allow_outbound" {
  depends_on = [ibm_is_security_group_rule.f5_allow_inbound]
  group      = ibm_is_security_group.f5_open_sg.id
  direction  = "outbound"
  remote     = "0.0.0.0/0"
}
