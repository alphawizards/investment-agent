#!/usr/bin/env python
"""
Daily update script - fetches latest prices for all tickers.
Run this daily to keep database fresh.
"""
import sys
import os

# Add paths
sys.path.insert(0, 'C:/Users/ckr_4/01 Projects/investment-agent')
os.chdir('C:/Users/ckr_4/01 Projects/investment-agent')

from datetime import datetime, timedelta
import time
from data_gatherer.database import (
    get_all_tickers, insert_daily_prices_batch, 
    update_ticker_last_updated, start_update_history, finish_update_history,
    get_latest_price_date
)
from data_gatherer.yahoo_finance import YahooFinanceFetcher

print("Starting daily update...")
print()

# Get tickers
tickers = get_all_tickers()
print(f"Found {len(tickers)} tickers")

# Create fetcher
fetcher = YahooFinanceFetcher(max_workers=1)

# Start update history
update_id = start_update_history("daily_update")

succeeded = 0
failed = 0
total_records = 0

# Process each ticker
for i, ticker_data in enumerate(tickers):
    ticker = ticker_data['ticker']
    ticker_id = ticker_data['id']
    exchange = ticker_data.get('exchange', 'US')
    
    # Get last date in DB
    last_date = get_latest_price_date(ticker_id)
    
    print(f"[{i+1}/{len(tickers)}] Updating {ticker} ({exchange}) since {last_date or '5 days ago'}...", end=' ', flush=True)
    
    # Try different ticker formats
    tickers_to_try = []
    if exchange == 'ASX':
        tickers_to_try = [f"{ticker}.AX", ticker]
    else:
        if len(ticker) <= 3:
            tickers_to_try = [ticker, f"{ticker}.AX"]
        else:
            tickers_to_try = [ticker]
    
    success = False
    prices = []
    error_msg = None
    
    for t in tickers_to_try:
        ok, prices, err = fetcher.fetch_incremental(t, last_date=last_date)
        if ok and prices:
            success = True
            error_msg = None
            break
        error_msg = err
    
    if success and prices:
        count = insert_daily_prices_batch(ticker_id, prices)
        update_ticker_last_updated(ticker_id)
        succeeded += 1
        total_records += count
        print(f"OK - {len(prices)} new records")
    else:
        failed += 1
        print(f"SKIP - {error_msg or 'No new data'}")
    
    # Small delay between tickers
    time.sleep(0.3)

# Finish update history
finish_update_history(
    update_id,
    tickers_processed=len(tickers),
    tickers_succeeded=succeeded,
    tickers_failed=failed,
    records_inserted=total_records,
    status='completed' if failed == 0 else 'completed_with_errors'
)

print()
print("=" * 60)
print("DAILY UPDATE COMPLETE")
print("=" * 60)
print(f"Processed: {len(tickers)}")
print(f"Updated:   {succeeded}")
print(f"Skipped:   {failed}")
print(f"New Records: {total_records}")
