/**
 * ComplianceApi — TypeScript interface for Compliance Engine REST API.
 *
 * All methods go through the Backstage backend proxy:
 *   /api/proxy/compliance-engine/* → ${COMPLIANCE_ENGINE_URL}/api/v1/*
 *
 * Đây là kiểu dữ liệu phía component. Response thật của backend được chuyển
 * đổi trong ./adapters.ts (audit 5.1).
 */

// ─── Response Types ──────────────────────────────────────────────────────────

export interface DomainScore {
  domain: 'cluster_security' | 'workload_security' | 'supply_chain' | 'platform_config';
  score: number;
  weight: number;
  total_checks: number;
  passed: number;
  failed: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export interface ScoresResponse {
  scan_id: number;
  overall_score: number;
  classification: 'excellent' | 'good' | 'fair' | 'poor';
  domains: DomainScore[];
  scanned_at: string;
  namespace: string | null;
  total_findings: number;
  total_passed: number;
  total_failed: number;
  critical_violations: number;
  high_violations: number;
}

export interface FindingResource {
  kind: string;
  name: string;
  namespace: string | null;
}

export interface Finding {
  /** DB id — dùng cho URL recommendation (/findings/{id}/recommendation) */
  id: number;
  /** ID logic, ví dụ KYV-..., TRV-..., CIS-... */
  finding_id: string;
  scan_id: number;
  source: 'kyverno' | 'trivy' | 'kube-bench';
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: 'pass' | 'fail' | 'warn' | 'skip';
  resource: FindingResource;
  title: string;
  description: string;
  collected_at: string;
}

export interface FindingsResponse {
  items: Finding[];
  total: number;
  scan_id: number | null;
}

/** Một điểm trong GET /scores/history */
export interface ScoreHistoryPoint {
  scan_id: number;
  overall_score: number;
  classification: ScoresResponse['classification'];
  scanned_at: string;
  total_findings: number;
  total_failed: number;
}

export interface RuleRecommendation {
  finding_id: string;
  rule_id: string;
  /** = rule_id (giữ tên cũ cho component) */
  policy: string;
  title: string;
  fix: string;
  yaml_fix: string;
  reference: string;
  latency_ms: number;
}

export interface CompareRecommendationsResponse {
  rule_based: RuleRecommendation | null;
  basic: AIRecommendation | null;
  context_enriched: AIRecommendation | null;
}

export interface AIRecommendation {
  finding_id: string;
  strategy_used: string;
  model: string;
  root_cause: string;
  yaml_fix: string;
  impact_if_unfixed: string;
  cis_references: string[];
  urgency: 'immediate' | 'soon' | 'low';
  confidence: number;
  latency_ms: number;
}

export interface PriorityFix {
  finding_id: string;
  title: string;
  severity: string;
  fix_summary: string;
  estimated_effort: string;
}

export interface RemediationPhase {
  phase: 'immediate' | 'this_sprint' | 'backlog';
  description: string;
  finding_ids: string[];
  total_estimated_effort: string;
}

export interface AISummaryResponse {
  overall_assessment: string;
  risk_level: 'critical' | 'high' | 'moderate' | 'low';
  top_priorities: PriorityFix[];
  remediation_phases: RemediationPhase[];
  trend_prediction: 'improving' | 'stable' | 'declining';
  generated_at: string;
  latency_ms: number;
}

export interface RemediationPlanResponse {
  phases: RemediationPhase[];
  total_findings: number;
  total_estimated_effort: string;
  generated_at: string;
}

export interface BatchAnalyzeRequest {
  finding_ids: string[];
  strategy: 'basic' | 'context_enriched';
}

export interface BatchAnalyzeResponse {
  results: AIRecommendation[];
  successful: number;
  failed: number;
  total_latency_ms: number;
}

// ─── API Interface ────────────────────────────────────────────────────────────

export interface ComplianceApi {
  /** GET /scores — latest cluster-wide scores; null khi chưa có scan nào (404) */
  getLatestScores(): Promise<ScoresResponse | null>;

  /** GET /scores/{namespace} — scores for a specific namespace */
  getScoresByNamespace(namespace: string): Promise<ScoresResponse>;

  /** GET /scores/history — score history for trend chart */
  getScoreHistory(limit?: number): Promise<ScoreHistoryPoint[]>;

  /** GET /findings — findings with optional filters */
  getFindings(filters?: {
    severity?: string;
    category?: string;
    status?: string;
    scan_id?: number;
  }): Promise<FindingsResponse>;

  /** POST /scans — trigger a new compliance scan */
  triggerScan(namespace?: string): Promise<{ scan_id: number; status: string }>;

  /** GET /findings/{id}/recommendation — rule-based; id = Finding.id (DB id) */
  getRuleRecommendation(findingDbId: number): Promise<RuleRecommendation>;

  /** GET /findings/{id}/ai-recommendation — AI recommendation */
  getAIRecommendation(
    findingDbId: number,
    strategy?: 'basic' | 'context_enriched',
  ): Promise<AIRecommendation>;

  /** GET /findings/{id}/compare-recommendations — rule + 2 AI strategies */
  compareRecommendations(findingDbId: number): Promise<CompareRecommendationsResponse>;

  /** GET /ai/summary — AI executive summary */
  getAISummary(): Promise<AISummaryResponse>;

  /** GET /ai/remediation-plan — AI remediation plan */
  getRemediationPlan(): Promise<RemediationPlanResponse>;

  /** POST /ai/batch-analyze — batch AI recommendation */
  batchAnalyze(
    findingIds: string[],
    strategy: 'basic' | 'context_enriched',
  ): Promise<BatchAnalyzeResponse>;
}
