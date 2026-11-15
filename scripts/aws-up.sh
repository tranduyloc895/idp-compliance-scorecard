#!/usr/bin/env bash
# Dựng LỚP TẠO-HUỶ cho một buổi lab (tính tiền theo giờ):
#   preflight -> 01-network -> 02-cluster-eks (+ Argo CD + root app) -> secret từ SSM
#   -> chờ Argo apps Synced/Healthy -> ghi URL engine vào SSM -> [05-backstage-ec2] -> smoke.sh
#
#   bash scripts/aws-up.sh [--dry-run] [--yes] [--with-backstage] [--skip-smoke]
#
# Không build image (quyết định #6): image phải có sẵn trong ECR do CI "build-all".
# Luôn kết thúc buổi lab bằng: bash scripts/aws-down.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
parse_common_flags "$@"
WITH_BACKSTAGE=0; SKIP_SMOKE=0
for a in "$@"; do
  case "$a" in
    --with-backstage) WITH_BACKSTAGE=1 ;;
    --skip-smoke) SKIP_SMOKE=1 ;;
  esac
done
APPS_TIMEOUT="${APPS_TIMEOUT:-2400}"   # giây chờ Argo apps

init_aws_context
evidence_init "up"
log "=== aws-up (dry-run=$DRY_RUN, backstage=$WITH_BACKSTAGE) ==="

# ── 0. Preflight ─────────────────────────────────────────────────────────────
preflight() {
  local ok=1
  state_bucket_exists || { warn "Chưa có state bucket $TF_STATE_BUCKET -> chạy scripts/aws-foundation-up.sh"; ok=0; }
  if state_bucket_exists; then
    state_exists 03-ecr || { warn "Chưa có 03-ecr (lớp nền)"; ok=0; }
  fi

  # Image phải có trong ECR với đúng tag mà GitOps tham chiếu.
  local reg; reg="$(awk '/registry:/ {print $2}' "$ROOT/idp-gitops/apps/image-registry.yaml")"
  local expect="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  if [ "$reg" != "$expect" ]; then
    warn "idp-gitops/apps/image-registry.yaml registry='$reg' (cần '$expect'). Chạy workflow build-all."
    ok=0
  fi
  local svc tag
  for svc in ui cart catalog orders checkout; do
    tag="$(awk '/^  tag:/ {gsub(/"/,"",$2); print $2}' "$ROOT/idp-gitops/apps/$svc/values.yaml")"
    check_image "$svc" "$tag" || ok=0
  done
  tag="$(awk '/newTag:/ {print $2}' "$ROOT/idp-gitops/compliance/compliance-engine/kustomization.yaml")"
  check_image compliance-engine "$tag" || ok=0

  # Argo CD đồng bộ từ GitHub, không từ máy local.
  local rev="${TF_VAR_gitops_revision:-main}"
  if git -C "$ROOT" rev-parse --verify -q "origin/$rev" >/dev/null; then
    if [ -n "$(git -C "$ROOT" diff "origin/$rev" -- idp-gitops 2>/dev/null)" ]; then
      warn "idp-gitops local khác origin/$rev: Argo CD sẽ dùng bản trên GitHub ($rev)."
    fi
  fi
  [ "$ok" = "1" ]
}

check_image() { # check_image <svc> <tag>
  if [ -z "$2" ] || [ "$2" = "not-built" ]; then
    warn "image $1: tag chưa được CI ghi (not-built)"; return 1
  fi
  if aws ecr describe-images --repository-name "retail-store/$1" --image-ids "imageTag=$2" >/dev/null 2>&1; then
    log "image ok  retail-store/$1:$2"
  else
    warn "image retail-store/$1:$2 không có trong ECR"; return 1
  fi
}

if ! preflight; then
  [ "$DRY_RUN" = "1" ] && warn "Preflight FAIL (dry-run vẫn tiếp tục để xem plan)." || die "Preflight FAIL — sửa các mục trên trước khi tạo tài nguyên tốn tiền."
fi
timing preflight

confirm "Tạo VPC + EKS (tính tiền theo giờ) trong $ACCOUNT_ID?"
echo "aws-up started $(date -u +%FT%TZ) account=$ACCOUNT_ID" >> "$EVIDENCE_DIR/steps.log"

# ── 1. Network + EKS + Argo CD ──────────────────────────────────────────────
tf_apply_or_plan 01-network
timing network

if [ "$DRY_RUN" = "1" ] && ! state_exists 01-network; then
  warn "Dry-run: 01-network chưa có state nên không plan được 02-cluster-eks (remote state)."
  log "Dry-run xong. Evidence: $EVIDENCE_DIR"
  exit 0
fi
tf_apply_or_plan 02-cluster-eks
timing eks

if [ "$DRY_RUN" = "1" ]; then
  [ "$WITH_BACKSTAGE" = "1" ] && tf_apply_or_plan 05-backstage-ec2
  log "Dry-run xong. Evidence: $EVIDENCE_DIR"
  exit 0
fi

# ── 2. Secret từ SSM ────────────────────────────────────────────────────────
init_kubectl
bash "$ROOT/scripts/k8s-secrets.sh"
timing secrets

# ── 3. Chờ Argo CD apps ─────────────────────────────────────────────────────
log "Chờ Argo CD Applications Synced/Healthy (tối đa ${APPS_TIMEOUT}s)"
deadline=$(( $(date +%s) + APPS_TIMEOUT ))
while :; do
  table="$(kc -n argocd get applications.argoproj.io \
    -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status --no-headers 2>/dev/null || true)"
  total=$(echo "$table" | grep -c . || true)
  bad=$(echo "$table" | awk 'NF && ($2!="Synced" || $3!="Healthy")' | grep -c . || true)
  log "apps: $total, chưa xong: $bad"
  if [ "$total" -gt 1 ] && [ "$bad" -eq 0 ]; then break; fi
  if [ "$(date +%s)" -gt "$deadline" ]; then
    echo "$table" | tee "$EVIDENCE_DIR/argocd-apps-timeout.txt"
    die "Timeout chờ Argo CD apps. Xem: kubectl -n argocd get applications; cluster VẪN ĐANG CHẠY -> sửa hoặc chạy aws-down.sh"
  fi
  sleep 30
done
echo "$table" > "$EVIDENCE_DIR/argocd-apps.txt"
timing argocd_healthy

# ── 4. URL engine cho Backstage (internal LB) ───────────────────────────────
lb=""
for _ in $(seq 1 30); do
  lb="$(kc -n compliance get svc compliance-engine-internal -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
  [ -n "$lb" ] && break; sleep 10
done
if [ -n "$lb" ]; then
  aws ssm put-parameter --name "$SSM_PREFIX/backstage/compliance-engine-url" --type String \
    --value "http://$lb:8000" --overwrite >/dev/null
  log "SSM $SSM_PREFIX/backstage/compliance-engine-url = http://$lb:8000"
else
  warn "Internal LB chưa có hostname (Backstage EC2 chưa gọi được engine)."
fi

# ── 5. Backstage EC2 (tuỳ chọn) ─────────────────────────────────────────────
if [ "$WITH_BACKSTAGE" = "1" ]; then
  tf_apply_or_plan 05-backstage-ec2
  timing backstage
fi

# ── 6. Smoke ────────────────────────────────────────────────────────────────
if [ "$SKIP_SMOKE" = "0" ]; then
  EVIDENCE_DIR="$EVIDENCE_DIR" bash "$ROOT/scripts/smoke.sh"
  timing smoke
fi

argo_pw="$(kc -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' 2>/dev/null | base64 -d 2>/dev/null || true)"
cat <<EOF

=== aws-up xong ($(( $(date +%s) - T_START ))s) — cluster đang tính tiền ===
Port-forward (chạy nơi có kubectl, ví dụ CloudShell):
  kubectl -n argocd port-forward svc/argocd-server 8080:80        # http://localhost:8080  user admin / ${argo_pw:+<argocd-initial-admin-secret>}
  kubectl -n compliance port-forward svc/compliance-engine 8000:8000  # http://localhost:8000/docs
  kubectl -n retail-store port-forward svc/ui 8081:80             # Retail Store UI
  kubectl -n monitoring port-forward svc/kps-grafana 3000:80      # Grafana (admin / SSM $SSM_PREFIX/monitoring/grafana-admin-password)
Argo CD admin password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
Evidence: $EVIDENCE_DIR
Kết thúc buổi lab: bash scripts/aws-down.sh
EOF
