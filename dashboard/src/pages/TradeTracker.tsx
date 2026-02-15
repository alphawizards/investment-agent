/**
 * Dashboard Layout Component
 * ==========================
 * Main dashboard container with metrics and trade history.
 */

import React from 'react';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  BarChart2,
  Clock,
  Award,
} from 'lucide-react';
import { MetricCard, MetricGrid } from '../metrics/MetricCard';
import { TradeTable } from '../trades/TradeTable';
import { TradeFilters } from '../trades/TradeFilters';
import { useTrades, useDashboard } from '../../hooks/useTrades';
import { formatCurrency, formatPercent } from '../../hooks/useMetrics';
import type { TradeFilters as TradeFiltersType } from '../../types/trade';
import CONFIG from '../../config';

export const Dashboard: React.FC = () => {
  const {
    trades,
    total,
    page,
    pageSize,
    totalPages,
    filters,
    loading: tradesLoading,
    updateFilters,
    goToPage,
  } = useTrades(1, 50);

  const { summary } = useDashboard(CONFIG.INITIAL_CAPITAL);

  const handleFilterChange = (newFilters: TradeFiltersType) => {
    updateFilters(newFilters);
  };

  const handleClearFilters = () => {
    updateFilters({});
  };

  const handleSort = (column: string, desc: boolean) => {
    updateFilters({ ...filters, sort_by: column, sort_desc: desc });
  };

  const portfolio = summary?.portfolio;

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Trading Dashboard
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Quantitative Strategy Performance
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-gray-500">Last Updated</p>
                <p className="text-sm font-medium text-gray-900">
                  {summary?.last_updated
                    ? new Date(summary.last_updated).toLocaleString('en-AU')
                    : '-'}
                </p>
              </div>
              <div className="h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Portfolio Value Section */}
        <div className="mb-6">
          <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 text-sm font-medium">
                  Portfolio Value
                </p>
                <p className="text-4xl font-bold mt-1">
                  {portfolio ? formatCurrency(portfolio.total_value) : '$0.00'}
                </p>
                <div className="flex items-center gap-4 mt-2">
                  <span className="text-blue-100">
                    Total Return:{' '}
                    <span className={portfolio?.total_return && portfolio.total_return >= 0 ? 'text-green-300' : 'text-red-300'}>
                      {portfolio?.total_return
                        ? formatPercent(portfolio.total_return)
                        : '0.00%'}
                    </span>
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <p className="text-blue-100 text-xs">Today</p>
                    <p className={`text-lg font-semibold ${(summary?.today_pnl || 0) >= 0 ? 'text-green-300' : 'text-red-300'
                      }`}>
                      {formatCurrency(summary?.today_pnl || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-blue-100 text-xs">This Week</p>
                    <p className={`text-lg font-semibold ${(summary?.week_pnl || 0) >= 0 ? 'text-green-300' : 'text-red-300'
                      }`}>
                      {formatCurrency(summary?.week_pnl || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-blue-100 text-xs">This Month</p>
                    <p className={`text-lg font-semibold ${(summary?.month_pnl || 0) >= 0 ? 'text-green-300' : 'text-red-300'
                      }`}>
                      {formatCurrency(summary?.month_pnl || 0)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Metrics Grid */}
        <MetricGrid columns={4} className="mb-6">
          <MetricCard
            label="Unrealized P&L"
            value={portfolio?.unrealized_pnl || 0}
            format="currency"
            icon={DollarSign}
            iconColor={
              (portfolio?.unrealized_pnl || 0) >= 0
                ? 'text-green-500'
                : 'text-red-500'
            }
          />
          <MetricCard
            label="Total P&L"
            value={portfolio?.total_pnl || 0}
            format="currency"
            icon={DollarSign}
            iconColor={
              (portfolio?.total_pnl || 0) >= 0
                ? 'text-green-500'
                : 'text-red-500'
            }
          />
          <MetricCard
            label="Win Rate"
            value={portfolio?.win_rate || 0}
            format="percent"
            icon={Target}
            iconColor="text-blue-500"
          />
          <MetricCard
            label="Total Trades"
            value={portfolio?.total_trades || 0}
            format="number"
            icon={BarChart2}
            iconColor="text-purple-500"
          />
          <MetricCard
            label="Open Positions"
            value={summary?.open_positions || 0}
            format="number"
            icon={Clock}
            iconColor="text-orange-500"
          />
        </MetricGrid>

        {/* Secondary Metrics */}
        <MetricGrid columns={4} className="mb-6">
          <MetricCard
            label="Winning Trades"
            value={portfolio?.winning_trades || 0}
            format="number"
            icon={TrendingUp}
            iconColor="text-green-500"
          />
          <MetricCard
            label="Losing Trades"
            value={portfolio?.losing_trades || 0}
            format="number"
            icon={TrendingDown}
            iconColor="text-red-500"
          />
          <MetricCard
            label="Best Trade"
            value={portfolio?.best_trade || 0}
            format="currency"
            icon={Award}
            iconColor="text-yellow-500"
          />
          <MetricCard
            label="Avg P&L / Trade"
            value={portfolio?.avg_pnl_per_trade || 0}
            format="currency"
            icon={Activity}
            iconColor="text-indigo-500"
          />
        </MetricGrid>

        {/* Trade Filters */}
        <TradeFilters
          filters={filters}
          onFilterChange={handleFilterChange}
          onClear={handleClearFilters}
        />

        {/* Trade History Table */}
        <TradeTable
          trades={trades}
          total={total}
          page={page}
          pageSize={pageSize}
          totalPages={totalPages}
          loading={tradesLoading}
          onPageChange={goToPage}
          onSort={handleSort}
          sortBy={filters.sort_by}
          sortDesc={filters.sort_desc}
        />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span>Quant Trading Dashboard v1.0.0</span>
            <span>Trade Fee: $3 AUD per trade</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;
