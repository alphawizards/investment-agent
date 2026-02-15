/**
 * DSR Badge Component
 * ===================
 * Status badge for Deflated Sharpe Ratio visualization.
 * Green (>1.0), Yellow (0.5-1.0), Red (<0.5)
 */

import React from 'react';
import { getDSRStatus } from '../../types/strategy';

interface DSRBadgeProps {
    dsr: number;
    showValue?: boolean;
}

export const DSRBadge: React.FC<DSRBadgeProps> = ({ dsr, showValue = true }) => {
    const status = getDSRStatus(dsr);

    const statusConfig = {
        success: {
            bg: 'bg-emerald-500/20',
            border: 'border-emerald-500/50',
            text: 'text-emerald-400',
            icon: '✓',
            label: 'VALID'
        },
        warning: {
            bg: 'bg-amber-500/20',
            border: 'border-amber-500/50',
            text: 'text-amber-400',
            icon: '⚠',
            label: 'CAUTION'
        },
        danger: {
            bg: 'bg-red-500/20',
            border: 'border-red-500/50',
            text: 'text-red-400',
            icon: '✗',
            label: 'OVERFIT'
        }
    };

    const config = statusConfig[status];

    return (
        <div className={`
      inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full 
      ${config.bg} ${config.text} border ${config.border}
      font-medium text-xs
    `}>
            <span>{config.icon}</span>
            {showValue && <span>{dsr.toFixed(2)}</span>}
            <span className="uppercase tracking-wide">{config.label}</span>
        </div>
    );
};

interface PSRIndicatorProps {
    psr: number;
    threshold?: number;
}

export const PSRIndicator: React.FC<PSRIndicatorProps> = ({ psr, threshold = 0.95 }) => {
    const isSignificant = psr >= threshold;
    const percentage = (psr * 100).toFixed(1);

    return (
        <div className="flex items-center gap-2">
            <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                    className={`h-full rounded-full transition-all ${isSignificant ? 'bg-emerald-500' : 'bg-slate-500'
                        }`}
                    style={{ width: `${Math.min(100, psr * 100)}%` }}
                />
            </div>
            <span className={`text-sm font-mono ${isSignificant ? 'text-emerald-400' : 'text-slate-400'
                }`}>
                {percentage}%
            </span>
        </div>
    );
};

interface GraveyardBadgeProps {
    trials: number;
}

export const GraveyardBadge: React.FC<GraveyardBadgeProps> = ({ trials }) => {
    // More trials = more potential overfitting
    const severity = trials > 100 ? 'danger' : trials > 50 ? 'warning' : 'neutral';

    const colors = {
        danger: 'bg-red-500/10 text-red-400 border-red-500/30',
        warning: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        neutral: 'bg-slate-500/10 text-slate-400 border-slate-500/30'
    };

    return (
        <div className={`
      inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-mono
      ${colors[severity]}
    `}>
            <span>⚰️</span>
            <span>{trials}</span>
        </div>
    );
};

export default DSRBadge;
