variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "Tên S3 bucket chứa state. Để trống: idp-tfstate-<account_id>-<region>."
  type        = string
  default     = ""
}

variable "project" {
  description = "Project tag"
  type        = string
  default     = "idp-compliance-scorecard"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "Dev"
}
