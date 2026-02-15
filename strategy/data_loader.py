"""
Data Loader Module
==================

Unified data loader using FastDataLoader backend.
Supports fetching Open and Close prices for robust backtesting.
"""

import pandas as pd
from typing import List, Tuple, Optional, Union
from strategy.fast_data_loader import FastDataLoader

class DataLoader:
    """
    Unified Data Loader wrapper around FastDataLoader.
    Provides standard interface for loading price data.
    """

    def __init__(self, start_date: str = "2005-01-01", end_date: str = None):
        self.loader = FastDataLoader(start_date=start_date, end_date=end_date)

    def load_selective_dataset(self, tickers: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load prices for selected tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Tuple of (close_prices, returns)

        Note:
            For open-to-open returns or raw open prices, use `load_ohlc_dataset`.
        """
        data = self.loader.fetch_prices_fast(tickers)
        close_prices = data.get('close', pd.DataFrame())

        # Calculate returns from Close prices (standard behavior)
        returns = close_prices.pct_change()

        return close_prices, returns

    def load_ohlc_dataset(self, tickers: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load Open and Close prices.

        Args:
            tickers: List of ticker symbols

        Returns:
            Tuple of (close_prices, open_prices)
        """
        data = self.loader.fetch_prices_fast(tickers)
        return data.get('close', pd.DataFrame()), data.get('open', pd.DataFrame())

def get_nasdaq_100_tickers() -> List[str]:
    """Mock function to return Nasdaq 100 tickers."""
    # In a real scenario, this would fetch from an API or file
    return ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "PEP", "AVGO", "CSCO"] # Partial list

def get_us_tickers() -> List[str]:
    """Mock function to return US tickers (ETFs)."""
    return ["SPY", "QQQ", "IWM", "EEM", "TLT", "LQD", "GLD", "SLV", "USO"]

def get_asx_tickers() -> List[str]:
    """Mock function to return ASX tickers."""
    return ["VAS.AX", "VGS.AX", "STW.AX"]
