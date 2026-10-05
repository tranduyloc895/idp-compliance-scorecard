# ============================================================
# IRSA (IAM Role for Service Account) cho EBS CSI Driver
# ------------------------------------------------------------
# Tại sao cần riêng role này?
#   EBS CSI controller pod gọi AWS API (CreateVolume, AttachVolume, ...)
#   để cấp phát EBS volume cho PVC. Thay vì cấp quyền rộng cho node,
#   ta tạo dedicated IAM role gắn vào service account của pod (nguyên
#   tắc least-privilege).
#
# Cơ chế:
#   - EKS có sẵn OIDC provider (enable_irsa mặc định true ở module v20+)
#   - Pod mount service account "kube-system:ebs-csi-controller-sa"
#   - AWS STS dùng OIDC token của pod để assume role này
#   - Role có policy AmazonEBSCSIDriverPolicy (managed by AWS)
# ============================================================

module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.39"

  role_name             = "${var.cluster_name}-ebs-csi-driver"
  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }
}
