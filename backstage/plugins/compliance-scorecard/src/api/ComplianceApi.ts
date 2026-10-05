/**
 * ComplianceApi — TypeScript interface for Compliance Engine REST API.
 *
 * All methods go through the Backstage backend proxy:
 *   /api/proxy/compliance-engine/* → http://compliance-engine:8000/api/v1/*
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
  finding_id: string;
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
  scan_id: number;
}

export interface RuleRecommendation {
  finding_id: string;
  policy: string;
  fix: string;
  reference: string;
  severity: string;
  latency_ms: number;
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
  /** GET /scores — latest cluster-wide scores */
  getLatestScores(): Promise<ScoresResponse>;

  /** GET /scores/{namespace} — scores for a specific namespace */
  getScoresByNamespace(namespace: string): Promise<ScoresResponse>;

  /** GET /scores/history — score history for trend chart */
  getScoreHistory(limit?: number): Promise<ScoresResponse[]>;

  /** GET /findings — findings with optional filters */
  getFindings(filters?: {
    severity?: string;
    category?: string;
    status?: string;
    scan_id?: number;
  }): Promise<FindingsResponse>;

  /** POST /scans — trigger a new compliance scan */
  triggerScan(namespace?: string): Promise<{ scan_id: number; status: string }>;

  /** GET /findings/{id}/recommendation — rule-based recommendation */
  getRuleRecommendation(findingId: string): Promise<RuleRecommendation>;

  /** GET /findings/{id}/ai-recommendation — AI recommendation */
  getAIRecommendation(
    findingId: string,
    strategy?: 'basic' | 'context_enriched',
  ): Promise<AIRecommendation>;

  /** GET /findings/{id}/compare-recommendations — compare both strategies */
  compareRecommendations(
    findingId: string,
  ): Promise<{ basic: AIRecommendation; context_enriched: AIRecommendation }>;

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
