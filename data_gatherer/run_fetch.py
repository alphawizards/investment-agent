#!/usr/bin/env python
"""
Simple runner for data fetch - avoids Unicode issues on Windows.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_gatherer.__main__ import fetch_all_historical
from datetime import datetime, timedelta

# Start from 5 years ago (enough for backtesting)
start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')

print(f"Starting fetch from {start_date}...")
print("This will take several hours. Progress will be saved to database.")
print()

result = fetch_all_historical(
    exchange='all',
    start_date=start_date,
    max_workers=1,  # Sequential for safety
    verbose=True
)

print()
print("=" * 60)
print("FETCH COMPLETE")
print("=" * 60)
print(f"Processed: {result['tickers_processed']}")
print(f"Succeeded:  {result['tickers_succeeded']}")
print(f"Failed:     {result['tickers_failed']}")
print(f"Records:    {result['records_inserted']}")
