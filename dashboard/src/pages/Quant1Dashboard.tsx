/**
 * Quant 1.0 Dashboard Page
 * ========================
 * Traditional strategies: Momentum, Dual Momentum, HRP, Inverse Volatility
 */

import React from 'react';
import { TrendingUp, RefreshCw, AlertCircle } from 'lucide-react';
import { useQuant1 } from '../hooks/useQuant1';
import { formatCurrency } from '../hooks/useMetrics';

const STRATEGY_LABELS: Record<string, string> = {
  Momentum: 'Momentum',
  Dual_Momentum: 'Dual Momentum',
  HRP: 'Hierarchical Risk Parity',
  InverseVolatility: 'Inverse Volatility',
};

export const Quant1Dashboard: React.FC = () => {
  const { data, loading, error, refresh } = useQuant1();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700">{error}</span>
          <button onClick={refresh} className="ml-auto text-sm text-red-600 underline">Retry</button>
        </div>
      </div>
    );
  }

  const strategies = data?.strategies ?? {};

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-blue-600" />
              Quant 1.0 Strategies
            </h1>
            <p className="text-sm text-gray-500 mt-1">Dual Momentum + HRP Portfolio Optimization</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400">
              {data?.source === 'cached' ? 'Cached' : 'Live'} &middot; {data?.generated_at ? new Date(data.generated_at).toLocaleString('en-AU') : ''}
            </span>
            <button onClick={refresh} className="p-2 rounded-lg hover:bg-gray-100 transition-colors" title="Refresh">
              <RefreshCw className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {Object.entries(strategies).map(([key, strategy]) => (
            <StrategyCard key={key} name={STRATEGY_LABELS[key] || key} strategy={strategy} />
          ))}
        </div>
      </main>
    </div>
  );
};

interface StrategyCardProps {
  name: string;
  strategy: { status: string; metrics?: Record<string, any>; weights?: Record<string, number>; final_value?: number; message?: string };
}

const StrategyCard: React.FC<StrategyCardProps> = ({ name, strategy }) => {
  if (strategy.status === 'no_data') {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
        <p className="text-sm text-gray-400 mt-2">{strategy.message || 'No data — run backtest to generate'}</p>
      </div>
    );
  }

  const m = strategy.metrics || {};
  const weights = strategy.weights || {};
  const topWeights = Object.entries(weights)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
        <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-700">Active</span>
      </div>

      {strategy.final_value != null && (
        <p className="text-2xl font-bold text-gray-900 mb-4">{formatCurrency(strategy.final_value)}</p>
      )}

      <div className="grid grid-cols-2 gap-3 text-sm">
        <MetricRow label="CAGR" value={m.cagr} />
        <MetricRow label="Sharpe" value={m.sharpe_ratio} />
        <MetricRow label="Max Drawdown" value={m.max_drawdown} />
        <MetricRow label="Win Rate" value={m.win_rate} />
        <MetricRow label="Volatility" value={m.volatility} />
        <MetricRow label="Sortino" value={m.sortino_ratio} />
      </div>

      {topWeights.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Top Holdings</h4>
          <div className="space-y-1">
            {topWeights.map(([ticker, weight]) => (
              <div key={ticker} className="flex items-center justify-between text-sm">
                <span className="font-medium text-gray-700">{ticker}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 bg-gray-100 rounded-full h-1.5">
                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${Math.min(weight * 100, 100)}%` }} />
                  </div>
                  <span className="text-gray-500 w-12 text-right">{(weight * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const MetricRow: React.FC<{ label: string; value: any }> = ({ label, value }) => (
  <div>
    <span className="text-gray-500">{label}</span>
    <span className="ml-2 font-medium text-gray-900">{value ?? 'N/A'}</span>
  </div>
);

export default Quant1Dashboard;
