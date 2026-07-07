import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import type { InsightsResponse } from '../types';

export function useInsights() {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(async (
    datasetId: string,
    options?: { model?: string; provider?: string },
  ) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runInsights({ dataset_id: datasetId, ...options });
      setData(res);
      return res;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Analysis failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, loading, error, runAnalysis, clear };
}
