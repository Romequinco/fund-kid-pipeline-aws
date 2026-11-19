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
  timeout       = 30 # Aurora puede tardar en despertar si estaba pausada
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
