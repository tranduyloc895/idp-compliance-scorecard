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
  default     = 3
}

variable "node_desired_size" {
  description = "Desired number of nodes in node group (chỉ áp dụng lúc tạo mới; sau đó Cluster Autoscaler quản lý — module có ignore_changes cho desired_size)"
  type        = number
  default     = 2
}

variable "node_disk_size" {
  description = "Disk size in GB for each node"
  type        = number
  default     = 30
}

variable "cluster_log_retention_days" {
  description = "Số ngày giữ CloudWatch log của control plane (nhỏ để giảm chi phí lab)"
  type        = number
  default     = 7
}

variable "argocd_chart_version" {
  description = "Helm chart version for ArgoCD"
  type        = string
  default     = "5.51.4"
}

variable "state_bucket" {
  description = "S3 bucket chứa Terraform state (output state_bucket của 00-bootstrap); dùng cho terraform_remote_state"
  type        = string
}

variable "gitops_repo_url" {
  description = "Repo Git mà Argo CD đồng bộ (monorepo)"
  type        = string
  default     = "https://github.com/tranduyloc895/idp-compliance-scorecard.git"
}

variable "gitops_revision" {
  description = "Branch/tag/commit Argo CD theo dõi"
  type        = string
  default     = "main"
}

variable "gitops_root_path" {
  description = "Thư mục chứa các Argo CD Application (app-of-apps)"
  type        = string
  default     = "idp-gitops/argocd"
}

variable "argocd_apps_chart_version" {
  description = "Helm chart version cho argocd-apps (tạo root Application)"
  type        = string
  default     = "2.0.2"
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
