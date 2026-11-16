# ============================================================
# 00-bootstrap — S3 bucket chứa Terraform state cho mọi module khác.
#
# Lớp NỀN: tạo một lần, không destroy sau mỗi buổi lab.
# State của chính module này để LOCAL (terraform.tfstate trong thư mục này,
# bị git ignore). Nếu mất file state local, import lại:
#   terraform import aws_s3_bucket.tfstate <bucket-name>
# (và các resource con: versioning, encryption, public access block).
#
# Khóa state: S3 native lockfile (`use_lockfile = true`, Terraform >= 1.10),
# không cần DynamoDB.
# ============================================================

data "aws_caller_identity" "current" {}

locals {
  # Tên mặc định gắn account + region để toàn cục duy nhất, không ghi cứng account ID.
  bucket_name = var.state_bucket_name != "" ? var.state_bucket_name : "idp-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}

resource "aws_s3_bucket" "tfstate" {
  bucket = local.bucket_name

  # Bucket chứa state của toàn bộ hạ tầng: không cho destroy nhầm.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Dọn bớt version cũ của state để chi phí lưu trữ gần 0.
resource "aws_s3_bucket_lifecycle_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    id     = "expire-noncurrent-state-versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
