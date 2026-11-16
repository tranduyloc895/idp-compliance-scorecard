variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name used in resource tags"
  type        = string
  default     = "idp-compliance-scorecard"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "Dev"
}

variable "instance_type" {
  description = "EC2 instance type for Backstage host"
  type        = string
  default     = "t3.small"
}

variable "key_name" {
  description = "EC2 Key Pair name for SSH access (leave empty to disable SSH key)"
  type        = string
  default     = ""
}

variable "ami_id" {
  description = "Amazon Linux 2023 AMI ID (region-specific). Leave empty to use data source lookup."
  type        = string
  default     = ""
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed for SSH access (port 22)"
  type        = list(string)
  default     = []
}

variable "volume_size_gb" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20
}

variable "state_bucket" {
  description = "S3 bucket chứa Terraform state (output của 00-bootstrap)"
  type        = string
}

variable "allowed_http_cidrs" {
  description = "CIDR được truy cập Backstage port 7007 (nên đặt IP của bạn /32)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssm_prefix" {
  description = "Tiền tố SSM Parameter Store chứa secret/URL"
  type        = string
  default     = "/idp"
}
