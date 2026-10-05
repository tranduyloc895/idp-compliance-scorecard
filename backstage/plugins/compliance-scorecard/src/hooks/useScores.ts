import { useState, useEffect, useCallback } from 'react';
import type { ScoresResponse } from '../api/ComplianceApi';
import { ComplianceClient } from '../api/ComplianceClient';

const client = new ComplianceClient();

export interface UseScoresResult {
  scores: ScoresResponse | null;
  history: ScoresResponse[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useScores(): UseScoresResult {
  const [scores, setScores] = useState<ScoresResponse | null>(null);
  const [history, setHistory] = useState<ScoresResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [latest, hist] = await Promise.all([
        client.getLatestScores(),
        client.getScoreHistory(10),
      ]);
      setScores(latest);
      setHistory(hist);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load scores');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { scores, history, loading, error, refresh: fetchData };
}
