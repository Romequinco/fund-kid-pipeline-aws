# Infraestructura del proyecto: la aplica GitHub Actions (deploy.yml) con el estado en S3 (D-5.1).
# datos.tf = S3 y Aurora; servicios.tf = API en Lambda y cuadro de mando en ECS Express.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Configuración parcial: el bucket y la región se pasan en `terraform init -backend-config=...` (deploy.yml)
  backend "s3" {
    key          = "main/terraform.tfstate"
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Proyecto = "fund-kid-pipeline" }
  }
}

# --- Variables ---

variable "region" {
  type    = string
  default = "eu-west-3"
}

variable "alias" {
  description = "Sufijo para que los nombres de bucket sean únicos en todo AWS (el mismo que en bootstrap)."
  type        = string
}

variable "bedrock_model_id" {
  description = "Modelo o perfil de inferencia de Bedrock (D-2.2)."
  type        = string
  default     = ""
}

variable "api_image_tag" {
  type    = string
  default = "latest"
}

variable "dashboard_image_tag" {
  type    = string
  default = "latest"
}

variable "desplegar_dashboard" {
  description = "Alternativa apagada: el cuadro de mando en ECS Express (~80 $/mes). En producción va en S3 + CloudFront (D-4.3)."
  type        = bool
  default     = false
}

# --- Salidas (las lee el job del lote con `terraform output`) ---

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

output "web_url" {
  description = "Aplicación web en producción: Streamlit en el navegador (stlite) servido por CloudFront (D-4.3)."
  value       = "https://${aws_cloudfront_distribution.web.domain_name}"
}

output "bedrock_model_id" {
  value = var.bedrock_model_id
}
