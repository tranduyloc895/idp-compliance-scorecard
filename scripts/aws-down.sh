#!/usr/bin/env bash
# Huỷ LỚP TẠO-HUỶ. KHÔNG đụng lớp nền (state bucket, ECR, OIDC, SSM).
#
#   bash scripts/aws-down.sh [--dry-run] [--yes]
#
# Thứ tự bắt buộc:
#   1. Xoá root Application (cascade) -> Argo CD gỡ mọi workload
#   2. Xoá/chờ hết Service LoadBalancer và PVC; kiểm không còn ELB/EBS của cluster
#   3. terraform destroy 05-backstage-ec2 -> 02-cluster-eks -> 01-network
#   4. Kiểm lại ELB, EBS, ENI, NAT, EIP mồ côi
# --dry-run: chỉ liệt kê + terraform plan -destroy, không xoá gì. Dùng cả khi
# bị dừng giữa chừng để xem còn sót tài nguyên nào.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
parse_common_flags "$@"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-900}"

init_aws_context
evidence_init "down"
log "=== aws-down (dry-run=$DRY_RUN) ==="
confirm "XOÁ VPC/EKS/Backstage EC2 trong $ACCOUNT_ID? (lớp nền được giữ)"

vpc_id=""
if state_exists 01-network; then
  tf_init 01-network
  vpc_id="$(tf_output 01-network vpc_id || true)"
fi
log "vpc_id=${vpc_id:-<none>}"

# ── 1–2. Gỡ workload trong cluster ──────────────────────────────────────────
if cluster_exists; then
  init_kubectl
  log "Applications hiện có:"
  kc -n argocd get applications.argoproj.io --no-headers 2>/dev/null | tee "$EVIDENCE_DIR/apps-before.txt" || true
  log "Service LoadBalancer:"
  kc get svc -A --no-headers 2>/dev/null | awk '$3=="LoadBalancer"' | tee "$EVIDENCE_DIR/lb-before.txt" || true
  log "PVC:"
  kc get pvc -A --no-headers 2>/dev/null | tee "$EVIDENCE_DIR/pvc-before.txt" || true

  if [ "$DRY_RUN" != "1" ]; then
    # Chặn selfHeal tạo lại trong lúc xoá: xoá root trước (cascade nhờ finalizer).
    log "1. delete Application root (cascade)"
    kc -n argocd delete applications.argoproj.io root --wait=false --ignore-not-found
    # Child app cũng có finalizer -> Argo CD xoá resource của chúng.
    kc -n argocd delete applications.argoproj.io --all --wait=false --ignore-not-found || true

    deadline=$(( $(date +%s) + WAIT_TIMEOUT ))
    while :; do
      n=$(kc -n argocd get applications.argoproj.io --no-headers 2>/dev/null | grep -c . || true)
      log "   Applications còn lại: $n"
      [ "$n" -eq 0 ] && break
      if [ "$(date +%s)" -gt "$deadline" ]; then
        warn "Timeout chờ Application bị xoá; gỡ finalizer để tiếp tục (resource sẽ dọn ở bước 2)"
        for a in $(kc -n argocd get applications.argoproj.io -o name 2>/dev/null); do
          kc -n argocd patch "$a" --type merge -p '{"metadata":{"finalizers":null}}' || true
        done
        break
      fi
      sleep 15
    done

    log "2. xoá Service LoadBalancer + PVC còn lại (PVC của StatefulSet không bị cascade)"
    kc get svc -A --no-headers 2>/dev/null | awk '$3=="LoadBalancer" {print $1" "$2}' | while read -r ns name; do
      kc -n "$ns" delete svc "$name" --wait=false || true
    done
    for ns in $(kc get pvc -A --no-headers 2>/dev/null | awk '{print $1}' | sort -u); do
      kc -n "$ns" delete pvc --all --wait=false || true
    done

    deadline=$(( $(date +%s) + WAIT_TIMEOUT ))
    while :; do
      lbs=$(kc get svc -A --no-headers 2>/dev/null | awk '$3=="LoadBalancer"' | grep -c . || true)
      pvs=$(kc get pv --no-headers 2>/dev/null | grep -c . || true)
      log "   LB services: $lbs, PV: $pvs"
      [ "$lbs" -eq 0 ] && [ "$pvs" -eq 0 ] && break
      [ "$(date +%s)" -gt "$deadline" ] && { warn "Timeout chờ LB/PV bị xoá"; break; }
      sleep 15
    done
  fi
else
  log "Cluster $CLUSTER_NAME không tồn tại — bỏ qua bước 1–2"
fi

# ── kiểm ELB/EBS còn gắn cluster ─────────────────────────────────────────────
orphans() { # in ra tài nguyên có thể mồ côi; trả 1 nếu có
  local found=0 out
  if [ -n "$vpc_id" ]; then
    out="$(aws elb describe-load-balancers --query "LoadBalancerDescriptions[?VPCId=='$vpc_id'].LoadBalancerName" --output text 2>/dev/null || true)"
    [ -n "$out" ] && { warn "Classic ELB trong VPC: $out"; found=1; }
    out="$(aws elbv2 describe-load-balancers --query "LoadBalancers[?VpcId=='$vpc_id'].LoadBalancerArn" --output text 2>/dev/null || true)"
    [ -n "$out" ] && { warn "ELBv2 trong VPC: $out"; found=1; }
    out="$(aws ec2 describe-network-interfaces --filters Name=vpc-id,Values="$vpc_id" \
      --query 'NetworkInterfaces[?Status==`available`].NetworkInterfaceId' --output text 2>/dev/null || true)"
    [ -n "$out" ] && { warn "ENI available trong VPC: $out"; found=1; }
  fi
  out="$(aws ec2 describe-volumes --filters Name=tag-key,Values=kubernetes.io/created-for/pvc/name Name=status,Values=available \
    --query 'Volumes[].VolumeId' --output text 2>/dev/null || true)"
  [ -n "$out" ] && { warn "EBS volume (từ PVC) chưa gắn: $out"; found=1; }
  out="$(aws ec2 describe-volumes --filters Name=tag-key,Values="kubernetes.io/cluster/$CLUSTER_NAME" Name=status,Values=available \
    --query 'Volumes[].VolumeId' --output text 2>/dev/null || true)"
  [ -n "$out" ] && { warn "EBS volume tag cluster chưa gắn: $out"; found=1; }
  local nat_filter=(Name=tag:Project,Values=idp-compliance-scorecard)
  [ -n "$vpc_id" ] && nat_filter=(Name=vpc-id,Values="$vpc_id")
  out="$(aws ec2 describe-nat-gateways --filter Name=state,Values=available,pending "${nat_filter[@]}" \
    --query 'NatGateways[].NatGatewayId' --output text 2>/dev/null || true)"
  [ -n "$out" ] && { warn "NAT gateway: $out"; found=1; }
  out="$(aws ec2 describe-addresses --filters Name=tag:Project,Values=idp-compliance-scorecard \
    --query 'Addresses[?AssociationId==null].PublicIp' --output text 2>/dev/null || true)"
  [ -n "$out" ] && { warn "Elastic IP không gắn: $out"; found=1; }
  return $found
}

if [ "$DRY_RUN" != "1" ] && cluster_exists; then
  if ! orphans > "$EVIDENCE_DIR/orphans-before-destroy.txt" 2>&1; then
    cat "$EVIDENCE_DIR/orphans-before-destroy.txt" >&2
    warn "Còn LB/EBS gắn cluster trước khi destroy VPC. Terraform có thể kẹt ở subnet/IGW; xoá tay theo danh sách trên nếu cần."
  fi
fi

# ── 3. Terraform destroy ────────────────────────────────────────────────────
tf_destroy_or_plan 05-backstage-ec2
timing destroy_backstage
tf_destroy_or_plan 02-cluster-eks
timing destroy_eks
tf_destroy_or_plan 01-network
timing destroy_network

# ── 4. Kiểm tra mồ côi ──────────────────────────────────────────────────────
log "4. kiểm tra tài nguyên mồ côi"
if orphans 2>&1 | tee "$EVIDENCE_DIR/orphans-after.txt"; then
  log "Không thấy ELB/EBS/ENI/NAT/EIP mồ côi."
  status=0
else
  [ "$DRY_RUN" = "1" ] && status=0 || status=1
  warn "Có tài nguyên có thể mồ côi (xem $EVIDENCE_DIR/orphans-after.txt) — kiểm tra AWS Console."
fi
log "aws-down xong ($(( $(date +%s) - T_START ))s). Lớp nền (S3 state, ECR, OIDC, SSM) được giữ."
exit $status
