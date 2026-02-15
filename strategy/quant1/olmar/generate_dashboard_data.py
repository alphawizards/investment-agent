"""
OLMAR Dashboard Data Generator
===============================
Generates JSON data for the OLMAR dashboard page.

Run this script to update the dashboard data:
    python -m strategy.quant1.olmar.generate_dashboard_data
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Custom JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategy.data_loader import DataLoader, get_nasdaq_100_tickers
from strategy.config import CONFIG, get_us_tickers, get_asx_tickers
from strategy.quant1.olmar.olmar_strategy import (
    OLMARStrategy,
    OLMARConfig,
    create_olmar_weekly,
    create_olmar_monthly
)
from strategy.quant1.olmar.constraints import get_turnover_stats


def load_data(months: int = 12) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load price data for the specified period."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    loader = DataLoader(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    # Get universe
    tickers = get_us_tickers() + get_asx_tickers()
    nasdaq = get_nasdaq_100_tickers()[:30]  # Top 30 Nasdaq for speed
    tickers = list(set(tickers + nasdaq))
    
    print(f"Loading {len(tickers)} tickers for past {months} months...")
    
    try:
        prices, returns = loader.load_selective_dataset(tickers)
    except Exception as e:
        print(f"Warning: Some tickers failed. Using available data...")
        # Fallback to ETFs only
        tickers = get_us_tickers() + get_asx_tickers()
        prices, returns = loader.load_selective_dataset(tickers)
    
    # Filter columns with good data
    valid_cols = prices.notna().mean() > 0.9
    prices = prices.loc[:, valid_cols]
    returns = returns.loc[:, valid_cols]
    
    return prices, returns


def get_monthly_selections(
    weights_history: pd.DataFrame,
    top_n: int = 10
) -> List[Dict]:
    """
    Extract top stock selections for each month.
    
    Args:
        weights_history: DataFrame of weights over time
        top_n: Number of top stocks to include per month
        
    Returns:
        List of monthly selection records
    """
    selections = []
    
    # Group by month
    weights_history.index = pd.to_datetime(weights_history.index)
    monthly = weights_history.resample('M').last()
    
    for date, row in monthly.iterrows():
        # Get top N stocks by weight
        top_stocks = row.nlargest(top_n)
        
        month_record = {
            'date': date.strftime('%Y-%m'),
            'month_name': date.strftime('%B %Y'),
            'stocks': []
        }
        
        for ticker, weight in top_stocks.items():
            if weight > 0.001:  # Only include meaningful weights
                month_record['stocks'].append({
                    'ticker': ticker,
                    'weight': round(float(weight) * 100, 2),
                    'weight_pct': f"{weight * 100:.1f}%"
                })
        
        selections.append(month_record)
    
    return selections


def get_weekly_selections(
    weights_history: pd.DataFrame,
    top_n: int = 8
) -> List[Dict]:
    """
    Extract top stock selections for each week.
    
    Args:
        weights_history: DataFrame of weights over time
        top_n: Number of top stocks to include per week
        
    Returns:
        List of weekly selection records
    """
    selections = []
    
    # Group by week
    weights_history.index = pd.to_datetime(weights_history.index)
    weekly = weights_history.resample('W').last()
    
    for date, row in weekly.iterrows():
        # Get top N stocks by weight
        top_stocks = row.nlargest(top_n)
        
        # Format as "Week of Jan 15, 2025"
        week_start = date - pd.Timedelta(days=6)
        
        week_record = {
            'date': date.strftime('%Y-%m-%d'),
            'week_name': f"Week of {week_start.strftime('%b %d, %Y')}",
            'month_name': date.strftime('%B %Y'),  # For grouping in UI
            'stocks': []
        }
        
        for ticker, weight in top_stocks.items():
            if weight > 0.001:  # Only include meaningful weights
                week_record['stocks'].append({
                    'ticker': ticker,
                    'weight': round(float(weight) * 100, 2),
                    'weight_pct': f"{weight * 100:.1f}%"
                })
        
        selections.append(week_record)
    
    return selections



def calculate_stock_frequency(weights_history: pd.DataFrame) -> List[Dict]:
    """
    Calculate how often each stock was selected.
    
    Returns list of stocks sorted by selection frequency.
    """
    # Count months where stock had > 1% weight
    monthly = weights_history.resample('M').last()
    selection_counts = (monthly > 0.01).sum()
    total_months = len(monthly)
    
    frequency = []
    for ticker, count in selection_counts.sort_values(ascending=False).items():
        if count > 0:
            frequency.append({
                'ticker': ticker,
                'months_selected': int(count),
                'frequency_pct': round(count / total_months * 100, 1),
                'avg_weight': round(monthly[ticker].mean() * 100, 2)
            })
    
    return frequency[:30]  # Top 30 most frequent


def run_olmar_and_generate_data():
    """Run OLMAR strategies and generate dashboard data."""
    print("=" * 60)
    print("OLMAR Dashboard Data Generator")
    print("=" * 60)
    
    # Load data
    prices, returns = load_data(months=12)
    
    print(f"\nData loaded: {len(prices.columns)} stocks, {len(prices)} days")
    print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
    
    # Run OLMAR strategies
    print("\nRunning OLMAR Weekly...")
    olmar_weekly = create_olmar_weekly(window=5, epsilon=10, max_turnover=0.5)
    weekly_result = olmar_weekly.generate_weights(prices)
    
    print("Running OLMAR Monthly...")
    olmar_monthly = create_olmar_monthly(window=5, epsilon=10, max_turnover=0.5)
    monthly_result = olmar_monthly.generate_weights(prices)
    
    # Calculate performance
    print("\nCalculating performance metrics...")
    
    def calc_metrics(weights: pd.DataFrame, prices: pd.DataFrame) -> Dict:
        returns = prices.pct_change()
        port_returns = (weights.shift(1) * returns).sum(axis=1).dropna()
        
        total_return = (1 + port_returns).prod() - 1
        years = len(port_returns) / 252
        cagr = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        volatility = port_returns.std() * np.sqrt(252)
        sharpe = (port_returns.mean() * 252 - 0.04) / volatility if volatility > 0 else 0
        
        cumulative = (1 + port_returns).cumprod()
        max_dd = ((cumulative / cumulative.cummax()) - 1).min()
        
        return {
            'total_return': round(total_return * 100, 2),
            'cagr': round(cagr * 100, 2),
            'volatility': round(volatility * 100, 2),
            'sharpe': round(sharpe, 3),
            'max_drawdown': round(max_dd * 100, 2)
        }
    
    weekly_metrics = calc_metrics(weekly_result.weights, prices)
    monthly_metrics = calc_metrics(monthly_result.weights, prices)
    
    # Get stock selections
    print("Extracting stock selections...")
    weekly_weekly_selections = get_weekly_selections(weekly_result.weights)  # Weekly data for weekly strategy
    weekly_monthly_selections = get_monthly_selections(weekly_result.weights)  # Monthly summary for weekly
    monthly_selections = get_monthly_selections(monthly_result.weights)
    
    # Get frequency stats
    weekly_frequency = calculate_stock_frequency(weekly_result.weights)
    monthly_frequency = calculate_stock_frequency(monthly_result.weights)
    
    # Get current top holdings
    current_weekly = weekly_result.weights.iloc[-1].nlargest(15)
    current_monthly = monthly_result.weights.iloc[-1].nlargest(15)
    
    # Build dashboard data
    dashboard_data = {
        'generated_at': datetime.now().isoformat(),
        'data_start': prices.index[0].strftime('%Y-%m-%d'),
        'data_end': prices.index[-1].strftime('%Y-%m-%d'),
        'universe_size': len(prices.columns),
        
        'strategies': {
            'weekly': {
                'name': 'OLMAR Weekly',
                'rebalance_freq': 'Weekly',
                'metrics': weekly_metrics,
                'turnover_stats': {
                    k: round(v * 100, 2) if k != 'rebalance_days' else v
                    for k, v in weekly_result.turnover_stats.items()
                }
            },
            'monthly': {
                'name': 'OLMAR Monthly',
                'rebalance_freq': 'Monthly',
                'metrics': monthly_metrics,
                'turnover_stats': {
                    k: round(v * 100, 2) if k != 'rebalance_days' else v
                    for k, v in monthly_result.turnover_stats.items()
                }
            }
        },
        
        'current_holdings': {
            'weekly': [
                {'ticker': t, 'weight': round(w * 100, 2)}
                for t, w in current_weekly.items() if w > 0.01
            ],
            'monthly': [
                {'ticker': t, 'weight': round(w * 100, 2)}
                for t, w in current_monthly.items() if w > 0.01
            ]
        },
        
        # Weekly strategy shows weekly selections, monthly shows monthly
        'weekly_selections': weekly_weekly_selections,  # Week-by-week data
        'monthly_selections': {
            'weekly': weekly_monthly_selections,  # Monthly summary for comparison
            'monthly': monthly_selections
        },
        
        'stock_frequency': {
            'weekly': weekly_frequency,
            'monthly': monthly_frequency
        }
    }
    
    # Save to dashboard folder
    output_path = Path(__file__).parent.parent.parent / "dashboard" / "olmar_data.json"
    with open(output_path, 'w') as f:
        json.dump(dashboard_data, f, indent=2, cls=NumpyEncoder)
    
    print(f"\n✅ Dashboard data saved to: {output_path}")
    
    return dashboard_data


if __name__ == "__main__":
    run_olmar_and_generate_data()
