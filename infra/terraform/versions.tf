terraform {
  required_version = "~> 1.15.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.55" }
  }
}

provider "aws" {
  region = var.region
  default_tags { tags = { Project = "worldguessr", Environment = var.environment_name, ManagedBy = "terraform" } }
}
