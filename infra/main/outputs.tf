# El workflow pipeline.yml lee estos valores con `terraform output` para configurar el lote.

output "bucket" {
  value = aws_s3_bucket.kid.bucket
}

output "db_cluster_arn" {
  value = aws_rds_cluster.kid.arn
}

output "db_secret_arn" {
  value = local.db_secret_arn
}

output "db_name" {
  value = aws_rds_cluster.kid.database_name
}

output "api_url" {
  value = aws_lambda_function_url.api.function_url
}

output "bedrock_model_id" {
  value = var.bedrock_model_id
}
