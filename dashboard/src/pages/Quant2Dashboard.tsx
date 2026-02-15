/**
 * Quant 2.0 Dashboard Page
 * ========================
 * Advanced strategies: Regime Detection, Stat Arb, Residual Momentum,
 * Meta-Labeling, Short Vol, NCO
 */

import React from 'react';
import { Brain, RefreshCw, AlertCircle } from 'lucide-react';
import { useQuant2, Quant2Regime } from '../hooks/useQuant2';
import { formatCurrency } from '../hooks/useMetrics';

const STRATEGY_LABELS: Record<string, string> = {
  Regime_Detection: 'Regime Detection',
  Stat_Arb: 'Statistical Arbitrage',
  Residual_Momentum: 'Residual Momentum',
  Meta_Labeling: 'Meta-Labeling',
  Short_Vol: 'Short Volatility',
  NCO: 'Nested Cluster Optimization',
};

const REGIME_COLORS: Record<string, { bg: string; text: string; border: string; bar: string }> = {
  BULL: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-300', bar: 'bg-green-500' },
  BEAR: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-300', bar: 'bg-red-500' },
  HIGH_VOL: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-300', bar: 'bg-amber-500' },
  SIDEWAYS: { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-300', bar: 'bg-gray-500' },
  UNKNOWN: { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-300', bar: 'bg-slate-500' },
};

export const Quant2Dashboard: React.FC = () => {
  const { data, loading, error, refresh } = useQuant2();

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
  const regime = data?.regime;

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Brain className="w-6 h-6 text-purple-600" />
              Quant 2.0 Strategies
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Regime Detection + ML-Enhanced Strategies &middot; {data?.universe?.name ?? data?.universe_key ?? 'SPX500'} ({data?.ticker_count ?? 0} tickers)
            </p>
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

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {regime && <RegimeCard regime={regime} />}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(strategies).map(([key, strategy]) => (
            <StrategyCard key={key} name={STRATEGY_LABELS[key] || key} strategy={strategy} />
          ))}
        </div>
      </main>
    </div>
  );
};

/* ── Regime Indicator Card ── */

const RegimeCard: React.FC<{ regime: Quant2Regime }> = ({ regime }) => {
  const colors = REGIME_COLORS[regime.current] || REGIME_COLORS.UNKNOWN;

  const probEntries: { label: string; key: string }[] = [
    { label: 'Bull', key: 'bull' },
    { label: 'Bear', key: 'bear' },
    { label: 'Sideways', key: 'sideways' },
  ];

  return (
    <div className={`bg-white rounded-xl border ${colors.border} p-6`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Market Regime</h2>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${colors.bg} ${colors.text}`}>
          {regime.current.replace('_', ' ')}
        </span>
      </div>

      {regime.message && (
        <p className="text-sm text-gray-500 mb-4">{regime.message}</p>
      )}

      <div className="space-y-3">
        {probEntries.map(({ label, key }) => {
          const value = regime.probabilities[key as keyof typeof regime.probabilities] ?? 0;
          const barColor = key === 'bull' ? 'bg-green-500' : key === 'bear' ? 'bg-red-500' : 'bg-gray-400';
          return (
            <div key={key}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-600">{label}</span>
                <span className="font-medium text-gray-900">{(value * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className={`${barColor} h-2 rounded-full transition-all`} style={{ width: `${Math.min(value * 100, 100)}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ── Strategy Card ── */

interface StrategyCardProps {
  name: string;
  strategy: { status: string; metrics?: Record<string, any>; final_value?: number; message?: string };
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
    </div>
  );
};

const MetricRow: React.FC<{ label: string; value: any }> = ({ label, value }) => (
  <div>
    <span className="text-gray-500">{label}</span>
    <span className="ml-2 font-medium text-gray-900">{value ?? 'N/A'}</span>
  </div>
);

export default Quant2Dashboard;
