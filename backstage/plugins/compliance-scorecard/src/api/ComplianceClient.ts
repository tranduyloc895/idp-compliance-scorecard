/**
 * ComplianceClient — Backstage fetch-based client for Compliance Engine API.
 *
 * All requests go through Backstage backend proxy:
 *   /api/proxy/compliance-engine/* → http://compliance-engine:8000/api/v1/*
 *
 * Note: Backstage proxy config strips the proxy prefix and rewrites to /api/v1/*
 */

import type {
  ComplianceApi,
  ScoresResponse,
  FindingsResponse,
  RuleRecommendation,
  AIRecommendation,
  AISummaryResponse,
  RemediationPlanResponse,
  BatchAnalyzeResponse,
} from './ComplianceApi';

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
      throw new Error(`Compliance API error ${res.status}: ${text}`);
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

  async getLatestScores(): Promise<ScoresResponse> {
    return this.get<ScoresResponse>('/scores');
  }

  async getScoresByNamespace(namespace: string): Promise<ScoresResponse> {
    return this.get<ScoresResponse>(`/scores/${encodeURIComponent(namespace)}`);
  }

  async getScoreHistory(limit = 10): Promise<ScoresResponse[]> {
    return this.get<ScoresResponse[]>(`/scores/history?limit=${limit}`);
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
    return this.get<FindingsResponse>(`/findings${qs ? `?${qs}` : ''}`);
  }

  async triggerScan(namespace?: string): Promise<{ scan_id: number; status: string }> {
    return this.post<{ scan_id: number; status: string }>('/scans', {
      namespace: namespace ?? null,
    });
  }

  async getRuleRecommendation(findingId: string): Promise<RuleRecommendation> {
    return this.get<RuleRecommendation>(`/findings/${encodeURIComponent(findingId)}/recommendation`);
  }

  async getAIRecommendation(
    findingId: string,
    strategy: 'basic' | 'context_enriched' = 'context_enriched',
  ): Promise<AIRecommendation> {
    return this.get<AIRecommendation>(
      `/findings/${encodeURIComponent(findingId)}/ai-recommendation?strategy=${strategy}`,
    );
  }

  async compareRecommendations(
    findingId: string,
  ): Promise<{ basic: AIRecommendation; context_enriched: AIRecommendation }> {
    return this.get(`/findings/${encodeURIComponent(findingId)}/compare-recommendations`);
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
