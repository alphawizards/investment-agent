/**
 * Custom Hooks for Trade Data
 * ===========================
 * React hooks for fetching and managing trade data.
 */

import { useState, useEffect, useCallback } from 'react';
import tradeApi from '../api/trades';
import type {
  Trade,
  TradeListResponse,
  TradeFilters,
  DashboardSummary,
  PortfolioMetrics,
} from '../types/trade';

/**
 * Hook for fetching paginated trades
 */
export function useTrades(
  initialPage: number = 1,
  initialPageSize: number = 50,
  initialFilters?: TradeFilters
) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState<TradeFilters>(initialFilters || {});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTrades = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response: TradeListResponse = await tradeApi.getAll(
        page,
        pageSize,
        filters
      );
      setTrades(response.trades);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch trades');
      setTrades([]);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filters]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  const refresh = useCallback(() => {
    fetchTrades();
  }, [fetchTrades]);

  const updateFilters = useCallback((newFilters: TradeFilters) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page when filters change
  }, []);

  const nextPage = useCallback(() => {
    if (page < totalPages) setPage((p) => p + 1);
  }, [page, totalPages]);

  const prevPage = useCallback(() => {
    if (page > 1) setPage((p) => p - 1);
  }, [page]);

  const goToPage = useCallback(
    (newPage: number) => {
      if (newPage >= 1 && newPage <= totalPages) setPage(newPage);
    },
    [totalPages]
  );

  return {
    trades,
    total,
    page,
    pageSize,
    totalPages,
    filters,
    loading,
    error,
    refresh,
    setPage,
    setPageSize,
    updateFilters,
    nextPage,
    prevPage,
    goToPage,
  };
}

/**
 * Hook for fetching dashboard summary
 */
export function useDashboard(initialCapital: number = 100000) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await tradeApi.getDashboardSummary(initialCapital);
      setSummary(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to fetch dashboard'
      );
    } finally {
      setLoading(false);
    }
  }, [initialCapital]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const refresh = useCallback(() => {
    fetchSummary();
  }, [fetchSummary]);

  return { summary, loading, error, refresh };
}

/**
 * Hook for fetching portfolio metrics
 */
export function usePortfolioMetrics(initialCapital: number = 100000) {
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await tradeApi.getPortfolioMetrics(initialCapital);
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
    } finally {
      setLoading(false);
    }
  }, [initialCapital]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const refresh = useCallback(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { metrics, loading, error, refresh };
}

/**
 * Hook for auto-refreshing data at intervals
 */
export function useAutoRefresh(
  refreshFn: () => void,
  intervalMs: number = 30000,
  enabled: boolean = true
) {
  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(refreshFn, intervalMs);
    return () => clearInterval(interval);
  }, [refreshFn, intervalMs, enabled]);
}
