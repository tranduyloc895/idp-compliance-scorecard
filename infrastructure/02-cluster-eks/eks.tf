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
  version = "~> 20.31"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  # Endpoint access control
  cluster_endpoint_public_access       = var.cluster_endpoint_public_access
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs
  cluster_endpoint_private_access      = var.cluster_endpoint_private_access

  # Encryption at rest for Kubernetes Secrets using KMS
  cluster_encryption_config = {
    provider_key_arn = aws_kms_key.eks.arn
    resources        = ["secrets"]
  }

  cluster_enabled_log_types              = ["api", "audit", "authenticator"]
  cloudwatch_log_group_retention_in_days = var.cluster_log_retention_days

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

  eks_managed_node_groups = {
    main_nodes = {
      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      instance_types = var.node_instance_types
      capacity_type  = var.node_capacity_type

      # disk_size chỉ có hiệu lực khi không dùng launch template tùy biến của module.
      use_custom_launch_template = false
      disk_size                  = var.node_disk_size
    }
  }
}
