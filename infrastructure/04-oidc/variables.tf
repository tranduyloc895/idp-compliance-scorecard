variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name for tagging"
  type        = string
  default     = "idp-compliance-scorecard"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "Dev"
}

variable "github_org" {
  description = "GitHub organization or username (e.g. tranduyloc895)"
  type        = string
  default     = "tranduyloc895"
}

variable "github_repo" {
  description = "GitHub repository (monorepo) được phép assume role"
  type        = string
  default     = "idp-compliance-scorecard"
}


variable "iam_role_name" {
  description = "Name of the IAM Role created for GitHub Actions"
  type        = string
  default     = "github-actions-idp-compliance-scorecard"
}

variable "state_bucket" {
  description = "S3 bucket chứa Terraform state (output của 00-bootstrap)"
  type        = string
}

variable "create_oidc_provider" {
  description = "Tạo GitHub OIDC provider mới (false nếu account đã có sẵn)"
  type        = bool
  default     = true
}
