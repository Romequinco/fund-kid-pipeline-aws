# Cuadro de mando: imagen en ECR -> ECS Express Mode (Fargate + balanceador HTTPS). Coste por hora (D-5.2).

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
