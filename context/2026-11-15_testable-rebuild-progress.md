# Tiến độ: testable rebuild

**Ngày bắt đầu:** 2026-11-15
**Branch:** `feat/testable-rebuild`
**Plan gốc:** `docs/plans/testable-rebuild.md`

## Đang làm
- Giai đoạn 0: compliance engine xong phần lớn; tiếp theo POST /scans body (#15), Terraform.

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
- [ ] `repoURL`/path toàn bộ Application (#1, #7), sync-wave
- [ ] Autoscaler region + role ARN (#8)
- [ ] Image compliance-engine (#19), secret key (#17)
- [ ] `ui` ClusterIP
- [ ] Tên Application khớp catalog (#11, #25)
- [ ] PostgreSQL cho compliance engine (#18)
- [ ] Argo CD chỉ cài bằng Terraform (#5), bỏ bootstrap cài Argo CD

### Giai đoạn 0 — CI
- [ ] Workflow về root `.github/workflows`, path filter, một tên secret GitOps (#1, #10)

### Giai đoạn 0 — Compliance engine
- [x] build-backend (#13) — `pip install -e .[dev]` chạy được trên py3.12 (máy)
- [x] Bỏ `await` load_incluster_config — test hồi quy fail trên code cũ, pass trên code mới (máy)
- [x] Sửa test_engine.py, test_normalize_all_returns_only_valid (máy: pytest pass)
- [x] Migration từ DB trắng (#14) — chọn `create_all`, bỏ Alembic (chưa kiểm chứng trên PostgreSQL thật; kiểm ở engine-smoke CI)
- [x] POST /scans có body (#15) — API nhận `{}`/rỗng; script/tài liệu gửi `{}` (SETUP viết lại ở GĐ4)
- [x] Parser kube-bench kiểm kiểu (máy: test dict/list)
- [x] Trivy dedup key / finding ID (máy: test)

### Giai đoạn 0 — Backstage
- [ ] Port/URL (#23)
- [ ] Proxy EC2 → EKS (#24)
- [ ] Đăng ký template (#26)
- [ ] API contract 5.1 + empty state

### Giai đoạn 1
- [ ] `.github/workflows/validate.yml`
- [ ] `scripts/validate-local.sh` chạy pass trên máy

### Giai đoạn 2
- [x] Collector fixture mode (`COLLECTOR_MODE=fixtures`, fixtures/scenario-abc) (máy: test)
- [ ] Job `engine-smoke`

### Giai đoạn 3
- [ ] `aws-foundation-up.sh`, `aws-up.sh`, `aws-down.sh`, `smoke.sh` (có `--dry-run`)
- [ ] Chạy thật trên EKS (chờ xác nhận)

### Giai đoạn 4
- [ ] Viết lại `docs/SETUP.md`

## Quyết định đã chốt
(Xem `docs/plans/testable-rebuild.md` mục "Quyết định đã chốt"; quyết định bổ sung ghi dưới đây.)

- **Tool local** (2026-11-15, được đồng ý): terraform 1.11.4 (`use_lockfile` của S3 backend cần ≥1.10), tflint 0.53.0, node 20.18.0, gh 2.62.0, aws-cli 2.22.0 (giải nén MSI) trong `C:/tools/*`. Python 3.12.10 có sẵn ở `C:/tools/python`. PATH (Git Bash): `/c/tools/terraform:/c/tools/tflint:/c/tools/node:/c/tools/gh/bin:/c/tools/awscli/Amazon/AWSCLIV2`.
- **Schema DB**: dùng `Base.metadata.create_all` lúc startup, bỏ Alembic. Lý do: migration duy nhất tham chiếu bảng `scans` chưa tồn tại, startup đã dùng create_all; một cơ chế idempotent là đủ cho khóa luận. Đổi schema sau này thì cần thêm Alembic lại có baseline.
- **Compose local**: mặc định fixture mode, không mount kubeconfig (image không có AWS CLI cho EKS exec credential, #16).
- **Terraform trên Windows**: Application Control chặn `terraform-provider-*.exe`. Người dùng chọn chạy `terraform validate`/`tflint` trong WSL Ubuntu-22.04 (`~/tools/bin`: terraform 1.11.4, tflint 0.53.0). `scripts/terraform-validate.sh` dùng chung cho WSL và CI.
- **Backend**: một bucket `idp-tfstate-<account>-us-east-1` (tên mặc định của 00-bootstrap), truyền qua `-backend-config=bucket=...` và `TF_VAR_state_bucket` — không ghi cứng account ID.
- **SSM**: secret do script `aws ssm put-parameter` nạp (SecureString, prefix `/idp`), không quản lý bằng Terraform để giá trị không nằm trong state.
- **Line endings**: `.gitattributes` ép LF (trừ `.ps1`) để script chạy được trên Linux/CI.

## Lỗi đang dở
(chưa có)

## Bước tiếp theo
Giai đoạn 0 — GitOps: repoURL/path, chart image.registry, secret, PostgreSQL, experiments app.
