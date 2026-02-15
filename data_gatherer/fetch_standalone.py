#!/usr/bin/env python
"""
Standalone fetch script - completely avoids Unicode issues.
Handles US vs ASX tickers properly.
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
    update_ticker_last_updated, start_update_history, finish_update_history
)
from data_gatherer.yahoo_finance import YahooFinanceFetcher

# 5 years of data
start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')

print(f"Starting fetch from {start_date}...")
print("This will take several hours (1.5s delay per ticker).")
print()

# Get tickers
tickers = get_all_tickers()
print(f"Found {len(tickers)} tickers")

# Create fetcher with conservative rate limiting
fetcher = YahooFinanceFetcher(max_workers=1)

# Start update history
update_id = start_update_history("full_fetch_standalone")

succeeded = 0
failed = 0
total_records = 0

# Process each ticker
for i, ticker_data in enumerate(tickers):
    ticker = ticker_data['ticker']
    ticker_id = ticker_data['id']
    exchange = ticker_data.get('exchange', 'US')  # Default to US
    
    print(f"[{i+1}/{len(tickers)}] Fetching {ticker} ({exchange})...", end=' ', flush=True)
    
    # Try different ticker formats
    tickers_to_try = []
    if exchange == 'ASX':
        # For ASX: try with .AX suffix
        tickers_to_try = [f"{ticker}.AX", ticker]
    else:
        # For US: try as-is, maybe with .AX if short
        if len(ticker) <= 3:
            tickers_to_try = [ticker, f"{ticker}.AX"]
        else:
            tickers_to_try = [ticker]
    
    success = False
    prices = []
    error_msg = None
    
    for t in tickers_to_try:
        ok, prices, err = fetcher.fetch_ticker_history(t, start_date=start_date)
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
        print(f"OK - {len(prices)} records")
    else:
        failed += 1
        print(f"FAIL - {error_msg}")
    
    # Small delay between tickers
    time.sleep(0.5)

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
print("FETCH COMPLETE")
print("=" * 60)
print(f"Processed: {len(tickers)}")
print(f"Succeeded:  {succeeded}")
print(f"Failed:     {failed}")
print(f"Records:    {total_records}")
