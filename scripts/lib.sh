#!/usr/bin/env bash
# Hàm dùng chung cho aws-*.sh, smoke.sh, k8s-secrets.sh. Source, không chạy trực tiếp.
#
# Môi trường chạy: AWS CloudShell hoặc Linux có aws-cli v2 + terraform >= 1.10.
# kubectl: dùng bản trong PATH; nếu không có mà có Docker thì chạy image
# alpine/k8s (kubectl) với kubeconfig chứa token tạm (aws eks get-token).
# Trên Windows Git Bash: terraform provider bị Application Control chặn và không
# có kubectl -> chạy các script này trong CloudShell (scripts/cloudshell-tools.sh).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$ROOT/infrastructure"

export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
CLUSTER_NAME="${CLUSTER_NAME:-ecommerce-cluster}"
SSM_PREFIX="${SSM_PREFIX:-/idp}"
KUBECTL_IMAGE="${KUBECTL_IMAGE:-alpine/k8s:1.35.0}"
DRY_RUN="${DRY_RUN:-0}"
ASSUME_YES="${ASSUME_YES:-0}"

# ── logging ──────────────────────────────────────────────────────────────────
c_info=$'\033[36m'; c_warn=$'\033[33m'; c_err=$'\033[31m'; c_off=$'\033[0m'
[ -t 1 ] || { c_info=""; c_warn=""; c_err=""; c_off=""; }
log()  { printf '%s[%s]%s %s\n' "$c_info" "$(date -u +%H:%M:%S)" "$c_off" "$*" >&2; }
warn() { printf '%s[warn]%s %s\n' "$c_warn" "$c_off" "$*" >&2; }
die()  { printf '%s[error]%s %s\n' "$c_err" "$c_off" "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "Thiếu '$1' trong PATH. ${2:-}"; }

confirm() { # confirm "message"
  [ "$DRY_RUN" = "1" ] && return 0
  [ "$ASSUME_YES" = "1" ] && return 0
  read -r -p "$1 [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || die "Huỷ theo yêu cầu."
}

# ── AWS identity / state bucket ──────────────────────────────────────────────
aws_account_id() { aws sts get-caller-identity --query Account --output text; }

init_aws_context() {
  need aws "Cài aws-cli v2 hoặc dùng AWS CloudShell."
  ACCOUNT_ID="$(aws_account_id)" || die "Không gọi được STS. Kiểm tra credential AWS."
  export ACCOUNT_ID
  export TF_STATE_BUCKET="${TF_STATE_BUCKET:-idp-tfstate-${ACCOUNT_ID}-${AWS_REGION}}"
  export TF_VAR_state_bucket="$TF_STATE_BUCKET"
  export TF_VAR_aws_region="$AWS_REGION"
  export TF_IN_AUTOMATION=1
  log "account=$ACCOUNT_ID region=$AWS_REGION state_bucket=$TF_STATE_BUCKET"
}

state_bucket_exists() { aws s3api head-bucket --bucket "$TF_STATE_BUCKET" >/dev/null 2>&1; }

state_exists() { # state_exists 01-network
  aws s3api head-object --bucket "$TF_STATE_BUCKET" --key "$1/terraform.tfstate" >/dev/null 2>&1
}

# ── terraform ────────────────────────────────────────────────────────────────
tf() { local mod="$1"; shift; terraform -chdir="$INFRA/$mod" "$@"; }

tf_init() { # tf_init <module>  (00-bootstrap dùng state local)
  local mod="$1"
  need terraform "Cài terraform >= 1.10 (scripts/cloudshell-tools.sh)."
  if [ "$mod" = "00-bootstrap" ]; then
    tf "$mod" init -input=false -no-color >/dev/null
  else
    tf "$mod" init -input=false -no-color -reconfigure \
      -backend-config="bucket=$TF_STATE_BUCKET" >/dev/null
  fi
}

tf_apply_or_plan() { # tf_apply_or_plan <module> [extra args]
  local mod="$1"; shift
  tf_init "$mod"
  if [ "$DRY_RUN" = "1" ]; then
    log "[$mod] terraform plan (dry-run)"
    tf "$mod" plan -input=false -no-color -lock=false "$@"
  else
    log "[$mod] terraform apply"
    tf "$mod" apply -input=false -no-color -auto-approve "$@"
  fi
}

tf_destroy_or_plan() {
  local mod="$1"; shift
  if [ "$mod" != "00-bootstrap" ] && ! state_exists "$mod"; then
    log "[$mod] không có state — bỏ qua"
    return 0
  fi
  tf_init "$mod"
  if [ "$DRY_RUN" = "1" ]; then
    log "[$mod] terraform plan -destroy (dry-run)"
    tf "$mod" plan -destroy -input=false -no-color -lock=false "$@"
  else
    log "[$mod] terraform destroy"
    tf "$mod" destroy -input=false -no-color -auto-approve "$@"
  fi
}

tf_output() { tf "$1" output -raw "$2" 2>/dev/null; }

# ── kubectl ──────────────────────────────────────────────────────────────────
cluster_exists() {
  aws eks describe-cluster --name "$CLUSTER_NAME" >/dev/null 2>&1
}

KC_MODE=""
init_kubectl() {
  if command -v kubectl >/dev/null 2>&1; then
    KC_MODE=native
    aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" >/dev/null
  elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    KC_MODE=docker
  else
    die "Cần kubectl (CloudShell: scripts/cloudshell-tools.sh) hoặc Docker để chạy $KUBECTL_IMAGE."
  fi
  log "kubectl mode: $KC_MODE"
}

_docker_kubeconfig() {
  # Kubeconfig dùng token tạm (15 phút) để image kubectl không cần aws-cli.
  local dir="${TMPDIR:-/tmp}/idp-kube"; mkdir -p "$dir"; chmod 700 "$dir"
  local endpoint ca token
  endpoint="$(aws eks describe-cluster --name "$CLUSTER_NAME" --query cluster.endpoint --output text)"
  ca="$(aws eks describe-cluster --name "$CLUSTER_NAME" --query cluster.certificateAuthority.data --output text)"
  token="$(aws eks get-token --cluster-name "$CLUSTER_NAME" --query status.token --output text)"
  umask 077
  cat > "$dir/config" <<EOF
apiVersion: v1
kind: Config
clusters: [{name: eks, cluster: {server: "$endpoint", certificate-authority-data: "$ca"}}]
users: [{name: eks, user: {token: "$token"}}]
contexts: [{name: eks, context: {cluster: eks, user: eks}}]
current-context: eks
EOF
  echo "$dir"
}

kc() {
  case "$KC_MODE" in
    native) kubectl "$@" ;;
    docker)
      local dir; dir="$(_docker_kubeconfig)"
      docker run --rm -i -v "$dir:/kube:ro" -e KUBECONFIG=/kube/config \
        -v "$ROOT:/repo:ro" -w /repo "$KUBECTL_IMAGE" "$@" ;;
    *) die "init_kubectl chưa được gọi" ;;
  esac
}

# ── SSM ──────────────────────────────────────────────────────────────────────
ssm_get() { # ssm_get <name> -> value hoặc rỗng
  aws ssm get-parameter --name "$SSM_PREFIX/$1" --with-decryption \
    --query Parameter.Value --output text 2>/dev/null || true
}

# ── evidence ─────────────────────────────────────────────────────────────────
evidence_init() { # evidence_init <prefix>
  EVIDENCE_DIR="${EVIDENCE_DIR:-$ROOT/docs/evidence/aws/$(date -u +%Y%m%dT%H%M%SZ)-$1}"
  mkdir -p "$EVIDENCE_DIR"
  export EVIDENCE_DIR
  T_START=$(date +%s)
  log "evidence: $EVIDENCE_DIR"
}
timing() { # timing <step>
  echo "$1=$(( $(date +%s) - T_START ))s $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$EVIDENCE_DIR/timings.txt"
}

parse_common_flags() {
  for a in "$@"; do
    case "$a" in
      --dry-run) DRY_RUN=1 ;;
      --yes|-y)  ASSUME_YES=1 ;;
    esac
  done
  export DRY_RUN ASSUME_YES
}
