# Aurora PostgreSQL Serverless v2 con Data API (D-3.1): sin VPC propia ni driver desde Lambda.
# La contraseña la genera y guarda RDS en Secrets Manager (D-0.4).

resource "aws_rds_cluster" "kid" {
  cluster_identifier          = "fund-kid"
  engine                      = "aurora-postgresql"
  engine_mode                 = "provisioned"
  database_name               = "kid"
  master_username             = "kid_admin"
  manage_master_user_password = true
  enable_http_endpoint        = true # RDS Data API
  storage_encrypted           = true
  skip_final_snapshot         = true

  serverlessv2_scaling_configuration {
    min_capacity             = 0 # se pausa sin uso
    max_capacity             = 1
    seconds_until_auto_pause = 600
  }
}

resource "aws_rds_cluster_instance" "kid" {
  identifier         = "fund-kid-1"
  cluster_identifier = aws_rds_cluster.kid.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.kid.engine
  engine_version     = aws_rds_cluster.kid.engine_version
}

locals {
  db_secret_arn = aws_rds_cluster.kid.master_user_secret[0].secret_arn
}
