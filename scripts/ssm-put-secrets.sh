#!/usr/bin/env bash
# Nạp secret vào SSM Parameter Store (SecureString) — lớp NỀN, chạy một lần.
#
#   bash scripts/ssm-put-secrets.sh [--dry-run] [--overwrite]
#
# Giá trị lấy theo thứ tự: biến môi trường -> scripts/secrets.env (git ignore,
# xem scripts/secrets.env.example) -> tự sinh ngẫu nhiên (chỉ với mật khẩu).
# Tham số đã có trong SSM được giữ nguyên trừ khi --overwrite.
# Giá trị KHÔNG đi qua Terraform nên không nằm trong state.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
parse_common_flags "$@"
OVERWRITE=0
for a in "$@"; do [ "$a" = "--overwrite" ] && OVERWRITE=1; done

[ -f "$ROOT/scripts/secrets.env" ] && { set -a; source "$ROOT/scripts/secrets.env"; set +a; }
init_aws_context

gen() { head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-24; }

# name | env var | required(generate if missing: gen / optional: skip)
PARAMS=(
  "compliance/postgres-password|COMPLIANCE_POSTGRES_PASSWORD|gen"
  "compliance/gemini-api-key|GEMINI_API_KEY|optional"
  "retail/catalog-db-password|CATALOG_DB_PASSWORD|gen"
  "retail/catalog-db-root-password|CATALOG_DB_ROOT_PASSWORD|gen"
  "retail/orders-db-password|ORDERS_DB_PASSWORD|gen"
  "monitoring/grafana-admin-password|GRAFANA_ADMIN_PASSWORD|gen"
  "monitoring/telegram-bot-token|TELEGRAM_BOT_TOKEN|optional"
)

for entry in "${PARAMS[@]}"; do
  IFS='|' read -r name var mode <<< "$entry"
  full="$SSM_PREFIX/$name"
  exists=0
  aws ssm get-parameter --name "$full" >/dev/null 2>&1 && exists=1
  if [ "$exists" = "1" ] && [ "$OVERWRITE" = "0" ]; then
    log "keep   $full (đã có)"
    continue
  fi
  value="${!var:-}"
  if [ -z "$value" ]; then
    if [ "$mode" = "gen" ]; then value="$(gen)"; src="generated"; else log "skip   $full (tuỳ chọn, chưa đặt $var)"; continue; fi
  else
    src="from \$$var"
  fi
  if [ "$DRY_RUN" = "1" ]; then
    log "would put $full ($src)"
    continue
  fi
  aws ssm put-parameter --name "$full" --type SecureString --value "$value" --overwrite >/dev/null
  log "put    $full ($src)"
done
log "SSM xong. Xem: aws ssm get-parameters-by-path --path $SSM_PREFIX --recursive --query 'Parameters[].Name'"
