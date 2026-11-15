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
- [ ] Một backend bucket, key `03-ecr` (#2)
- [ ] `00-bootstrap` tạo state bucket
- [ ] Tách lớp nền (bootstrap, ECR, OIDC, SSM) / lớp tạo-huỷ (network, EKS, Backstage EC2)
- [ ] Nối module bằng `terraform_remote_state`, sửa output (#3), input (#4)
- [ ] ECR `compliance-engine` (#9), `force_delete=false`, lifecycle
- [ ] Biến cấu hình node (instance type, số node, capacity type) (#12)

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
- [ ] POST /scans có body (#15)
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

- **Tool local** (2026-11-15, được đồng ý): terraform 1.11.4 (`use_lockfile` của S3 backend cần ≥1.10), tflint 0.53.0, node 20.18.0, gh 2.62.0, aws-cli 2.22.0 (giải nén MSI) trong `C:	ools\*`. Python 3.12.10 có sẵn ở `C:	ools\python`. PATH: `C:	ools	erraform;C:	ools	flint;C:	ools
ode;C:	ools\ghin;C:	oolswscli\Amazon\AWSCLIV2`.
- **Schema DB**: dùng `Base.metadata.create_all` lúc startup, bỏ Alembic. Lý do: migration duy nhất tham chiếu bảng `scans` chưa tồn tại, startup đã dùng create_all; một cơ chế idempotent là đủ cho khóa luận. Đổi schema sau này thì cần thêm Alembic lại có baseline.
- **Compose local**: mặc định fixture mode, không mount kubeconfig (image không có AWS CLI cho EKS exec credential, #16).
- **Line endings**: `.gitattributes` ép LF (trừ `.ps1`) để script chạy được trên Linux/CI.

## Lỗi đang dở
(chưa có)

## Bước tiếp theo
Kiểm tra tool local, hỏi cài tool thiếu.
