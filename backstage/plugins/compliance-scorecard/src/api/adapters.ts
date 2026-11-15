/**
 * Lớp chuyển đổi giữa response thật của Compliance Engine (FastAPI) và kiểu dữ
 * liệu mà các component dùng (audit mục 5.1). Chỉ chứa hàm thuần, không phụ
 * thuộc React/Backstage, để kiểm được bằng `tsc` + Node trong CI
 * (scripts/contract-check.mjs).
 *
 * Nguồn contract backend: compliance-engine/app/api/routes/*.py
 */

import type {
  AIRecommendation,
  CompareRecommendationsResponse,
  Finding,
  FindingsResponse,
  RuleRecommendation,
  ScoreHistoryPoint,
  ScoresResponse,
} from './ComplianceApi';

// ─── Raw backend shapes ──────────────────────────────────────────────────────

/** GET /findings → {cached, data: {findings, total, limit, offset}} */
export interface RawFindingsEnvelope {
  cached: boolean;
  data: {
    total: number;
    limit: number;
    offset: number;
    findings: RawFinding[];
  };
}

export interface RawFinding {
  id: number;
  finding_id: string;
  source: Finding['source'];
  category: string;
  severity: Finding['severity'];
  status: Finding['status'];
  resource_kind: string;
  resource_name: string;
  resource_namespace: string | null;
  title: string;
  description: string | null;
  collected_at: string;
  scan_id: number;
}

/** GET /scores/history → {history: [...], count} */
export interface RawHistoryEnvelope {
  history: ScoreHistoryPoint[];
  count: number;
}

/** GET /findings/{id}/recommendation */
export interface RawRuleRecommendation {
  finding_id: string;
  type: 'rule_based';
  rule_id: string;
  title: string;
  fix_description: string;
  yaml_fix: string;
  reference: string;
  generated_at: string;
  latency_ms: number;
}

/** GET /findings/{id}/ai-recommendation (route đơn dùng `strategy`) */
export interface RawAIRecommendation {
  cached?: boolean;
  finding_id: string;
  type?: 'ai_generated';
  strategy?: AIRecommendation['strategy_used'];
  strategy_used?: AIRecommendation['strategy_used'];
  model: string;
  root_cause: string;
  yaml_fix: string;
  impact_if_unfixed: string;
  cis_references: string[];
  urgency: AIRecommendation['urgency'];
  confidence: number;
  latency_ms: number | null;
}

/** GET /findings/{id}/compare-recommendations */
export interface RawCompareEnvelope {
  finding_id: string;
  recommendations: {
    rule_based: ({ available: true } & Omit<RawRuleRecommendation, 'finding_id' | 'type' | 'generated_at'>) | { available: false };
    ai_basic: ({ available: true } & RawAIRecommendation) | { available: false };
    ai_context_enriched: ({ available: true } & RawAIRecommendation) | { available: false };
  };
}

// ─── Adapters ────────────────────────────────────────────────────────────────

export function toFinding(raw: RawFinding): Finding {
  return {
    id: raw.id,
    finding_id: raw.finding_id,
    scan_id: raw.scan_id,
    source: raw.source,
    category: raw.category,
    severity: raw.severity,
    status: raw.status,
    resource: {
      kind: raw.resource_kind,
      name: raw.resource_name,
      namespace: raw.resource_namespace,
    },
    title: raw.title,
    description: raw.description ?? '',
    collected_at: raw.collected_at,
  };
}

export function toFindingsResponse(raw: RawFindingsEnvelope): FindingsResponse {
  const items = (raw.data?.findings ?? []).map(toFinding);
  return {
    items,
    total: raw.data?.total ?? items.length,
    // Backend không trả scan_id ở cấp danh sách; lấy từ finding đầu (null nếu rỗng).
    scan_id: items.length > 0 ? items[0].scan_id : null,
  };
}

export function toScoresResponse(raw: ScoresResponse & { cached?: boolean }): ScoresResponse {
  const { cached: _cached, ...rest } = raw;
  return rest;
}

export function toHistory(raw: RawHistoryEnvelope): ScoreHistoryPoint[] {
  return raw.history ?? [];
}

export function toRuleRecommendation(raw: RawRuleRecommendation): RuleRecommendation {
  return {
    finding_id: raw.finding_id,
    rule_id: raw.rule_id,
    policy: raw.rule_id,
    title: raw.title,
    fix: raw.fix_description,
    yaml_fix: raw.yaml_fix,
    reference: raw.reference,
    latency_ms: raw.latency_ms ?? 0,
  };
}

export function toAIRecommendation(raw: RawAIRecommendation): AIRecommendation {
  return {
    finding_id: raw.finding_id,
    strategy_used: raw.strategy_used ?? raw.strategy ?? 'context_enriched',
    model: raw.model,
    root_cause: raw.root_cause,
    yaml_fix: raw.yaml_fix,
    impact_if_unfixed: raw.impact_if_unfixed,
    cis_references: raw.cis_references ?? [],
    urgency: raw.urgency,
    confidence: raw.confidence,
    latency_ms: raw.latency_ms ?? 0,
  };
}

export function toCompareResponse(raw: RawCompareEnvelope): CompareRecommendationsResponse {
  const r = raw.recommendations;
  return {
    rule_based:
      r.rule_based.available
        ? toRuleRecommendation({
            ...(r.rule_based as Omit<RawRuleRecommendation, 'finding_id' | 'type' | 'generated_at'>),
            finding_id: raw.finding_id,
            type: 'rule_based',
            generated_at: '',
          })
        : null,
    basic: r.ai_basic.available ? toAIRecommendation(r.ai_basic as RawAIRecommendation) : null,
    context_enriched: r.ai_context_enriched.available
      ? toAIRecommendation(r.ai_context_enriched as RawAIRecommendation)
      : null,
  };
}
