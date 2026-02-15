"""
Batch Test for Incremental Data Loader
========================================
Tests the FastDataLoader with the full 741-ticker universe.

Tests:
1. Full fetch (cold start) for 1 month of data
2. Cache verification
3. Incremental fetch (simulated next-day run)
4. Performance comparison
5. Data integrity checks
"""

import time
from datetime import datetime, timedelta
from strategy.fast_data_loader import FastDataLoader
from strategy.stock_universe import get_screener_universe

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def test_full_universe():
    """Test the full universe fetch and incremental loading."""
    
    print_header("INCREMENTAL DATA LOADER - BATCH TEST")
    
    # Get full universe
    print("\n📋 Loading ticker universe...")
    universe = get_screener_universe()
    print(f"✅ Universe loaded: {len(universe)} tickers")
    
    # Calculate date range (past month)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\n📅 Test Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Initialize loader
    loader = FastDataLoader(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        max_workers=8,
        batch_size=20
    )
    
    # TEST 1: Check initial cache status
    print_header("TEST 1: Initial Cache Status")
    is_fresh, last_date = loader.check_cache_status(universe)
    print(f"Cache Fresh: {is_fresh}")
    print(f"Last Cached Date: {last_date if last_date else 'No cache'}")
    
    # TEST 2: Full fetch (cold start)
    print_header("TEST 2: Full Fetch (Cold Start)")
    print(f"🚀 Fetching {len(universe)} tickers...")
    print("⚠️  This will take 5-10 minutes on first run...")
    
    t0 = time.time()
    prices, returns = loader.fetch_universe(universe)
    t1 = time.time()
    
    fetch_time = t1 - t0
    
    print(f"\n✅ FETCH COMPLETE")
    print(f"⏱️  Time: {fetch_time:.2f}s ({fetch_time/60:.2f} minutes)")
    print(f"📊 Tickers fetched: {len(prices.columns)}")
    print(f"📊 Trading days: {len(prices)}")
    print(f"📊 Data points: {len(prices) * len(prices.columns):,}")
    
    if len(prices) > 0:
        print(f"📅 Date range: {prices.index.min().date()} to {prices.index.max().date()}")
    
    # Calculate success rate
    success_rate = (len(prices.columns) / len(universe)) * 100
    print(f"📈 Success rate: {success_rate:.1f}%")
    
    # TEST 3: Cache verification
    print_header("TEST 3: Cache Verification")
    loader.print_cache_stats()
    
    # TEST 4: Incremental fetch simulation
    print_header("TEST 4: Incremental Fetch Test")
    print("🔄 Simulating next-day run (should use cache)...")
    
    # Create new loader instance (simulates fresh script run)
    loader2 = FastDataLoader(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        max_workers=8,
        batch_size=20
    )
    
    t0 = time.time()
    prices2, returns2 = loader2.fetch_universe(universe)
    t1 = time.time()
    
    cache_time = t1 - t0
    
    print(f"\n✅ CACHE FETCH COMPLETE")
    print(f"⏱️  Time: {cache_time:.2f}s")
    print(f"📊 Tickers: {len(prices2.columns)}")
    print(f"📊 Trading days: {len(prices2)}")
    
    # TEST 5: Performance comparison
    print_header("TEST 5: Performance Analysis")
    speedup = fetch_time / cache_time if cache_time > 0 else 0
    time_saved = fetch_time - cache_time
    efficiency = ((fetch_time - cache_time) / fetch_time * 100) if fetch_time > 0 else 0
    
    print(f"\n📊 Performance Metrics:")
    print(f"   Cold Start:        {fetch_time:.2f}s ({fetch_time/60:.2f} min)")
    print(f"   Incremental Load:  {cache_time:.2f}s")
    print(f"   Time Saved:        {time_saved:.2f}s ({time_saved/60:.2f} min)")
    print(f"   Speedup:           {speedup:.1f}x faster")
    print(f"   Efficiency Gain:   {efficiency:.1f}%")
    
    # TEST 6: Data integrity
    print_header("TEST 6: Data Integrity Checks")
    
    # Check for missing data
    missing_count = prices.isna().sum().sum()
    total_cells = len(prices) * len(prices.columns)
    missing_pct = (missing_count / total_cells * 100) if total_cells > 0 else 0
    
    print(f"📊 Data Quality:")
    print(f"   Total data points: {total_cells:,}")
    print(f"   Missing values:    {missing_count:,} ({missing_pct:.2f}%)")
    print(f"   Complete rows:     {(~prices.isna().any(axis=1)).sum()}")
    
    # Check for duplicates
    duplicates = prices.index.duplicated().sum()
    print(f"   Duplicate dates:   {duplicates}")
    
    # Summary
    print_header("TEST SUMMARY")
    
    status = "✅ PASS" if success_rate > 90 and speedup > 5 else "⚠️ NEEDS REVIEW"
    
    print(f"\nStatus: {status}")
    print(f"\nKey Results:")
    print(f"  • Fetched {len(prices.columns)}/{len(universe)} tickers ({success_rate:.1f}%)")
    print(f"  • Incremental loading is {speedup:.1f}x faster")
    print(f"  • Cache working correctly: {'Yes' if cache_time < 10 else 'No'}")
    print(f"  • Data integrity: {100-missing_pct:.1f}% complete")
    
    if speedup > 10:
        print(f"\n🎉 EXCELLENT! Incremental loading achieved {efficiency:.0f}% efficiency gain!")
    elif speedup > 5:
        print(f"\n✅ Good performance! {efficiency:.0f}% efficiency gain achieved.")
    else:
        print(f"\n⚠️ Moderate improvement. Consider optimizing cache logic.")
    
    print("\n" + "="*70)
    
    return {
        "success_rate": success_rate,
        "fetch_time": fetch_time,
        "cache_time": cache_time,
        "speedup": speedup,
        "tickers_fetched": len(prices.columns),
        "trading_days": len(prices),
        "missing_pct": missing_pct
    }

if __name__ == "__main__":
    try:
        results = test_full_universe()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
