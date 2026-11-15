#!/usr/bin/env bash
# Dựng LỚP NỀN (chạy một lần, idempotent, chi phí gần 0):
#   00-bootstrap (S3 state bucket) -> 03-ecr (6 repo) -> 04-oidc (GitHub OIDC + role CI)
#   -> SSM Parameter Store (secret)
#
#   bash scripts/aws-foundation-up.sh [--dry-run] [--yes]
#
# --dry-run: chỉ terraform plan + liệt kê SSM sẽ tạo; không tạo gì.
# Không bao giờ destroy lớp nền (bucket có prevent_destroy, ECR force_delete=false).
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
parse_common_flags "$@"
init_aws_context

log "=== Foundation layer (dry-run=$DRY_RUN) ==="
confirm "Tạo/cập nhật lớp nền trong account $ACCOUNT_ID ($AWS_REGION)?"

# 1. State bucket (state local trong infrastructure/00-bootstrap)
tf_init 00-bootstrap
if state_bucket_exists && ! tf 00-bootstrap state list 2>/dev/null | grep -q aws_s3_bucket.tfstate; then
  if [ "$DRY_RUN" = "1" ]; then
    warn "Bucket $TF_STATE_BUCKET đã tồn tại nhưng state local không có — lần chạy thật sẽ import."
  else
    log "Bucket đã tồn tại, import vào state local"
    for r in aws_s3_bucket.tfstate aws_s3_bucket_versioning.tfstate \
             aws_s3_bucket_server_side_encryption_configuration.tfstate \
             aws_s3_bucket_public_access_block.tfstate aws_s3_bucket_lifecycle_configuration.tfstate; do
      tf 00-bootstrap import -input=false -no-color "$r" "$TF_STATE_BUCKET" || warn "import $r thất bại (có thể chưa tồn tại)"
    done
  fi
fi
tf_apply_or_plan 00-bootstrap

if [ "$DRY_RUN" = "1" ] && ! state_bucket_exists; then
  warn "Dry-run: bucket chưa có nên không plan được 03-ecr/04-oidc (backend S3). Chạy thật sẽ tạo theo thứ tự."
  bash "$ROOT/scripts/ssm-put-secrets.sh" --dry-run
  exit 0
fi

# 2. ECR
tf_apply_or_plan 03-ecr

# 3. GitHub OIDC + IAM role cho CI (đọc ARN repo ECR qua remote state)
if [ "$DRY_RUN" = "1" ] && ! state_exists 03-ecr; then
  warn "Dry-run: 03-ecr chưa có state nên bỏ qua plan 04-oidc."
else
  extra=()
  if aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[].Arn' --output text \
      | grep -q 'token.actions.githubusercontent.com' \
     && ! { tf_init 04-oidc && tf 04-oidc state list 2>/dev/null | grep -q 'aws_iam_openid_connect_provider.github'; }; then
    log "Account đã có GitHub OIDC provider (không do module quản lý) -> create_oidc_provider=false"
    extra+=(-var create_oidc_provider=false)
  fi
  tf_apply_or_plan 04-oidc "${extra[@]}"
fi

# 4. Secret
bash "$ROOT/scripts/ssm-put-secrets.sh" $([ "$DRY_RUN" = "1" ] && echo --dry-run)

if [ "$DRY_RUN" != "1" ]; then
  role_arn="$(tf_output 04-oidc role_arn || true)"
  cat <<EOF

=== Lớp nền xong ===
State bucket : $TF_STATE_BUCKET
ECR registry : $(tf_output 03-ecr registry || echo '?')
CI role ARN  : ${role_arn:-?}

Việc còn lại (thủ công, một lần):
  1. GitHub repo -> Settings -> Secrets and variables -> Actions:
       AWS_ROLE_ARN = ${role_arn:-<output role_arn của 04-oidc>}
     (GITOPS_TOKEN tuỳ chọn; không đặt thì CI dùng GITHUB_TOKEN, cần
      Settings -> Actions -> Workflow permissions = Read and write)
  2. Chạy workflow "build-all" trên nhánh mà Argo CD theo dõi (mặc định main)
     để build/push 6 image và ghi tag vào idp-gitops.
  3. Sau đó: bash scripts/aws-up.sh --dry-run, rồi aws-up.sh.
EOF
fi
