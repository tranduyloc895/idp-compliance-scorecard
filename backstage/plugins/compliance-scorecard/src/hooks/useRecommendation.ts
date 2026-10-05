import { useState, useCallback } from 'react';
import type { RuleRecommendation, AIRecommendation, AISummaryResponse } from '../api/ComplianceApi';
import { ComplianceClient } from '../api/ComplianceClient';

const client = new ComplianceClient();

export interface UseRecommendationResult {
  ruleRec: RuleRecommendation | null;
  basicRec: AIRecommendation | null;
  enrichedRec: AIRecommendation | null;
  aiSummary: AISummaryResponse | null;
  loading: boolean;
  error: string | null;
  loadForFinding: (findingId: string) => void;
  loadAISummary: () => void;
  compareAll: (findingId: string) => void;
}

export function useRecommendation(): UseRecommendationResult {
  const [ruleRec, setRuleRec] = useState<RuleRecommendation | null>(null);
  const [basicRec, setBasicRec] = useState<AIRecommendation | null>(null);
  const [enrichedRec, setEnrichedRec] = useState<AIRecommendation | null>(null);
  const [aiSummary, setAISummary] = useState<AISummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadForFinding = useCallback(async (findingId: string) => {
    setLoading(true);
    setError(null);
    try {
      const rule = await client.getRuleRecommendation(findingId);
      setRuleRec(rule);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load recommendation');
    } finally {
      setLoading(false);
    }
  }, []);

  const compareAll = useCallback(async (findingId: string) => {
    setLoading(true);
    setError(null);
    try {
      const { basic, context_enriched } = await client.compareRecommendations(findingId);
      setBasicRec(basic);
      setEnrichedRec(context_enriched);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to compare recommendations');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAISummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await client.getAISummary();
      setAISummary(summary);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load AI summary');
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    ruleRec,
    basicRec,
    enrichedRec,
    aiSummary,
    loading,
    error,
    loadForFinding,
    loadAISummary,
    compareAll,
  };
}
