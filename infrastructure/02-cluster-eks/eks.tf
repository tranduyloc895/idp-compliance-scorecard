# KMS Key for EKS Secrets Encryption
resource "aws_kms_key" "eks" {
  description             = "KMS key for EKS cluster ${var.cluster_name} secrets encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.cluster_name}-eks-secrets"
  target_key_id = aws_kms_key.eks.key_id
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = data.aws_vpc.ecommerce.id
  subnet_ids = data.aws_subnets.private.ids

  # Endpoint access control
  cluster_endpoint_public_access       = var.cluster_endpoint_public_access
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs
  cluster_endpoint_private_access      = var.cluster_endpoint_private_access

  # Encryption at rest for Kubernetes Secrets using KMS
  cluster_encryption_config = {
    provider_key_arn = aws_kms_key.eks.arn
    resources        = ["secrets"]
  }

  cluster_enabled_log_types = ["api", "audit", "authenticator"]

  enable_cluster_creator_admin_permissions = true

  # EKS managed addons
  # - aws-ebs-csi-driver: cần thiết để provisioning PVC qua EBS
  #   (plugin in-tree kubernetes.io/aws-ebs đã deprecated ở K8s 1.23+
  #    và bị vô hiệu hóa dần ở 1.27+; bắt buộc dùng CSI driver)
  cluster_addons = {
    aws-ebs-csi-driver = {
      most_recent              = true
      service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
    }
  }

  # Note: `access_entries` for Jenkins Agent was removed after migrating to GitOps.
  # ArgoCD (running in-cluster) now handles all kubectl apply operations.
  # Jenkins Agent only needs to push images to ECR and commits to the gitops repo.

  eks_managed_node_groups = {
    main_nodes = {
      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      instance_types = var.node_instance_types
      capacity_type  = var.node_capacity_type

      disk_size = var.node_disk_size
    }
  }
}

# SG rule `jenkins_agent_to_eks` was removed after migrating to GitOps.
# Jenkins Agent no longer needs to reach the EKS API endpoint (port 443).
# Only ArgoCD (inside the cluster) talks to the API server now.
