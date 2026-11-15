#!/usr/bin/env bash
# Render + kiểm schema mọi manifest GitOps (chạy trong CI; cần helm, kustomize, kubeconform).
# KHÔNG chạy trên máy dev (không cài helm/kubectl trên Windows).
#
#   1. helm lint + helm template chart microservice với values của từng app
#   2. kustomize build các thư mục kustomize
#   3. manifest thuần (databases, namespace, experiments, kube-bench, policies, argocd)
#   4. helm template chart upstream với values của repo (bắt version chart sai / values lỗi)
# Tất cả đưa qua kubeconform (K8s 1.31) có CRD schema (Argo CD, Kyverno, Trivy, Prometheus).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
G="$ROOT/idp-gitops"
OUT="${OUT_DIR:-$ROOT/.render}"
# Schema kubeconform (thư viện schema có thể chưa có bản mới nhất) và version
# truyền cho helm template (= cluster_version trong Terraform) tách riêng.
K8S_VERSION="${K8S_VERSION:-1.31.0}"
HELM_KUBE_VERSION="${HELM_KUBE_VERSION:-1.35.0}"
rm -rf "$OUT" && mkdir -p "$OUT/ours" "$OUT/upstream"

# CRD schema từ datree CRDs-catalog (pin theo commit qua CRDS_CATALOG_REF nếu cần).
CRDS_CATALOG_REF="${CRDS_CATALOG_REF:-main}"
KC=(kubeconform -strict -summary -kubernetes-version "$K8S_VERSION"
  -schema-location default
  -schema-location "https://raw.githubusercontent.com/datreeio/CRDs-catalog/${CRDS_CATALOG_REF}/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json")

echo "==> helm lint + template: charts/microservice"
for svc in ui cart catalog orders checkout; do
  helm lint "$G/charts/microservice" -f "$G/apps/image-registry.yaml" -f "$G/apps/$svc/values.yaml" --quiet
  helm template "$svc" "$G/charts/microservice" \
    -f "$G/apps/image-registry.yaml" -f "$G/apps/$svc/values.yaml" > "$OUT/ours/svc-$svc.yaml"
done
# ui phải là ClusterIP (không tạo ELB công khai)
if grep -A3 'kind: Service' "$OUT/ours/svc-ui.yaml" | grep -q 'type: LoadBalancer'; then
  echo "FAIL: ui Service must not be LoadBalancer"; exit 1
fi

echo "==> kustomize build"
kustomize build "$G/compliance/compliance-engine" > "$OUT/ours/compliance-engine.yaml"
kustomize build "$G/platform/monitoring/dashboards" > "$OUT/ours/dashboards.yaml"
# Overlay dev hiện chưa có resource (placeholder) -> kustomize báo "empty"; chỉ build khi có nội dung.
if grep -qE '^(resources|patches|components):' "$G/environments/dev/kustomization.yaml"; then
  kustomize build "$G/environments/dev" > "$OUT/ours/env-dev.yaml"
else
  echo "  skip environments/dev (kustomization chưa có resources)"
fi

echo "==> plain manifests"
for d in apps/databases apps/namespace experiments platform/kube-bench platform/kyverno/policies argocd; do
  name="$(echo "$d" | tr '/' '-')"
  find "$G/$d" -name '*.y*ml' -print0 | sort -z | xargs -0 -I{} sh -c 'cat "{}"; echo; echo "---"' > "$OUT/ours/$name.yaml"
done
# Thêm newline + '---' giữa file: namespace.yml không có newline cuối file.
{ cat "$G/platform/monitoring/namespace.yml"; printf '
---
'; cat "$G/platform/monitoring/storageclass-gp3.yaml"; } > "$OUT/ours/monitoring-base.yaml"

echo "==> kubeconform (repo manifests, strict, CRD schemas required)"
"${KC[@]}" "$OUT"/ours/*.yaml

echo "==> upstream charts with repo values"
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null
helm repo add kyverno https://kyverno.github.io/kyverno/ >/dev/null
helm repo add aqua https://aquasecurity.github.io/helm-charts/ >/dev/null
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo add grafana https://grafana.github.io/helm-charts >/dev/null
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null
helm repo add autoscaler https://kubernetes.github.io/autoscaler >/dev/null
helm repo update >/dev/null

# Version phải khớp với Application / Terraform; đọc từ file để không lệch.
ver() { grep -A3 "chart: $1" "$G/argocd/$2" | awk '/targetRevision:/ {print $2; exit}'; }
tfvar() { awk -v n="$1" '$0 ~ "variable \""n"\"" {f=1} f && /default/ {gsub(/"/,"",$3); print $3; exit}' "$ROOT/infrastructure/02-cluster-eks/variables.tf"; }

render() { # name chart version [values...]
  local name="$1" chart="$2" version="$3"; shift 3
  local args=()
  for v in "$@"; do args+=(-f "$v"); done
  echo "  - $chart@$version"
  helm template "$name" "$chart" --version "$version" --kube-version "$HELM_KUBE_VERSION" "${args[@]}" > "$OUT/upstream/$name.yaml"
}
render kyverno kyverno/kyverno "$(ver kyverno platform-kyverno-application.yml)" "$G/platform/kyverno/values.yaml"
render trivy-operator aqua/trivy-operator "$(ver trivy-operator platform-trivy-operator-application.yml)" "$G/platform/trivy-operator/values.yaml"
render kps prometheus-community/kube-prometheus-stack "$(ver kube-prometheus-stack platform-kps-application.yml)" "$G/platform/monitoring/values-kube-prometheus-stack.yaml"
render loki grafana/loki "$(ver loki platform-loki-application.yml)" "$G/platform/monitoring/values-loki.yaml"
render promtail grafana/promtail "$(ver promtail platform-promtail-application.yml)" "$G/platform/monitoring/values-promtail.yaml"
render metrics-server metrics-server/metrics-server "$(ver metrics-server platform-metrics-server-application.yml)" "$G/platform/metrics-server/values.yaml"
render cluster-autoscaler autoscaler/cluster-autoscaler "$(ver cluster-autoscaler platform-cluster-autoscaler-application.yml)" "$G/platform/cluster-autoscaler/values.yaml"
render argocd argo/argo-cd "$(tfvar argocd_chart_version)"
render argocd-apps argo/argocd-apps "$(tfvar argocd_apps_chart_version)"

echo "==> kubeconform (upstream renders, CRD có thể thiếu schema -> bỏ qua)"
# Không -strict: chart upstream có field thừa mà API server vẫn nhận (vd kyverno
# 3.2.6 RoleBinding kyverno:remove-configmap có roleRef.namespace). Manifest của
# repo ở trên vẫn kiểm strict.
"${KC[@]/-strict/}" -ignore-missing-schemas "$OUT"/upstream/*.yaml

echo "==> third-party images exist (docker manifest inspect)"
imgs="$(cat "$OUT"/ours/*.yaml | awk '/^[[:space:]]+image:/ {print $2}' | tr -d '"' | sort -u   | grep -v -e 'ECR_REGISTRY_NOT_SET' -e '^compliance-engine$' -e 'dkr.ecr' || true)"
missing=0
for img in $imgs; do
  if docker manifest inspect "$img" >/dev/null 2>&1; then echo "  ok   $img"; else echo "  MISSING $img"; missing=1; fi
done
[ "$missing" -eq 0 ] || { echo "FAIL: image tag không tồn tại"; exit 1; }

echo "k8s-render-check: OK"
