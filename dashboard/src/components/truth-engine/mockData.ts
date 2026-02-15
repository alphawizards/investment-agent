/**
 * Mock Data for Truth Engine
 * ==========================
 * Demo data with Graveyard counts (rejected trials).
 * Simulates Renaissance-style strategy validation.
 */

import { StrategyMetrics, MarketRegime, EquityPoint, DrawdownPoint } from '../../types/strategy';

// Generate equity curve with regime data
function generateEquityCurve(days: number = 252): EquityPoint[] {
    const curve: EquityPoint[] = [];
    let value = 100;
    const regimes: MarketRegime[] = ['BULL', 'BEAR', 'HIGH_VOL', 'SIDEWAYS'];
    let currentRegime: MarketRegime = 'BULL';

    for (let i = 0; i < days; i++) {
        // Switch regime occasionally
        if (Math.random() < 0.03) {
            currentRegime = regimes[Math.floor(Math.random() * regimes.length)];
        }

        // Generate return based on regime
        const baseReturn = currentRegime === 'BULL' ? 0.001 :
            currentRegime === 'BEAR' ? -0.0005 :
                currentRegime === 'HIGH_VOL' ? 0.0002 : 0.0001;
        const volatility = currentRegime === 'HIGH_VOL' ? 0.03 : 0.015;

        value *= (1 + baseReturn + (Math.random() - 0.5) * volatility);

        const date = new Date(2023, 0, 1);
        date.setDate(date.getDate() + i);

        curve.push({
            date: date.toISOString().split('T')[0],
            value: Math.round(value * 100) / 100,
            regime: currentRegime
        });
    }

    return curve;
}

// Generate drawdown series
function generateDrawdown(equityCurve: EquityPoint[]): DrawdownPoint[] {
    let peak = equityCurve[0].value;
    return equityCurve.map(point => {
        peak = Math.max(peak, point.value);
        const dd = (point.value - peak) / peak;
        return {
            date: point.date,
            drawdown: Math.round(dd * 10000) / 10000
        };
    });
}

// === MOCK STRATEGIES ===
// These demonstrate the "Graveyard" - strategies that failed validation

export const MOCK_STRATEGIES: StrategyMetrics[] = [
    {
        id: 'momentum-alpha',
        name: 'Residual Momentum Alpha',
        returns: { cagr: 0.18, win_rate: 0.58, total_return: 0.42 },
        risk: { max_drawdown: -0.14, tail_ratio: 1.8, volatility: 0.16 },
        efficiency: { sharpe: 1.45, sortino: 2.1, calmar: 1.28 },
        validity: {
            psr: 0.97,        // ✓ Significant
            dsr: 1.24,        // ✓ Green badge
            num_trials: 15,   // Only 15 variations tested
            is_significant: true,
            confidence_level: 'HIGH'
        },
        regime_performance: [
            { regime: 'BULL', sharpe: 1.8, return_pct: 0.24, days: 120 },
            { regime: 'BEAR', sharpe: 0.4, return_pct: 0.02, days: 40 },
            { regime: 'HIGH_VOL', sharpe: 0.9, return_pct: 0.08, days: 50 },
            { regime: 'SIDEWAYS', sharpe: 1.1, return_pct: 0.08, days: 42 }
        ],
        equity_curve: generateEquityCurve(252),
        drawdown_series: []
    },
    {
        id: 'hmm-regime',
        name: 'HMM Regime Allocation',
        returns: { cagr: 0.15, win_rate: 0.54, total_return: 0.35 },
        risk: { max_drawdown: -0.18, tail_ratio: 1.5, volatility: 0.14 },
        efficiency: { sharpe: 1.12, sortino: 1.6, calmar: 0.83 },
        validity: {
            psr: 0.94,        // Just below 95% threshold
            dsr: 0.78,        // ⚠️ Yellow badge - borderline
            num_trials: 48,   // Many variations tested
            is_significant: false,
            confidence_level: 'MEDIUM'
        },
        regime_performance: [
            { regime: 'BULL', sharpe: 1.4, return_pct: 0.18, days: 110 },
            { regime: 'BEAR', sharpe: 0.8, return_pct: 0.05, days: 60 },
            { regime: 'HIGH_VOL', sharpe: 0.6, return_pct: 0.04, days: 45 },
            { regime: 'SIDEWAYS', sharpe: 1.0, return_pct: 0.08, days: 37 }
        ],
        equity_curve: generateEquityCurve(252),
        drawdown_series: []
    },
    {
        id: 'stat-arb-pairs',
        name: 'Statistical Arbitrage Pairs',
        returns: { cagr: 0.22, win_rate: 0.62, total_return: 0.55 },
        risk: { max_drawdown: -0.08, tail_ratio: 2.4, volatility: 0.12 },
        efficiency: { sharpe: 1.92, sortino: 2.8, calmar: 2.75 },
        validity: {
            psr: 0.99,        // ✓ Very significant
            dsr: 1.65,        // ✓ Strong green badge
            num_trials: 8,    // Few variations tested
            is_significant: true,
            confidence_level: 'HIGH'
        },
        regime_performance: [
            { regime: 'BULL', sharpe: 1.6, return_pct: 0.20, days: 100 },
            { regime: 'BEAR', sharpe: 2.1, return_pct: 0.18, days: 50 },
            { regime: 'HIGH_VOL', sharpe: 2.4, return_pct: 0.12, days: 62 },
            { regime: 'SIDEWAYS', sharpe: 1.7, return_pct: 0.05, days: 40 }
        ],
        equity_curve: generateEquityCurve(252),
        drawdown_series: []
    },
    {
        id: 'ml-predictor',
        name: 'ML Return Predictor',
        returns: { cagr: 0.28, win_rate: 0.55, total_return: 0.72 },
        risk: { max_drawdown: -0.25, tail_ratio: 1.2, volatility: 0.24 },
        efficiency: { sharpe: 1.18, sortino: 1.4, calmar: 1.12 },
        validity: {
            psr: 0.82,        // ✗ Not significant
            dsr: 0.32,        // ✗ RED badge - likely overfit
            num_trials: 247,  // GRAVEYARD: 247 variations tested!
            is_significant: false,
            confidence_level: 'LOW'
        },
        regime_performance: [
            { regime: 'BULL', sharpe: 1.5, return_pct: 0.30, days: 90 },
            { regime: 'BEAR', sharpe: -0.2, return_pct: -0.05, days: 70 },
            { regime: 'HIGH_VOL', sharpe: 0.3, return_pct: 0.02, days: 52 },
            { regime: 'SIDEWAYS', sharpe: 0.8, return_pct: 0.08, days: 40 }
        ],
        equity_curve: generateEquityCurve(252),
        drawdown_series: []
    },
    {
        id: 'dual-momentum',
        name: 'Dual Momentum ETF',
        returns: { cagr: 0.12, win_rate: 0.52, total_return: 0.28 },
        risk: { max_drawdown: -0.16, tail_ratio: 1.4, volatility: 0.13 },
        efficiency: { sharpe: 0.95, sortino: 1.3, calmar: 0.75 },
        validity: {
            psr: 0.91,        // Borderline
            dsr: 0.85,        // ⚠️ Yellow
            num_trials: 22,
            is_significant: false,
            confidence_level: 'MEDIUM'
        },
        regime_performance: [
            { regime: 'BULL', sharpe: 1.2, return_pct: 0.15, days: 115 },
            { regime: 'BEAR', sharpe: 0.1, return_pct: 0.01, days: 55 },
            { regime: 'HIGH_VOL', sharpe: 0.5, return_pct: 0.04, days: 48 },
            { regime: 'SIDEWAYS', sharpe: 0.7, return_pct: 0.08, days: 34 }
        ],
        equity_curve: generateEquityCurve(252),
        drawdown_series: []
    }
];

// Add drawdown series
MOCK_STRATEGIES.forEach(s => {
    s.drawdown_series = generateDrawdown(s.equity_curve);
});

// Graveyard Statistics
export const GRAVEYARD_STATS = {
    total_trials_tested: MOCK_STRATEGIES.reduce((sum, s) => sum + s.validity.num_trials, 0),
    trials_accepted: MOCK_STRATEGIES.filter(s => s.validity.is_significant).length,
    trials_rejected: MOCK_STRATEGIES.filter(s => !s.validity.is_significant).length,
    acceptance_rate: MOCK_STRATEGIES.filter(s => s.validity.is_significant).length / MOCK_STRATEGIES.length
};
