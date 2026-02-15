/**
 * Quant 1.0 Data Hook
 */

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export interface Quant1Strategy {
  status: string;
  metrics?: Record<string, any>;
  weights?: Record<string, number>;
  final_value?: number;
  message?: string;
}

export interface Quant1Data {
  generated_at: string;
  source: string;
  strategies: Record<string, Quant1Strategy>;
}

export function useQuant1() {
  const [data, setData] = useState<Quant1Data | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<Quant1Data>('/api/dashboard/quant1');
      setData(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch Quant 1 data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { data, loading, error, refresh: fetchData };
}
