# Giai đoạn 1–2 — CI kiểm tra tĩnh và smoke Compliance Engine

**Ngày:** 2026-11-15
**Thành phần:** other (CI), compliance-engine, backstage
**Loại:** test

## Mô tả
- `.github/workflows/validate.yml` chạy cho mọi push/PR: chặn placeholder/account ID/region sai, kiểm LF + cú pháp shell + YAML; `terraform fmt -check`/`init -backend=false`/`validate`/`tflint` cho 6 module; `helm lint`/`helm template` chart microservice với values từng app, `kustomize build`, manifest thuần, render chart upstream (kyverno, trivy-operator, kube-prometheus-stack, loki, promtail, metrics-server, cluster-autoscaler, argo-cd, argocd-apps) với values của repo, tất cả qua `kubeconform` K8s 1.31 có CRD schema (datree CRDs-catalog); `kyverno test` 8 policy × workload A/B/C; pytest; tsc; `docker build` 6 image không push.
- Job `engine-smoke`: docker compose (API + PostgreSQL + Redis, DB trắng, `COLLECTOR_MODE=fixtures`) → `GET /scores` phải 404 → `POST /api/v1/scans` body `{}` → poll completed → scores/history/findings có dữ liệu của cả 3 nguồn và 3 workload → rule recommendation cho finding Kyverno FAIL → `contract-check.mjs` cho response đi qua adapter của plugin → upload evidence.
- `scripts/validate-local.sh` chạy phần nhẹ trên máy (Git Bash); bước Terraform gọi qua WSL vì Windows Application Control chặn provider .exe.

## Các file đã thay đổi
- `.github/workflows/validate.yml`
- `scripts/validate-local.sh`, `scripts/terraform-validate.sh`, `scripts/k8s-render-check.sh`, `scripts/check-placeholders.sh`, `scripts/engine-smoke.sh`, `scripts/contract-check.mjs`
- `idp-gitops/platform/kyverno/tests/kyverno-test.yaml`
- `backstage/plugins/compliance-scorecard/tsconfig.{typecheck,contract}.json`, `package-lock.json`

## Ghi chú / Vấn đề còn lại
- Kết quả trên máy: validate-local PASS (placeholders, yaml, sh, terraform/WSL, pytest 68 passed, tsc), 32s.
- validate.yml và engine-smoke **chưa chạy** (cần đồng ý push branch). Các điểm dễ lỗi khi chạy lần đầu: version chart upstream (`argocd-apps 2.0.2`, `kyverno 3.2.6`, `trivy-operator 0.24.1`), kết quả autogen trong `kyverno test` (tên rule `autogen-*`), schema CRD thiếu trong catalog, Trivy gate CRITICAL trên image Retail Store (chỉ ở `_build-push`, không ở validate), PyYAML trên runner.
- CRDs-catalog đang theo `main` (chưa pin commit) — đặt `CRDS_CATALOG_REF` khi cần tái lập.
- Phần chỉ kiểm được trên cluster (để Giai đoạn 3): Argo CD sync thật theo wave, scanner sinh report thật, CronJob scan và kube-bench, NetworkPolicy (VPC CNI mặc định không enforce), probe/Ready của workload A/B/C, internal LB.
