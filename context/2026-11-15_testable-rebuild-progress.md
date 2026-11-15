# Tiến độ: testable rebuild

**Ngày bắt đầu:** 2026-11-15
**Branch:** `feat/testable-rebuild`
**Plan gốc:** `docs/plans/testable-rebuild.md`

## Đang làm
- Kiểm tra tool local.

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
- [ ] build-backend (#13)
- [ ] Bỏ `await` load_incluster_config
- [ ] Sửa test_engine.py, test_normalize_all_returns_only_valid
- [ ] Migration từ DB trắng (#14)
- [ ] POST /scans có body (#15)
- [ ] Parser kube-bench kiểm kiểu
- [ ] Trivy dedup key / finding ID

### Giai đoạn 0 — Backstage
- [ ] Port/URL (#23)
- [ ] Proxy EC2 → EKS (#24)
- [ ] Đăng ký template (#26)
- [ ] API contract 5.1 + empty state

### Giai đoạn 1
- [ ] `.github/workflows/validate.yml`
- [ ] `scripts/validate-local.sh` chạy pass trên máy

### Giai đoạn 2
- [ ] Collector fixture mode
- [ ] Job `engine-smoke`

### Giai đoạn 3
- [ ] `aws-foundation-up.sh`, `aws-up.sh`, `aws-down.sh`, `smoke.sh` (có `--dry-run`)
- [ ] Chạy thật trên EKS (chờ xác nhận)

### Giai đoạn 4
- [ ] Viết lại `docs/SETUP.md`

## Quyết định đã chốt
(Xem `docs/plans/testable-rebuild.md` mục "Quyết định đã chốt"; quyết định bổ sung ghi dưới đây.)

## Lỗi đang dở
(chưa có)

## Bước tiếp theo
Kiểm tra tool local, hỏi cài tool thiếu.
