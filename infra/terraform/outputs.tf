output "cluster_name" { value = module.eks.cluster_name }
output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "registries" { value = { for k, v in aws_ecr_repository.images : k => v.repository_url } }
output "application_secret_arn" { value = aws_secretsmanager_secret.application.arn }
output "backup_bucket" { value = aws_s3_bucket.velero.id }
output "vpc_id" { value = module.vpc.vpc_id }
output "domain_name" { value = var.domain_name }
output "database_endpoint" { value = aws_db_instance.postgres.address }
output "database_master_secret_arn" { value = aws_db_instance.postgres.master_user_secret[0].secret_arn }
output "cache_endpoint" { value = aws_elasticache_replication_group.valkey.primary_endpoint_address }
