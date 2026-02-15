"""
OLMAR SMA vs EMA Comparison
============================
Optimize and compare OLMAR strategy using Simple Moving Average (SMA) 
vs Exponential Moving Average (EMA).

Usage:
    python -m strategy.olps.compare_sma_ema
    python -m strategy.olps.compare_sma_ema --n-trials 50
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import numpy as np
import optuna
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strategy.config import CONFIG
from strategy.olps.kernels import olmar_weights, olmar_weights_ema
from strategy.olps.backtest_olmar_optimized import load_data_cached
from backend.quant.validation import calculate_dsr


# =============================================================================
# BACKTEST FUNCTIONS
# =============================================================================

def run_backtest(
    prices: pd.DataFrame,
    weights: pd.DataFrame,
    transaction_cost_bps: float = 15.0
) -> Dict[str, float]:
    """
    Run backtest given pre-computed weights.
    
    Args:
        prices: Price DataFrame
        weights: Weight DataFrame (same index as prices)
        transaction_cost_bps: Transaction cost in basis points
        
    Returns:
        Dict with performance metrics
    """
    price_returns = prices.pct_change()
    
    # Portfolio returns (signal lag)
    portfolio_returns = (weights.shift(1) * price_returns).sum(axis=1)
    portfolio_returns = portfolio_returns.dropna()
    
    # Transaction costs
    weight_changes = weights.diff().abs().sum(axis=1)
    daily_turnover = weight_changes / 2
    daily_cost = daily_turnover * (transaction_cost_bps / 10000)
    portfolio_returns = portfolio_returns - daily_cost.reindex(portfolio_returns.index, fill_value=0)
    
    # Metrics
    trading_days = 252
    
    if len(portfolio_returns) < 20:
        return {'sharpe_ratio': -999, 'total_return': 0, 'cagr': 0, 'max_drawdown': 0}
    
    total_return = (1 + portfolio_returns).prod() - 1
    years = len(portfolio_returns) / trading_days
    cagr = (1 + total_return) ** (1 / max(years, 0.01)) - 1
    
    volatility = portfolio_returns.std() * np.sqrt(trading_days)
    sharpe = (portfolio_returns.mean() * trading_days - CONFIG.RISK_FREE_RATE) / volatility if volatility > 1e-6 else 0
    
    cumulative = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    return {
        'sharpe_ratio': float(sharpe),
        'total_return': float(total_return),
        'cagr': float(cagr),
        'volatility': float(volatility),
        'max_drawdown': float(max_drawdown),
        'portfolio_returns': portfolio_returns  # For DSR
    }


# =============================================================================
# OPTIMIZATION
# =============================================================================

# Global price data
_price_data: pd.DataFrame = None


def objective_sma(trial: optuna.Trial) -> float:
    """Optuna objective for OLMAR-SMA."""
    global _price_data
    
    window = trial.suggest_int('window', 3, 20)
    epsilon = trial.suggest_float('epsilon', 1.0, 50.0)
    
    try:
        weights = olmar_weights(_price_data, window=window, epsilon=epsilon)
        metrics = run_backtest(_price_data, weights)
        
        dsr = calculate_dsr(metrics['portfolio_returns'], total_trials=1)
        
        trial.set_user_attr('total_return', metrics['total_return'])
        trial.set_user_attr('max_drawdown', metrics['max_drawdown'])
        trial.set_user_attr('dsr', dsr)
        
        return metrics['sharpe_ratio']
    except Exception as e:
        print(f"SMA trial failed: {e}")
        return -999


def objective_ema(trial: optuna.Trial) -> float:
    """Optuna objective for OLMAR-EMA."""
    global _price_data
    
    span = trial.suggest_int('span', 3, 20)
    epsilon = trial.suggest_float('epsilon', 1.0, 50.0)
    
    try:
        weights = olmar_weights_ema(_price_data, span=span, epsilon=epsilon)
        metrics = run_backtest(_price_data, weights)
        
        dsr = calculate_dsr(metrics['portfolio_returns'], total_trials=1)
        
        trial.set_user_attr('total_return', metrics['total_return'])
        trial.set_user_attr('max_drawdown', metrics['max_drawdown'])
        trial.set_user_attr('dsr', dsr)
        
        return metrics['sharpe_ratio']
    except Exception as e:
        print(f"EMA trial failed: {e}")
        return -999


def run_comparison(n_trials: int = 30, max_tickers: int = 20) -> Dict:
    """
    Run optimization comparison between SMA and EMA variants.
    
    Args:
        n_trials: Number of trials per strategy
        max_tickers: Maximum tickers to load
        
    Returns:
        Dict with comparison results
    """
    global _price_data
    
    # Load data
    _price_data = load_data_cached(max_tickers=max_tickers)
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    print(f"\nData: {len(_price_data.columns)} assets, {len(_price_data)} days")
    print("=" * 60)
    
    # Optimize SMA
    print(f"\n[1/2] Optimizing OLMAR-SMA ({n_trials} trials)...")
    study_sma = optuna.create_study(
        direction='maximize',
        study_name='OLMAR_SMA',
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    study_sma.optimize(objective_sma, n_trials=n_trials, show_progress_bar=True)
    
    # Optimize EMA
    print(f"\n[2/2] Optimizing OLMAR-EMA ({n_trials} trials)...")
    study_ema = optuna.create_study(
        direction='maximize',
        study_name='OLMAR_EMA',
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    study_ema.optimize(objective_ema, n_trials=n_trials, show_progress_bar=True)
    
    return {
        'sma': study_sma,
        'ema': study_ema
    }


def print_comparison(results: Dict):
    """Print comparison results."""
    study_sma = results['sma']
    study_ema = results['ema']
    
    print("\n" + "=" * 60)
    print("COMPARISON: OLMAR-SMA vs OLMAR-EMA")
    print("=" * 60)
    
    # Table header
    print(f"\n{'Metric':<20}{'OLMAR-SMA':<20}{'OLMAR-EMA':<20}{'Winner':<10}")
    print("-" * 70)
    
    # Best parameters
    sma_param = f"window={study_sma.best_params.get('window', 'N/A')}"
    ema_param = f"span={study_ema.best_params.get('span', 'N/A')}"
    print(f"{'MA Parameter':<20}{sma_param:<20}{ema_param:<20}{'—':<10}")
    
    sma_eps = f"{study_sma.best_params.get('epsilon', 0):.2f}"
    ema_eps = f"{study_ema.best_params.get('epsilon', 0):.2f}"
    print(f"{'Epsilon':<20}{sma_eps:<20}{ema_eps:<20}{'—':<10}")
    
    # Sharpe Ratio
    sma_sharpe = study_sma.best_value
    ema_sharpe = study_ema.best_value
    winner_sharpe = "SMA ✓" if sma_sharpe > ema_sharpe else "EMA ✓"
    print(f"{'Sharpe Ratio':<20}{sma_sharpe:<20.4f}{ema_sharpe:<20.4f}{winner_sharpe:<10}")
    
    # Total Return
    sma_ret = study_sma.best_trial.user_attrs.get('total_return', 0) * 100
    ema_ret = study_ema.best_trial.user_attrs.get('total_return', 0) * 100
    winner_ret = "SMA ✓" if sma_ret > ema_ret else "EMA ✓"
    print(f"{'Total Return':<20}{sma_ret:<20.1f}%{ema_ret:<19.1f}%{winner_ret:<10}")
    
    # Max Drawdown
    sma_dd = study_sma.best_trial.user_attrs.get('max_drawdown', 0) * 100
    ema_dd = study_ema.best_trial.user_attrs.get('max_drawdown', 0) * 100
    winner_dd = "SMA ✓" if sma_dd > ema_dd else "EMA ✓"  # Less negative is better
    print(f"{'Max Drawdown':<20}{sma_dd:<20.1f}%{ema_dd:<19.1f}%{winner_dd:<10}")
    
    print("-" * 70)
    
    # Overall winner
    if sma_sharpe > ema_sharpe:
        print(f"\n🏆 WINNER: OLMAR-SMA (Sharpe: {sma_sharpe:.4f})")
        print(f"   Best params: window={study_sma.best_params['window']}, epsilon={study_sma.best_params['epsilon']:.2f}")
    else:
        print(f"\n🏆 WINNER: OLMAR-EMA (Sharpe: {ema_sharpe:.4f})")
        print(f"   Best params: span={study_ema.best_params['span']}, epsilon={study_ema.best_params['epsilon']:.2f}")
    
    diff = abs(sma_sharpe - ema_sharpe)
    print(f"   Difference: {diff:.4f} Sharpe ({diff/max(abs(sma_sharpe), 0.001)*100:.1f}%)")


def save_results(results: Dict, output_dir: Path = None):
    """Save comparison results to JSON."""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "reports"
    
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "olmar_sma_vs_ema_comparison.json"
    
    study_sma = results['sma']
    study_ema = results['ema']
    
    data = {
        'run_date': datetime.now().isoformat(),
        'sma': {
            'best_params': study_sma.best_params,
            'best_sharpe': study_sma.best_value,
            'best_total_return': study_sma.best_trial.user_attrs.get('total_return'),
            'best_max_drawdown': study_sma.best_trial.user_attrs.get('max_drawdown'),
            'n_trials': len(study_sma.trials)
        },
        'ema': {
            'best_params': study_ema.best_params,
            'best_sharpe': study_ema.best_value,
            'best_total_return': study_ema.best_trial.user_attrs.get('total_return'),
            'best_max_drawdown': study_ema.best_trial.user_attrs.get('max_drawdown'),
            'n_trials': len(study_ema.trials)
        },
        'winner': 'SMA' if study_sma.best_value > study_ema.best_value else 'EMA'
    }
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Compare OLMAR-SMA vs OLMAR-EMA'
    )
    parser.add_argument(
        '--n-trials', type=int, default=30,
        help='Number of optimization trials per strategy (default: 30)'
    )
    parser.add_argument(
        '--max-tickers', type=int, default=20,
        help='Maximum tickers in universe (default: 20)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("OLMAR Strategy Comparison: SMA vs EMA")
    print("=" * 60)
    
    results = run_comparison(n_trials=args.n_trials, max_tickers=args.max_tickers)
    print_comparison(results)
    save_results(results)
    
    return results


if __name__ == "__main__":
    main()
