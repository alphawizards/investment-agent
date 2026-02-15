/**
 * Strategy Metrics Types
 * ======================
 * TypeScript interfaces for Truth Engine Dashboard.
 * Renaissance-style statistical validity metrics.
 */

export type MarketRegime = 'BULL' | 'BEAR' | 'HIGH_VOL' | 'SIDEWAYS';

export interface StrategyMetrics {
    id: string;
    name: string;
    returns: {
        cagr: number;
        win_rate: number;
        total_return: number;
    };
    risk: {
        max_drawdown: number;
        tail_ratio: number;
        volatility: number;
    };
    efficiency: {
        sharpe: number;
        sortino: number;
        calmar: number;
    };
    validity: {
        psr: number;           // 0.0 to 1.0 - Probabilistic Sharpe Ratio
        dsr: number;           // Deflated Sharpe Ratio
        num_trials: number;    // The "Graveyard" count
        is_significant: boolean;
        confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
    };
    regime_performance: RegimePerformance[];
    equity_curve: EquityPoint[];
    drawdown_series: DrawdownPoint[];
}

export interface RegimePerformance {
    regime: MarketRegime;
    sharpe: number;
    return_pct: number;
    days: number;
}

export interface EquityPoint {
    date: string;
    value: number;
    regime: MarketRegime;
}

export interface DrawdownPoint {
    date: string;
    drawdown: number; // Negative percentage (e.g., -0.15 = -15%)
}

export interface ValidationResponse {
    strategies: StrategyMetrics[];
    total_trials_rejected: number;
    total_trials_accepted: number;
    generated_at: string;
}

// Badge status helper
export function getDSRStatus(dsr: number): 'success' | 'warning' | 'danger' {
    if (dsr >= 1.0) return 'success';
    if (dsr >= 0.5) return 'warning';
    return 'danger';
}

// PSR significance check
export function isPSRSignificant(psr: number): boolean {
    return psr >= 0.95;
}
