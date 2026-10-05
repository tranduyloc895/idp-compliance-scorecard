terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.95.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # ─── S3 Backend ───────────────────────────────────────────────────────────
  # Bucket này cần được tạo thủ công TRƯỚC khi chạy `terraform init`.
  # Xem README.md để biết câu lệnh tạo bucket.
  backend "s3" {
    bucket       = "idp-platform-tfstate-tranduyloc895"
    key          = "04-oidc/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "Terraform"
      Module      = "04-oidc"
    }
  }
}
