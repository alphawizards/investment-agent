"""
Fetch 1 Year of ASX Ticker Data using yFinance
===============================================
Fetches ASX tickers (*.AX) using yFinance and saves to separate cache.
Since Tiingo doesn't support ASX tickers, we use yFinance as primary source.
"""

from strategy.fast_data_loader import FastDataLoader
from strategy.stock_universe import get_screener_universe, get_asx_etfs
from datetime import datetime
import time
from pathlib import Path
import sys
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*80)
print("ASX TICKER DATA FETCH - 1 YEAR (yFinance)")
print("="*80)

# Get ASX-only tickers
print("\n📊 Loading ASX stock universe...")
all_universe = get_screener_universe()
asx_etfs = get_asx_etfs()

# Filter for ASX tickers (those ending with .AX)
asx_stocks = [t for t in all_universe if t.endswith('.AX')]
asx_tickers = list(set(asx_stocks + asx_etfs))

print(f"✅ Total ASX tickers to fetch: {len(asx_tickers)}")
print(f"   - ASX Stocks: {len(asx_stocks)}")
print(f"   - ASX ETFs: {len(asx_etfs)}")

# Show sample
print(f"\n📋 Sample ASX tickers:")
print(f"   {asx_tickers[:10]}")

# Initialize FastDataLoader WITHOUT Tiingo (use yFinance directly)
print("\n🔧 Initializing FastDataLoader for ASX (yFinance primary)...")
loader = FastDataLoader(
    start_date="2024-01-01",  # 1 year back
    end_date="2025-12-26",
    use_tiingo_fallback=False,  # Don't use Tiingo for ASX
    max_workers=8,
    batch_size=20
)

# Fetch data
print(f"\n🚀 Starting 1-year ASX data fetch...")
print(f"   Date range: 2024-01-01 to 2025-12-26 (1 year)")
print(f"   Data source: yFinance (FREE)")
print(f"   Expected time: ~{len(asx_tickers) * 0.3 / 60:.1f} minutes")
print()

start_time = time.time()

# Fetch prices (this will use yFinance since Tiingo is disabled)
prices = loader.fetch_prices_fast(asx_tickers, use_cache=True)

end_time = time.time()
elapsed = end_time - start_time

# Results
print("\n" + "="*80)
print("FETCH RESULTS")
print("="*80)

if prices.empty or len(prices.columns) == 0:
    print("❌ No data fetched! All tickers failed.")
else:
    print(f"✅ Success! Fetched {len(prices.columns)} out of {len(asx_tickers)} tickers")
    print(f"⏱️  Time elapsed: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print(f"📊 Data shape: {prices.shape[0]} days × {prices.shape[1]} tickers")
    print(f"📅 Date range: {prices.index.min().date()} to {prices.index.max().date()}")
    print(f"📈 Years of data: {(prices.index.max() - prices.index.min()).days / 365.25:.1f} years")
    print(f"🎯 Success rate: {len(prices.columns)/len(asx_tickers)*100:.1f}%")

# Sample data
print(f"\n📋 Successfully fetched tickers:")
print(f"   {list(prices.columns[:10])}")

print(f"\n📈 Sample data (last 5 days, first 5 tickers):")
print(prices.iloc[-5:, :min(5, len(prices.columns))])

# Health status
print("\n" + "="*80)
print("FETCH METRICS")
print("="*80)
loader.print_health_status()

# Save to separate ASX cache file
cache_dir = Path("cache")
cache_dir.mkdir(exist_ok=True)

asx_cache_file = cache_dir / "asx_prices_1yr.parquet"
prices.to_parquet(asx_cache_file)

print(f"\n💾 ASX Cache saved separately:")
print(f"   File: {asx_cache_file}")
print(f"   Size: {asx_cache_file.stat().st_size / (1024**2):.2f} MB")
print(f"   Tickers: {len(prices.columns)}")
print(f"   Days: {len(prices)}")

# Cache summary
cache_files = list(cache_dir.glob("*.parquet"))
total_size = sum(f.stat().st_size for f in cache_files) / (1024**2)

print(f"\n💾 Total cache statistics:")
print(f"   Files: {len(cache_files)}")
for f in sorted(cache_files):
    size_mb = f.stat().st_size / (1024**2)
    print(f"   - {f.name}: {size_mb:.2f} MB")
print(f"   Total size: {total_size:.1f} MB")

print("\n" + "="*80)
print("✅ ASX DATA FETCH COMPLETE")
print("="*80)
print(f"\n🎉 You now have {len(prices)} days of ASX data for {len(prices.columns)} tickers!")
print(f"   US data (Tiingo): 21 years, 529 tickers")
print(f"   ASX data (yFinance): 1 year, {len(prices.columns)} tickers")
print(f"   Combined universe ready for backtesting! 🚀")
