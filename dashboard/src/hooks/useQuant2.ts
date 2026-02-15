/**
 * Quant 2.0 Data Hook
 */

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export interface Quant2Strategy {
  status: string;
  metrics?: Record<string, any>;
  final_value?: number;
  message?: string;
}

export interface Quant2Regime {
  current: 'BULL' | 'BEAR' | 'HIGH_VOL' | 'SIDEWAYS' | 'UNKNOWN';
  probabilities: { bull: number; bear: number; sideways: number };
  message?: string;
}

export interface Quant2Universe {
  name: string;
  ticker_count: number;
}

export interface Quant2Data {
  generated_at: string;
  source: 'cached' | 'live';
  universe: Quant2Universe;
  universe_key: string;
  ticker_count: number;
  regime: Quant2Regime;
  strategies: Record<string, Quant2Strategy>;
}

export function useQuant2(universe: string = 'SPX500') {
  const [data, setData] = useState<Quant2Data | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<Quant2Data>('/api/dashboard/quant2', {
        params: { universe },
      });
      setData(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch Quant 2 data');
    } finally {
      setLoading(false);
    }
  }, [universe]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { data, loading, error, refresh: fetchData };
}
