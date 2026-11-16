# Buổi AWS 1: lớp nền trên AWS, sửa ref trivy-action và validate sau apply

**Ngày:** 2026-11-16
**Thành phần:** infrastructure, other (CI, scripts), docs
**Loại:** fix

## Mô tả
- Lớp nền đã tạo trên account 736508008585 (us-east-1) bằng `aws-foundation-up.sh --yes` (WSL, `AWS_PROFILE=idp`), 174s: 00-bootstrap 5 add, 03-ecr 12 add, 04-oidc 3 add, SSM 5 SecureString. Output trong `context/2026-11-15_testable-rebuild-progress.md`.
- CI trên `main` sau khi merge PR #1: 6 workflow build fail ở *Set up job* vì `aquasecurity/trivy-action@0.28.0` không resolve được (tag không có tiền tố `v` đã bị xoá; tag được tạo lại ngày 2026-03-20). Đây không phải lỗi thiếu `AWS_ROLE_ARN` như dự đoán. Sửa: pin theo SHA `ed142fd0673e97e23eac54620cfb913e5ce36c25` (v0.36.0, commit verified, nằm trên master). Đã đối chiếu các input đang dùng (`image-ref`, `format`, `severity`, `exit-code`, `ignore-unfixed`, `vuln-type`, `output`, `skip-setup-trivy`) có trong `action.yaml` v0.36.0. Mọi `uses:` khác trong `.github/workflows` đều resolve được (kiểm bằng `gh api .../git/ref/tags/<ver>`).
- `terraform-validate.sh` fail ở 03-ecr/04-oidc sau khi apply thật (`.terraform/` đã init backend S3 nên `init -backend=false` vẫn đòi credential). Sửa: `TF_DATA_DIR` riêng trong `/tmp/tf-validate/<module>`.
- Commit `wsl-tools.sh` (e886670) push sau khi PR #1 merge nên không vào main → cherry-pick sang `fix/aws-lab-1`. Tên profile AWS đổi từ `idp-lab` thành `idp` trong prompt và progress file.

## Các file đã thay đổi
- `.github/workflows/_build-push.yml`, `backstage/templates/new-microservice/skeleton/.github/workflows/ci.yml`
- `scripts/terraform-validate.sh`, `scripts/wsl-tools.sh` (cherry-pick)
- `docs/SETUP.md` (Troubleshooting), `docs/plans/aws-session-prompt.md`, `context/2026-11-15_testable-rebuild-progress.md`

## Ghi chú / Vấn đề còn lại
- Kiểm chứng: `validate-local.sh` PASS trên máy (terraform 47s qua WSL, pytest 69 passed, tsc). Workflow build chỉ kiểm được khi chạy thật (cần `AWS_ROLE_ARN`).
- trivy-action v0.36.0 mặc định cài Trivy v0.70.0 (trước đây ~0.56); DB lỗ hổng mới hơn nên gate CRITICAL có thể chặn image Retail Store.
- State `00-bootstrap` chỉ nằm ở local (`infrastructure/00-bootstrap/terraform.tfstate`, git ignore).
- Trust policy role CI cho mọi ref của repo (`repo:tranduyloc895/idp-compliance-scorecard:*`).

## Cập nhật 03:25 UTC — OIDC immutable subject
- CI build trên main (sau merge PR #2) fail ở `Configure AWS credentials`: repo bật immutable subject nên claim `sub` có owner/repo ID; trust policy không khớp. Sửa `infrastructure/04-oidc/{main,variables}.tf` nhận cả hai dạng `sub`; plan 0/1/0. Chưa apply.
