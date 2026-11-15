#!/usr/bin/env bash
# Smoke test Compliance Engine KHÔNG cần cluster (chạy trong GitHub Actions).
#
#   1. docker compose up: API + PostgreSQL + Redis, DB trắng, COLLECTOR_MODE=fixtures
#   2. POST /api/v1/scans có body {} rồi poll tới completed
#   3. GET /scores, /scores/history, /findings có dữ liệu
#   4. GET recommendation rule-based cho một finding Kyverno FAIL
#   5. Lưu response làm evidence (contract-check.mjs kiểm kiểu phía plugin)
#
# KHÔNG chạy trên máy dev Windows (quy ước dự án: không docker compose local).
#   EVIDENCE_DIR=... bash scripts/engine-smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_DIR="$ROOT/compliance-engine"
EVIDENCE_DIR="${EVIDENCE_DIR:-$ROOT/engine-smoke-evidence}"
API="${API:-http://localhost:8000}"
mkdir -p "$EVIDENCE_DIR"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$EVIDENCE_DIR/steps.log"; }
t0=$(date +%s)
step_time() { echo "$1=$(( $(date +%s) - t0 ))s" >> "$EVIDENCE_DIR/timings.txt"; }

cleanup() {
  (cd "$ENGINE_DIR" && docker compose logs --no-color > "$EVIDENCE_DIR/compose.log" 2>&1 || true)
  if [ "${KEEP_UP:-0}" != "1" ]; then
    (cd "$ENGINE_DIR" && docker compose down -v >/dev/null 2>&1 || true)
  fi
}
trap cleanup EXIT

log "docker compose up (fixtures mode, blank DB)"
(cd "$ENGINE_DIR" && docker compose down -v >/dev/null 2>&1 || true)
(cd "$ENGINE_DIR" && COLLECTOR_MODE=fixtures docker compose up -d --build)

log "waiting for /health"
for i in $(seq 1 60); do
  if curl -fsS "$API/health" > "$EVIDENCE_DIR/health.json" 2>/dev/null; then break; fi
  [ "$i" -eq 60 ] && { log "API not healthy after 120s"; exit 1; }
  sleep 2
done
step_time api_ready

log "GET /scores before any scan must be 404 (empty state)"
code=$(curl -s -o /dev/null -w '%{http_code}' "$API/api/v1/scores")
[ "$code" = "404" ] || { log "expected 404, got $code"; exit 1; }

log "POST /api/v1/scans with body {}"
curl -fsS -X POST "$API/api/v1/scans" -H 'Content-Type: application/json' -d '{}' \
  | tee "$EVIDENCE_DIR/scan-trigger.json"
echo
scan_id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["scan_id"])' "$EVIDENCE_DIR/scan-trigger.json")

log "poll scan $scan_id"
status=""
for i in $(seq 1 60); do
  curl -fsS "$API/api/v1/scans/$scan_id" > "$EVIDENCE_DIR/scan.json"
  status=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$EVIDENCE_DIR/scan.json")
  [ "$status" = "completed" ] && break
  [ "$status" = "failed" ] && { cat "$EVIDENCE_DIR/scan.json"; exit 1; }
  sleep 2
done
[ "$status" = "completed" ] || { log "scan not completed: $status"; exit 1; }
step_time scan_completed

log "GET scores / history / findings"
curl -fsS "$API/api/v1/scores" > "$EVIDENCE_DIR/scores.json"
curl -fsS "$API/api/v1/scores/history?limit=10" > "$EVIDENCE_DIR/history.json"
curl -fsS "$API/api/v1/findings?limit=200" > "$EVIDENCE_DIR/findings.json"
curl -fsS "$API/api/v1/findings?source=kyverno&status=fail&limit=50" > "$EVIDENCE_DIR/findings-kyverno-fail.json"

python3 - "$EVIDENCE_DIR" <<'PY'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
scan = json.loads((d / "scan.json").read_text())
scores = json.loads((d / "scores.json").read_text())
data = json.loads((d / "findings.json").read_text())["data"]
assert scan["total_findings"] > 0, "scan has no findings"
assert data["total"] == scan["total_findings"], (data["total"], scan["total_findings"])
sources = {f["source"] for f in data["findings"]}
assert sources == {"kyverno", "trivy", "kube-bench"}, sources
names = {f["resource_name"] for f in data["findings"]}
for w in ("workload-a-poor", "workload-b-excellent", "workload-c-fair"):
    assert any(n.startswith(w) for n in names), f"no finding for {w}"
assert 0 <= scores["overall_score"] <= 100
print(f"scan={scan['scan_id']} findings={scan['total_findings']} score={scores['overall_score']} ({scores['classification']})")
fail = json.loads((d / "findings-kyverno-fail.json").read_text())["data"]["findings"]
assert fail, "no kyverno FAIL finding"
(d / "rec-target.txt").write_text(str(fail[0]["id"]))
PY

rec_id=$(cat "$EVIDENCE_DIR/rec-target.txt")
log "GET rule-based recommendation for finding $rec_id"
curl -fsS "$API/api/v1/findings/$rec_id/recommendation" > "$EVIDENCE_DIR/recommendation.json"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["type"]=="rule_based" and r["rule_id"], r; print("rule:", r["rule_id"])' \
  "$EVIDENCE_DIR/recommendation.json"
step_time done

log "engine-smoke: OK (evidence in $EVIDENCE_DIR)"
