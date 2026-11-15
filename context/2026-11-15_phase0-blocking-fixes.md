# Giai đoạn 0 — Sửa lỗi chặn (testable rebuild)

**Ngày:** 2026-11-15
**Thành phần:** infrastructure, gitops, compliance-engine, backstage, other (CI)
**Loại:** fix

## Mô tả
Sửa các lỗi chặn trong audit để hệ thống kiểm tra tĩnh được và dựng lại được trên AWS theo hai lớp (nền / tạo-huỷ). Mọi thay đổi trên branch `feat/testable-rebuild`; kế hoạch gốc ở `docs/plans/testable-rebuild.md`, tiến độ ở `context/2026-11-15_testable-rebuild-progress.md`.

Mục audit đã xử lý trong giai đoạn này (cách kiểm chứng):

| Mục | Xử lý | Kiểm chứng |
|---|---|---|
| #1 | Monorepo: mọi Application trỏ `tranduyloc895/idp-compliance-scorecard`, path `idp-gitops/...`; CI về `.github/workflows` root | YAML parse (máy); render ở CI |
| #2 | Một bucket state, partial backend config; key `03-ecr` | `terraform validate` (WSL) |
| #3, #4 | `terraform_remote_state` (02←01, 04←03, 05←01); bỏ `ecr_account_id`, `vpc_id`, `subnet_id` | `terraform validate` (WSL); chưa `plan` |
| #5, #6 | Argo CD chỉ bằng Terraform `helm_release` + chart `argocd-apps` (root app); xoá `idp-gitops/scripts/bootstrap.*` | validate (WSL) |
| #7 | Kyverno/Trivy/kube-bench/compliance app: bỏ `YOUR_ORG`, sửa duplicate `source`/`sources`, pin chart | YAML parse; check-placeholders |
| #8 | Autoscaler `us-east-1`; ServiceAccount + role ARN do Terraform tạo | validate (WSL) |
| #9 | ECR 6 repo gồm `compliance-engine`, `force_delete=false`, giữ 10 image | validate (WSL) |
| #10 | `_build-push.yml` dùng chung; secret `AWS_ROLE_ARN` + `GITOPS_TOKEN` (tuỳ chọn) cho 6 workflow + template | chưa chạy CI |
| #11, #25 | Catalog `argocd/app-name: retail-store-*` | đọc file |
| #12 | Biến node; mặc định 2× t3.large ON_DEMAND (max 3), disk 30GB có hiệu lực | validate (WSL) |
| #13 | `build-backend = setuptools.build_meta` | `pip install -e .[dev]` (máy) |
| #14 | Chọn `create_all`, bỏ Alembic | pytest; DB trắng kiểm ở engine-smoke CI |
| #15 | API nhận `{}`/body rỗng; script gửi `{}` | OpenAPI không còn `required` (máy) |
| #16 | Compose không mount kubeconfig, mặc định fixture mode | đọc file |
| #17 | Secret khỏi Git; key `postgres-user`, `postgres-password`, `gemini-api-key` (optional) | đọc file |
| #18 | PostgreSQL riêng namespace `compliance` | YAML parse |
| #19 | Image engine qua kustomize `images:` (CI ghi) | YAML parse |
| #23 | Backstage một port 7007 | đọc file |
| #24 | Proxy `${COMPLIANCE_ENGINE_URL}/api/v1`, internal LB trong VPC | chưa kiểm chứng (cần AWS) |
| #26 | Template đăng ký trong `catalog/all.yaml` | đọc file |
| 5.1 | `adapters.ts` chuyển đổi contract; recommendation dùng DB id; empty state | `tsc` pass; contract-check (response dựng từ model backend) |
| 5.5 | kube-bench parser dict/list; Trivy dedup/ID có namespace/container/package; kube-bench dùng container kubectl riêng, ConfigMap ra khỏi Git; workload B/C dùng nginx-unprivileged:8080 | pytest (máy); cluster ở GĐ3 |
| Bổ sung | `await load_incluster_config()` → gọi sync | test hồi quy fail trên code cũ |
| Bổ sung | MUI v4 `Box` không có prop `gap` (5 lỗi tsc) | tsc pass |

## Các file đã thay đổi
- `infrastructure/00-bootstrap/*` (mới), `infrastructure/0[1-5]-*/*.tf`, `infrastructure/.tflint.hcl`
- `idp-gitops/argocd/*.yml` (sửa + `experiments-application.yml`, `platform-kyverno-policies-application.yml` mới; xoá `root-application.yml`)
- `idp-gitops/apps/image-registry.yaml` (mới, MANAGED BY CI), `idp-gitops/apps/*/values.yaml`, `idp-gitops/charts/microservice/*`
- `idp-gitops/compliance/compliance-engine/{kustomization,postgres,service-internal-lb}.yaml` (mới), `deployment.yaml`, xoá `secret.yaml`
- `idp-gitops/platform/kube-bench/cronjob.yaml`, xoá `results-configmap.yaml`; `platform/cluster-autoscaler/values.yaml`
- `idp-gitops/experiments/workload-{b,c}-*/deployment.yaml`; xoá secret demo `apps/databases/*/secret.yaml`
- `.github/workflows/*` (mới), xoá `idp-microservices/.github/workflows/*`; `scripts/ci-set-image.sh`
- `compliance-engine/`: `pyproject.toml`, `app/main.py`, `app/config.py`, `app/collector/{aggregator,kubebench,fixtures}.py`, `app/normalizer/mapper.py`, `app/api/routes/scan.py`, `Dockerfile`, `docker-compose.yml`, `fixtures/generate_scenario_abc.py`, `fixtures/scenario-abc/*`, tests; xoá `alembic/`, `alembic.ini`
- `backstage/`: `app-config*.yaml`, `catalog/*.yaml`, `docker-compose.yml`, `.env.example`, `scripts/deploy.sh`, `templates/new-microservice/*`, plugin `src/api/adapters.ts` + client/hooks/components, `tsconfig.{typecheck,contract}.json`, `package-lock.json`
- `.gitattributes` (LF), `.gitignore`

## Ghi chú / Vấn đề còn lại
- Chưa chạy `terraform plan` (cần đồng ý dùng credential AWS). Version chart `argocd-apps 2.0.2`, `kyverno 3.2.6`, `trivy-operator 0.24.1`, benchmark kube-bench `eks-1.2.0` trong image v0.8.0: **chưa kiểm chứng** — CI `helm template`/`helm pull` sẽ bắt chart sai version; benchmark chỉ kiểm được trên EKS.
- Chưa xử lý (ngoài phạm vi đợt này): #20 (truy cập API bằng port-forward — sẽ có trong script), #21 (không có scheduler trong app; dùng CronJob), #22 (Backstage workspace), #27 (Golden Path chưa sinh service chạy được), 5.2 (missing data = 100 điểm), 5.3 (điểm theo workload), 5.4 (≥20 rule, đo AI).
- EIP của Backstage nằm ở lớp tạo-huỷ nên IP/OAuth callback đổi mỗi buổi lab.
- Trust policy OIDC chỉ cho repo monorepo; repo tạo từ template cần thêm vào `github_repo`.
