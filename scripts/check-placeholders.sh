#!/usr/bin/env bash
# Chặn placeholder và giá trị ghi cứng: YOUR_ORG, YOUR_ECR_REGISTRY, CHANGE_ME,
# region ap-southeast-1, AWS account ID 12 chữ số (trong ARN hoặc ECR host).
#
# Ngoại lệ có chủ đích:
#  - Tài liệu ghi lại lịch sử/yêu cầu (audit, plan, context log) — mô tả chính các lỗi này.
#  - File "MANAGED BY CI": dòng ECR registry do workflow ghi (quyết định #5).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EXCLUDES=(
  ':(exclude)docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md'
  ':(exclude)docs/plans/**'
  ':(exclude)context/**'
  ':(exclude)scripts/check-placeholders.sh'
  ':(exclude)idp-microservices/src/**'
  ':(exclude)**/package-lock.json'
)

fail=0
report() {
  local label="$1" pattern="$2"
  local out
  out="$(git grep --untracked -nIE "$pattern" -- . "${EXCLUDES[@]}" || true)"
  if [ -n "$out" ]; then
    echo "FAIL: $label"
    echo "$out" | sed 's/^/    /'
    fail=1
  else
    echo "ok   $label"
  fi
}

report "YOUR_ORG / YOUR_ECR_REGISTRY placeholder" 'YOUR_ORG|YOUR_ECR_REGISTRY'
report "CHANGE_ME placeholder"                     'CHANGE_ME'
report "region ap-southeast-1 (dự án dùng us-east-1)" 'ap-southeast-1'

# Account ID: arn:aws:<svc>:<region>:<12 digits>: hoặc <12 digits>.dkr.ecr.
acct_out="$(git grep --untracked -nIE '(arn:aws:[a-z0-9-]+:[a-z0-9-]*:[0-9]{12}:|[0-9]{12}\.dkr\.ecr\.)' -- . "${EXCLUDES[@]}" || true)"
if [ -n "$acct_out" ]; then
  # Cho phép dòng ECR registry trong file có header "MANAGED BY CI".
  filtered=""
  while IFS= read -r line; do
    file="${line%%:*}"
    if grep -q 'MANAGED BY CI' "$file" && echo "$line" | grep -qE '[0-9]{12}\.dkr\.ecr\.us-east-1\.amazonaws\.com'; then
      continue
    fi
    filtered+="$line"$'\n'
  done <<< "$acct_out"
  if [ -n "${filtered//$'\n'/}" ]; then
    echo "FAIL: AWS account ID ghi cứng"
    printf '%s' "$filtered" | sed 's/^/    /'
    fail=1
  else
    echo "ok   AWS account ID (chỉ có trong file MANAGED BY CI)"
  fi
else
  echo "ok   AWS account ID"
fi

exit "$fail"
