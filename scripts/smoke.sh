#!/usr/bin/env bash
# Smoke test trên EKS thật (sau aws-up):
#   - mọi Argo CD Application Healthy
#   - có PolicyReport, VulnerabilityReport (compliance-test) và kết quả kube-bench
#   - scan namespace compliance-test -> score/finding cho workload A/B/C -> rule recommendation
#   - evidence (scan ID, timestamp, image digest, thời gian từng bước) -> docs/evidence/aws/
#
#   bash scripts/smoke.sh
#
# Gọi API từ BÊN TRONG pod compliance-engine (kubectl exec + python) nên không
# cần port-forward hay LB công khai.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
parse_common_flags "$@"
REPORT_TIMEOUT="${REPORT_TIMEOUT:-1200}"
NS_TEST="compliance-test"
WORKLOADS=(workload-a-poor workload-b-excellent workload-c-fair)

init_aws_context
evidence_init "smoke"
init_kubectl
fail=0
check() { if eval "$2"; then log "PASS $1"; echo "PASS $1" >> "$EVIDENCE_DIR/result.txt"; else warn "FAIL $1"; echo "FAIL $1" >> "$EVIDENCE_DIR/result.txt"; fail=1; fi; }

api() { # api METHOD PATH [JSON]
  kc -n compliance exec deploy/compliance-engine -c compliance-engine -- python -c '
import sys, urllib.request
m, p = sys.argv[1], sys.argv[2]
data = sys.argv[3].encode() if len(sys.argv) > 3 else None
req = urllib.request.Request("http://localhost:8000" + p, data=data, method=m,
                             headers={"Content-Type": "application/json"})
try:
    print(urllib.request.urlopen(req, timeout=30).read().decode())
except urllib.error.HTTPError as e:
    print(e.read().decode()); sys.exit(22)
' "$@"
}

# ── 1. Argo CD ───────────────────────────────────────────────────────────────
kc -n argocd get applications.argoproj.io \
  -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status --no-headers \
  > "$EVIDENCE_DIR/argocd-apps.txt"
check "argocd: all Applications Synced+Healthy" \
  "[ -s '$EVIDENCE_DIR/argocd-apps.txt' ] && ! awk '\$2!=\"Synced\" || \$3!=\"Healthy\"' '$EVIDENCE_DIR/argocd-apps.txt' | grep -q ."
timing argocd

# ── 2. Workload A/B/C Ready ─────────────────────────────────────────────────
for w in "${WORKLOADS[@]}"; do
  check "workload $w available" "kc -n $NS_TEST wait --for=condition=Available deploy/$w --timeout=300s >/dev/null"
done
kc -n "$NS_TEST" get pods -o wide > "$EVIDENCE_DIR/pods-compliance-test.txt" || true

# ── 3. Scanner reports ──────────────────────────────────────────────────────
log "kube-bench: chạy job từ CronJob"
job="kube-bench-smoke-$(date +%s)"
kc -n monitoring create job "$job" --from=cronjob/kube-bench >/dev/null
check "kube-bench job completed" "kc -n monitoring wait --for=condition=complete job/$job --timeout=600s >/dev/null"
check "kube-bench ConfigMap has results" \
  "[ \"\$(kc -n monitoring get configmap kube-bench-results -o jsonpath='{.data.results\.json}' | head -c 1)\" = '{' ] || [ \"\$(kc -n monitoring get configmap kube-bench-results -o jsonpath='{.data.results\.json}' | head -c 1)\" = '[' ]"

log "Chờ PolicyReport và VulnerabilityReport cho $NS_TEST (tối đa ${REPORT_TIMEOUT}s)"
deadline=$(( $(date +%s) + REPORT_TIMEOUT ))
while :; do
  pr=$(kc -n "$NS_TEST" get policyreports.wgpolicyk8s.io --no-headers 2>/dev/null | grep -c . || true)
  vr=$(kc -n "$NS_TEST" get vulnerabilityreports.aquasecurity.github.io --no-headers 2>/dev/null | grep -c . || true)
  log "  PolicyReport=$pr VulnerabilityReport=$vr"
  [ "$pr" -ge 3 ] && [ "$vr" -ge 3 ] && break
  [ "$(date +%s)" -gt "$deadline" ] && break
  sleep 30
done
check "PolicyReport >= 3 in $NS_TEST" "[ '$pr' -ge 3 ]"
check "VulnerabilityReport >= 3 in $NS_TEST" "[ '$vr' -ge 3 ]"
timing reports

# ── 4. Scan -> score/findings -> recommendation ─────────────────────────────
api GET /health > "$EVIDENCE_DIR/health.json" || true
api POST /api/v1/scans "{\"namespace\": \"$NS_TEST\"}" > "$EVIDENCE_DIR/scan-trigger.json"
scan_id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["scan_id"])' "$EVIDENCE_DIR/scan-trigger.json")
log "scan_id=$scan_id"
status=""
for _ in $(seq 1 60); do
  api GET "/api/v1/scans/$scan_id" > "$EVIDENCE_DIR/scan.json"
  status=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$EVIDENCE_DIR/scan.json")
  [ "$status" = "completed" ] || [ "$status" = "failed" ] && break
  sleep 5
done
check "scan $scan_id completed" "[ '$status' = completed ]"
timing scan

api GET "/api/v1/scores/$NS_TEST" > "$EVIDENCE_DIR/scores.json" || true
api GET "/api/v1/findings?scan_id=$scan_id&limit=200" > "$EVIDENCE_DIR/findings.json" || true
check "findings for all 3 workloads + 3 sources" "python3 - '$EVIDENCE_DIR' <<'PY'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
data = json.loads((d / 'findings.json').read_text())['data']['findings']
names = {f['resource_name'] for f in data}
srcs = {f['source'] for f in data}
missing = [w for w in ('workload-a-poor','workload-b-excellent','workload-c-fair') if not any(n.startswith(w) for n in names)]
print('sources', sorted(srcs), 'missing', missing)
sys.exit(0 if not missing and srcs == {'kyverno','trivy','kube-bench'} else 1)
PY"

rec_id=$(python3 -c '
import json,sys
fs=json.load(open(sys.argv[1]))["data"]["findings"]
c=[f["id"] for f in fs if f["source"]=="kyverno" and f["status"]=="fail"]
print(c[0] if c else "")' "$EVIDENCE_DIR/findings.json" || true)
if [ -n "$rec_id" ]; then
  api GET "/api/v1/findings/$rec_id/recommendation" > "$EVIDENCE_DIR/recommendation.json" || true
fi
check "rule recommendation for a Kyverno FAIL" "[ -n '$rec_id' ] && grep -q '\"rule_based\"' '$EVIDENCE_DIR/recommendation.json'"
timing recommendation

# ── 5. Evidence ─────────────────────────────────────────────────────────────
{
  echo "scan_id=$scan_id"
  echo "finished_at=$(date -u +%FT%TZ)"
  echo "cluster=$CLUSTER_NAME account=$ACCOUNT_ID region=$AWS_REGION"
  echo "git_commit=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
} > "$EVIDENCE_DIR/meta.txt"
kc get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .status.containerStatuses[*]}{.imageID}{" "}{end}{"\n"}{end}' \
  > "$EVIDENCE_DIR/image-digests.tsv" 2>/dev/null || true
python3 - "$EVIDENCE_DIR" <<'PY' || true
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
try:
    s = json.loads((d / "scores.json").read_text())
    print(f"score={s.get('overall_score')} classification={s.get('classification')}")
except Exception as e:
    print("scores.json unreadable:", e)
PY

if [ "$fail" -ne 0 ]; then
  warn "smoke: FAIL (xem $EVIDENCE_DIR/result.txt)"
  exit 1
fi
log "smoke: PASS (evidence $EVIDENCE_DIR)"
