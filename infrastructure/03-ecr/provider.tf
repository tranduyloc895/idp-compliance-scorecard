terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.95.0"
    }
  }

  # Backend S3 cấu hình một phần: bucket truyền lúc init
  #   terraform init -backend-config="bucket=$TF_STATE_BUCKET"
  # (scripts/lib.sh tự làm việc này). Một bucket duy nhất cho mọi module.
  backend "s3" {
    key          = "03-ecr/terraform.tfstate"
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
      Layer       = "foundation"
    }
  }
}
