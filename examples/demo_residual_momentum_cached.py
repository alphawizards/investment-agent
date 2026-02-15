"""
Demo: Residual Momentum with Cached Data
=========================================
Demonstrates using FastDataLoader to access cached Tiingo stocks
for instant residual momentum calculation.
"""

from strategy.fast_data_loader import FastDataLoader
from strategy.quant2.momentum.residual_momentum import ResidualMomentum
import pandas as pd

def demo_residual_momentum_with_cached_stocks():
    """Run Residual Momentum calculation using cached stock data."""
    
    print("="*60)
    print("RESIDUAL MOMENTUM - CACHED DATA DEMO")
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
    
    # Convert to monthly returns (required for Fama-French)
    monthly_prices = prices.resample('M').last()
    monthly_returns = monthly_prices.pct_change().dropna()
    
    print(f"\n📅 Monthly Data:")
    print(f"   Months: {len(monthly_returns)}")
    print(f"   Period: {monthly_returns.index.min().date()} to {monthly_returns.index.max().date()}")
    
    # Select top 100 stocks by average absolute return
    avg_returns = monthly_returns.mean().abs()
    top_100_tickers = avg_returns.nlargest(100).index.tolist()
    
    print(f"\n🎯 Analyzing top 100 stocks by average return...")
    print(f"   Sample: {', '.join(top_100_tickers[:10])}...")
    
    # Run Residual Momentum
    print(f"\n🔍 Calculating Residual Momentum...")
    print(f"   (This will download Fama-French factors from web...)")
    
    res_mom = ResidualMomentum(
        lookback_months=36,
        scoring_months=12,
        min_observations=24
    )
    
    result = res_mom.calculate_scores(
        stock_returns=monthly_returns[top_100_tickers],
        as_of_date=str(monthly_returns.index[-1].date())
    )
    
    # Display results
    print(f"\n✅ Results:")
    print(f"   Method: {result.metadata['method']}")
    print(f"   Stocks Analyzed: {result.metadata['n_stocks']}")
    print(f"   Lookback Period: {result.metadata['lookback_months']} months")
    print(f"   Scoring Period: {result.metadata['scoring_months']} months")
    
    # Top 10 by residual momentum
    top_10 = res_mom.get_top_n(result, n=10)
    print(f"\n📈 Top 10 Stocks (Long Candidates):")
    for i, ticker in enumerate(top_10, 1):
        score = result.scores.loc[ticker] if ticker in result.scores.index else float('nan')
        print(f"   {i:2}. {ticker:6}: Score = {score:.3f}")
    
    # Bottom 10 for short leg
    bottom_10 = res_mom.get_bottom_n(result, n=10)
    print(f"\n📉 Bottom 10 Stocks (Short Candidates):")
    for i, ticker in enumerate(bottom_10, 1):
        score = result.scores.loc[ticker] if ticker in result.scores.index else float('nan')
        print(f"   {i:2}. {ticker:6}: Score = {score:.3f}")
    
    # Factor exposure summary
    if result.factor_exposures:
        exposure_summary = res_mom.get_factor_exposure_summary(result)
        print(f"\n🔬 Factor Exposure Summary:")
        print(exposure_summary.to_string())
    
    print("\n" + "="*60)
    print("✅ Demo Complete")
    print("="*60)
    
    return result


if __name__ == "__main__":
    demo_residual_momentum_with_cached_stocks()
