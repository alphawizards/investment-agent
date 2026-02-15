#!/usr/bin/env python3
"""
ASX Data Fetch Script
======================
Utilizes the UnifiedASXLoader to fetch ASX data from Norgate (primary)
with yfinance fallback.

Outputs:
- cache/asx_prices_hybrid.parquet (Adjusted Close)
- cache/asx_volume_hybrid.parquet (Volume)
- Source report showing % from Norgate vs yFinance

Usage:
    python fetch_asx_data.py
    python fetch_asx_data.py --start-date 2023-01-01
    python fetch_asx_data.py --indices-only
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategy.unified_asx_loader import UnifiedASXLoader
from strategy.stock_universe import get_asx200_tickers, get_asx_etfs


# ============================================================================
# ASX INDICES
# ============================================================================

ASX_INDICES = [
    '^AXJO',    # S&P/ASX 200
    '^AORD',    # All Ordinaries
]


# ============================================================================
# MAIN FETCH FUNCTION
# ============================================================================

def fetch_asx_universe(
    start_date: str = '2024-01-01',
    end_date: str = None,
    include_indices: bool = True,
    include_stocks: bool = True,
    include_etfs: bool = True,
    output_dir: str = 'cache',
    verbose: bool = True
) -> dict:
    """
    Fetch the full ASX universe data.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (defaults to today)
        include_indices: Include ASX indices (^AXJO, ^AORD)
        include_stocks: Include ASX 200 stocks
        include_etfs: Include ASX ETFs
        output_dir: Directory for parquet output
        verbose: Print detailed status
        
    Returns:
        dict with summary statistics
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 70)
    print("ASX Data Fetch - Hybrid Norgate/yFinance")
    print("=" * 70)
    print(f"Date Range: {start_date} to {end_date}")
    print("=" * 70)
    
    # Build ticker universe
    tickers = []
    
    if include_stocks:
        asx200 = get_asx200_tickers()
        tickers.extend(asx200)
        print(f"\n[Universe] Added {len(asx200)} ASX 200 stocks")
    
    if include_etfs:
        etfs = get_asx_etfs()
        # Remove duplicates from ETFs if already in ASX200
        new_etfs = [e for e in etfs if e not in tickers]
        tickers.extend(new_etfs)
        print(f"[Universe] Added {len(new_etfs)} ASX ETFs")
    
    if include_indices:
        # Add indices (not duplicated)
        new_indices = [i for i in ASX_INDICES if i not in tickers]
        tickers.extend(new_indices)
        print(f"[Universe] Added {len(new_indices)} ASX Indices")
    
    # Remove duplicates while preserving order
    tickers = list(dict.fromkeys(tickers))
    print(f"\n[Universe] Total unique tickers: {len(tickers)}")
    
    # Initialize loader and fetch data
    loader = UnifiedASXLoader(verbose=verbose)
    
    prices_df, volume_df = loader.fetch_data(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date
    )
    
    if prices_df.empty:
        print("\n❌ ERROR: No data was fetched!")
        return {'success': False}
    
    # Get source statistics
    source_stats = loader.get_source_statistics()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save to parquet
    prices_file = output_path / 'asx_prices_hybrid.parquet'
    volume_file = output_path / 'asx_volume_hybrid.parquet'
    
    prices_df.to_parquet(prices_file)
    volume_df.to_parquet(volume_file)
    
    print("\n" + "=" * 70)
    print("DATA SAVED")
    print("=" * 70)
    print(f"Prices: {prices_file} ({prices_file.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"Volume: {volume_file} ({volume_file.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Print source report
    print("\n" + "=" * 70)
    print("SOURCE REPORT")
    print("=" * 70)
    print(f"Total Tickers Fetched: {source_stats['total_tickers']}")
    print("")
    print("📊 NORGATE DATA:")
    print(f"   Count: {source_stats['norgate_count']} ({source_stats['norgate_pct']:.1f}%)")
    if source_stats['norgate_tickers']:
        preview = source_stats['norgate_tickers'][:10]
        print(f"   Sample: {', '.join(preview)}{'...' if len(source_stats['norgate_tickers']) > 10 else ''}")
    
    print("")
    print("📈 YFINANCE:")
    print(f"   Count: {source_stats['yfinance_count']} ({source_stats['yfinance_pct']:.1f}%)")
    if source_stats['yfinance_tickers']:
        preview = source_stats['yfinance_tickers'][:10]
        print(f"   Sample: {', '.join(preview)}{'...' if len(source_stats['yfinance_tickers']) > 10 else ''}")
    
    print("=" * 70)
    
    # Data quality summary
    print("\n" + "=" * 70)
    print("DATA QUALITY SUMMARY")
    print("=" * 70)
    
    # Check for missing data
    missing_pct = (prices_df.isna().sum() / len(prices_df) * 100).sort_values(ascending=False)
    high_missing = missing_pct[missing_pct > 10]
    
    if len(high_missing) > 0:
        print("\n⚠️ Tickers with >10% missing data:")
        for ticker, pct in high_missing.head(10).items():
            print(f"   {ticker}: {pct:.1f}% missing")
    else:
        print("✓ All tickers have <10% missing data")
    
    print("\n" + "=" * 70)
    print("✅ FETCH COMPLETE")
    print("=" * 70)
    
    return {
        'success': True,
        'prices_file': str(prices_file),
        'volume_file': str(volume_file),
        'tickers_requested': len(tickers),
        'tickers_fetched': source_stats['total_tickers'],
        'norgate_pct': source_stats['norgate_pct'],
        'yfinance_pct': source_stats['yfinance_pct'],
        'date_range': (start_date, end_date),
        'trading_days': len(prices_df),
    }


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Fetch ASX data using Norgate Data (primary) with yfinance fallback'
    )
    parser.add_argument(
        '--start-date', '-s',
        type=str,
        default='2024-01-01',
        help='Start date (YYYY-MM-DD), default: 2024-01-01'
    )
    parser.add_argument(
        '--end-date', '-e',
        type=str,
        default=None,
        help='End date (YYYY-MM-DD), default: today'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default='cache',
        help='Output directory for parquet files, default: cache'
    )
    parser.add_argument(
        '--indices-only',
        action='store_true',
        help='Only fetch indices (no stocks or ETFs)'
    )
    parser.add_argument(
        '--no-indices',
        action='store_true',
        help='Exclude indices'
    )
    parser.add_argument(
        '--no-etfs',
        action='store_true',
        help='Exclude ETFs'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    # Determine what to include
    if args.indices_only:
        include_stocks = False
        include_etfs = False
        include_indices = True
    else:
        include_stocks = True
        include_etfs = not args.no_etfs
        include_indices = not args.no_indices
    
    result = fetch_asx_universe(
        start_date=args.start_date,
        end_date=args.end_date,
        include_indices=include_indices,
        include_stocks=include_stocks,
        include_etfs=include_etfs,
        output_dir=args.output_dir,
        verbose=not args.quiet
    )
    
    if result['success']:
        print(f"\n🎉 Successfully fetched {result['tickers_fetched']} tickers")
        print(f"   Norgate: {result['norgate_pct']:.1f}% | yFinance: {result['yfinance_pct']:.1f}%")
    else:
        print("\n❌ Fetch failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
