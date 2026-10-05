import { useState, useEffect, useCallback } from 'react';
import type { FindingsResponse } from '../api/ComplianceApi';
import { ComplianceClient } from '../api/ComplianceClient';

const client = new ComplianceClient();

export interface FindingFilters {
  severity?: string;
  category?: string;
  status?: string;
}

export interface UseFindingsResult {
  data: FindingsResponse | null;
  loading: boolean;
  error: string | null;
  filters: FindingFilters;
  setFilters: (f: FindingFilters) => void;
  refresh: () => void;
}

export function useFindings(initialFilters?: FindingFilters): UseFindingsResult {
  const [data, setData] = useState<FindingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FindingFilters>(initialFilters ?? {});

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await client.getFindings(filters);
      setData(resp);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load findings');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, filters, setFilters, refresh: fetchData };
}
