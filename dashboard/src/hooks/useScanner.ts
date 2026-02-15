import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export interface ScanResult {
  ticker: string;
  name: string;
  price: number;
  change_pct: number;
  volume: number;
  signal: string;
  score: number;
  details?: Record<string, any>;
}

export interface ScannerData {
  results: ScanResult[];
  total_found: number;
  generated_at: string | null;
  scanner_type: string;
}

export interface ScanStatus {
  status: string;
  has_results: boolean;
  last_scan: string | null;
}

export function useScanner(limit: number = 50) {
  const [data, setData] = useState<ScannerData | null>(null);
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [resultsRes, statusRes] = await Promise.all([
        axios.get<ScannerData>(`/api/scanner/results?limit=${limit}`),
        axios.get<ScanStatus>('/api/scanner/status'),
      ]);
      setData(resultsRes.data);
      setStatus(statusRes.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scanner data');
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { data, status, loading, error, refresh: fetchData };
}
