/**
 * Regime Chart Component
 * ======================
 * Line chart with regime-colored background overlays.
 * BULL = green, BEAR = red, HIGH_VOL = orange, SIDEWAYS = gray
 */

import React, { useMemo } from 'react';
import {
    ComposedChart,
    Area,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceArea,
    ReferenceLine,
} from 'recharts';
import { EquityPoint, MarketRegime } from '../../types/strategy';

interface RegimeChartProps {
    data: EquityPoint[];
    title?: string;
}

const REGIME_COLORS: Record<MarketRegime, string> = {
    BULL: 'rgba(16, 185, 129, 0.15)',      // Emerald
    BEAR: 'rgba(239, 68, 68, 0.15)',       // Red
    HIGH_VOL: 'rgba(245, 158, 11, 0.15)',  // Amber
    SIDEWAYS: 'rgba(100, 116, 139, 0.15)', // Slate
};

const REGIME_LABELS: Record<MarketRegime, string> = {
    BULL: '🐂 Bull',
    BEAR: '🐻 Bear',
    HIGH_VOL: '⚡ High Vol',
    SIDEWAYS: '📊 Sideways',
};

export const RegimeChart: React.FC<RegimeChartProps> = ({ data, title = 'Equity Curve with Regime Overlay' }) => {
    // Calculate regime spans for background rectangles
    const regimeSpans = useMemo(() => {
        const spans: { start: string; end: string; regime: MarketRegime }[] = [];
        if (data.length === 0) return spans;

        let currentSpan = { start: data[0].date, end: data[0].date, regime: data[0].regime };

        for (let i = 1; i < data.length; i++) {
            if (data[i].regime === currentSpan.regime) {
                currentSpan.end = data[i].date;
            } else {
                spans.push({ ...currentSpan });
                currentSpan = { start: data[i].date, end: data[i].date, regime: data[i].regime };
            }
        }
        spans.push(currentSpan);
        return spans;
    }, [data]);

    // Calculate min/max for Y axis
    const yDomain = useMemo(() => {
        const values = data.map(d => d.value);
        const min = Math.min(...values) * 0.95;
        const max = Math.max(...values) * 1.05;
        return [min, max];
    }, [data]);

    // Custom tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const point = payload[0].payload as EquityPoint;
            return (
                <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 shadow-xl">
                    <p className="text-slate-400 text-xs mb-1">{point.date}</p>
                    <p className="text-emerald-400 font-mono text-lg font-semibold">
                        ${point.value.toFixed(2)}
                    </p>
                    <p className="text-xs mt-1" style={{ color: REGIME_COLORS[point.regime].replace('0.15', '1') }}>
                        {REGIME_LABELS[point.regime]}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-100">{title}</h3>

                {/* Legend */}
                <div className="flex items-center gap-4 text-xs">
                    {Object.entries(REGIME_LABELS).map(([regime, label]) => (
                        <div key={regime} className="flex items-center gap-1.5">
                            <div
                                className="w-3 h-3 rounded"
                                style={{ backgroundColor: REGIME_COLORS[regime as MarketRegime].replace('0.15', '0.6') }}
                            />
                            <span className="text-slate-400">{label}</span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                            </linearGradient>
                        </defs>

                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />

                        <XAxis
                            dataKey="date"
                            stroke="#64748b"
                            tick={{ fill: '#64748b', fontSize: 11 }}
                            tickFormatter={(value) => {
                                const date = new Date(value);
                                return date.toLocaleDateString('en-US', { month: 'short' });
                            }}
                            interval="preserveStartEnd"
                        />

                        <YAxis
                            domain={yDomain as [number, number]}
                            stroke="#64748b"
                            tick={{ fill: '#64748b', fontSize: 11 }}
                            tickFormatter={(value) => `$${value.toFixed(0)}`}
                        />

                        <Tooltip content={<CustomTooltip />} />

                        {/* Regime background areas */}
                        {regimeSpans.map((span, i) => (
                            <ReferenceArea
                                key={i}
                                x1={span.start}
                                x2={span.end}
                                fill={REGIME_COLORS[span.regime]}
                                fillOpacity={1}
                            />
                        ))}

                        {/* Starting value reference line */}
                        <ReferenceLine
                            y={100}
                            stroke="#64748b"
                            strokeDasharray="5 5"
                            label={{ value: 'Start', position: 'left', fill: '#64748b', fontSize: 11 }}
                        />

                        {/* Equity curve area */}
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke="#10b981"
                            strokeWidth={2}
                            fill="url(#colorValue)"
                        />

                        {/* Equity curve line */}
                        <Line
                            type="monotone"
                            dataKey="value"
                            stroke="#10b981"
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 6, fill: '#10b981', stroke: '#0f172a', strokeWidth: 2 }}
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default RegimeChart;
