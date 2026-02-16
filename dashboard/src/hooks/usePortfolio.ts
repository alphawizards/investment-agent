/**
 * Global Portfolio Hooks
 * =====================
 * React Query hooks for global portfolio state management.
 * These hooks provide centralized data fetching and caching.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

// Types
export interface PortfolioMetrics {
  total_value: number;
  cash_balance: number;
  invested_value: number;
  daily_return?: number;
  total_return?: number;
  volatility?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate?: number;
  total_pnl: number;
  unrealized_pnl?: number;
  avg_pnl_per_trade?: number;
  best_trade?: number;
  worst_trade?: number;
}

export interface Trade {
  id: number;
  trade_id: string;
  ticker: string;
  asset_name?: string;
  direction: 'BUY' | 'SELL';
  quantity: number;
  entry_price: number;
  exit_price?: number;
  commission: number;
  currency: string;
  entry_date: string;
  exit_date?: string;
  pnl?: number;
  pnl_percent?: number;
  strategy_name: string;
  status: 'OPEN' | 'CLOSED' | 'CANCELLED';
}

export interface DashboardSummary {
  portfolio: PortfolioMetrics;
  recent_trades: Trade[];
  open_positions: number;
  today_pnl: number;
  week_pnl: number;
  month_pnl: number;
  last_updated: string;
}

// API Functions
async function fetchDashboardSummary(initialCapital: number = 100000): Promise<DashboardSummary> {
  const { data } = await axios.get<DashboardSummary>(`${API_BASE}/trades/dashboard`, {
    params: { initial_capital: initialCapital }
  });
  return data;
}

async function fetchTrades(page: number = 1, pageSize: number = 50) {
  const { data } = await axios.get(`${API_BASE}/trades/`, {
    params: { page, page_size: pageSize }
  });
  return data;
}

async function fetchValidationData() {
  const { data } = await axios.get(`${API_BASE}/validation/strategies`);
  return data;
}

// Query Keys
export const queryKeys = {
  dashboard: (capital: number) => ['dashboard', capital] as const,
  trades: (page: number, pageSize: number) => ['trades', page, pageSize] as const,
  validation: ['validation'] as const,
  scanner: ['scanner'] as const,
  systemHealth: ['system-health'] as const,
};

// Hooks
export function useDashboard(initialCapital: number = 100000) {
  return useQuery({
    queryKey: queryKeys.dashboard(initialCapital),
    queryFn: () => fetchDashboardSummary(initialCapital),
    staleTime: 1000 * 60, // 1 minute
    gcTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useTrades(page: number = 1, pageSize: number = 50) {
  return useQuery({
    queryKey: queryKeys.trades(page, pageSize),
    queryFn: () => fetchTrades(page, pageSize),
    staleTime: 1000 * 30, // 30 seconds
  });
}

export function useValidationData() {
  return useQuery({
    queryKey: queryKeys.validation,
    queryFn: fetchValidationData,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useSystemHealth() {
  return useQuery({
    queryKey: queryKeys.systemHealth,
    queryFn: async () => {
      const { data } = await axios.get(`${API_BASE}/data/status`);
      return data;
    },
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: 1000 * 60, // Refresh every minute
  });
}

// Mutation Hook for invalidating queries
export function useInvalidatePortfolio() {
  const queryClient = useQueryClient();
  
  return () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['trades'] });
  };
}

// Toast helper for API errors
export function handleApiError(error: unknown, operation: string = 'operation') {
  const message = error instanceof Error ? error.message : 'An unexpected error occurred';
  toast.error(`${operation} failed`, {
    description: message,
  });
}
