#!/usr/bin/env bash
# terraform fmt -check + init -backend=false + validate + tflint cho mọi module.
# Không cần credential AWS, không tạo tài nguyên.
#
# Dùng trong CI (Linux) và validate-local.sh. Trên Windows có Application
# Control chặn provider .exe, validate-local.sh gọi script này qua WSL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$ROOT/infrastructure"
# terraform/tflint cài trong ~/tools/bin (WSL) được ưu tiên nếu có.
if [ -d "$HOME/tools/bin" ]; then export PATH="$HOME/tools/bin:$PATH"; fi
export TF_IN_AUTOMATION=1
export TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-$HOME/.terraform.d/plugin-cache}"
mkdir -p "$TF_PLUGIN_CACHE_DIR"

fail=0
echo "==> terraform fmt -check"
if ! terraform -chdir="$INFRA" fmt -check -recursive -diff; then
  echo "FAIL: terraform fmt (chạy: terraform fmt -recursive infrastructure)"
  fail=1
fi

for dir in "$INFRA"/0*/; do
  mod="$(basename "$dir")"
  # TF_DATA_DIR riêng: không dùng .terraform/ của aws-*.sh (đã init backend S3),
  # nếu không `init -backend=false` vẫn đọc backend cũ và đòi credential AWS.
  export TF_DATA_DIR="${TMPDIR:-/tmp}/tf-validate/$mod"
  echo "==> [$mod] init -backend=false"
  if ! terraform -chdir="$dir" init -backend=false -input=false -no-color >"/tmp/tf-init-$mod.log" 2>&1; then
    tail -30 "/tmp/tf-init-$mod.log"
    echo "FAIL: [$mod] init"
    fail=1
    continue
  fi
  echo "==> [$mod] validate"
  terraform -chdir="$dir" validate -no-color || { echo "FAIL: [$mod] validate"; fail=1; }

  if command -v tflint >/dev/null 2>&1; then
    echo "==> [$mod] tflint"
    (cd "$dir" && tflint --init --config "$INFRA/.tflint.hcl" >/dev/null && tflint --config "$INFRA/.tflint.hcl" --no-color) \
      || { echo "FAIL: [$mod] tflint"; fail=1; }
  else
    echo "SKIP: tflint không có trong PATH"
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "terraform-validate: FAILED"
  exit 1
fi
echo "terraform-validate: OK"
