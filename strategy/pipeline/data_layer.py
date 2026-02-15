"""
Data Layer
==========
Unified data fetching from OpenBB and yfinance with caching.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import warnings

warnings.filterwarnings('ignore')

# Try to import data providers
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("Warning: yfinance not installed")

try:
    from openbb import obb
    HAS_OPENBB = True
except ImportError:
    HAS_OPENBB = False


@dataclass
class DataConfig:
    """Configuration for data layer."""
    
    # Cache settings
    CACHE_DIR: str = ".cache/data"
    CACHE_EXPIRY_HOURS: int = 24
    
    # Data settings
    START_DATE: str = "2020-01-01"
    END_DATE: str = None  # None = today
    
    # Universe
    DEFAULT_UNIVERSE: List[str] = field(default_factory=lambda: [
        # Major ETFs
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI',
        # Sector ETFs
        'XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLI', 'XLB', 'XLC', 'XLRE', 'XLU', 'XLP',
        # Thematic
        'ARKK', 'SOXX', 'SMH', 'XBI', 'TAN',
        # International
        'EFA', 'EEM', 'VEA', 'VWO',
        # Bonds
        'TLT', 'IEF', 'BND', 'HYG', 'LQD',
        # Commodities
        'GLD', 'SLV', 'USO', 'DBC'
    ])
    
    def __post_init__(self):
        if self.END_DATE is None:
            self.END_DATE = datetime.now().strftime("%Y-%m-%d")


class DataManager:
    """
    Unified data manager for the trading pipeline.
    
    Provides:
    - Price data fetching (OHLCV)
    - Fundamental data
    - Currency conversion
    - Caching and persistence
    """
    
    def __init__(self, config: DataConfig = None):
        self.config = config or DataConfig()
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Create cache directory
        cache_path = Path(self.config.CACHE_DIR)
        cache_path.mkdir(parents=True, exist_ok=True)
    
    def fetch_prices(
        self,
        tickers: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch adjusted close prices for tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with columns = tickers, index = dates
        """
        tickers = tickers or self.config.DEFAULT_UNIVERSE
        start_date = start_date or self.config.START_DATE
        end_date = end_date or self.config.END_DATE
        
        cache_key = f"prices_{hash(tuple(sorted(tickers)))}_{start_date}_{end_date}"
        
        # Check cache
        if use_cache and cache_key in self._cache:
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]
        
        print(f"📊 Fetching prices for {len(tickers)} tickers...")
        
        # Try yfinance first
        if HAS_YFINANCE:
            try:
                prices = self._fetch_yfinance(tickers, start_date, end_date)
                if not prices.empty:
                    self._cache[cache_key] = prices
                    self._cache_timestamps[cache_key] = datetime.now()
                    return prices
            except Exception as e:
                print(f"yfinance error: {e}")
        
        # Try OpenBB as fallback
        if HAS_OPENBB:
            try:
                prices = self._fetch_openbb(tickers, start_date, end_date)
                if not prices.empty:
                    self._cache[cache_key] = prices
                    self._cache_timestamps[cache_key] = datetime.now()
                    return prices
            except Exception as e:
                print(f"OpenBB error: {e}")
        
        print("❌ Failed to fetch data from any provider")
        return pd.DataFrame()
    
    def _fetch_yfinance(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Fetch data using yfinance."""
        data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            progress=False,
            threads=False,
            auto_adjust=True
        )
        
        if isinstance(data.columns, pd.MultiIndex):
            prices = data['Close']
        else:
            prices = data[['Close']] if 'Close' in data.columns else data
            if len(tickers) == 1:
                prices.columns = tickers[:1]
        
        # Filter for valid data
        min_data_pct = 0.7
        valid_cols = prices.columns[prices.notna().sum() / len(prices) >= min_data_pct]
        prices = prices[valid_cols].dropna(how='all')
        
        print(f"   ✓ Loaded {len(prices.columns)} tickers from yfinance")
        return prices
    
    def _fetch_openbb(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Fetch data using OpenBB."""
        all_prices = {}
        
        for ticker in tickers:
            try:
                result = obb.equity.price.historical(
                    symbol=ticker,
                    start_date=start_date,
                    end_date=end_date
                )
                if result and len(result.results) > 0:
                    df = result.to_df()
                    if 'close' in df.columns:
                        all_prices[ticker] = df['close']
            except Exception:
                continue
        
        if all_prices:
            prices = pd.DataFrame(all_prices)
            print(f"   ✓ Loaded {len(prices.columns)} tickers from OpenBB")
            return prices
        
        return pd.DataFrame()
    
    def fetch_ohlcv(
        self,
        tickers: List[str] = None,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch full OHLCV data for tickers.
        
        Returns dict with keys: 'open', 'high', 'low', 'close', 'volume'
        """
        tickers = tickers or self.config.DEFAULT_UNIVERSE
        start_date = start_date or self.config.START_DATE
        end_date = end_date or self.config.END_DATE
        
        if not HAS_YFINANCE:
            print("OHLCV requires yfinance")
            return {}
        
        try:
            data = yf.download(
                tickers,
                start=start_date,
                end=end_date,
                progress=False,
                threads=False
            )
            
            if isinstance(data.columns, pd.MultiIndex):
                return {
                    'open': data['Open'],
                    'high': data['High'],
                    'low': data['Low'],
                    'close': data['Close'],
                    'volume': data['Volume']
                }
            else:
                return {
                    'open': data[['Open']],
                    'high': data[['High']],
                    'low': data[['Low']],
                    'close': data[['Close']],
                    'volume': data[['Volume']]
                }
        except Exception as e:
            print(f"Failed to fetch OHLCV: {e}")
            return {}
    
    def get_returns(
        self,
        prices: pd.DataFrame = None,
        period: int = 1
    ) -> pd.DataFrame:
        """Calculate returns from prices."""
        if prices is None:
            prices = self.fetch_prices()
        return prices.pct_change(period).dropna()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        expiry = timedelta(hours=self.config.CACHE_EXPIRY_HOURS)
        return datetime.now() - cache_time < expiry
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamps.clear()
        print("🗑️ Cache cleared")


# Singleton instance
_data_manager: Optional[DataManager] = None

def get_data_manager() -> DataManager:
    """Get or create the global data manager instance."""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager
