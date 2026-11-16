#!/usr/bin/env bash
# Kiểm tra tĩnh NHẸ chạy được trên máy dev (Git Bash trên Windows, hoặc Linux).
# Không build image, không docker compose, không cluster, không AWS credential.
#
#   bash scripts/validate-local.sh            # chạy tất cả
#   bash scripts/validate-local.sh tf py      # chỉ một số bước: placeholders yaml sh tf py ts
#
# Trên Windows có Application Control chặn terraform-provider-*.exe: bước "tf"
# chạy qua WSL (WSL_DISTRO, mặc định Ubuntu-22.04; terraform/tflint trong ~/tools/bin).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
STEPS=("$@")
[ ${#STEPS[@]} -eq 0 ] && STEPS=(placeholders yaml sh tf py ts)

for d in /c/tools/terraform /c/tools/tflint /c/tools/node /c/tools/python; do
  [ -d "$d" ] && PATH="$d:$PATH"
done
export PATH

declare -A RESULT
run_step() {
  local name="$1"; shift
  echo
  echo "════════ $name ════════"
  local start=$SECONDS
  if "$@"; then RESULT[$name]="PASS ($((SECONDS - start))s)"; else RESULT[$name]="FAIL ($((SECONDS - start))s)"; fi
}

is_windows() { case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; *) return 1 ;; esac; }

step_placeholders() { bash scripts/check-placeholders.sh; }

step_yaml() {
  local py
  py="$(pick_python)" || { echo "python not found"; return 1; }
  "$py" - <<'PY'
import pathlib, sys
try:
    import yaml
except ImportError:
    print("SKIP: PyYAML not installed"); sys.exit(0)

class Loader(yaml.SafeLoader):
    pass
# Bỏ qua tag Helm/Go template: file template Helm không phải YAML hợp lệ trước khi render.
bad = 0
roots = ["idp-gitops", "backstage", ".github", "compliance-engine"]
for root in roots:
    for p in pathlib.Path(root).rglob("*.y*ml"):
        if "templates" in p.parts and "charts" in p.parts:
            continue
        if "node_modules" in p.parts or "skeleton" in p.parts:
            continue
        try:
            list(yaml.load_all(p.read_text(encoding="utf-8"), Loader=Loader))
        except Exception as e:
            bad += 1
            print(f"FAIL {p}: {e}".splitlines()[0])
print("yaml: OK" if not bad else f"yaml: {bad} file(s) invalid")
sys.exit(1 if bad else 0)
PY
}

step_sh() {
  local fail=0
  for f in scripts/*.sh infrastructure/05-backstage-ec2/userdata.sh backstage/scripts/*.sh; do
    [ -f "$f" ] || continue
    if bash -n "$f"; then echo "ok   $f"; else echo "FAIL $f"; fail=1; fi
    if grep -q $'\r' "$f"; then echo "FAIL $f has CRLF line endings"; fail=1; fi
  done
  return $fail
}

step_tf() {
  if is_windows; then
    local distro="${WSL_DISTRO:-Ubuntu-22.04}"
    local wsl_root
    wsl_root="/mnt/$(echo "${ROOT:1:1}" | tr 'A-Z' 'a-z')${ROOT:2}"
    echo "Windows: chạy terraform/tflint trong WSL ($distro) tại $wsl_root"
    # wsl.exe tự expand $VAR trong tham số -> gọi thẳng file script (script tự thêm ~/tools/bin vào PATH).
    MSYS_NO_PATHCONV=1 wsl.exe -d "$distro" -- bash "$wsl_root/scripts/terraform-validate.sh"
  else
    bash scripts/terraform-validate.sh
  fi
}

pick_python() {
  local c
  for c in compliance-engine/.venv/Scripts/python.exe compliance-engine/.venv/bin/python; do
    if [ -x "$ROOT/$c" ]; then echo "$ROOT/$c"; return 0; fi
  done
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then command -v "$c"; return 0; fi
  done
  return 1
}

step_py() {
  local py
  py="$(pick_python)" || { echo "python not found"; return 1; }
  echo "python: $("$py" --version)  ($py)"
  (cd compliance-engine && "$py" -m pytest tests/ -q -p no:cacheprovider 2>&1 | tail -5; exit "${PIPESTATUS[0]}")
}

step_ts() {
  local plugin=backstage/plugins/compliance-scorecard
  if [ ! -d "$plugin/node_modules" ]; then
    echo "Chưa có node_modules. Chạy: (cd $plugin && npm ci --ignore-scripts --legacy-peer-deps)"
    return 1
  fi
  (cd "$plugin" && npx --no-install tsc -p tsconfig.typecheck.json) || return 1
  echo "tsc typecheck: OK"
  (cd "$plugin" && npx --no-install tsc -p tsconfig.contract.json) || return 1
  echo "tsc contract build: OK"
}

for s in "${STEPS[@]}"; do
  case "$s" in
    placeholders) run_step placeholders step_placeholders ;;
    yaml)         run_step yaml step_yaml ;;
    sh)           run_step sh step_sh ;;
    tf)           run_step terraform step_tf ;;
    py)           run_step pytest step_py ;;
    ts)           run_step tsc step_ts ;;
    *) echo "unknown step: $s"; exit 2 ;;
  esac
done

echo
echo "════════ SUMMARY ════════"
rc=0
for k in "${!RESULT[@]}"; do
  printf '%-14s %s\n' "$k" "${RESULT[$k]}"
  [[ "${RESULT[$k]}" == FAIL* ]] && rc=1
done
exit $rc
