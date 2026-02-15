/**
 * Drawdown Chart Component
 * ========================
 * Underwater equity chart showing drawdown periods.
 */

import React from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
} from 'recharts';
import { DrawdownPoint } from '../../types/strategy';

interface DrawdownChartProps {
    data: DrawdownPoint[];
    title?: string;
}

export const DrawdownChart: React.FC<DrawdownChartProps> = ({ data, title = 'Drawdown Analysis' }) => {
    // Custom tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const point = payload[0].payload as DrawdownPoint;
            const ddPct = (point.drawdown * 100).toFixed(2);
            return (
                <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 shadow-xl">
                    <p className="text-slate-400 text-xs mb-1">{point.date}</p>
                    <p className={`font-mono text-lg font-semibold ${point.drawdown < -0.1 ? 'text-red-400' : 'text-amber-400'
                        }`}>
                        {ddPct}%
                    </p>
                </div>
            );
        }
        return null;
    };

    // Find max drawdown
    const maxDD = Math.min(...data.map(d => d.drawdown));
    const maxDDPct = (maxDD * 100).toFixed(1);

    return (
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">Max Drawdown:</span>
                    <span className="text-sm font-mono text-red-400 font-semibold">
                        {maxDDPct}%
                    </span>
                </div>
            </div>

            <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
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
                            stroke="#64748b"
                            tick={{ fill: '#64748b', fontSize: 11 }}
                            tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                            domain={['dataMin', 0]}
                        />

                        <Tooltip content={<CustomTooltip />} />

                        {/* Zero line */}
                        <ReferenceLine y={0} stroke="#64748b" strokeWidth={1} />

                        {/* Max drawdown line */}
                        <ReferenceLine
                            y={maxDD}
                            stroke="#ef4444"
                            strokeDasharray="5 5"
                            label={{ value: `Max DD: ${maxDDPct}%`, position: 'right', fill: '#ef4444', fontSize: 10 }}
                        />

                        {/* Drawdown area */}
                        <Area
                            type="monotone"
                            dataKey="drawdown"
                            stroke="#ef4444"
                            strokeWidth={1}
                            fill="url(#colorDrawdown)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default DrawdownChart;
