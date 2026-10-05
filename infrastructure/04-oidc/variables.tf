variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name for tagging"
  type        = string
  default     = "IDP-Platform"
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
  description = "GitHub repository name for idp-microservices"
  type        = string
  default     = "idp-microservices"
}

variable "ecr_account_id" {
  description = "AWS Account ID owning the ECR repositories"
  type        = string
  # Không có default — bắt buộc phải truyền vào (hoặc set TF_VAR_ecr_account_id)
}

variable "iam_role_name" {
  description = "Name of the IAM Role created for GitHub Actions"
  type        = string
  default     = "github-actions-idp-microservices"
}
