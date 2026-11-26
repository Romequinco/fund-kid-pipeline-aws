# Raíz aparte de infra/. Se aplica UNA vez y en local (aws login), porque crea el rol con el que GitHub Actions se autentica (D-5.1):
#   cd infra/bootstrap && terraform init && terraform apply -var="alias=<iniciales>"
# Su estado se queda en local (no hay backend todavía); no se sube a Git (.gitignore).

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "eu-west-3"
}

variable "alias" {
  description = "Sufijo para que los nombres de bucket sean únicos en todo AWS."
  type        = string
}

variable "github_repo" {
  type    = string
  default = "Romequinco/fund-kid-pipeline-aws"
}

# GitHub firma hoy el token con un "sujeto inmutable" que lleva los ID numéricos del usuario y del repositorio
# (`gh api repos/<repo>/actions/oidc/customization/sub`). Es más seguro: un repositorio nuevo con el mismo nombre
# tendría otros ID. Se aceptan los dos formatos.
variable "github_repo_inmutable" {
  type    = string
  default = "Romequinco@236243639/fund-kid-pipeline-aws@1464495334"
}

# --- Estado remoto de infra/ ---
resource "aws_s3_bucket" "tfstate" {
  bucket = "fund-kid-${var.alias}-tfstate"
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- OIDC: GitHub pide credenciales temporales a AWS, sin claves guardadas (curso, lección 22) ---
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_role" "github" {
  name = "fund-kid-github-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        # La condición de confianza es lo que limita el acceso a este repositorio
        StringLike = { "token.actions.githubusercontent.com:sub" = [
          "repo:${var.github_repo_inmutable}:*",
          "repo:${var.github_repo}:*",
        ] }
      }
    }]
  })
}

# Permisos amplios para empezar; limitarlos a los recursos del proyecto queda abierto en D-5.3.
resource "aws_iam_role_policy_attachment" "github" {
  for_each = toset([
    "arn:aws:iam::aws:policy/PowerUserAccess",
    "arn:aws:iam::aws:policy/IAMFullAccess",
  ])
  role       = aws_iam_role.github.name
  policy_arn = each.value
}

# Rol vinculado al servicio ECS: ECS Express lo necesita y AWS solo lo crea solo la primera vez que se entra en ECS desde
# la consola. En una cuenta que nunca ha usado ECS, el despliegue falla con "Unable to assume the service linked role".
resource "aws_iam_service_linked_role" "ecs" {
  aws_service_name = "ecs.amazonaws.com"
  description      = "Policy to enable Amazon ECS to manage your EC2 instances and related resources." # la de AWS
}

output "tfstate_bucket" {
  value = aws_s3_bucket.tfstate.bucket
}

output "github_role_arn" {
  description = "Va en la variable AWS_ROLE_ARN del repositorio (Settings > Variables > Actions)."
  value       = aws_iam_role.github.arn
}
