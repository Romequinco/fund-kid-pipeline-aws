# API: imagen en ECR -> Lambda -> Function URL pública (solo lectura).
# Primer despliegue: deploy.yml crea antes los repositorios ECR con -target y sube la imagen.

resource "aws_ecr_repository" "api" {
  name         = "fund-kid-api"
  force_delete = true
}

resource "aws_iam_role" "api" {
  name = "fund-kid-api"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "api_logs" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Mínimo privilegio: solo la Data API de este clúster y su secreto
resource "aws_iam_role_policy" "api_db" {
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["rds-data:ExecuteStatement"], Resource = aws_rds_cluster.kid.arn },
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = local.db_secret_arn },
    ]
  })
}

resource "aws_lambda_function" "api" {
  function_name = "fund-kid-api"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
  role          = aws_iam_role.api.arn
  timeout       = 60 # Aurora tarda unos segundos en despertar de la pausa; db.py reintenta hasta ~30 s
  memory_size   = 512

  environment {
    variables = {
      DB_CLUSTER_ARN = aws_rds_cluster.kid.arn
      DB_SECRET_ARN  = local.db_secret_arn
      DB_NAME        = aws_rds_cluster.kid.database_name
    }
  }
}

# Desde la consola se crea solo; con Terraform hay que dar el permiso de invocación pública explícitamente
resource "aws_lambda_permission" "api_url" {
  statement_id           = "FunctionUrlPublica"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["GET"]
  }
}

# Cuadro de mando en ECS Express Mode (Fargate + balanceador HTTPS): ALTERNATIVA APAGADA (D-4.3).
# Cuesta ~2,7 $/día encendido, las 24 h. Se reactiva con la variable de repositorio DESPLEGAR_DASHBOARD=true.

resource "aws_ecr_repository" "dashboard" {
  name         = "fund-kid-dashboard"
  force_delete = true
}

resource "aws_iam_role" "ecs_execution" {
  name = "fund-kid-ecs-execution"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_infrastructure" {
  name = "fund-kid-ecs-infrastructure"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ecs.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_infrastructure" {
  role       = aws_iam_role.ecs_infrastructure.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices"
}

resource "aws_ecs_express_gateway_service" "dashboard" {
  count                   = var.desplegar_dashboard ? 1 : 0
  service_name            = "fund-kid-dashboard"
  execution_role_arn      = aws_iam_role.ecs_execution.arn
  infrastructure_role_arn = aws_iam_role.ecs_infrastructure.arn
  health_check_path       = "/_stcore/health"

  primary_container {
    image          = "${aws_ecr_repository.dashboard.repository_url}:${var.dashboard_image_tag}"
    container_port = 8501

    environment {
      name  = "API_URL"
      value = aws_lambda_function_url.api.function_url
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_execution,
    aws_iam_role_policy_attachment.ecs_infrastructure,
  ]
}

# Solo se guardan las 3 últimas imágenes de cada repositorio: cada push añade cientos de MB (0,10 $/GB al mes)
resource "aws_ecr_lifecycle_policy" "ultimas_3" {
  for_each   = { api = aws_ecr_repository.api.name, dashboard = aws_ecr_repository.dashboard.name }
  repository = each.value
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Conservar las 3 imágenes más recientes"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 3 }
      action       = { type = "expire" }
    }]
  })
}

# --- Aplicación web en producción (D-4.3) ---
# Streamlit en el navegador del usuario (stlite sobre Pyodide): index.html carga stlite y ejecuta src/dashboard.py, que
# llama a la API. No hay servidor: un bucket privado y CloudFront delante, con HTTPS. Coste ~0 $ (capa gratuita).

resource "aws_s3_bucket" "web" {
  bucket = "fund-kid-${var.alias}-web"
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

locals {
  web = {
    "index.html"   = { origen = "${path.module}/../src/index.html", tipo = "text/html; charset=utf-8" }
    "dashboard.py" = { origen = "${path.module}/../src/dashboard.py", tipo = "text/x-python; charset=utf-8" }
  }
}

resource "aws_s3_object" "web" {
  for_each     = local.web
  bucket       = aws_s3_bucket.web.id
  key          = each.key
  source       = each.value.origen
  etag         = filemd5(each.value.origen)
  content_type = each.value.tipo
}

resource "aws_s3_object" "api_url" {
  bucket       = aws_s3_bucket.web.id
  key          = "api_url.txt"
  content      = aws_lambda_function_url.api.function_url
  content_type = "text/plain; charset=utf-8"
}

# Solo CloudFront puede leer el bucket (Origin Access Control): nadie entra directamente a S3
resource "aws_cloudfront_origin_access_control" "web" {
  name                              = "fund-kid-web"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_cloudfront_cache_policy" "sin_cache" {
  name = "Managed-CachingDisabled" # son 3 ficheros pequeños: así cada despliegue se ve al instante
}

resource "aws_cloudfront_distribution" "web" {
  enabled             = true
  comment             = "Fund KID: aplicacion web (Streamlit en el navegador)"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    origin_id                = "web"
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.web.id
  }

  default_cache_behavior {
    target_origin_id       = "web"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = data.aws_cloudfront_cache_policy.sin_cache.id
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_s3_bucket_policy" "web" {
  bucket = aws_s3_bucket.web.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.web.arn}/*"
      Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.web.arn } }
    }]
  })
}
