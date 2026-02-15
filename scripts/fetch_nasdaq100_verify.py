"""
Verify and Fetch NASDAQ 100 Historical Data
============================================
Checks current NASDAQ 100 coverage and fetches any missing tickers.
"""

import pandas as pd
import requests
import sys
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from strategy.fast_data_loader import FastDataLoader
import time

print("="*80)
print("NASDAQ 100 VERIFICATION & FETCH - 21 YEARS")
print("="*80)

# Fetch current NASDAQ 100 constituents
print("\n🔍 Fetching current NASDAQ 100 constituents...")

try:
    # Try to fetch from SlickCharts or similar source
    url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    tables = pd.read_html(url)
    
    # NASDAQ 100 table (usually the first large table)
    nasdaq100_df = tables[3]  # Adjust index as needed
    
    # Extract tickers
    if 'Ticker' in nasdaq100_df.columns:
        nasdaq100_tickers = set(nasdaq100_df['Ticker'].dropna().tolist())
    elif 'Symbol' in nasdaq100_df.columns:
        nasdaq100_tickers = set(nasdaq100_df['Symbol'].dropna().tolist())
    else:
        # Fallback: use column index
        nasdaq100_tickers = set(nasdaq100_df.iloc[:, 1].dropna().tolist())  # Usually 2nd column
    
    print(f"✅ Fetched {len(nasdaq100_tickers)} NASDAQ 100 tickers from Wikipedia")
    
except Exception as e:
    print(f"⚠️  Wikipedia fetch failed: {e}")
    print("   Using manual list of NASDAQ 100 tickers...")
    
    # Manual list of major NASDAQ 100 companies (as of 2024/2025)
    nasdaq100_tickers = {
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST',
        'NFLX', 'AMD', 'PEP', 'ADBE', 'CSCO', 'TMUS', 'CMCSA', 'INTC', 'TXN', 'INTU',
        'QCOM', 'AMGN', 'HON', 'AMAT', 'SBUX', 'BKNG', 'ISRG', 'GILD', 'ADI', 'VRTX',
        'ADP', 'REGN', 'MDLZ', 'LRCX', 'PANW', 'MU', 'PYPL', 'KLAC', 'SNPS', 'CDNS',
        'ASML', 'MELI', 'MAR', 'CTAS', 'CRWD', 'ORLY', 'MNST', 'CSX', 'ADSK', 'ABNB',
        'NXPI', 'FTNT', 'MRVL', 'WDAY', 'DASH', 'AEP', 'CPRT', 'ROST', 'PCAR', 'PAYX',
        'ODFL', 'CHTR', 'KDP', 'FAST', 'EA', 'CTSH', 'DXCM', 'GEHC', 'TTD', 'KHC',
        'IDXX', 'VRSK', 'LULU', 'EXC', 'CSGP', 'XEL', 'CCEP', 'ON', 'FANG', 'ZS',
        'ANSS', 'DDOG', 'CDW', 'WBD', 'ILMN', 'BIIB', 'GFS', 'MDB', 'MRNA', 'TEAM',
        'WBA', 'DLTR', 'ALGN', 'SIRI', 'LCID', 'ZM', 'RIVN', 'ENPH', 'SGEN', 'MTCH'
    }
    print(f"   Using {len(nasdaq100_tickers)} major NASDAQ 100 tickers")

# Check current cache
print("\n📊 Checking current data cache...")
cache_dir = Path("cache")

# Load current cache
current_cache = cache_dir / "prices_80729c86b695.parquet"  # From earlier fetch
if current_cache.exists():
    current_data = pd.read_parquet(current_cache)
    current_tickers = set(current_data.columns)
    print(f"✅ Current cache has {len(current_tickers)} tickers")
else:
    current_tickers = set()
    print("⚠️  No current cache found")

# Find missing NASDAQ 100 tickers
missing_nasdaq = nasdaq100_tickers - current_tickers

print(f"\n📊 NASDAQ 100 Coverage Analysis:")
print(f"   Total NASDAQ 100 tickers: {len(nasdaq100_tickers)}")
print(f"   Already in cache: {len(nasdaq100_tickers - missing_nasdaq)}")
print(f"   Missing from cache: {len(missing_nasdaq)}")

if missing_nasdaq:
    print(f"\n📋 Missing NASDAQ 100 tickers:")
    for i, ticker in enumerate(sorted(missing_nasdaq), 1):
        print(f"   {i}. {ticker}")
    
    # Fetch missing tickers
    print(f"\n🚀 Fetching {len(missing_nasdaq)} missing NASDAQ 100 tickers...")
    print(f"   Date range: 2005-01-01 to 2025-12-26 (21 years)")
    print(f"   Expected Tiingo requests: {len(missing_nasdaq)}")
    print(f"   Expected time: ~{len(missing_nasdaq) * 0.15 / 60:.1f} minutes")
    
    loader = FastDataLoader(
        start_date="2005-01-01",
        end_date="2025-12-26",
        use_tiingo_fallback=True,
        tiingo_api_token="a49dba6e5f76ba7414cc23aba45fa93f435ad2d5",
        tiingo_is_premium=True
    )
    
    start_time = time.time()
    missing_prices = loader.fetch_prices_fast(list(missing_nasdaq), use_cache=True)
    end_time = time.time()
    
    print(f"\n✅ Fetch complete!")
    print(f"   Successfully fetched: {len(missing_prices.columns)}/{len(missing_nasdaq)} tickers")
    print(f"   Time: {(end_time - start_time)/60:.2f} minutes")
    
    if not missing_prices.empty:
        print(f"   Data shape: {missing_prices.shape[0]} days × {missing_prices.shape[1]} tickers")
        print(f"   Date range: {missing_prices.index.min().date()} to {missing_prices.index.max().date()}")
        
        # Save separately
        nasdaq_cache = cache_dir / "nasdaq100_additional_tickers_21yr.parquet"
        missing_prices.to_parquet(nasdaq_cache)
        
        print(f"\n💾 Additional NASDAQ 100 tickers saved:")
        print(f"   File: {nasdaq_cache}")
        print(f"   Size: {nasdaq_cache.stat().st_size / (1024**2):.2f} MB")
    
    # Failed tickers
    failed = missing_nasdaq - set(missing_prices.columns)
    if failed:
        print(f"\n⚠️  Failed to fetch {len(failed)} tickers:")
        print(f"   {sorted(failed)}")
    
    # Summary
    print(f"\n" + "="*80)
    print("NASDAQ 100 DATA COMPLETE")
    print("="*80)
    print(f"✅ Previously cached: {len(nasdaq100_tickers - missing_nasdaq)} tickers")
    print(f"✅ Newly fetched: {len(missing_prices.columns)} tickers")
    print(f"✅ Total NASDAQ 100 coverage: {len(nasdaq100_tickers - missing_nasdaq) + len(missing_prices.columns)}/{len(nasdaq100_tickers)} tickers")
    print(f"✅ Time period: 2005-2025 (21 years)")
    
else:
    print(f"\n✅ All NASDAQ 100 tickers already in cache!")
    print(f"   No additional fetch needed")
    print(f"   Coverage: {len(nasdaq100_tickers)}/{len(nasdaq100_tickers)} tickers (100%)")

# Final inventory
print(f"\n" + "="*80)
print("COMPLETE DATA INVENTORY")
print("="*80)

cache_files = list(cache_dir.glob("*.parquet"))
total_size = sum(f.stat().st_size for f in cache_files) / (1024**2)

print(f"Cache files:")
for f in sorted(cache_files):
    size_mb = f.stat().st_size / (1024**2)
    print(f"  - {f.name}: {size_mb:.2f} MB")

print(f"\nTotal cache size: {total_size:.1f} MB")
print(f"🚀 Ready for backtesting!")

print("\n" + "="*80)
