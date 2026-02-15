/**
 * Truth Engine Dashboard Page
 * ===========================
 * Institutional-grade strategy validation dashboard.
 * Displays DSR/PSR metrics, graveyard statistics, and regime analysis.
 */

import React, { useState, useMemo } from 'react';
import {
    AlphaMatrix,
    RegimeChart,
    DrawdownChart,
    MOCK_STRATEGIES,
    GRAVEYARD_STATS
} from '../components/truth-engine';
import { StrategyMetrics } from '../types/strategy';
import {
    Shield,
    AlertTriangle,
    CheckCircle,
    XCircle,
    TrendingUp,
    Activity
} from 'lucide-react';

export const TruthEngine: React.FC = () => {
    const [selectedStrategy, setSelectedStrategy] = useState<StrategyMetrics | null>(
        MOCK_STRATEGIES[0]
    );

    // Derive summary stats
    const summaryStats = useMemo(() => {
        const significant = MOCK_STRATEGIES.filter(s => s.validity.is_significant);
        const avgDSR = MOCK_STRATEGIES.reduce((sum, s) => sum + s.validity.dsr, 0) / MOCK_STRATEGIES.length;
        const avgPSR = MOCK_STRATEGIES.reduce((sum, s) => sum + s.validity.psr, 0) / MOCK_STRATEGIES.length;

        return {
            total: MOCK_STRATEGIES.length,
            significant: significant.length,
            rejected: MOCK_STRATEGIES.length - significant.length,
            avgDSR: avgDSR.toFixed(2),
            avgPSR: (avgPSR * 100).toFixed(1),
            totalTrials: GRAVEYARD_STATS.total_trials_tested
        };
    }, []);

    return (
        <div className="min-h-screen bg-slate-950 text-white">
            {/* Header */}
            <header className="bg-slate-900/80 backdrop-blur-lg border-b border-slate-800 px-6 py-4 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center">
                            <Shield className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white">Truth Engine</h1>
                            <p className="text-xs text-slate-500">Statistical Validity Dashboard</p>
                        </div>
                    </div>

                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">

                {/* Summary Stats Bar */}
                <section className="grid grid-cols-6 gap-4">
                    <StatCard
                        icon={<Activity className="w-5 h-5" />}
                        label="Strategies"
                        value={summaryStats.total.toString()}
                        color="slate"
                    />
                    <StatCard
                        icon={<CheckCircle className="w-5 h-5" />}
                        label="Significant"
                        value={summaryStats.significant.toString()}
                        color="emerald"
                    />
                    <StatCard
                        icon={<XCircle className="w-5 h-5" />}
                        label="Rejected"
                        value={summaryStats.rejected.toString()}
                        color="red"
                    />
                    <StatCard
                        icon={<Shield className="w-5 h-5" />}
                        label="Avg DSR"
                        value={summaryStats.avgDSR}
                        color="cyan"
                    />
                    <StatCard
                        icon={<TrendingUp className="w-5 h-5" />}
                        label="Avg PSR"
                        value={`${summaryStats.avgPSR}%`}
                        color="violet"
                    />
                    <StatCard
                        icon={<AlertTriangle className="w-5 h-5" />}
                        label="⚰️ Graveyard"
                        value={summaryStats.totalTrials.toString()}
                        color="amber"
                    />
                </section>

                {/* Alpha Matrix */}
                <section>
                    <AlphaMatrix
                        strategies={MOCK_STRATEGIES}
                        onSelectStrategy={setSelectedStrategy}
                    />
                </section>

                {/* Microscope View */}
                {selectedStrategy && (
                    <section className="space-y-6">
                        <div className="flex items-center gap-3">
                            <h2 className="text-lg font-semibold text-slate-100">
                                🔬 Microscope: {selectedStrategy.name}
                            </h2>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${selectedStrategy.validity.is_significant
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : 'bg-red-500/20 text-red-400'
                                }`}>
                                {selectedStrategy.validity.is_significant ? 'VALIDATED' : 'NOT SIGNIFICANT'}
                            </span>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Regime Chart */}
                            <RegimeChart
                                data={selectedStrategy.equity_curve}
                                title={`${selectedStrategy.name} - Equity Curve`}
                            />

                            {/* Drawdown Chart */}
                            <DrawdownChart
                                data={selectedStrategy.drawdown_series}
                                title="Underwater Analysis"
                            />
                        </div>

                        {/* Regime Performance Breakdown */}
                        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                            <h3 className="text-lg font-semibold text-slate-100 mb-4">
                                Regime Performance Breakdown
                            </h3>
                            <div className="grid grid-cols-4 gap-4">
                                {selectedStrategy.regime_performance.map((rp, i) => (
                                    <div key={i} className="bg-slate-800/50 rounded-xl p-4">
                                        <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">
                                            {rp.regime}
                                        </div>
                                        <div className="text-2xl font-bold text-slate-100 mb-1">
                                            {rp.sharpe.toFixed(2)}
                                        </div>
                                        <div className="text-xs text-slate-400">
                                            Sharpe • {(rp.return_pct * 100).toFixed(1)}% return
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">
                                            {rp.days} days
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
};

// Stat Card Component
interface StatCardProps {
    icon: React.ReactNode;
    label: string;
    value: string;
    color: 'slate' | 'emerald' | 'red' | 'cyan' | 'violet' | 'amber';
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, color }) => {
    const colorClasses = {
        slate: 'text-slate-400 border-slate-700',
        emerald: 'text-emerald-400 border-emerald-500/30',
        red: 'text-red-400 border-red-500/30',
        cyan: 'text-cyan-400 border-cyan-500/30',
        violet: 'text-violet-400 border-violet-500/30',
        amber: 'text-amber-400 border-amber-500/30',
    };

    return (
        <div className={`bg-slate-900/50 rounded-xl border ${colorClasses[color]} p-4`}>
            <div className="flex items-center gap-2 mb-2">
                <span className={colorClasses[color]}>{icon}</span>
                <span className="text-xs text-slate-500 uppercase tracking-wide">{label}</span>
            </div>
            <div className={`text-2xl font-bold ${colorClasses[color]}`}>
                {value}
            </div>
        </div>
    );
};

export default TruthEngine;
