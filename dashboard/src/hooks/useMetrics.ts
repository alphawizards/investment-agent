/**
 * Metrics Calculation Hook
 * ========================
 * Client-side metric calculations and formatting.
 */

import { useMemo } from 'react';
import type { Trade } from '../types/trade';

/**
 * Format currency values
 */
export function formatCurrency(value: number, currency: string = 'AUD'): string {
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format percentage values
 */
export function formatPercent(value: number, decimals: number = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Format number with commas
 */
export function formatNumber(value: number, decimals: number = 0): string {
  return new Intl.NumberFormat('en-AU', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Get P&L color class
 */
export function getPnlColorClass(value: number): string {
  if (value > 0) return 'text-profit';
  if (value < 0) return 'text-loss';
  return 'text-neutral';
}

/**
 * Get P&L background class
 */
export function getPnlBgClass(value: number): string {
  if (value > 0) return 'bg-profit-light';
  if (value < 0) return 'bg-loss-light';
  return 'bg-neutral-light';
}

/**
 * Hook for calculating derived metrics from trades
 */
export function useTradeMetrics(trades: Trade[]) {
  return useMemo(() => {
    const closedTrades = trades.filter((t) => t.status === 'CLOSED');
    const openTrades = trades.filter((t) => t.status === 'OPEN');

    const pnls = closedTrades
      .map((t) => t.pnl)
      .filter((p): p is number => p !== undefined && p !== null);

    const totalPnl = pnls.reduce((sum, p) => sum + p, 0);
    const winningTrades = pnls.filter((p) => p > 0).length;
    const losingTrades = pnls.filter((p) => p <= 0).length;
    const winRate = pnls.length > 0 ? (winningTrades / pnls.length) * 100 : 0;
    const avgPnl = pnls.length > 0 ? totalPnl / pnls.length : 0;
    const bestTrade = pnls.length > 0 ? Math.max(...pnls) : 0;
    const worstTrade = pnls.length > 0 ? Math.min(...pnls) : 0;

    // Calculate invested value from open positions
    const investedValue = openTrades.reduce(
      (sum, t) => sum + t.entry_price * t.quantity,
      0
    );

    return {
      totalTrades: trades.length,
      closedTrades: closedTrades.length,
      openTrades: openTrades.length,
      totalPnl,
      winningTrades,
      losingTrades,
      winRate,
      avgPnl,
      bestTrade,
      worstTrade,
      investedValue,
    };
  }, [trades]);
}

/**
 * Hook for period-based P&L calculations
 */
export function usePeriodMetrics(trades: Trade[]) {
  return useMemo(() => {
    const now = new Date();
    const todayStart = new Date(now.setHours(0, 0, 0, 0));
    const weekStart = new Date(todayStart);
    weekStart.setDate(weekStart.getDate() - weekStart.getDay());
    const monthStart = new Date(todayStart.getFullYear(), todayStart.getMonth(), 1);

    const closedTrades = trades.filter((t) => t.status === 'CLOSED' && t.exit_date);

    const todayPnl = closedTrades
      .filter((t) => new Date(t.exit_date!) >= todayStart)
      .reduce((sum, t) => sum + (t.pnl || 0), 0);

    const weekPnl = closedTrades
      .filter((t) => new Date(t.exit_date!) >= weekStart)
      .reduce((sum, t) => sum + (t.pnl || 0), 0);

    const monthPnl = closedTrades
      .filter((t) => new Date(t.exit_date!) >= monthStart)
      .reduce((sum, t) => sum + (t.pnl || 0), 0);

    return {
      todayPnl,
      weekPnl,
      monthPnl,
    };
  }, [trades]);
}

/**
 * Format date for display
 */
export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-AU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format datetime for display
 */
export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-AU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Get status badge color
 */
export function getStatusBadgeClass(status: string): string {
  switch (status) {
    case 'OPEN':
      return 'bg-blue-100 text-blue-800';
    case 'CLOSED':
      return 'bg-gray-100 text-gray-800';
    case 'CANCELLED':
      return 'bg-orange-100 text-orange-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * Get direction badge color
 */
export function getDirectionBadgeClass(direction: string): string {
  return direction === 'BUY'
    ? 'bg-green-100 text-green-800'
    : 'bg-red-100 text-red-800';
}
