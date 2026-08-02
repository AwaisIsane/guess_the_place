terraform {
  required_version = "~> 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.90" }
  }
}

provider "aws" {
  region = var.region
  default_tags { tags = { Project = "worldguessr", Environment = var.environment_name, ManagedBy = "terraform" } }
}
