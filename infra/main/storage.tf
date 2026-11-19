# Bucket de los KID: privado, cifrado y versionado. Solo se accede por el pipeline y la API.

resource "aws_s3_bucket" "kid" {
  bucket = "fund-kid-${var.alias}-documentos"
}

resource "aws_s3_bucket_public_access_block" "kid" {
  bucket                  = aws_s3_bucket.kid.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "kid" {
  bucket = aws_s3_bucket.kid.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kid" {
  bucket = aws_s3_bucket.kid.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
