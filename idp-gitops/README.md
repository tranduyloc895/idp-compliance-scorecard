# IDP Platform — GitOps Repository

Source of truth cho toàn bộ Kubernetes workloads và platform add-ons. ArgoCD watches repo này và sync liên tục.

## Cấu trúc

```
idp-gitops/
├── argocd/           # ArgoCD Application definitions (App-of-Apps)
├── apps/             # Per-service Helm values (ui, cart, catalog, orders, checkout)
├── charts/           # Shared Helm chart cho microservices
├── platform/         # Platform add-ons (monitoring, cluster-autoscaler, kyverno...)
├── environments/     # Environment-specific overrides
└── scripts/          # bootstrap.sh để setup fresh cluster
```

## Bootstrap cluster mới

```bash
# Sau khi EKS + ArgoCD đã được tạo bởi Terraform:
bash scripts/bootstrap.sh
```

Script sẽ apply `root-application.yml` → ArgoCD tự sync toàn bộ apps.
