/**
 * Scanner Dashboard Page
 * ======================
 * Quallamaggie momentum scanner results.
 */

import React from 'react';
import { Search, RefreshCw, AlertCircle, Zap } from 'lucide-react';
import { useScanner } from '../hooks/useScanner';
import { formatCurrency, formatNumber } from '../hooks/useMetrics';

const SIGNAL_COLORS: Record<string, string> = {
  BUY: 'bg-green-100 text-green-700',
  STRONG_BUY: 'bg-emerald-100 text-emerald-700',
  WATCH: 'bg-amber-100 text-amber-700',
  HOLD: 'bg-gray-100 text-gray-600',
  SELL: 'bg-red-100 text-red-700',
};

export const ScannerDashboard: React.FC = () => {
  const { data, status, loading, error, refresh } = useScanner();

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

  const results = data?.results ?? [];
  const scanStatus = status?.status ?? 'unknown';

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Search className="w-6 h-6 text-orange-500" />
              Stock Scanner
            </h1>
            <p className="text-sm text-gray-500 mt-1">Quallamaggie Breakout Signals</p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={scanStatus} />
            {data?.generated_at && (
              <span className="text-xs text-gray-400">
                {new Date(data.generated_at).toLocaleString('en-AU')}
              </span>
            )}
            <button onClick={refresh} className="p-2 rounded-lg hover:bg-gray-100 transition-colors" title="Refresh">
              <RefreshCw className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {results.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <Zap className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">No scan results available.</p>
            <p className="text-sm text-gray-400 mt-1">Run a scan from the API to generate signals.</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Scan Results</h2>
              <span className="text-sm text-gray-500">{data?.total_found ?? 0} signals found</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 uppercase text-xs tracking-wide">
                  <tr>
                    <th className="px-6 py-3 text-left">Ticker</th>
                    <th className="px-6 py-3 text-right">Price</th>
                    <th className="px-6 py-3 text-right">Change</th>
                    <th className="px-6 py-3 text-right">Volume</th>
                    <th className="px-6 py-3 text-center">Signal</th>
                    <th className="px-6 py-3 text-right">Score</th>
                    <th className="px-6 py-3 text-left">Pattern</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {results.map((r) => (
                    <tr key={r.ticker} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-3 font-medium text-gray-900">{r.ticker}</td>
                      <td className="px-6 py-3 text-right text-gray-700">{formatCurrency(r.price, 'USD')}</td>
                      <td className={`px-6 py-3 text-right font-medium ${r.change_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {r.change_pct >= 0 ? '+' : ''}{r.change_pct.toFixed(2)}%
                      </td>
                      <td className="px-6 py-3 text-right text-gray-500">{formatNumber(r.volume)}</td>
                      <td className="px-6 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${SIGNAL_COLORS[r.signal] ?? 'bg-gray-100 text-gray-600'}`}>
                          {r.signal}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 bg-gray-100 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${r.score >= 70 ? 'bg-green-500' : r.score >= 40 ? 'bg-amber-500' : 'bg-gray-400'}`}
                              style={{ width: `${Math.min(r.score, 100)}%` }}
                            />
                          </div>
                          <span className="text-gray-700 w-8 text-right">{r.score}</span>
                        </div>
                      </td>
                      <td className="px-6 py-3 text-gray-500">{r.details?.pattern ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    idle: 'bg-gray-100 text-gray-600',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
  };
  const isFailed = status.startsWith('failed');
  const cls = isFailed ? 'bg-red-100 text-red-700' : (colors[status] ?? 'bg-gray-100 text-gray-600');
  const label = isFailed ? 'Failed' : status.charAt(0).toUpperCase() + status.slice(1);

  return <span className={`px-2 py-1 rounded text-xs font-medium ${cls}`}>{label}</span>;
};

export default ScannerDashboard;
