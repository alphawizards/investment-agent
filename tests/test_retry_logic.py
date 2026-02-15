"""
Test Retry Logic and Enhancements
===================================
Test the enhanced FastDataLoader with retry logic and metrics.
"""

from strategy.fast_data_loader import FastDataLoader, RetryConfig
from strategy.stock_universe import get_core_etfs
import time

print("="*70)
print("FAST DATA LOADER - RETRY LOGIC TEST")
print("="*70)

# Test 1: Fetch with retry logic enabled
print("\n📋 Test 1: Fetch Core ETFs with Retry Logic")
print("-"*70)

loader = FastDataLoader(
    retry_config=RetryConfig(
        max_retries=3,
        base_delay=1.0,
        backoff_factor=2.0
    )
)

# Get core ETFs (21 tickers - small test)
tickers = get_core_etfs()
print(f"Fetching {len(tickers)} core ETFs...")
print(f"Tickers: {', '.join(tickers[:10])}...")

t0 = time.time()
prices, returns = loader.fetch_universe(tickers)
t1 = time.time()

print(f"\n✅ Fetch complete in {t1-t0:.2f}s")
print(f"📊 Retrieved: {len(prices.columns)} / {len(tickers)} tickers")
print(f"📅 Date range: {prices.index.min().date() if not prices.empty else 'N/A'} to {prices.index.max().date() if not prices.empty else 'N/A'}")

# Test 2: Check metrics
print("\n" + "="*70)
print("📊 Test 2: Metrics & Health Status")
print("="*70)

loader.print_health_status

()

# Test 3: Export failed ticker report (if any)
print("="*70)
print("📄 Test 3: Failed Ticker Report")
print("="*70)

if loader.failed_tickers:
    loader.export_failed_tickers_report()
else:
    print("✅ No failed tickers - all fetches successful!")

# Test 4: Cache stats
print("\n" + "="*70)
print("💾 Test 4: Cache Statistics")
print("="*70)

loader.print_cache_stats()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print(f"\nSummary:")
print(f"  Success Rate: {loader.metrics.success_rate:.1f}%")
print(f"  Total Retries: {loader.metrics.retry_count}")
print(f"  Failed Tickers: {loader.metrics.failed_tickers}")
print("\n" + "="*70)
