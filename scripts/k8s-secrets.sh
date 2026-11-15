#!/usr/bin/env bash
# Tạo Kubernetes Secret từ SSM Parameter Store (aws-up bước 2).
#
#   bash scripts/k8s-secrets.sh [--dry-run]
#
# Quyết định #4: script thay cho External Secrets Operator (ít thành phần hơn
# cho lab tạo-huỷ). Các Secret này KHÔNG nằm trong Git nên Argo CD không sync
# đè. Key khớp với Deployment (audit #17). Idempotent (apply).
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
parse_common_flags "$@"
init_aws_context

if [ "$DRY_RUN" = "1" ]; then
  for p in compliance/postgres-password compliance/gemini-api-key retail/catalog-db-password \
           retail/catalog-db-root-password retail/orders-db-password monitoring/grafana-admin-password \
           monitoring/telegram-bot-token; do
    if aws ssm get-parameter --name "$SSM_PREFIX/$p" >/dev/null 2>&1; then log "ssm ok      $SSM_PREFIX/$p"; else warn "ssm missing $SSM_PREFIX/$p"; fi
  done
  log "dry-run: không tạo Secret"
  exit 0
fi

init_kubectl

req() { local v; v="$(ssm_get "$1")"; [ -n "$v" ] || die "Thiếu SSM $SSM_PREFIX/$1 — chạy scripts/ssm-put-secrets.sh"; printf '%s' "$v"; }

TMP="$(mktemp -d)"; chmod 700 "$TMP"; trap 'rm -rf "$TMP"' EXIT

apply_secret() { # apply_secret <namespace> <name> key=value...
  local ns="$1" name="$2"; shift 2
  local envf="$TMP/$ns-$name.env"
  : > "$envf"
  for kv in "$@"; do printf '%s\n' "$kv" >> "$envf"; done
  kc create namespace "$ns" --dry-run=client -o yaml | kc apply -f - >/dev/null
  # --from-env-file: giá trị không xuất hiện trên command line
  if [ "$KC_MODE" = "docker" ]; then
    kc create secret generic "$name" -n "$ns" --from-env-file=/dev/stdin --dry-run=client -o yaml < "$envf" | kc apply -f - >/dev/null
  else
    kc create secret generic "$name" -n "$ns" --from-env-file="$envf" --dry-run=client -o yaml | kc apply -f - >/dev/null
  fi
  log "secret $ns/$name"
}

gemini="$(ssm_get compliance/gemini-api-key)"
telegram="$(ssm_get monitoring/telegram-bot-token)"

engine_kv=("postgres-user=compliance" "postgres-password=$(req compliance/postgres-password)")
[ -n "$gemini" ] && engine_kv+=("gemini-api-key=$gemini")
apply_secret compliance compliance-engine-secrets "${engine_kv[@]}"

apply_secret retail-store catalog-mysql-secret \
  "password=$(req retail/catalog-db-password)" "root-password=$(req retail/catalog-db-root-password)"
apply_secret retail-store orders-postgres-secret "password=$(req retail/orders-db-password)"

apply_secret monitoring grafana-admin "admin-user=admin" "admin-password=$(req monitoring/grafana-admin-password)"
# Alertmanager mount secret này; thiếu thì Pod không chạy. Không có token -> giá trị giả.
apply_secret monitoring telegram-alertmanager-secret "bot-token=${telegram:-disabled}"

log "k8s-secrets: OK"
