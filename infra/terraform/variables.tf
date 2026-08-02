variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "environment_name" {
  type    = string
  default = "lab"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium"]
}

variable "node_min" {
  type    = number
  default = 1
}

variable "node_max" {
  type    = number
  default = 3
}

variable "database_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "cache_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "production_safeguards" {
  type    = bool
  default = false
}

variable "domain_name" {
  type     = string
  default  = null
  nullable = true
}
variable "github_oidc_subject" {
  type        = string
  description = "For example repo:owner/name:environment:production"
}
