data "aws_availability_zones" "available" { state = "available" }
data "aws_caller_identity" "current" {}

locals {
  name = "worldguessr-${var.environment_name}"
  azs  = slice(data.aws_availability_zones.available.names, 0, 2)
}

module "vpc" {
  source                 = "terraform-aws-modules/vpc/aws"
  version                = "6.6.1"
  name                   = local.name
  cidr                   = var.vpc_cidr
  azs                    = local.azs
  public_subnets         = [for i in range(2) : cidrsubnet(var.vpc_cidr, 4, i)]
  private_subnets        = [for i in range(2) : cidrsubnet(var.vpc_cidr, 4, i + 2)]
  database_subnets       = [for i in range(2) : cidrsubnet(var.vpc_cidr, 4, i + 4)]
  enable_nat_gateway     = true
  single_nat_gateway     = !var.production_safeguards
  one_nat_gateway_per_az = var.production_safeguards
  enable_dns_hostnames   = true
  public_subnet_tags     = { "kubernetes.io/role/elb" = "1" }
  private_subnet_tags    = { "kubernetes.io/role/internal-elb" = "1" }
}

module "eks" {
  source                                   = "terraform-aws-modules/eks/aws"
  version                                  = "21.24.0"
  name                                     = local.name
  kubernetes_version                       = "1.36"
  endpoint_public_access                   = true
  enable_cluster_creator_admin_permissions = true
  vpc_id                                   = module.vpc.vpc_id
  subnet_ids                               = module.vpc.private_subnets
  addons = {
    eks-pod-identity-agent = {}
  }
  eks_managed_node_groups = {
    app = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      min_size       = var.node_min
      max_size       = var.node_max
      desired_size   = var.node_min
    }
  }
}

resource "aws_ecr_repository" "images" {
  for_each             = toset(["frontend", "backend"])
  name                 = "${local.name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}

resource "aws_s3_bucket" "velero" {
  bucket_prefix = "${local.name}-velero-"
  force_destroy = !var.production_safeguards
}
resource "aws_s3_bucket_versioning" "velero" {
  bucket = aws_s3_bucket.velero.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "velero" {
  bucket = aws_s3_bucket.velero.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_public_access_block" "velero" {
  bucket                  = aws_s3_bucket.velero.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_secretsmanager_secret" "application" {
  name                    = "${local.name}/application"
  recovery_window_in_days = var.production_safeguards ? 30 : 0
  description             = "Populate out-of-band with database URL, signing secret, and Mapillary tokens."
}

resource "aws_security_group" "data" {
  name_prefix = "${local.name}-data-"
  vpc_id      = module.vpc.vpc_id
  ingress {
    description = "PostgreSQL from EKS nodes"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
  ingress {
    description = "Valkey from EKS nodes"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

resource "aws_db_instance" "postgres" {
  identifier                   = local.name
  engine                       = "postgres"
  engine_version               = "18"
  instance_class               = var.database_instance_class
  allocated_storage            = 20
  max_allocated_storage        = 100
  storage_encrypted            = true
  db_name                      = "worldguessr"
  username                     = "worldguessr"
  manage_master_user_password  = true
  db_subnet_group_name         = module.vpc.database_subnet_group_name
  vpc_security_group_ids       = [aws_security_group.data.id]
  multi_az                     = var.production_safeguards
  backup_retention_period      = var.production_safeguards ? 14 : 1
  deletion_protection          = var.production_safeguards
  skip_final_snapshot          = !var.production_safeguards
  performance_insights_enabled = var.production_safeguards
}

resource "aws_elasticache_subnet_group" "data" {
  name       = local.name
  subnet_ids = module.vpc.database_subnets
}

resource "aws_elasticache_replication_group" "valkey" {
  replication_group_id       = local.name
  description                = "Reconstructible WorldGuessr cache and ARQ queue"
  engine                     = "valkey"
  engine_version             = "9.1"
  node_type                  = var.cache_node_type
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.data.name
  security_group_ids         = [aws_security_group.data.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  automatic_failover_enabled = var.production_safeguards
  multi_az_enabled           = var.production_safeguards
  num_cache_clusters         = var.production_safeguards ? 2 : 1
}
