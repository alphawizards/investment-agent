"""
Main data gatherer - fetches and stores stock data from Yahoo Finance.
"""
import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_gatherer.database import (
    init_database,
    add_ticker,
    add_tickers_batch,
    get_ticker_id,
    get_all_tickers,
    get_latest_price_date,
    insert_daily_prices_batch,
    log_data_quality_issue,
    update_ticker_last_updated,
    start_update_history,
    finish_update_history,
    get_data_freshness,
)
from data_gatherer.yahoo_finance import YahooFinanceFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Default ticker universes
US_TICKERS = [
    # S&P 500 ETFs
    {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF', 'exchange': 'US', 'sector': 'ETF'},
    {'ticker': 'IVV', 'name': 'iShares Core S&P 500 ETF', 'exchange': 'US', 'sector': 'ETF'},
    {'ticker': 'VOO', 'name': 'Vanguard S&P 500 ETF', 'exchange': 'US', 'sector': 'ETF'},
    # Tech
    {'ticker': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'US', 'sector': 'Technology'},
    {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'exchange': 'US', 'sector': 'Technology'},
    {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'US', 'sector': 'Technology'},
    {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'exchange': 'US', 'sector': 'Technology'},
    {'ticker': 'META', 'name': 'Meta Platforms Inc.', 'exchange': 'US', 'sector': 'Technology'},
    # Finance
    {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.', 'exchange': 'US', 'sector': 'Financial'},
    {'ticker': 'BAC', 'name': 'Bank of America', 'exchange': 'US', 'sector': 'Financial'},
    {'ticker': 'WFC', 'name': 'Wells Fargo', 'exchange': 'US', 'sector': 'Financial'},
    # Consumer
    {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'exchange': 'US', 'sector': 'Consumer'},
    {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'exchange': 'US', 'sector': 'Consumer'},
    {'ticker': 'WMT', 'name': 'Walmart Inc.', 'exchange': 'US', 'sector': 'Consumer'},
    # Healthcare
    {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'exchange': 'US', 'sector': 'Healthcare'},
    {'ticker': 'UNH', 'name': 'UnitedHealth Group', 'exchange': 'US', 'sector': 'Healthcare'},
    # Energy
    {'ticker': 'XOM', 'name': 'Exxon Mobil', 'exchange': 'US', 'sector': 'Energy'},
    {'ticker': 'CVX', 'name': 'Chevron Corporation', 'exchange': 'US', 'sector': 'Energy'},
    # US Bond ETFs
    {'ticker': 'AGG', 'name': 'iShares Core US Aggregate Bond ETF', 'exchange': 'US', 'sector': 'ETF'},
    {'ticker': 'BND', 'name': 'Vanguard Total Bond Market ETF', 'exchange': 'US', 'sector': 'ETF'},
    # International
    {'ticker': 'VXUS', 'name': 'Vanguard Total International Stock ETF', 'exchange': 'US', 'sector': 'ETF'},
    {'ticker': 'EFA', 'name': 'iShares MSCI EAFE ETF', 'exchange': 'US', 'sector': 'ETF'},
    # Gold
    {'ticker': 'GLD', 'name': 'SPDR Gold Shares', 'exchange': 'US', 'sector': 'Commodity'},
    # Tech ETFs
    {'ticker': 'QQQ', 'name': 'Invesco QQQ Trust', 'exchange': 'US', 'sector': 'ETF'},
    {'ticker': 'XLK', 'name': 'Technology Select Sector SPDR', 'exchange': 'US', 'sector': 'ETF'},
]

ASX_TICKERS = [
    # Large Cap
    {'ticker': 'BHP', 'name': 'BHP Group Ltd', 'exchange': 'ASX', 'sector': 'Materials'},
    {'ticker': 'RIO', 'name': 'Rio Tinto Ltd', 'exchange': 'ASX', 'sector': 'Materials'},
    {'ticker': 'CBA', 'name': 'Commonwealth Bank', 'exchange': 'ASX', 'sector': 'Financial'},
    {'ticker': 'WBC', 'name': 'Westpac Banking', 'exchange': 'ASX', 'sector': 'Financial'},
    {'ticker': 'ANZ', 'name': 'ANZ Banking Group', 'exchange': 'ASX', 'sector': 'Financial'},
    {'ticker': 'NAB', 'name': 'National Australia Bank', 'exchange': 'ASX', 'sector': 'Financial'},
    # Tech
    {'ticker': 'CSL', 'name': 'CSL Limited', 'exchange': 'ASX', 'sector': 'Healthcare'},
    {'ticker': 'TLS', 'name': 'Telstra Corporation', 'exchange': 'ASX', 'sector': 'Telecom'},
    # Retail & Consumer
    {'ticker': 'WOW', 'name': 'Woolworths Group', 'exchange': 'ASX', 'sector': 'Consumer'},
    {'ticker': 'COL', 'name': 'Coles Group', 'exchange': 'ASX', 'sector': 'Consumer'},
    # Energy
    {'ticker': 'WDS', 'name': 'Woodside Energy', 'exchange': 'ASX', 'sector': 'Energy'},
    {'ticker': 'STO', 'name': 'Santos Limited', 'exchange': 'ASX', 'sector': 'Energy'},
    # Mining
    {'ticker': 'FMG', 'name': 'Fortescue Metals', 'exchange': 'ASX', 'sector': 'Materials'},
    {'ticker': 'NCM', 'name': 'Newcrest Mining', 'exchange': 'ASX', 'sector': 'Materials'},
    # Real Estate
    {'ticker': 'VCX', 'name': 'Vicinity Centres', 'exchange': 'ASX', 'sector': 'Real Estate'},
    {'ticker': 'SCG', 'name': 'Scentre Group', 'exchange': 'ASX', 'sector': 'Real Estate'},
    # Australian ETFs
    {'ticker': 'VAS', 'name': 'Vanguard Australian Share Index ETF', 'exchange': 'ASX', 'sector': 'ETF'},
    {'ticker': 'VGS', 'name': 'Vanguard International Shares ETF', 'exchange': 'ASX', 'sector': 'ETF'},
    {'ticker': 'VAF', 'name': 'Vanguard Australian Fixed Interest ETF', 'exchange': 'ASX', 'sector': 'ETF'},
    {'ticker': 'GOLD', 'name': 'BetaShares Gold ETF', 'exchange': 'ASX', 'sector': 'ETF'},
]


def setup_universe(exchange: str = 'all') -> int:
    """Add tickers to the database universe."""
    tickers_to_add = []
    
    if exchange in ('all', 'us'):
        tickers_to_add.extend(US_TICKERS)
    if exchange in ('all', 'asx'):
        tickers_to_add.extend(ASX_TICKERS)
    
    count = add_tickers_batch(tickers_to_add)
    logger.info(f"Added {count} tickers to universe")
    return count


def fetch_all_historical(
    exchange: str = 'all',
    start_date: str = None,
    max_workers: int = 5,
    verbose: bool = False
) -> Dict[str, int]:
    """
    Fetch historical data for all tickers in the universe.
    
    Returns dict with stats: tickers_processed, tickers_succeeded, tickers_failed, records_inserted
    """
    if start_date is None:
        # Default to 10 years of history
        start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    
    # Get tickers
    tickers = get_all_tickers()
    if exchange == 'us':
        tickers = [t for t in tickers if t['exchange'] == 'US']
    elif exchange == 'asx':
        tickers = [t for t in tickers if t['exchange'] == 'ASX']
    
    if not tickers:
        logger.warning("No tickers found in database. Run with --setup first.")
        return {'tickers_processed': 0, 'tickers_succeeded': 0, 'tickers_failed': 0, 'records_inserted': 0}
    
    # Create fetcher
    fetcher = YahooFinanceFetcher(max_workers=max_workers)
    
    # Start update history
    update_id = start_update_history(f"full_load_{exchange}")
    
    succeeded = 0
    failed = 0
    total_records = 0
    
    def progress(current, total):
        if verbose:
            print(f"\rProgress: {current}/{total}", end='', flush=True)
    
    # Process each ticker
    for ticker_data in tickers:
        ticker = ticker_data['ticker']
        ticker_id = ticker_data['id']
        
        if verbose:
            print(f"\nFetching {ticker}...", end=' ')
        
        success, prices, error = fetcher.fetch_ticker_history(
            ticker, 
            start_date=start_date
        )
        
        if success and prices:
            count = insert_daily_prices_batch(ticker_id, prices)
            update_ticker_last_updated(ticker_id)
            succeeded += 1
            total_records += count
            if verbose:
                print(f"✓ {len(prices)} records")
        else:
            failed += 1
            if verbose:
                print(f"✗ {error}")
    
    if verbose:
        print()  # New line after progress
    
    # Finish update history
    finish_update_history(
        update_id,
        tickers_processed=len(tickers),
        tickers_succeeded=succeeded,
        tickers_failed=failed,
        records_inserted=total_records,
        status='completed' if failed == 0 else 'completed_with_errors'
    )
    
    logger.info(f"Historical fetch complete: {succeeded}/{len(tickers)} succeeded, {total_records} records")
    
    return {
        'tickers_processed': len(tickers),
        'tickers_succeeded': succeeded,
        'tickers_failed': failed,
        'records_inserted': total_records
    }


def update_daily(exchange: str = 'all', max_workers: int = 5, verbose: bool = False) -> Dict[str, int]:
    """
    Update daily prices for all tickers (incremental).
    """
    # Get tickers
    tickers = get_all_tickers()
    if exchange == 'us':
        tickers = [t for t in tickers if t['exchange'] == 'US']
    elif exchange == 'asx':
        tickers = [t for t in tickers if t['exchange'] == 'ASX']
    
    if not tickers:
        logger.warning("No tickers found in database.")
        return {'tickers_processed': 0, 'tickers_succeeded': 0, 'tickers_failed': 0, 'records_inserted': 0}
    
    # Create fetcher
    fetcher = YahooFinanceFetcher(max_workers=max_workers)
    
    # Start update history
    update_id = start_update_history(f"daily_update_{exchange}")
    
    succeeded = 0
    failed = 0
    total_records = 0
    
    # Process each ticker
    for ticker_data in tickers:
        ticker = ticker_data['ticker']
        ticker_id = ticker_data['id']
        
        # Get last date in database
        last_date = get_latest_price_date(ticker_id)
        
        if verbose:
            print(f"\nFetching {ticker} since {last_date or '5 days ago'}...", end=' ')
        
        success, prices, error = fetcher.fetch_incremental(ticker, last_date=last_date)
        
        if success and prices:
            count = insert_daily_prices_batch(ticker_id, prices)
            update_ticker_last_updated(ticker_id)
            succeeded += 1
            total_records += count
            if verbose:
                print(f"✓ {len(prices)} new records")
        else:
            failed += 1
            if verbose:
                print(f"✗ {error or 'No new data'}")
    
    # Finish update history
    finish_update_history(
        update_id,
        tickers_processed=len(tickers),
        tickers_succeeded=succeeded,
        tickers_failed=failed,
        records_inserted=total_records,
        status='completed' if failed == 0 else 'completed_with_errors'
    )
    
    logger.info(f"Daily update complete: {succeeded}/{len(tickers)} succeeded, {total_records} new records")
    
    return {
        'tickers_processed': len(tickers),
        'tickers_succeeded': succeeded,
        'tickers_failed': failed,
        'records_inserted': total_records
    }


def check_freshness():
    """Display data freshness information."""
    freshness = get_data_freshness()
    
    print("\n" + "="*60)
    print("DATA FRESHNESS REPORT")
    print("="*60)
    print(f"Total Tickers: {freshness['total_tickers']}")
    print(f"Total Records: {freshness['total_records']}")
    print(f"Date Range: {freshness['earliest_date']} to {freshness['latest_date']}")
    
    print("\n--- Most Recent Updates ---")
    for item in freshness['recent_updates'][:10]:
        print(f"  {item['ticker']:6} ({item['exchange']:3}): {item['max_date']} ({item['record_count']} days)")
    
    if freshness['stale_tickers']:
        print("\n--- Stale Tickers (>7 days old) ---")
        for item in freshness['stale_tickers']:
            print(f"  {item['ticker']}: {item['last_updated']}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Stock Data Gatherer - Fetch and store daily stock prices'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Initialize database and add tickers')
    setup_parser.add_argument(
        '--exchange', 
        choices=['all', 'us', 'asx'], 
        default='all',
        help='Which exchange to set up'
    )
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch historical data')
    fetch_parser.add_argument(
        '--exchange',
        choices=['all', 'us', 'asx'],
        default='all',
        help='Which exchange to fetch'
    )
    fetch_parser.add_argument(
        '--start-date',
        help='Start date (YYYY-MM-DD). Default: 10 years ago'
    )
    fetch_parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of parallel workers'
    )
    fetch_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    # Update command (daily)
    update_parser = subparsers.add_parser('update', help='Update daily prices (incremental)')
    update_parser.add_argument(
        '--exchange',
        choices=['all', 'us', 'asx'],
        default='all',
        help='Which exchange to update'
    )
    update_parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of parallel workers'
    )
    update_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    # Freshness command
    subparsers.add_parser('freshness', help='Check data freshness')
    
    # Init command
    subparsers.add_parser('init', help='Initialize database schema only')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_database()
        
    elif args.command == 'setup':
        init_database()
        setup_universe(args.exchange)
        print(f"\n✓ Database initialized with {args.exchange.upper()} tickers")
        print("Run 'python -m data_gatherer fetch' to download historical data")
        
    elif args.command == 'fetch':
        result = fetch_all_historical(
            exchange=args.exchange,
            start_date=args.start_date,
            max_workers=args.workers,
            verbose=args.verbose
        )
        print(f"\n✓ Fetch complete: {result['tickers_succeeded']}/{result['tickers_processed']} tickers, {result['records_inserted']} records")
        
    elif args.command == 'update':
        result = update_daily(
            exchange=args.exchange,
            max_workers=args.workers,
            verbose=args.verbose
        )
        print(f"\n✓ Update complete: {result['tickers_succeeded']}/{result['tickers_processed']} tickers, {result['records_inserted']} new records")
        
    elif args.command == 'freshness':
        check_freshness()
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
