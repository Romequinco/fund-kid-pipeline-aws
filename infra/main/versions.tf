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
