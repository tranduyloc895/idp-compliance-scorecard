# Tiến độ: testable rebuild

**Ngày bắt đầu:** 2026-11-15
**Branch:** `feat/testable-rebuild`
**Plan gốc:** `docs/plans/testable-rebuild.md`

## Đang làm
- 2026-11-16: PR #1 đã merge vào `main` (d52d859). Buổi AWS làm trên branch `fix/aws-lab-1`. Đang chờ người dùng xác nhận account trước khi chạy `aws-foundation-up.sh --dry-run`.

## Checklist

### Theo dõi
- [x] Tạo branch, lưu prompt, tạo progress file

### Giai đoạn 0 — Terraform
- [x] Một backend bucket (partial backend config), key `03-ecr` (#2) — validate (WSL)
- [x] `00-bootstrap` tạo state bucket (state local, prevent_destroy) — validate (WSL)
- [x] Tách lớp nền (00, 03, 04 + SSM qua script) / lớp tạo-huỷ (01, 02, 05); tag `Layer` — validate (WSL)
- [x] Nối module bằng `terraform_remote_state` (02←01, 04←03, 05←01) (#3, #4) — validate (WSL); chưa plan với AWS
- [x] ECR `compliance-engine` (#9), `force_delete=false`, giữ 10 image — validate (WSL)
- [x] Biến cấu hình node; mặc định 2× t3.large ON_DEMAND, max 3, disk 30GB (#12) — validate (WSL)

### Giai đoạn 0 — GitOps
- [x] `repoURL`/path toàn bộ Application (#1, #7), sync-wave + health Application — YAML parse (máy); render/kubeconform ở CI
- [x] Autoscaler region + SA do Terraform tạo kèm role ARN (#8)
- [x] Image compliance-engine qua kustomize images (#19); Secret bỏ khỏi Git, key do script tạo (#17)
- [x] `ui` ClusterIP (LB duy nhất: internal LB compliance-engine cho Backstage)
- [x] Catalog `argocd/app-name: retail-store-*` (#11, #25)
- [x] PostgreSQL riêng trong namespace compliance (#18)
- [x] Argo CD chỉ cài bằng Terraform + argocd-apps root (#5); xoá bootstrap.sh/.ps1 (#6)

### Giai đoạn 0 — CI
- [x] Workflow về root `.github/workflows`, path filter, `GITOPS_TOKEN` (tuỳ chọn) + `AWS_ROLE_ARN` (#1, #10) — chưa chạy CI

### Giai đoạn 0 — Compliance engine
- [x] build-backend (#13) — `pip install -e .[dev]` chạy được trên py3.12 (máy)
- [x] Bỏ `await` load_incluster_config — test hồi quy fail trên code cũ, pass trên code mới (máy)
- [x] Sửa test_engine.py, test_normalize_all_returns_only_valid (máy: pytest pass)
- [x] Migration từ DB trắng (#14) — chọn `create_all`, bỏ Alembic (chưa kiểm chứng trên PostgreSQL thật; kiểm ở engine-smoke CI)
- [x] POST /scans có body (#15) — API nhận `{}`/rỗng; script/tài liệu gửi `{}` (SETUP viết lại ở GĐ4)
- [x] Parser kube-bench kiểm kiểu (máy: test dict/list)
- [x] Trivy dedup key / finding ID (máy: test)

### Giai đoạn 0 — Backstage
- [x] Port/URL 7007 (#23)
- [x] Proxy → `${COMPLIANCE_ENGINE_URL}/api/v1` qua internal LB (#24) — chưa kiểm chứng trên AWS
- [x] Đăng ký template trong catalog (#26)
- [x] API contract 5.1 (adapters.ts) + empty state — tsc pass; contract-check với response dựng từ model backend pass (máy); với API thật ở engine-smoke CI

### Giai đoạn 1
- [x] `.github/workflows/validate.yml` — **CI PASS 14/14** ở run 43715994569 (vòng 5)
- [x] `scripts/validate-local.sh` pass trên máy: placeholders, yaml, sh, terraform (WSL), pytest 68 passed, tsc — tổng 32s

### Giai đoạn 2
- [x] Collector fixture mode (`COLLECTOR_MODE=fixtures`, fixtures/scenario-abc) (máy: test)
- [x] Job `engine-smoke` + `contract-check.mjs` — PASS trong CI (scan=1, 34 findings, score 35.31 poor cho toàn bộ fixture A+B+C; rule WS-004; contract-check OK)

### Giai đoạn 3
- [x] `aws-foundation-up.sh`, `aws-up.sh`, `aws-down.sh`, `smoke.sh` (có `--dry-run`) — bash -n + dry-run không credential (máy); chưa chạy với AWS
- [x] Tool trong WSL (2026-11-16, `scripts/wsl-tools.sh`): terraform 1.11.4, tflint 0.53.0, kubectl v1.35.0 (sha256 OK), aws-cli 2.22.0 ở `~/tools/bin`; PATH thêm vào `~/.bashrc`. AWS profile `idp` (us-east-1) do người dùng cấu hình trong WSL; STS 2026-11-16: account 736508008585, `arn:aws:iam::736508008585:user/idp`.
- [x] Lớp nền trên AWS (2026-11-16, `aws-foundation-up.sh`, 174s) — kiểm bằng `aws iam get-role`, `ecr describe-repositories`, `s3 ls`, `ssm get-parameters-by-path`
- [ ] Chạy thật trên EKS (chờ xác nhận: push branch → CI; merge main; dùng credential AWS)

### Giai đoạn 4
- [x] Viết lại `docs/SETUP.md` (troubleshooting mới có lỗi local; bổ sung lỗi AWS sau lần chạy đầu)

## Quyết định đã chốt
(Xem `docs/plans/testable-rebuild.md` mục "Quyết định đã chốt"; quyết định bổ sung ghi dưới đây.)

- **Tool local** (2026-11-15, được đồng ý): terraform 1.11.4 (`use_lockfile` của S3 backend cần ≥1.10), tflint 0.53.0, node 20.18.0, gh 2.62.0, aws-cli 2.22.0 (giải nén MSI) trong `C:/tools/*`. Python 3.12.10 có sẵn ở `C:/tools/python`. PATH (Git Bash): `/c/tools/terraform:/c/tools/tflint:/c/tools/node:/c/tools/gh/bin:/c/tools/awscli/Amazon/AWSCLIV2`.
- **Schema DB**: dùng `Base.metadata.create_all` lúc startup, bỏ Alembic. Lý do: migration duy nhất tham chiếu bảng `scans` chưa tồn tại, startup đã dùng create_all; một cơ chế idempotent là đủ cho khóa luận. Đổi schema sau này thì cần thêm Alembic lại có baseline.
- **Compose local**: mặc định fixture mode, không mount kubeconfig (image không có AWS CLI cho EKS exec credential, #16).
- **Terraform trên Windows**: Application Control chặn `terraform-provider-*.exe`. Người dùng chọn chạy `terraform validate`/`tflint` trong WSL Ubuntu-22.04 (`~/tools/bin`: terraform 1.11.4, tflint 0.53.0). `scripts/terraform-validate.sh` dùng chung cho WSL và CI.
- **Backend**: một bucket `idp-tfstate-<account>-us-east-1` (tên mặc định của 00-bootstrap), truyền qua `-backend-config=bucket=...` và `TF_VAR_state_bucket` — không ghi cứng account ID.
- **SSM**: secret do script `aws ssm put-parameter` nạp (SecureString, prefix `/idp`), không quản lý bằng Terraform để giá trị không nằm trong state.
- **Image registry/tag**: account ID chỉ xuất hiện ở 2 file "MANAGED BY CI" (`idp-gitops/apps/image-registry.yaml`, `idp-gitops/compliance/compliance-engine/kustomization.yaml`), do `scripts/ci-set-image.sh` ghi. Giá trị khởi đầu `ECR_REGISTRY_NOT_SET` / `not-built`; aws-up preflight phải dừng nếu chưa chạy `build-all`.
- **Secret vào cluster**: script `kubectl create secret` từ SSM (không dùng External Secrets Operator). Lý do: không thêm operator/CRD/IRSA, ít thành phần hỏng hơn cho lab tạo-huỷ; Argo CD không quản lý các Secret này nên không ghi đè. Secret demo của catalog-mysql/orders-postgres cũng chuyển ra khỏi Git.
- **Đường Backstage EC2 → engine**: Service `compliance-engine-internal` type LoadBalancer internal (Classic ELB của legacy cloud provider, không cần AWS LB Controller). Đây là LB duy nhất; aws-down xoá trước khi destroy VPC.
- **Backstage EC2 mặc định không dựng trong aws-up** (cần `--with-backstage`): repo chưa có `packages/app`, `packages/backend` (audit #22) nên image Backstage chưa build được.
- **kubectl/helm**: không cài trên Windows. Script AWS chạy trong AWS CloudShell hoặc Linux; nếu có Docker thì gọi kubectl qua image.
- **kubectl cho buổi AWS** (2026-11-15, người dùng chốt): cài kubectl v1.35.0 vào `~/tools/bin` trong WSL Ubuntu-22.04 (không cài trên Windows); script AWS chạy trong WSL với `AWS_PROFILE=idp`.
- **Line endings**: `.gitattributes` ép LF (trừ `.ps1`) để script chạy được trên Linux/CI.

## Lỗi đang dở
(không có)

## Kết quả CI (2026-11-15, branch feat/testable-rebuild)
| Vòng | Run | Kết quả | Lỗi tìm được → sửa |
|---|---|---|---|
| 1 | 43714705374 | 10/14 | `import app.models` ghi đè `app` trong lifespan (API không start); `disallow-latest-tag` dùng foreach nên không autogen; overlay `environments/dev` rỗng; `actions/cache@v4.1.2` bị chặn |
| 2 | 43715177717 | 13/14 | nối manifest không có newline (lỗi script) |
| 3 | 43715401370 | 13/14 | values Kyverno `crds.groups.*: true` sai kiểu → chart không render (lỗi thật, sẽ chặn Argo CD) |
| 4 | 43715681311 | 13/14 | kubeconform -strict từ chối RoleBinding của chính chart kyverno → chỉ strict cho manifest repo |
| 5 | 43715994569 | **14/14** | — repo 88/88 hợp lệ; upstream 277 hợp lệ, 18 bỏ qua (thiếu schema CRD); 12 image bên thứ ba tồn tại; 9 chart version tồn tại |


## Bước tiếp theo
0. Buổi sau bắt đầu bằng prompt `docs/plans/aws-session-prompt.md`.
1. Người dùng review và merge PR vào `main` (hỏi trước khi merge; không tự merge). Sau merge, kiểm CI trên `main` xanh.
2. Khi được đồng ý dùng credential AWS: trong CloudShell `bash scripts/cloudshell-tools.sh`, rồi `bash scripts/aws-foundation-up.sh --dry-run` → chạy thật → đặt GitHub secret `AWS_ROLE_ARN` (+ Workflow permissions Read and write) → chạy workflow `build-all` trên `main`.
3. `bash scripts/aws-up.sh --dry-run` → aws-up → smoke → sửa lỗi → **luôn** `aws-down`; ghi tiến độ vào file này trước mỗi lệnh tốn tiền.
4. Chưa kiểm chứng (sẽ thấy ở bước 3): chart 2024 trên K8s 1.35, internal CLB, `kube-bench v0.8.0 --benchmark eks-1.2.0`, image `cluster-autoscaler v1.35.0`, đủ tài nguyên 2× t3.large.

## CI trên main sau merge (2026-11-16)
| Workflow | Run | Kết quả | Nguyên nhân |
|---|---|---|---|
| validate | 43791263227 | pass | — |
| CI — ui/cart/catalog/orders/checkout/compliance-engine | 43791263217 … 43791263366 | fail ở "Set up job" (4–8s) | `aquasecurity/trivy-action@0.28.0` không resolve được (không phải lỗi thiếu `AWS_ROLE_ARN` như dự đoán). Chặn `build-all`; cần sửa ref action trong `_build-push.yml` trước khi chạy build-all. |

Ghi chú: commit `wsl-tools.sh` (e886670) không vào được PR #1 (push sau khi merge) → cherry-pick sang `fix/aws-lab-1`.

## Nhật ký lệnh AWS (buổi 2026-11-16)
| Thời điểm (UTC) | Lệnh | Tạo gì | Chi phí ước tính | Kết quả |
|---|---|---|---|---|
| 2026-11-16 02:46 | `aws-foundation-up.sh --dry-run` (WSL, AWS_PROFILE=idp) | không | 0 | exit 0; 00-bootstrap plan 5 add/0/0; 03/04 chưa plan được (chưa có bucket); SSM would put 5 |
| 2026-11-16 02:50 | `aws-foundation-up.sh --yes` (người dùng chọn chạy full) | S3 state bucket, 6 ECR repo, GitHub OIDC provider + IAM role CI, 5 SSM SecureString | < $0.01/tháng (S3) + ECR $0.10/GB-tháng khi có image; OIDC/IAM/SSM $0 | **exit 0, 174s**: 00-bootstrap 5 add, 03-ecr 12 add, 04-oidc 3 add; SSM put 5 (generated) |

## Output lớp nền (2026-11-16, không chứa secret)
- State bucket: `idp-tfstate-736508008585-us-east-1` (state 03-ecr, 04-oidc trong bucket; state 00-bootstrap **chỉ ở local** `infrastructure/00-bootstrap/terraform.tfstate`, git ignore — mất file thì script tự import lại)
- ECR registry: `736508008585.dkr.ecr.us-east-1.amazonaws.com` — 6 repo `retail-store/{ui,cart,catalog,orders,checkout,compliance-engine}`, MUTABLE
- CI role ARN: `arn:aws:iam::736508008585:role/github-actions-idp-compliance-scorecard`; trust: OIDC `token.actions.githubusercontent.com`, aud `sts.amazonaws.com`, sub `repo:tranduyloc895/idp-compliance-scorecard:*` (mọi branch/PR của repo)
- SSM `/idp/...`: 5 SecureString tự sinh (postgres-password, catalog-db-password, catalog-db-root-password, orders-db-password, grafana-admin-password); chưa có gemini-api-key, telegram-bot-token

## Bước tiếp theo (cập nhật 2026-11-16)
1. [x] Sửa ref trivy-action → SHA v0.36.0 (commit b058f7b), PR `fix/aws-lab-1` → main.
2. [x] 2026-11-16 03:17 UTC: `gh secret set AWS_ROLE_ARN` (người dùng đồng ý) = role ARN CI. Workflow permissions mặc định của repo = `read`, **không cần đổi**: `_build-push.yml`/`build-all.yml`/`ci-*.yml` khai báo `permissions: contents: write, id-token: write, security-events: write` ở cấp workflow (repo cá nhân, không có giới hạn org). `main` không có branch protection/ruleset nên `GITHUB_TOKEN` push được commit tag.
3. Merge fix vào main (hỏi), rồi chạy `build-all` trên main (hỏi).

## CI build trên main sau merge PR #2 (2026-11-16 03:20 UTC)
- Merge PR #2 tự kích hoạt 6 workflow `CI — *` (path filter có `_build-push.yml`); người dùng đồng ý cho chạy thay `build-all`.
- Kết quả: cả 6 qua *Set up job* (fix trivy-action OK) nhưng fail ở `Configure AWS credentials (OIDC)`: `Not authorized to perform sts:AssumeRoleWithWebIdentity`. Không có image nào lên ECR, không có commit nào của CI vào main.
- Nguyên nhân: repo bật **immutable subject** (`use_immutable_subject: true`), `sub` = `repo:tranduyloc895@141894428/idp-compliance-scorecard@1405539355:...`; trust policy chỉ có `repo:tranduyloc895/idp-compliance-scorecard:*`.
- Sửa (branch `fix/aws-lab-2`): `04-oidc` thêm `github_owner_id`/`github_repo_id`, `sub` StringLike nhận cả hai dạng. `terraform plan 04-oidc`: 0 add, 1 change (assume_role_policy), 0 destroy. validate-local PASS.

## Bước tiếp theo (cập nhật 2026-11-16 03:25)
1. 2026-11-16 03:27 UTC: người dùng đồng ý → `terraform apply 04-oidc` (WSL, AWS_PROFILE=idp; chỉ đổi assume_role_policy, $0) — **xong**: 0 add, 1 change, 0 destroy; `aws iam get-role` xác nhận sub có cả hai dạng.
2. 2026-11-16 03:29 UTC: người dùng đồng ý → `gh workflow run build-all --ref main` (6 image → Trivy gate → push ECR → CI commit tag vào main). Chi phí: ECR ~$0.10/GB-tháng (ước tính 1–2 GB) + phút GitHub Actions (repo public, miễn phí) — **xong, run 43798460094: 1/6 pass**.
3. Merge PR `fix/aws-lab-2` (hỏi).

## Kết quả build-all lần 1 (run 43798460094, 2026-11-16 03:26–03:31 UTC)
- OIDC/ECR login OK cho cả 6 (fix 04-oidc có hiệu lực).
- `compliance-engine`: pass Trivy gate → push `retail-store/compliance-engine:f71fced` (~98 MB) → CI commit `98dff48` vào main (kustomization.yaml).
- 5 service Retail Store **bị Trivy gate chặn** (CRITICAL có bản sửa; Trivy v0.70.0 qua trivy-action v0.36.0). Không push, không commit tag:
  | Service | CRITICAL | Gói chính (cài → bản sửa) |
  |---|---|---|
  | ui (Java, Boot 3.5.5) | 9 | netty-handler 4.1.124 → 4.1.137; spring-webflux 6.2.10 → **chỉ có 7.0.9**; thymeleaf(+spring6) 3.1.3 → 3.1.5 |
  | cart (Java, Boot 3.5.5) | 10 | netty-handler; tomcat-embed-core 10.1.44 → 10.1.58; spring-webmvc 6.2.10 → **chỉ có 7.0.9** |
  | orders (Java, Boot 3.5.5) | 10 | như cart |
  | catalog (Go) | 1 | google.golang.org/grpc v1.73.0 (indirect) → 1.79.3 |
  | checkout (Node) | 6 | form-data 2.3.3, protobufjs 7.4.0, proxy-addr 2.0.7, tar 7.5.7 (+2) |
- CVE của Spring Framework chỉ có bản sửa ở 7.0.x → cần Spring Boot 4 (đổi major). Chờ người dùng chọn hướng xử lý.
- **Quyết định (2026-11-16, người dùng chọn):** Trivy gate **report-only** cho 5 service Retail Store (`trivy_gate: false` trong `ci-{ui,cart,catalog,orders,checkout}.yml` và matrix `build-all`); `compliance-engine` và template Golden Path vẫn gate. Lý do: code mẫu upstream, CVE Spring 6.2 chỉ sửa ở 7.x (cần Spring Boot 4, ngoài phạm vi); CVE còn lại thành dữ liệu thật cho miền Supply Chain qua Trivy Operator. SARIF vẫn upload.

## Bước tiếp theo (cập nhật 2026-11-16)
1. PR `fix/aws-lab-2` → main (OIDC immutable subject + Trivy report-only). Hỏi trước khi merge. Lưu ý: merge sửa `_build-push.yml` nên **tự kích hoạt 6 workflow `CI — *`** trên main (tương đương build-all) → theo dõi tới khi 6 image lên ECR và tag được commit.
2. Kiểm `image-registry.yaml` + tag 5 service trong main; `aws-up.sh --dry-run`.
