"""
Universe Provider
=================
Provides Point-in-Time (PIT) universe definitions for backtesting.

This class queries the IndexConstituent table to determine which stocks
were in a given index at any historical point, eliminating survivorship bias.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import pandas as pd

# Import database components
from backend.database.models import IndexConstituent
from backend.database.connection import SessionLocal


class UniverseProvider:
    """
    Provides Point-in-Time (PIT) universe definitions.
    
    Usage:
        provider = UniverseProvider()
        tickers = provider.get_assets_at_date(datetime(2015, 1, 1), 'SP500')
        # Returns list of S&P 500 constituents as of Jan 1, 2015
    """
    
    def __init__(self):
        """Initialize the UniverseProvider."""
        pass

    def get_assets_at_date(self, date: datetime, index_name: str = 'SP500') -> List[str]:
        """
        Returns list of tickers that were in the index on the specific date.
        Uses the most recent snapshot before or on 'date'.
        
        Args:
            date: The historical date to query
            index_name: Index to query (default: 'SP500', also supports 'ASX200')
            
        Returns:
            List of ticker symbols that were in the index on that date
        """
        db: Session = SessionLocal()
        try:
            # 1. Find the latest snapshot date <= requested date
            latest_snapshot = db.query(func.max(IndexConstituent.start_date))\
                .filter(IndexConstituent.index_name == index_name)\
                .filter(IndexConstituent.start_date <= date)\
                .scalar()
            
            if not latest_snapshot:
                return []

            # 2. Get all tickers from that snapshot
            tickers = db.query(IndexConstituent.ticker)\
                .filter(IndexConstituent.index_name == index_name)\
                .filter(IndexConstituent.start_date == latest_snapshot)\
                .all()
            
            return [t[0] for t in tickers]
            
        finally:
            db.close()
    
    def get_assets_in_range(self, 
                            start_date: datetime, 
                            end_date: datetime, 
                            index_name: str = 'SP500') -> List[str]:
        """
        Returns list of all unique tickers that were in the index 
        at any point during the date range.
        
        Useful for fetching data for all historically relevant tickers.
        
        Args:
            start_date: Start of the date range
            end_date: End of the date range
            index_name: Index to query
            
        Returns:
            List of unique ticker symbols
        """
        db: Session = SessionLocal()
        try:
            tickers = db.query(IndexConstituent.ticker.distinct())\
                .filter(IndexConstituent.index_name == index_name)\
                .filter(IndexConstituent.start_date >= start_date)\
                .filter(IndexConstituent.start_date <= end_date)\
                .all()
            
            return [t[0] for t in tickers]
            
        finally:
            db.close()
    
    def get_all_historical_tickers(self, index_name: str = 'SP500') -> List[str]:
        """
        Returns all unique tickers that have ever been in the index.
        
        Useful for data fetching - ensures we get data for delisted companies
        like Lehman Brothers, Enron, etc.
        
        Args:
            index_name: Index to query
            
        Returns:
            List of all unique ticker symbols ever in the index
        """
        db: Session = SessionLocal()
        try:
            tickers = db.query(IndexConstituent.ticker.distinct())\
                .filter(IndexConstituent.index_name == index_name)\
                .all()
            
            return [t[0] for t in tickers]
            
        finally:
            db.close()
    
    def get_snapshot_dates(self, index_name: str = 'SP500') -> List[datetime]:
        """
        Returns all available snapshot dates for the index.
        
        Args:
            index_name: Index to query
            
        Returns:
            List of datetime objects representing snapshot dates
        """
        db: Session = SessionLocal()
        try:
            dates = db.query(IndexConstituent.start_date.distinct())\
                .filter(IndexConstituent.index_name == index_name)\
                .order_by(IndexConstituent.start_date)\
                .all()
            
            return [d[0] for d in dates]
            
        finally:
            db.close()
