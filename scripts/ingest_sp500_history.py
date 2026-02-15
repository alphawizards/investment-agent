"""
Ingest S&P 500 Historical Constituents
======================================
Downloads S&P 500 historical membership data from GitHub and populates
the IndexConstituents table for survivorship bias-free backtesting.

Source: fja05680/sp500 repository
"""

import sys
import os
import requests
import pandas as pd
import io
from datetime import datetime
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import SessionLocal, engine, Base
from backend.database.models import IndexConstituent

# Raw CSV from fja05680/sp500 GitHub repo
GITHUB_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes(10-14-2022).csv"


def clean_ticker(ticker_str):
    """Removes suffix from delisted tickers (e.g., 'AAL-199702' -> 'AAL')"""
    if not isinstance(ticker_str, str):
        return None
    return ticker_str.split('-')[0].strip()


def run_ingestion():
    print("🚀 Starting S&P 500 Historical Ingestion...")
    
    # 1. Ensure DB table exists
    Base.metadata.create_all(bind=engine)
    
    # 2. Fetch Data
    print(f"📥 Downloading data from GitHub...")
    try:
        response = requests.get(GITHUB_URL, timeout=30)
        response.raise_for_status()
        s = response.content
        df = pd.read_csv(io.StringIO(s.decode('utf-8')))
    except requests.RequestException as e:
        print(f"❌ Failed to download data: {e}")
        return
    
    print(f"📊 Downloaded {len(df)} date snapshots")
    
    db = SessionLocal()
    try:
        # Clear existing SP500 data to prevent duplicates on re-run
        existing_count = db.query(IndexConstituent).filter(
            IndexConstituent.index_name == 'SP500'
        ).count()
        
        if existing_count > 0:
            print(f"🗑️  Clearing {existing_count} existing SP500 records...")
            db.query(IndexConstituent).filter(
                IndexConstituent.index_name == 'SP500'
            ).delete()
        
        count = 0
        unique_tickers = set()
        
        for _, row in df.iterrows():
            date_str = row['date']
            tickers_raw = row['tickers']
            
            if pd.isna(tickers_raw):
                continue
            
            # Parse date
            try:
                snapshot_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                continue
            
            # Parse tickers from comma-separated string
            ticker_list = tickers_raw.split(',')
            
            for t_raw in ticker_list:
                t_clean = clean_ticker(t_raw)
                if not t_clean:
                    continue
                
                unique_tickers.add(t_clean)
                
                # Store each snapshot as a record
                # The start_date represents the snapshot date
                record = IndexConstituent(
                    ticker=t_clean,
                    index_name='SP500',
                    start_date=snapshot_date,
                    end_date=None,  # Snapshot model - validity checked by nearest date <= T
                    active=True
                )
                db.add(record)
                count += 1
                
                # Commit in batches to avoid memory issues
                if count % 10000 == 0:
                    db.commit()
                    print(f"   Inserted {count} records...")
        
        db.commit()
        print(f"\n✅ Successfully inserted {count:,} historical constituent records.")
        print(f"📈 Unique tickers tracked: {len(unique_tickers)}")
        print(f"📅 Date range: {df['date'].min()} to {df['date'].max()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_ingestion()
