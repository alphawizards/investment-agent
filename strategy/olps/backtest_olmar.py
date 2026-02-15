"""
OLMAR Backtest Script
======================
Backtest OLMAR strategy with weekly and monthly rebalancing scenarios.

Usage:
    python -m strategy.olps.backtest_olmar

Output:
    - Console comparison of weekly vs monthly rebalancing
    - reports/olmar_backtest_results.json
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strategy.data_loader import DataLoader, get_nasdaq_100_tickers
from strategy.config import CONFIG, get_us_tickers, get_asx_tickers
from strategy.backtest import PortfolioBacktester, BacktestResult
from strategy.olps.olmar_strategy import (
    OLMARStrategy,
    OLMARConfig,
    create_olmar_weekly,
    create_olmar_monthly
)
from strategy.olps.constraints import calculate_cost_drag, get_turnover_stats


def load_extended_universe(
    start_date: str = "2020-01-01",
    end_date: str = None,
    include_nasdaq: bool = True,
    max_nasdaq: int = 50
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load extended universe including ETFs and Nasdaq stocks.
    
    Args:
        start_date: Start date for data
        end_date: End date for data (default: today)
        include_nasdaq: Whether to include Nasdaq-100 stocks
        max_nasdaq: Maximum number of Nasdaq stocks to include
        
    Returns:
        Tuple of (prices, returns) DataFrames
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    loader = DataLoader(start_date=start_date, end_date=end_date)
    
    # Get base universe (ETFs)
    tickers = get_us_tickers() + get_asx_tickers()
    
    # Add Nasdaq-100 stocks
    if include_nasdaq:
        nasdaq_tickers = get_nasdaq_100_tickers()[:max_nasdaq]
        tickers = list(set(tickers + nasdaq_tickers))  # Dedupe
    
    print(f"\nLoading {len(tickers)} tickers...")
    
    try:
        prices, returns = loader.load_selective_dataset(tickers)
    except Exception as e:
        print(f"Warning: Some tickers failed to load. Retrying with available data...")
        # Fallback: try loading in smaller batches
        all_prices = []
        for i in range(0, len(tickers), 10):
            batch = tickers[i:i+10]
            try:
                batch_prices, _ = loader.load_selective_dataset(batch)
                all_prices.append(batch_prices)
            except Exception as batch_e:
                print(f"  Batch {i//10 + 1} failed: {batch_e}")
                continue
        
        if not all_prices:
            raise ValueError("No data could be loaded")
        
        prices = pd.concat(all_prices, axis=1)
        prices = prices.loc[:, ~prices.columns.duplicated()]
        returns = prices.pct_change().dropna()
    
    # Remove columns with too much missing data
    valid_cols = prices.notna().mean() > 0.8  # Require 80% data availability
    prices = prices.loc[:, valid_cols]
    returns = returns.loc[:, valid_cols]
    
    print(f"Final universe: {len(prices.columns)} assets, {len(prices)} days")
    
    return prices, returns


def run_olmar_backtest(
    prices: pd.DataFrame,
    strategy: OLMARStrategy,
    include_costs: bool = True,
    transaction_cost_bps: float = 15.0
) -> Dict:
    """
    Run OLMAR backtest and calculate metrics.
    
    Args:
        prices: Price DataFrame
        strategy: OLMARStrategy instance
        include_costs: Whether to include transaction costs
        transaction_cost_bps: Transaction cost in basis points
        
    Returns:
        Dict with backtest results and metrics
    """
    print(f"\nRunning {strategy.name}...")
    
    # Generate weights
    result = strategy.generate_weights(prices, apply_cost_constraints=True)
    
    # Calculate returns
    price_returns = prices.pct_change()
    
    # Portfolio returns (weights applied to next day's returns for signal lag)
    portfolio_returns = (result.weights.shift(1) * price_returns).sum(axis=1)
    portfolio_returns = portfolio_returns.dropna()
    
    # Calculate cost drag
    daily_cost, total_cost = calculate_cost_drag(
        result.weights, 
        transaction_cost_bps
    )
    
    # Adjust returns for costs if requested
    if include_costs:
        portfolio_returns = portfolio_returns - daily_cost.reindex(portfolio_returns.index, fill_value=0)
    
    # Calculate metrics
    trading_days = 252
    total_return = (1 + portfolio_returns).prod() - 1
    years = len(portfolio_returns) / trading_days
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    volatility = portfolio_returns.std() * np.sqrt(trading_days)
    sharpe = (portfolio_returns.mean() * trading_days - CONFIG.RISK_FREE_RATE) / volatility if volatility > 0 else 0
    
    # Drawdown calculation
    cumulative = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # Turnover stats
    turnover_stats = result.turnover_stats
    
    metrics = {
        'strategy': strategy.name,
        'rebalance_freq': strategy.config.rebalance_freq,
        'total_return': float(total_return),
        'cagr': float(cagr),
        'volatility': float(volatility),
        'sharpe_ratio': float(sharpe),
        'max_drawdown': float(max_drawdown),
        'total_cost_drag': float(total_cost),
        'annualized_turnover': float(turnover_stats['annualized_turnover']),
        'mean_daily_turnover': float(turnover_stats['mean_daily_turnover']),
        'rebalance_days': int(turnover_stats['rebalance_days']),
        'n_assets': len(prices.columns),
        'n_periods': len(prices),
        'start_date': str(prices.index[0].date()),
        'end_date': str(prices.index[-1].date())
    }
    
    return {
        'metrics': metrics,
        'portfolio_returns': portfolio_returns,
        'weights': result.weights,
        'cumulative_return': cumulative
    }


def run_benchmark_comparison(prices: pd.DataFrame) -> Dict:
    """
    Run equal-weight benchmark for comparison.
    
    Args:
        prices: Price DataFrame
        
    Returns:
        Dict with benchmark metrics
    """
    print("\nRunning Equal-Weight Benchmark...")
    
    n_assets = len(prices.columns)
    equal_weights = pd.DataFrame(
        1.0 / n_assets,
        index=prices.index,
        columns=prices.columns
    )
    
    price_returns = prices.pct_change()
    portfolio_returns = (equal_weights.shift(1) * price_returns).sum(axis=1)
    portfolio_returns = portfolio_returns.dropna()
    
    # Calculate metrics
    trading_days = 252
    total_return = (1 + portfolio_returns).prod() - 1
    years = len(portfolio_returns) / trading_days
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    volatility = portfolio_returns.std() * np.sqrt(trading_days)
    sharpe = (portfolio_returns.mean() * trading_days - CONFIG.RISK_FREE_RATE) / volatility if volatility > 0 else 0
    
    cumulative = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    return {
        'metrics': {
            'strategy': 'Equal-Weight Benchmark',
            'total_return': float(total_return),
            'cagr': float(cagr),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe),
            'max_drawdown': float(max_drawdown)
        },
        'portfolio_returns': portfolio_returns,
        'cumulative_return': cumulative
    }


def format_results_table(results: List[Dict]) -> str:
    """Format results as a comparison table."""
    headers = ['Strategy', 'Total Return', 'CAGR', 'Volatility', 'Sharpe', 'Max DD', 'Turn/Yr', 'Cost Drag']
    
    rows = []
    for r in results:
        m = r['metrics']
        row = [
            m['strategy'],
            f"{m['total_return']*100:.1f}%",
            f"{m['cagr']*100:.1f}%",
            f"{m['volatility']*100:.1f}%",
            f"{m['sharpe_ratio']:.2f}",
            f"{m['max_drawdown']*100:.1f}%",
            f"{m.get('annualized_turnover', 0)*100:.0f}%",
            f"{m.get('total_cost_drag', 0)*100:.2f}%"
        ]
        rows.append(row)
    
    # Calculate column widths
    widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
    
    # Format table
    sep = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    header_row = '| ' + ' | '.join(h.ljust(widths[i]) for i, h in enumerate(headers)) + ' |'
    
    lines = [sep, header_row, sep]
    for row in rows:
        lines.append('| ' + ' | '.join(str(v).ljust(widths[i]) for i, v in enumerate(row)) + ' |')
    lines.append(sep)
    
    return '\n'.join(lines)


def main():
    """Main entry point for OLMAR backtest."""
    print("=" * 70)
    print("OLMAR Backtest - Weekly vs Monthly Rebalancing")
    print("=" * 70)
    
    # Configuration
    START_DATE = "2020-01-01"
    END_DATE = None  # Today
    INCLUDE_NASDAQ = True
    MAX_NASDAQ = 50  # Use top 50 Nasdaq stocks for reasonable data loading time
    TRANSACTION_COST_BPS = 15.0
    
    # Load data
    print(f"\nLoading data from {START_DATE}...")
    prices, returns = load_extended_universe(
        start_date=START_DATE,
        end_date=END_DATE,
        include_nasdaq=INCLUDE_NASDAQ,
        max_nasdaq=MAX_NASDAQ
    )
    
    # Create strategies
    olmar_weekly = create_olmar_weekly(
        window=5,
        epsilon=10.0,
        max_turnover=0.5
    )
    
    olmar_monthly = create_olmar_monthly(
        window=5,
        epsilon=10.0,
        max_turnover=0.5
    )
    
    # Run backtests
    results = []
    
    # Weekly OLMAR
    weekly_result = run_olmar_backtest(
        prices, 
        olmar_weekly,
        include_costs=True,
        transaction_cost_bps=TRANSACTION_COST_BPS
    )
    results.append(weekly_result)
    
    # Monthly OLMAR
    monthly_result = run_olmar_backtest(
        prices,
        olmar_monthly,
        include_costs=True,
        transaction_cost_bps=TRANSACTION_COST_BPS
    )
    results.append(monthly_result)
    
    # Benchmark
    benchmark_result = run_benchmark_comparison(prices)
    results.append(benchmark_result)
    
    # Print comparison table
    print("\n" + "=" * 70)
    print("RESULTS COMPARISON")
    print("=" * 70)
    print(format_results_table(results))
    
    # Summary insights
    print("\n" + "=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)
    
    weekly_sharpe = weekly_result['metrics']['sharpe_ratio']
    monthly_sharpe = monthly_result['metrics']['sharpe_ratio']
    benchmark_sharpe = benchmark_result['metrics']['sharpe_ratio']
    
    weekly_cost = weekly_result['metrics']['total_cost_drag']
    monthly_cost = monthly_result['metrics']['total_cost_drag']
    
    print(f"• Weekly rebalancing cost drag: {weekly_cost*100:.2f}%")
    print(f"• Monthly rebalancing cost drag: {monthly_cost*100:.2f}%")
    print(f"• Cost savings (monthly vs weekly): {(weekly_cost - monthly_cost)*100:.2f}%")
    
    if monthly_sharpe > weekly_sharpe:
        print(f"• Monthly rebalancing outperforms weekly by {(monthly_sharpe - weekly_sharpe):.2f} Sharpe")
    else:
        print(f"• Weekly rebalancing outperforms monthly by {(weekly_sharpe - monthly_sharpe):.2f} Sharpe")
    
    best_strategy = max(results, key=lambda x: x['metrics']['sharpe_ratio'])
    print(f"• Best strategy: {best_strategy['metrics']['strategy']} (Sharpe: {best_strategy['metrics']['sharpe_ratio']:.2f})")
    
    # Save results
    output_dir = Path(__file__).parent.parent.parent / "reports"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "olmar_backtest_results.json"
    
    # Prepare export data (convert non-serializable types)
    export_data = {
        'run_date': datetime.now().isoformat(),
        'config': {
            'start_date': START_DATE,
            'transaction_cost_bps': TRANSACTION_COST_BPS,
            'include_nasdaq': INCLUDE_NASDAQ,
            'max_nasdaq': MAX_NASDAQ
        },
        'results': [r['metrics'] for r in results]
    }
    
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()
