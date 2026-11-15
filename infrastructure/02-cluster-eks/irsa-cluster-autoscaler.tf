# ============================================================
# IRSA (IAM Role for Service Account) cho Cluster Autoscaler
# ------------------------------------------------------------
# Tại sao cần riêng role này?
#   Cluster Autoscaler pod gọi AWS API (autoscaling:SetDesiredCapacity,
#   TerminateInstanceInAutoScalingGroup, Describe*, ec2:Describe*) để nâng/hạ
#   số node của ASG khi có pod Pending vì thiếu chỗ. Theo nguyên tắc
#   least-privilege, ta tạo dedicated IAM role gắn vào service account của pod
#   thay vì cấp quyền rộng cho node.
#
# Cơ chế:
#   - Dùng OIDC provider sẵn có của EKS (giống IRSA của EBS CSI).
#   - Pod CA mount service account "kube-system:cluster-autoscaler".
#   - Preset attach_cluster_autoscaler_policy của module IAM tự sinh policy
#     least-privilege, giới hạn theo đúng cluster qua cluster_autoscaler_cluster_names.
#
# Lưu ý discovery:
#   - EKS managed node group tự gắn tag k8s.io/cluster-autoscaler/<cluster> lên
#     ASG, nên CA dùng autoDiscovery.clusterName là tìm thấy node group
#     (cấu hình ở idp-gitops/platform/cluster-autoscaler/values.yaml).
# ============================================================

module "cluster_autoscaler_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.39"

  role_name                        = "${var.cluster_name}-cluster-autoscaler"
  attach_cluster_autoscaler_policy = true
  cluster_autoscaler_cluster_names = [var.cluster_name]

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:cluster-autoscaler"]
    }
  }
}

# ServiceAccount do Terraform tạo để gắn role ARN lấy trực tiếp từ output IRSA
# (audit #8): GitOps không phải ghi cứng account ID. Chart cluster-autoscaler
# trong idp-gitops dùng rbac.serviceAccount.create=false + name này.
resource "kubernetes_service_account_v1" "cluster_autoscaler" {
  metadata {
    name      = "cluster-autoscaler"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = module.cluster_autoscaler_irsa.iam_role_arn
    }
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  depends_on = [module.eks]
}
