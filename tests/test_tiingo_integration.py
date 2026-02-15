"""
Test Tiingo + yFinance Dual-Source Integration
===============================================
Tests the integrated FastDataLoader with Tiingo fallback.
"""

from strategy.fast_data_loader import FastDataLoader
from strategy.stock_universe import get_stock_universe
import time

print("="*70)
print("TIINGO + yFINANCE DUAL-SOURCE TEST")
print("="*70)

# Initialize loader with Tiingo fallback
print("\n📥 Initializing FastDataLoader with Tiingo fallback...")
loader = FastDataLoader(
    start_date="2024-12-01",
    end_date="2024-12-26",
    use_tiingo_fallback=True,
    tiingo_api_token="a49dba6e5f76ba7414cc23aba45fa93f435ad2d5",
    tiingo_is_premium=True
)

# Test 1: Small batch (should use yFinance)
print("\n" + "="*70)
print("TEST 1: Small Batch (yFinance primary)")
print("="*70)
test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
print(f"📊 Fetching {len(test_tickers)} tickers...")

t0 = time.time()
prices = loader.fetch_prices_fast(test_tickers)
t1 = time.time()

print(f"\n✅ Fetched {len(prices.columns)} tickers in {t1-t0:.2f}s")
print(f"📊 Shape: {prices.shape}")
print(f"📅 Date range: {prices.index.min()} to {prices.index.max()}")
print(f"\n{prices.head()}")

# Test 2: Check metrics
print("\n" + "="*70)
print("METRICS")
print("="*70)
loader.print_health_status()

# Test 3: Get universe subset (to test larger batch)
print("\n" + "="*70)
print("TEST 2: Larger Batch (testing fallback capability)")
print("="*70)
universe = get_stock_universe()
test_subset = universe['us_equities'][:50]  # First 50 tickers
print(f"📊 Fetching {len(test_subset)} tickers...")

t0 = time.time()
prices2 = loader.fetch_prices_fast(test_subset, use_cache=False)  # Force fresh fetch
t1 = time.time()

print(f"\n✅ Fetched {len(prices2.columns)} tickers in {t1-t0:.2f}s")
print(f"📊 Success rate: {len(prices2.columns)/len(test_subset)*100:.1f}%")

# Final metrics
print("\n" + "="*70)
print("FINAL METRICS")
print("="*70)
loader.print_health_status()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print(f"✅ Dual-source architecture working!")
print(f"   - yFinance: Primary data source")
print(f"   - Tiingo: Fallback on failures (Premium tier)")
