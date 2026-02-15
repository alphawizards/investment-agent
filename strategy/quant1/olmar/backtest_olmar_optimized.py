"""
OLMAR Optimized Backtest with Optuna
=====================================
High-performance hyperparameter optimization for OLMAR strategy.

Uses Optuna's TPE sampler for intelligent parameter search with parquet
data caching for fast I/O.

Optimizes 2 parameters:
- window: Moving average window (3-20)
- epsilon: Sensitivity parameter (1.0-50.0)

Usage:
    python -m strategy.quant1.olmar.backtest_olmar_optimized
    python -m strategy.quant1.olmar.backtest_olmar_optimized --n-trials 50
    python -m strategy.quant1.olmar.backtest_olmar_optimized --n-trials 100 --n-jobs 4
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import optuna
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategy.config import CONFIG
from strategy.data_loader import DataLoader, get_nasdaq_100_tickers
from strategy.quant1.olmar.kernels import olmar_weights
from backend.quant.validation import calculate_dsr, validate_backtest_result


# =============================================================================
# DATA LOADING WITH PARQUET CACHING
# =============================================================================

DATA_CACHE_PATH = Path(__file__).parent.parent.parent.parent / "data" / "price_cache.parquet"


def load_data_cached(
    start_date: str = "2020-01-01",
    end_date: str = None,
    max_tickers: int = 30,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Load price data with parquet caching for fast repeated access.
    
    Parquet is ~10x faster than CSV and preserves dtypes.
    
    Args:
        start_date: Start date for data
        end_date: End date (default: today)
        max_tickers: Maximum number of tickers to load
        force_refresh: If True, re-download data even if cache exists
        
    Returns:
        pd.DataFrame: Price data (Time x Assets)
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    # Check cache
    if DATA_CACHE_PATH.exists() and not force_refresh:
        print(f"Loading cached data from {DATA_CACHE_PATH}")
        prices = pd.read_parquet(DATA_CACHE_PATH)
        
        # Verify cache is still valid (same date range)
        cache_start = prices.index[0].strftime("%Y-%m-%d")
        if cache_start == start_date:
            return prices
        else:
            print(f"Cache date mismatch ({cache_start} vs {start_date}), refreshing...")
    
    # Load fresh data
    print(f"Downloading fresh data from {start_date} to {end_date}...")
    loader = DataLoader(start_date=start_date, end_date=end_date)
    
    # Get diversified ticker universe
    nasdaq_tickers = get_nasdaq_100_tickers()[:max_tickers]
    
    try:
        prices, _ = loader.load_selective_dataset(nasdaq_tickers)
    except Exception as e:
        print(f"Error loading data: {e}")
        # Fallback to smaller universe
        fallback_tickers = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'NVDA', 
                           'META', 'TSLA', 'JPM', 'V', 'JNJ']
        prices, _ = loader.load_selective_dataset(fallback_tickers)
    
    # Remove columns with too much missing data
    valid_cols = prices.notna().mean() > 0.8
    prices = prices.loc[:, valid_cols]
    
    # Forward fill remaining NaN values
    prices = prices.ffill().bfill()
    
    # Save to cache
    DATA_CACHE_PATH.parent.mkdir(exist_ok=True)
    prices.to_parquet(DATA_CACHE_PATH)
    print(f"Cached {len(prices.columns)} assets, {len(prices)} days to {DATA_CACHE_PATH}")
    
    return prices


# =============================================================================
# BACKTEST LOGIC
# =============================================================================

def run_olmar_backtest(
    prices: pd.DataFrame,
    window: int,
    epsilon: float,
    transaction_cost_bps: float = 15.0
) -> Dict[str, float]:
    """
    Run OLMAR backtest for a specific parameter combination.
    
    Args:
        prices: Price DataFrame (Time x Assets)
        window: Moving average window
        epsilon: Sensitivity parameter
        transaction_cost_bps: Transaction cost in basis points
        
    Returns:
        Dict with performance metrics
    """
    # Calculate OLMAR weights
    weights = olmar_weights(prices, window=window, epsilon=epsilon)
    
    # Calculate returns
    price_returns = prices.pct_change()
    
    # Portfolio returns (weights applied to next day's returns for signal lag)
    portfolio_returns = (weights.shift(1) * price_returns).sum(axis=1)
    portfolio_returns = portfolio_returns.dropna()
    
    # Calculate turnover for cost adjustment
    weight_changes = weights.diff().abs().sum(axis=1)
    daily_turnover = weight_changes / 2  # Each trade is counted twice
    daily_cost = daily_turnover * (transaction_cost_bps / 10000)
    
    # Adjust returns for costs
    portfolio_returns = portfolio_returns - daily_cost.reindex(portfolio_returns.index, fill_value=0)
    
    # Calculate metrics
    trading_days = 252
    
    if len(portfolio_returns) < 20:
        return {'sharpe_ratio': -999, 'total_return': 0, 'max_drawdown': 0}
    
    total_return = (1 + portfolio_returns).prod() - 1
    years = len(portfolio_returns) / trading_days
    cagr = (1 + total_return) ** (1 / max(years, 0.01)) - 1
    
    volatility = portfolio_returns.std() * np.sqrt(trading_days)
    if volatility < 1e-6:
        sharpe = 0
    else:
        sharpe = (portfolio_returns.mean() * trading_days - CONFIG.RISK_FREE_RATE) / volatility
    
    # Drawdown
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
        'total_cost': float(daily_cost.sum()),
        'portfolio_returns': portfolio_returns  # For DSR calculation
    }


# =============================================================================
# OPTUNA OPTIMIZATION
# =============================================================================

# Global price data (loaded once, shared across trials)
_price_data: pd.DataFrame = None


def objective(trial: optuna.Trial) -> float:
    """
    Optuna objective function for OLMAR parameter optimization.
    
    Optimizes for Sharpe Ratio.
    
    Args:
        trial: Optuna trial object
        
    Returns:
        float: Sharpe Ratio (to maximize)
    """
    global _price_data
    
    # Suggest hyperparameters
    window = trial.suggest_int('window', 3, 20)
    epsilon = trial.suggest_float('epsilon', 1.0, 50.0)
    
    try:
        # Run backtest
        metrics = run_olmar_backtest(_price_data, window=window, epsilon=epsilon)
        
        # Calculate DSR (will be recalculated with final trial count at end)
        dsr = calculate_dsr(metrics['portfolio_returns'], total_trials=1)
        
        # Store additional metrics for analysis
        trial.set_user_attr('total_return', metrics['total_return'])
        trial.set_user_attr('max_drawdown', metrics['max_drawdown'])
        trial.set_user_attr('cagr', metrics['cagr'])
        trial.set_user_attr('dsr', dsr)
        
        return metrics['sharpe_ratio']
        
    except Exception as e:
        print(f"Trial failed: {e}")
        return -999


def run_optimization(
    n_trials: int = 50,
    n_jobs: int = 1,
    start_date: str = "2020-01-01",
    max_tickers: int = 30
) -> optuna.Study:
    """
    Run Optuna optimization for OLMAR parameters.
    
    Args:
        n_trials: Number of optimization trials
        n_jobs: Number of parallel jobs (1 = sequential)
        start_date: Start date for backtest data
        max_tickers: Maximum tickers in universe
        
    Returns:
        optuna.Study: Completed study with results
    """
    global _price_data
    
    # Load data (cached)
    _price_data = load_data_cached(start_date=start_date, max_tickers=max_tickers)
    
    # Suppress Optuna logging
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    # Create study with TPE sampler (intelligent search)
    study = optuna.create_study(
        direction='maximize',
        study_name='OLMAR_Optimization',
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    
    print(f"\nStarting Optuna optimization with {n_trials} trials...")
    print(f"Parameter space: window [3-20], epsilon [1.0-50.0]")
    print(f"Data: {len(_price_data.columns)} assets, {len(_price_data)} days")
    print("-" * 60)
    
    # Run optimization
    study.optimize(
        objective,
        n_trials=n_trials,
        n_jobs=n_jobs,
        show_progress_bar=True
    )
    
    return study


def print_results(study: optuna.Study):
    """Print optimization results summary."""
    print("\n" + "=" * 60)
    print("OPTIMIZATION RESULTS")
    print("=" * 60)
    
    n_trials = len(study.trials)
    
    print(f"\nBest Parameters:")
    print(f"  window:  {study.best_params['window']}")
    print(f"  epsilon: {study.best_params['epsilon']:.2f}")
    
    print(f"\nBest Metrics:")
    print(f"  Sharpe Ratio:  {study.best_value:.4f}")
    
    if study.best_trial.user_attrs:
        attrs = study.best_trial.user_attrs
        print(f"  Total Return:  {attrs.get('total_return', 0)*100:.2f}%")
        print(f"  CAGR:          {attrs.get('cagr', 0)*100:.2f}%")
        print(f"  Max Drawdown:  {attrs.get('max_drawdown', 0)*100:.2f}%")
    
    # Recalculate DSR with actual trial count
    global _price_data
    best_metrics = run_olmar_backtest(
        _price_data, 
        window=study.best_params['window'], 
        epsilon=study.best_params['epsilon']
    )
    final_dsr = calculate_dsr(best_metrics['portfolio_returns'], total_trials=n_trials)
    
    print(f"\n[2025 Validation]")
    print(f"  Total Trials:      {n_trials}")
    print(f"  Deflated Sharpe:   {final_dsr:.4f}")
    if final_dsr >= 0.95:
        print(f"  Status:            ✅ VALIDATED (DSR >= 0.95)")
    elif final_dsr >= 0.80:
        print(f"  Status:            ⚠️ MARGINAL (0.80 <= DSR < 0.95)")
    else:
        print(f"  Status:            ❌ SUSPICIOUS (DSR < 0.80)")
    
    # Compare with default parameters
    print("\n" + "-" * 60)
    print("Comparison with Default Parameters (window=5, epsilon=10):")
    
    default_metrics = run_olmar_backtest(_price_data, window=5, epsilon=10.0)
    
    print(f"  Default Sharpe:   {default_metrics['sharpe_ratio']:.4f}")
    print(f"  Optimized Sharpe: {study.best_value:.4f}")
    
    improvement = study.best_value - default_metrics['sharpe_ratio']
    print(f"  Improvement:      {improvement:+.4f} ({improvement/abs(default_metrics['sharpe_ratio'])*100:+.1f}%)")
    
    # Top 5 trials
    print("\n" + "-" * 60)
    print("Top 5 Parameter Combinations:")
    print(f"{'Rank':<6}{'Window':<10}{'Epsilon':<12}{'Sharpe':<10}")
    print("-" * 38)
    
    sorted_trials = sorted(study.trials, key=lambda t: t.value if t.value else -999, reverse=True)
    for i, trial in enumerate(sorted_trials[:5], 1):
        window = trial.params.get('window', 'N/A')
        epsilon = trial.params.get('epsilon', 'N/A')
        sharpe = trial.value if trial.value else 'Failed'
        if isinstance(sharpe, float):
            print(f"{i:<6}{window:<10}{epsilon:<12.2f}{sharpe:<10.4f}")
        else:
            print(f"{i:<6}{window:<10}{epsilon:<12}{sharpe:<10}")


def save_results(study: optuna.Study, output_dir: Path = None):
    """Save optimization results to JSON."""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "reports"
    
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "olmar_optimization_results.json"
    
    results = {
        'run_date': datetime.now().isoformat(),
        'n_trials': len(study.trials),
        'best_params': study.best_params,
        'best_sharpe': study.best_value,
        'best_trial_attrs': study.best_trial.user_attrs,
        'all_trials': [
            {
                'number': t.number,
                'params': t.params,
                'value': t.value,
                'attrs': t.user_attrs
            }
            for t in study.trials if t.value is not None
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description='OLMAR Parameter Optimization with Optuna'
    )
    parser.add_argument(
        '--n-trials', type=int, default=50,
        help='Number of optimization trials (default: 50)'
    )
    parser.add_argument(
        '--n-jobs', type=int, default=1,
        help='Number of parallel jobs (default: 1)'
    )
    parser.add_argument(
        '--start-date', type=str, default='2020-01-01',
        help='Start date for backtest data (default: 2020-01-01)'
    )
    parser.add_argument(
        '--max-tickers', type=int, default=30,
        help='Maximum tickers in universe (default: 30)'
    )
    parser.add_argument(
        '--force-refresh', action='store_true',
        help='Force refresh of cached data'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("OLMAR Parameter Optimization")
    print("=" * 60)
    
    # Run optimization
    study = run_optimization(
        n_trials=args.n_trials,
        n_jobs=args.n_jobs,
        start_date=args.start_date,
        max_tickers=args.max_tickers
    )
    
    # Print and save results
    print_results(study)
    save_results(study)
    
    return study


if __name__ == "__main__":
    main()
