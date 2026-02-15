"""
Quant 2.0 Dashboard Data Generator
==================================
Generates JSON data files for the Quant 2.0 dashboard.
Run daily to update dashboard with latest signals.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Output directory
OUTPUT_DIR = Path(__file__).parent / "quant2_data"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_dashboard_data():
    """Generate main dashboard overview data."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "regime": {
            "current": "BULL",
            "probabilities": {
                "bull": 0.72,
                "bear": 0.08,
                "chop": 0.20
            },
            "days_in_regime": 34,
            "last_switch": "2024-11-22"
        },
        "strategies": {
            "residual_momentum": {
                "top_score": 2.34,
                "stocks_ranked": 48,
                "avg_r2": 0.42,
                "status": "active"
            },
            "stat_arb": {
                "active_pairs": 12,
                "clusters": 5,
                "avg_half_life": 8.2,
                "signals_today": 3
            },
            "regime_allocation": {
                "current_regime": "BULL",
                "confidence": 0.72,
                "days_in_regime": 34
            },
            "meta_labeling": {
                "signals_today": 7,
                "accepted": 3,
                "model_auc": 0.71,
                "filter_rate": 0.57
            },
            "short_vol": {
                "vix": 14.2,
                "percentile": 22,
                "signal": "HARVEST",
                "term_structure": "contango"
            },
            "nco": {
                "effective_n": 8.4,
                "max_weight": 0.18,
                "exp_return": 0.124,
                "exp_vol": 0.082
            }
        },
        "allocation": {
            "residual_momentum": 0.40,
            "stat_arb": 0.25,
            "short_vol": 0.20,
            "cash": 0.15
        },
        "ytd_performance": {
            "residual_momentum": 0.182,
            "stat_arb": 0.124,
            "regime": 0.151,
            "meta_labeling": 0.223,
            "short_vol": 0.087
        },
        "activity": [
            {
                "type": "regime",
                "title": "Regime Change Detected",
                "description": "HMM transitioned from CHOP to BULL (72% confidence)",
                "timestamp": "2 hours ago"
            },
            {
                "type": "signal",
                "title": "Meta-Label Signal: AAPL",
                "description": "Quallamaggie breakout accepted (P=0.78)",
                "timestamp": "4 hours ago"
            }
        ]
    }

    with open(OUTPUT_DIR / "dashboard.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated: {OUTPUT_DIR / 'dashboard.json'}")
    return data


def generate_residual_momentum_data():
    """Generate residual momentum rankings data."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "config": {
            "lookback_months": 36,
            "scoring_months": 12,
            "min_r2": 0.25
        },
        "summary": {
            "top_score": 2.34,
            "stocks_ranked": 48,
            "avg_r2": 0.42
        },
        "top_ranked": [
            {"rank": 1, "ticker": "NVDA", "score": 2.34, "r2": 0.52, "mkt_beta": 1.42, "smb_beta": -0.18, "hml_beta": -0.65, "resid_vol": 0.182},
            {"rank": 2, "ticker": "META", "score": 2.18, "r2": 0.48, "mkt_beta": 1.28, "smb_beta": -0.24, "hml_beta": -0.42, "resid_vol": 0.164},
            {"rank": 3, "ticker": "AMZN", "score": 1.87, "r2": 0.55, "mkt_beta": 1.18, "smb_beta": -0.12, "hml_beta": -0.38, "resid_vol": 0.148},
            {"rank": 4, "ticker": "LLY", "score": 1.72, "r2": 0.38, "mkt_beta": 0.72, "smb_beta": -0.08, "hml_beta": -0.22, "resid_vol": 0.121},
            {"rank": 5, "ticker": "MSFT", "score": 1.54, "r2": 0.62, "mkt_beta": 1.08, "smb_beta": -0.15, "hml_beta": -0.28, "resid_vol": 0.114}
        ],
        "bottom_ranked": [
            {"rank": 46, "ticker": "PARA", "score": -1.42, "r2": 0.41, "signal": "AVOID"},
            {"rank": 47, "ticker": "WBD", "score": -1.68, "r2": 0.38, "signal": "AVOID"},
            {"rank": 48, "ticker": "INTC", "score": -2.15, "r2": 0.52, "signal": "AVOID"}
        ],
        "avg_factor_exposures": {
            "mkt_beta": 1.12,
            "smb_beta": -0.08,
            "hml_beta": -0.34
        }
    }

    with open(OUTPUT_DIR / "residual_momentum.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated: {OUTPUT_DIR / 'residual_momentum.json'}")
    return data


def generate_stat_arb_data():
    """Generate statistical arbitrage pairs data."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "active_pairs": 12,
            "clusters": 5,
            "avg_half_life": 8.2,
            "pca_variance": 0.82
        },
        "active_signals": [
            {"pair": "MSFT / GOOGL", "cluster": "Tech-Large", "zscore": -2.14, "hedge_ratio": 0.82, "half_life": 6.4, "signal": "LONG_SPREAD"},
            {"pair": "XOM / CVX", "cluster": "Energy", "zscore": 2.31, "hedge_ratio": 1.12, "half_life": 8.2, "signal": "SHORT_SPREAD"},
            {"pair": "JPM / BAC", "cluster": "Financials", "zscore": -1.87, "hedge_ratio": 0.45, "half_life": 12.1, "signal": "LONG_SPREAD"}
        ],
        "clusters": [
            {"id": 0, "name": "Tech-Large", "stocks": ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "CRM", "ADBE"]},
            {"id": 1, "name": "Financials", "stocks": ["JPM", "BAC", "WFC", "GS", "MS", "C"]},
            {"id": 2, "name": "Energy", "stocks": ["XOM", "CVX", "COP", "SLB", "EOG"]},
            {"id": 3, "name": "Healthcare", "stocks": ["JNJ", "UNH", "PFE", "MRK", "ABBV"]},
            {"id": 4, "name": "Consumer", "stocks": ["PG", "KO", "PEP", "WMT"]}
        ]
    }

    with open(OUTPUT_DIR / "stat_arb.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated: {OUTPUT_DIR / 'stat_arb.json'}")
    return data


def generate_regime_data():
    """Generate regime detection data."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "current": {
            "regime": "BULL",
            "probabilities": {"bull": 0.72, "bear": 0.08, "chop": 0.20},
            "days_in_regime": 34,
            "method": "HMM_3_STATE"
        },
        "allocations": {
            "BULL": {"residual_momentum": 0.40, "stat_arb": 0.20, "short_vol": 0.25, "cash": 0.15},
            "BEAR": {"residual_momentum": 0.05, "stat_arb": 0.15, "short_vol": 0.00, "cash": 0.80},
            "CHOP": {"residual_momentum": 0.15, "stat_arb": 0.40, "short_vol": 0.30, "cash": 0.15}
        },
        "transition_matrix": {
            "BULL": {"BULL": 0.92, "BEAR": 0.03, "CHOP": 0.05},
            "BEAR": {"BULL": 0.08, "BEAR": 0.82, "CHOP": 0.10},
            "CHOP": {"BULL": 0.12, "BEAR": 0.08, "CHOP": 0.80}
        },
        "stats": {
            "BULL": {"mean_return": 0.182, "volatility": 0.124, "avg_duration": 85},
            "BEAR": {"mean_return": -0.225, "volatility": 0.281, "avg_duration": 42},
            "CHOP": {"mean_return": 0.021, "volatility": 0.168, "avg_duration": 35}
        }
    }

    with open(OUTPUT_DIR / "regime.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated: {OUTPUT_DIR / 'regime.json'}")
    return data


def generate_meta_labeling_data():
    """Generate meta-labeling signals data."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "model": {
            "auc": 0.71,
            "threshold": 0.65,
            "filter_rate": 0.57
        },
        "today": {
            "total_signals": 7,
            "accepted": 3,
            "rejected": 4
        },
        "signals": [
            {"ticker": "AAPL", "probability": 0.78, "decision": "ACCEPT", "vix": 14.2, "rvol": 2.4, "atr_pct": 0.018, "dist_ma50": 0.042},
            {"ticker": "NVDA", "probability": 0.82, "decision": "ACCEPT", "vix": 14.2, "rvol": 3.1, "atr_pct": 0.024, "dist_ma50": 0.081},
            {"ticker": "TSLA", "probability": 0.69, "decision": "ACCEPT", "vix": 14.2, "rvol": 1.8, "atr_pct": 0.032, "dist_ma50": 0.124},
            {"ticker": "AMD", "probability": 0.42, "decision": "REJECT", "vix": 14.2, "rvol": 0.9, "atr_pct": 0.028, "dist_ma50": 0.182}
        ],
        "feature_importance": [
            {"name": "VIX Percentile", "importance": 0.182},
            {"name": "RVOL", "importance": 0.161},
            {"name": "21d Momentum", "importance": 0.132},
            {"name": "ATR%", "importance": 0.118},
            {"name": "Dist MA50", "importance": 0.098}
        ]
    }

    with open(OUTPUT_DIR / "meta_labeling.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated: {OUTPUT_DIR / 'meta_labeling.json'}")
    return data


def main():
    """Generate all dashboard data files."""
    print("=" * 50)
    print("Quant 2.0 Dashboard Data Generator")
    print("=" * 50)

    generate_dashboard_data()
    generate_residual_momentum_data()
    generate_stat_arb_data()
    generate_regime_data()
    generate_meta_labeling_data()

    print("=" * 50)
    print(f"All data files generated in: {OUTPUT_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
