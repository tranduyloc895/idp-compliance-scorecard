#!/usr/bin/env node
// Kiểm tra response THẬT của Compliance Engine (do engine-smoke.sh lưu) đi qua
// lớp adapter của plugin Backstage và ra đúng kiểu component cần (audit 5.1).
//
//   node scripts/contract-check.mjs <evidence-dir>
//
// Yêu cầu: đã biên dịch adapter:
//   npx tsc -p backstage/plugins/compliance-scorecard/tsconfig.contract.json
import { createRequire } from 'node:module';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const adapters = require(join(root, 'backstage/plugins/compliance-scorecard/dist-contract/adapters.js'));

const dir = process.argv[2];
if (!dir) {
  console.error('usage: contract-check.mjs <evidence-dir>');
  process.exit(2);
}
const load = name => JSON.parse(readFileSync(join(dir, name), 'utf8'));

let failures = 0;
const check = (cond, msg) => {
  if (cond) {
    console.log(`  ok   ${msg}`);
  } else {
    console.log(`  FAIL ${msg}`);
    failures += 1;
  }
};
const isNum = v => typeof v === 'number' && Number.isFinite(v);
const isStr = v => typeof v === 'string';

console.log('scores.json -> ScoresResponse');
const scores = adapters.toScoresResponse(load('scores.json'));
check(isNum(scores.overall_score), 'overall_score is number');
check(['excellent', 'good', 'fair', 'poor'].includes(scores.classification), 'classification enum');
check(Array.isArray(scores.domains) && scores.domains.length === 4, '4 domains');
check(scores.domains.every(d => isStr(d.domain) && isNum(d.score) && isNum(d.weight)), 'domain fields');
check(!('cached' in scores), 'cached flag stripped');

console.log('history.json -> ScoreHistoryPoint[]');
const history = adapters.toHistory(load('history.json'));
check(Array.isArray(history) && history.length >= 1, 'history is non-empty array');
check(history.every(h => isNum(h.overall_score) && isStr(h.scanned_at) && isNum(h.scan_id)), 'history point fields');

console.log('findings.json -> FindingsResponse');
const findings = adapters.toFindingsResponse(load('findings.json'));
check(Array.isArray(findings.items) && findings.items.length > 0, 'items non-empty');
check(isNum(findings.total) && findings.total >= findings.items.length, 'total >= items');
const f = findings.items[0];
check(isNum(f.id), 'finding.id (DB id) is number');
check(isStr(f.finding_id), 'finding.finding_id is string');
check(f.resource && isStr(f.resource.kind) && isStr(f.resource.name), 'finding.resource object');
check(['kyverno', 'trivy', 'kube-bench'].includes(f.source), 'finding.source enum');

if (existsSync(join(dir, 'recommendation.json'))) {
  console.log('recommendation.json -> RuleRecommendation');
  const rec = adapters.toRuleRecommendation(load('recommendation.json'));
  check(isStr(rec.rule_id) && rec.rule_id.length > 0, 'rule_id');
  check(rec.policy === rec.rule_id, 'policy mirrors rule_id');
  check(isStr(rec.fix) && rec.fix.length > 0, 'fix (from fix_description)');
  check(isStr(rec.yaml_fix), 'yaml_fix');
} else {
  console.log('  FAIL recommendation.json missing');
  failures += 1;
}

if (failures > 0) {
  console.error(`contract-check: ${failures} failure(s)`);
  process.exit(1);
}
console.log('contract-check: OK');
