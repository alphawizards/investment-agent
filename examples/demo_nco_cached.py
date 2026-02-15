"""
Demo: NCO Portfolio Optimization with Cached Data
==================================================
Demonstrates using FastDataLoader to access cached Tiingo stocks
for instant portfolio optimization.
"""

from strategy.fast_data_loader import FastDataLoader
from strategy.quant2.optimization.nco_optimizer import NCOOptimizer
import pandas as pd
import numpy as np

def demo_nco_with_cached_stocks():
    """Run NCO optimization using cached stock data."""
    
    print("="*60)
    print("NCO PORTFOLIO OPTIMIZATION - CACHED DATA DEMO")
    print("="*60)
    
    # Load cached stock data (instant, 560 stocks, 21 years)
    loader = FastDataLoader()
    prices = loader.load_cached_tiingo_stocks()
    
    if prices.empty:
        print("ERROR: No cached stocks found. Run fetch_us_stocks_20yr_tiingo.py first.")
        return
    
    print(f"\n📊 Stock Data Loaded:")
    print(f"   Stocks: {len(prices.columns)}")
    print(f"   Period: {prices.index.min().date()} to {prices.index.max().date()}")
    print(f"   Days: {len(prices)}")
    
    # Select top 50 stocks by recent volatility for optimization
    recent_prices = prices.tail(252 * 3)  # Last 3 years
    returns = recent_prices.pct_change().dropna()
    
    volatilities = returns.std() * np.sqrt(252)
    top_50_tickers = volatilities.nlargest(50).index.tolist()
    
    print(f"\n🎯 Optimizing portfolio with top 50 stocks by volatility...")
    print(f"   Selected stocks: {', '.join(top_50_tickers[:10])}...")
    
    # Run NCO optimization
    optimizer = NCOOptimizer(
        inner_objective='MinRisk',
        outer_objective='ERC',
        max_clusters=10,
        min_weight=0.02,
        max_weight=0.30
    )
    
    portfolio_returns = returns[top_50_tickers]
    result = optimizer.optimize(portfolio_returns)
    
    # Display results
    print(f"\n✅ Optimization Results:")
    print(f"   Effective N: {result.metadata['effective_n']:.2f}")
    print(f"   Number of Assets: {result.metadata['n_assets']}")
    print(f"   Max Weight: {result.weights.max():.2%}")
    print(f"   Min Weight: {result.weights.min():.2%}")
    
    print(f"\n📈 Top 10 Holdings:")
    for ticker, weight in result.weights.nlargest(10).items():
        print(f"   {ticker:6}: {weight:6.2%}")
    
    # Portfolio statistics
    stats = optimizer.get_portfolio_stats(portfolio_returns, result.weights)
    print(f"\n💰 Portfolio Statistics:")
    print(f"   Expected Return: {stats['expected_return']:.2%}")
    print(f"   Volatility: {stats['volatility']:.2%}")
    print(f"   Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
    
    print("\n" + "="*60)
    print("✅ Demo Complete")
    print("="*60)
    
    return result


if __name__ == "__main__":
    demo_nco_with_cached_stocks()
