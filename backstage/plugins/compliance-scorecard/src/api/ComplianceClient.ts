/**
 * ComplianceClient — Backstage fetch-based client for Compliance Engine API.
 *
 * All requests go through Backstage backend proxy:
 *   /api/proxy/compliance-engine/* → ${COMPLIANCE_ENGINE_URL}/api/v1/*
 *
 * Backstage proxy bỏ prefix /api/proxy/compliance-engine và nối phần còn lại
 * vào target (target đã gồm /api/v1). Response được chuyển qua ./adapters.ts.
 */

import type {
  ComplianceApi,
  ScoresResponse,
  ScoreHistoryPoint,
  FindingsResponse,
  RuleRecommendation,
  AIRecommendation,
  CompareRecommendationsResponse,
  AISummaryResponse,
  RemediationPlanResponse,
  BatchAnalyzeResponse,
} from './ComplianceApi';
import {
  RawAIRecommendation,
  RawCompareEnvelope,
  RawFindingsEnvelope,
  RawHistoryEnvelope,
  RawRuleRecommendation,
  toAIRecommendation,
  toCompareResponse,
  toFindingsResponse,
  toHistory,
  toRuleRecommendation,
  toScoresResponse,
} from './adapters';

export class ComplianceApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const PROXY_BASE = '/api/proxy/compliance-engine';

export class ComplianceClient implements ComplianceApi {
  private readonly fetchApi: typeof fetch;

  constructor(fetchApi?: typeof fetch) {
    this.fetchApi = fetchApi ?? window.fetch.bind(window);
  }

  private async get<T>(path: string): Promise<T> {
    const res = await this.fetchApi(`${PROXY_BASE}${path}`);
    if (!res.ok) {
      const text = await res.text();
      throw new ComplianceApiError(res.status, `Compliance API error ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const res = await this.fetchApi(`${PROXY_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Compliance API error ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
  }

  async getLatestScores(): Promise<ScoresResponse | null> {
    try {
      return toScoresResponse(await this.get<ScoresResponse & { cached?: boolean }>('/scores'));
    } catch (e) {
      // 404 = DB chưa có scan nào: dashboard hiển thị empty state thay vì lỗi.
      if (e instanceof ComplianceApiError && e.status === 404) return null;
      throw e;
    }
  }

  async getScoresByNamespace(namespace: string): Promise<ScoresResponse> {
    return toScoresResponse(
      await this.get<ScoresResponse & { cached?: boolean }>(`/scores/${encodeURIComponent(namespace)}`),
    );
  }

  async getScoreHistory(limit = 10): Promise<ScoreHistoryPoint[]> {
    return toHistory(await this.get<RawHistoryEnvelope>(`/scores/history?limit=${limit}`));
  }

  async getFindings(filters?: {
    severity?: string;
    category?: string;
    status?: string;
    scan_id?: number;
  }): Promise<FindingsResponse> {
    const params = new URLSearchParams();
    if (filters?.severity) params.set('severity', filters.severity);
    if (filters?.category) params.set('category', filters.category);
    if (filters?.status) params.set('status', filters.status);
    if (filters?.scan_id) params.set('scan_id', String(filters.scan_id));
    const qs = params.toString();
    return toFindingsResponse(await this.get<RawFindingsEnvelope>(`/findings${qs ? `?${qs}` : ''}`));
  }

  async triggerScan(namespace?: string): Promise<{ scan_id: number; status: string }> {
    return this.post<{ scan_id: number; status: string }>('/scans', {
      namespace: namespace ?? null,
    });
  }

  async getRuleRecommendation(findingDbId: number): Promise<RuleRecommendation> {
    return toRuleRecommendation(
      await this.get<RawRuleRecommendation>(`/findings/${findingDbId}/recommendation`),
    );
  }

  async getAIRecommendation(
    findingDbId: number,
    strategy: 'basic' | 'context_enriched' = 'context_enriched',
  ): Promise<AIRecommendation> {
    return toAIRecommendation(
      await this.get<RawAIRecommendation>(`/findings/${findingDbId}/ai-recommendation?strategy=${strategy}`),
    );
  }

  async compareRecommendations(findingDbId: number): Promise<CompareRecommendationsResponse> {
    return toCompareResponse(
      await this.get<RawCompareEnvelope>(`/findings/${findingDbId}/compare-recommendations`),
    );
  }

  async getAISummary(): Promise<AISummaryResponse> {
    return this.get<AISummaryResponse>('/ai/summary');
  }

  async getRemediationPlan(): Promise<RemediationPlanResponse> {
    return this.get<RemediationPlanResponse>('/ai/remediation-plan');
  }

  async batchAnalyze(
    findingIds: string[],
    strategy: 'basic' | 'context_enriched',
  ): Promise<BatchAnalyzeResponse> {
    return this.post<BatchAnalyzeResponse>('/ai/batch-analyze', {
      finding_ids: findingIds,
      strategy,
    });
  }
}
