"""
Test Tiingo Data Fetch for Current Stock Universe
==================================================
Fetches adjusted close and volume data for the current universe
to verify Tiingo API request usage.
"""

from strategy.fast_data_loader import FastDataLoader
from strategy.stock_universe import get_screener_universe, get_core_etfs
from datetime import datetime, timedelta
import time

print("="*80)
print("TIINGO DATA FETCH TEST - CURRENT UNIVERSE")
print("="*80)

# Get current stock universe
print("\n📊 Loading current stock universe...")
universe = get_screener_universe()
etfs = get_core_etfs()

# Combine all tickers
all_tickers = list(set(universe + etfs))
print(f"✅ Total tickers to fetch: {len(all_tickers)}")
print(f"   - Stocks: {len(universe)}")
print(f"   - ETFs: {len(etfs)}")

# Initialize FastDataLoader with Tiingo PRIMARY
print("\n🔧 Initializing FastDataLoader with Tiingo PRIMARY source...")
loader = FastDataLoader(
    start_date="2024-12-01",  # Last month for quick test
    end_date="2025-12-26",
    use_tiingo_fallback=True,
    tiingo_api_token="a49dba6e5f76ba7414cc23aba45fa93f435ad2d5",
    tiingo_is_premium=True
)

# Fetch data
print(f"\n🚀 Starting data fetch...")
print(f"   Date range: 2024-12-01 to 2025-12-26")
print(f"   Expected requests: {len(all_tickers)} (1 per ticker)")
print(f"   Expected time: ~{len(all_tickers) * 0.1 / 60:.1f} minutes")
print()

start_time = time.time()

# Fetch prices
prices = loader.fetch_prices_fast(all_tickers, use_cache=False)

end_time = time.time()
elapsed = end_time - start_time

# Results
print("\n" + "="*80)
print("FETCH RESULTS")
print("="*80)
print(f"✅ Success! Fetched {len(prices.columns)} out of {len(all_tickers)} tickers")
print(f"⏱️  Time elapsed: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
print(f"📊 Data shape: {prices.shape}")
print(f"📅 Date range: {prices.index.min()} to {prices.index.max()}")
print(f"🎯 Success rate: {len(prices.columns)/len(all_tickers)*100:.1f}%")

# Show sample data
print(f"\n📈 Sample data (first 5 tickers, last 5 days):")
print(prices.iloc[-5:, :5])

# Health status
print("\n" + "="*80)
print("LOADER HEALTH STATUS")
print("="*80)
loader.print_health_status()

# Expected vs Actual
print("\n" + "="*80)
print("TIINGO REQUEST VERIFICATION")
print("="*80)
print(f"Expected Tiingo requests: {len(all_tickers)}")
print(f"Successful fetches: {len(prices.columns)}")
print(f"Failed fetches: {len(all_tickers) - len(prices.columns)}")
print()
print("⚠️  IMPORTANT: Check your Tiingo dashboard to confirm actual request count!")
print("   Expected count should match the number of successful fetches.")
print("   URL: https://www.tiingo.com/account/usage")
print()
print("="*80)

# Save to cache for inspection
cache_file = loader.cache_dir / "test_fetch_results.parquet"
prices.to_parquet(cache_file)
print(f"\n💾 Results saved to: {cache_file}")
print()
print("="*80)
print("TEST COMPLETE")
print("="*80)
