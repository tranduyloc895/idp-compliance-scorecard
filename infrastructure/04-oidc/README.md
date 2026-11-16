# 04-oidc — GitHub Actions OIDC

Tạo (hoặc dùng lại, `create_oidc_provider=false`) OIDC provider `token.actions.githubusercontent.com` và IAM role cho repo `tranduyloc895/idp-compliance-scorecard`. Quyền push/pull chỉ trên các repo ECR do `03-ecr` tạo (đọc qua `terraform_remote_state`). Output `role_arn` → GitHub secret `AWS_ROLE_ARN`.

Chạy qua `scripts/aws-foundation-up.sh` (xem `docs/SETUP.md`).
