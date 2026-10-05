variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "ecommerce-cluster"
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "cluster_endpoint_public_access" {
  description = "Enable public access to EKS API endpoint"
  type        = bool
  default     = true
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "List of CIDR blocks allowed to access EKS public endpoint. Restrict to your IP/VPN for security."
  type        = list(string)
  default     = ["0.0.0.0/0"] # TODO: Thay bằng IP thực tế của bạn, ví dụ ["123.45.67.89/32"]
}

variable "cluster_endpoint_private_access" {
  description = "Enable private access to EKS API endpoint (from within VPC)"
  type        = bool
  default     = true
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS node group"
  type        = list(string)
  default     = ["t3.large"]
}

variable "node_capacity_type" {
  description = "Capacity type for node group (ON_DEMAND or SPOT)"
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.node_capacity_type)
    error_message = "Capacity type must be ON_DEMAND or SPOT."
  }
}

variable "node_min_size" {
  description = "Minimum number of nodes in node group"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of nodes in node group (trần cho Cluster Autoscaler)"
  type        = number
  default     = 4
}

variable "node_desired_size" {
  description = "Desired number of nodes in node group (chỉ áp dụng lúc tạo mới; sau đó Cluster Autoscaler quản lý — module có ignore_changes cho desired_size)"
  type        = number
  default     = 3
}

variable "node_disk_size" {
  description = "Disk size in GB for each node"
  type        = number
  default     = 50
}

variable "argocd_chart_version" {
  description = "Helm chart version for ArgoCD"
  type        = string
  default     = "5.51.4"
}

variable "vpc_name" {
  description = "Name tag of the VPC to lookup"
  type        = string
  default     = "ecommerce-vpc"
}

variable "project" {
  description = "Project name for tagging"
  type        = string
  default     = "DevSecOps-Ecommerce"
}

variable "environment" {
  description = "Environment name (Dev, Staging, Prod)"
  type        = string
  default     = "Dev"
}
