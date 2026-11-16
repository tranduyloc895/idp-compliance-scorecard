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
  description = "Environment name (Dev, Staging, Prod)"
  type        = string
  default     = "Dev"
}

variable "repository_prefix" {
  description = "Tiền tố tên repo ECR"
  type        = string
  default     = "retail-store"
}

variable "keep_images" {
  description = "Số image gần nhất giữ lại mỗi repo"
  type        = number
  default     = 10
}
