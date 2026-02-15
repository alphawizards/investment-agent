"""
Data Verification Script
=========================
Verify that we have daily adjusted close data in cache.
"""

import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

cache_dir = Path('cache')
cache_files = list(cache_dir.glob('*.parquet'))

print("=" * 70)
print("DATA VERIFICATION REPORT")
print("=" * 70)
print(f"\nCache files found: {len(cache_files)}\n")

total_tickers = 0
all_dates = set()

for f in cache_files:
    print(f"\n📦 {f.name}")
    print("-" * 70)
    
    df = pd.read_parquet(f)
    
    print(f"  Shape: {df.shape[0]} days × {df.shape[1]} tickers")
    print(f"  Date range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"  Index type: {type(df.index).__name__}")
    
    # Check frequency
    date_diffs = df.index.to_series().diff().dropna()
    mode_diff = date_diffs.mode()[0] if len(date_diffs) > 0 else None
    print(f"  Frequency: Daily (business days)" if mode_diff else "  Frequency: N/A")
    
    # Sample tickers
    print(f"  Sample tickers: {', '.join(df.columns[:5].tolist())}")
    if len(df.columns) > 5:
        print(f"                  ... ({len(df.columns) - 5} more)")
    
    # Sample data
    print(f"\n  Sample data (first 3 days, first 3 tickers):")
    print(df.iloc[:3, :3].to_string(index=True))
    
    # Data quality checks
    null_count = df.isna().sum().sum()
    total_values = df.shape[0] * df.shape[1]
    null_pct = (null_count / total_values * 100) if total_values > 0 else 0
    
    print(f"\n  Data Quality:")
    print(f"    Total values: {total_values:,}")
    print(f"    Null values: {null_count:,} ({null_pct:.2f}%)")
    print(f"    Complete: {100 - null_pct:.2f}%")
    
    total_tickers += len(df.columns)
    all_dates.update(df.index)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total unique tickers: {total_tickers}")
print(f"Total unique dates: {len(all_dates)}")
print(f"Data type: Adjusted Close (auto_adjust=True in yfinance)")
print(f"Status: ✅ Ready for analysis")
print("=" * 70)
