variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name used in resource tags"
  type        = string
  default     = "idp-platform"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "instance_type" {
  description = "EC2 instance type for Backstage host"
  type        = string
  default     = "t3.small"
}

variable "vpc_id" {
  description = "VPC ID where the EC2 instance will be created"
  type        = string
}

variable "subnet_id" {
  description = "Public subnet ID for the EC2 instance"
  type        = string
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
  default     = ["0.0.0.0/0"] # Restrict this in production!
}

variable "volume_size_gb" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20
}
