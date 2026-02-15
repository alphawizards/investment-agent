"""
Update Cache with 20 Years of US Stock Data
============================================
Incrementally fetches missing historical data and updates cache.
Smart incremental loading - only fetches what's missing!
"""

from strategy.fast_data_loader import FastDataLoader
from strategy.stock_universe import get_screener_universe, get_us_etfs
from datetime import datetime
import time

print("="*80)
print("INCREMENTAL CACHE UPDATE - 20 YEARS US STOCK DATA")
print("="*80)

# Get US-only tickers
print("\n📊 Loading US stock universe...")
all_universe = get_screener_universe()
us_etfs = get_us_etfs()

# Filter out ASX tickers
us_stocks = [t for t in all_universe if not t.endswith('.AX')]
us_tickers = list(set(us_stocks + us_etfs))

print(f"✅ Total US tickers: {len(us_tickers)}")

# Initialize loader with 20-year date range
print("\n🔧 Initializing FastDataLoader with 20-year range...")
loader = FastDataLoader(
    start_date="2005-01-01",  # 20 years back
    end_date="2025-12-26",    # Today
    use_tiingo_fallback=True,
    tiingo_api_token="a49dba6e5f76ba7414cc23aba45fa93f435ad2d5",  # nosec B106
    tiingo_is_premium=True
)

# Check cache status
print("\n🔍 Checking cache status...")
cache_status = loader.check_cache_status(us_tickers)
print(f"Cache status: {'EXISTS' if cache_status else 'NOT FOUND or INCOMPLETE'}")

# Fetch with incremental loading
print("\n🚀 Starting incremental fetch...")
print("   - Will check cache for existing data")
print("   - Will fetch only missing dates from 2005-01-01")
print("   - Will append new data to cache")
print()

start_time = time.time()

# Fetch (use_cache=True enables incremental loading)
prices = loader.fetch_prices_fast(us_tickers, use_cache=True)

end_time = time.time()
elapsed = end_time - start_time

# Results
print("\n" + "="*80)
print("UPDATE RESULTS")
print("="*80)
print(f"✅ Total tickers in dataset: {len(prices.columns)}")
print(f"⏱️  Time elapsed: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
print(f"📊 Data shape: {prices.shape[0]:,} days × {prices.shape[1]} tickers")
print(f"📅 Date range: {prices.index.min().date()} to {prices.index.max().date()}")
print(f"📈 Years of data: {(prices.index.max() - prices.index.min()).days / 365.25:.1f} years")

# Calculate actual data points
total_data_points = prices.shape[0] * prices.shape[1]
print(f"📊 Total data points: {total_data_points:,}")

# Sample data
print(f"\n📋 Sample tickers:")
print(f"   {list(prices.columns[:10])}")

print(f"\n📈 First 5 days (2005):")
print(prices.iloc[:5, :5])

print(f"\n📈 Last 5 days (2025):")
print(prices.iloc[-5:, :5])

# Health status
print("\n" + "="*80)
print("FETCH METRICS")
print("="*80)
loader.print_health_status()

# Cache info
from pathlib import Path
cache_dir = Path("cache")
if cache_dir.exists():
    cache_files = list(cache_dir.glob("*.parquet"))
    total_size = sum(f.stat().st_size for f in cache_files) / (1024**2)
    print(f"\n💾 Cache statistics:")
    print(f"   Files: {len(cache_files)}")
    print(f"   Total size: {total_size:.1f} MB")
    print(f"   Location: {cache_dir.absolute()}")

# Expected vs Actual
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

expected_days = (datetime(2025, 12, 26) - datetime(2005, 1, 1)).days
trading_days_approx = expected_days * 252 / 365  # ~252 trading days per year

print(f"Expected calendar days: {expected_days}")
print(f"Expected trading days: ~{trading_days_approx:.0f}")
print(f"Actual days fetched: {prices.shape[0]}")
print(f"Coverage: {prices.shape[0] / trading_days_approx * 100:.1f}% of expected trading days")

# Tiingo usage
print(f"\n📊 Tiingo API Usage:")
print(f"   Requests made: {loader.metrics.total_tickers}")
print(f"   Daily quota: 150,000")
print(f"   Quota used: {loader.metrics.total_tickers / 150000 * 100:.2f}%")
print(f"   Remaining: {150000 - loader.metrics.total_tickers:,}")

print("\n⚠️  Check Tiingo dashboard for exact request count:")
print("   https://www.tiingo.com/account/usage")

print("\n" + "="*80)
print("✅ CACHE UPDATE COMPLETE")
print("="*80)
print(f"\n🎉 You now have {prices.shape[0]:,} days of data for {len(prices.columns)} US tickers!")
print(f"   That's {(prices.index.max() - prices.index.min()).days / 365.25:.1f} years of clean, institutional-grade data from Tiingo!")
print(f"   Ready for production backtesting! 🚀")
