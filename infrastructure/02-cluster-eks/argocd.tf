# ============================================================
# Argo CD — cơ chế cài DUY NHẤT (audit #5). Không cài lại bằng
# idp-gitops/scripts/bootstrap.*.
#
# 1. helm_release.argocd       : Argo CD server/controller/repo-server.
# 2. helm_release.argocd_root  : chart argocd-apps tạo root Application
#    (app-of-apps) trỏ vào idp-gitops/argocd trong monorepo.
#
# Dùng chart argocd-apps thay vì kubernetes_manifest vì kubernetes_manifest
# cần CRD Application tồn tại ngay lúc plan — không có trên cluster mới.
# ============================================================

resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_chart_version

  namespace        = "argocd"
  create_namespace = true

  # Gọn cho lab: 1 replica mỗi thành phần, tắt dex (không dùng SSO).
  values = [yamlencode({
    dex = { enabled = false }
    configs = {
      params = { "server.insecure" = true }
    }
  })]

  depends_on = [module.eks]
}

resource "helm_release" "argocd_root" {
  name       = "argocd-root"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argocd-apps"
  version    = var.argocd_apps_chart_version
  namespace  = "argocd"

  values = [yamlencode({
    applications = {
      root = {
        namespace = "argocd"
        # Finalizer để xoá root theo kiểu cascade (aws-down bước 1).
        finalizers = ["resources-finalizer.argocd.argoproj.io"]
        project    = "default"
        source = {
          repoURL        = var.gitops_repo_url
          targetRevision = var.gitops_revision
          path           = var.gitops_root_path
          directory      = { recurse = false }
        }
        destination = {
          server    = "https://kubernetes.default.svc"
          namespace = "argocd"
        }
        syncPolicy = {
          automated = { prune = true, selfHeal = true }
        }
      }
    }
  })]

  depends_on = [helm_release.argocd]
}
