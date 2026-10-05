terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.95.0"
    }
  }

  # ─── S3 Backend ───────────────────────────────────────────────────────────
  # Reuses the same state bucket created for other modules.
  backend "s3" {
    bucket       = "idp-platform-tfstate-tranduyloc895"
    key          = "05-backstage-ec2/terraform.tfstate"
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
      Module      = "05-backstage-ec2"
    }
  }
}
