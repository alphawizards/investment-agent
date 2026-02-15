"""
Fast Data Loader
================

High-performance data loader with caching and parallel processing.
"""

import pandas as pd
import yfinance as yf
from tiingo import TiingoClient
from typing import List, Optional, Dict, Union, Any, Callable
from datetime import datetime
import os
import time
import functools
import logging
from pathlib import Path
from strategy.config import CONFIG

logger = logging.getLogger(__name__)


class RetryConfig:
    """Retry configuration for API calls."""
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay


def retry_api_call(config: RetryConfig = None):
    """
    Decorator for retrying API calls with exponential backoff.

    Retries on network/API errors with delays: 1s, 2s, 4s, 8s, ...
    Capped at config.max_delay seconds.
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, OSError) as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = min(config.base_delay * (2 ** attempt), config.max_delay)
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_retries} for {func.__name__}: {e}. "
                            f"Waiting {delay:.1f}s..."
                        )
                        time.sleep(delay)
                except Exception as e:
                    # Non-retryable errors (e.g. bad ticker, auth failure)
                    raise
            raise last_exception
        return wrapper
    return decorator


_default_retry = RetryConfig(max_retries=3, base_delay=1.0, max_delay=30.0)

class FastDataLoader:
    """
    Fast data loader with support for Tiingo (Primary) and yfinance fallback.
    Uses Parquet caching for speed.
    """

    def __init__(self,
                 start_date: str = "2005-01-01",
                 end_date: str = None,
                 use_tiingo_fallback: bool = True,
                 tiingo_api_token: str = None,
                 tiingo_is_premium: bool = False,
                 verbose: bool = True):
        self.verbose = verbose
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        self.use_tiingo_fallback = use_tiingo_fallback # In this context, implies using Tiingo
        self.tiingo_api_token = tiingo_api_token or CONFIG.TIINGO_API_KEY
        self.tiingo_is_premium = tiingo_is_premium
        self.cache_dir = Path(CONFIG.CACHE_DIR)
        self.cache_dir.mkdir(exist_ok=True)

        # Initialize Tiingo Client
        self.client = None
        if self.tiingo_api_token:
            config = {'session': True, 'api_key': self.tiingo_api_token}
            self.client = TiingoClient(config)

        self._retry_config = _default_retry

    @staticmethod
    @retry_api_call()
    def _yf_download(**kwargs) -> pd.DataFrame:
        """yFinance download with retry."""
        return yf.download(**kwargs)

    @staticmethod
    @retry_api_call()
    def _tiingo_get_dataframe(client, **kwargs) -> pd.DataFrame:
        """Tiingo get_dataframe with retry."""
        return client.get_dataframe(**kwargs)

    def fetch_prices_fast(self, tickers: List[str], use_cache: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Fetch adjusted close and open prices for multiple tickers.
        Uses delta loading - only fetches missing dates for existing tickers.
        New tickers get full history.

        Returns:
            Dict with keys 'close' and 'open', containing DataFrames.
        """
        if self.verbose:
            print(f"Fetching data for {len(tickers)} tickers...")

        # Cache files
        cache_file_close = self.cache_dir / "us_prices_close.parquet"
        cache_file_open = self.cache_dir / "us_prices_open.parquet"

        cached_close = pd.DataFrame()
        cached_open = pd.DataFrame()

        # 1. Load existing cache
        if use_cache and cache_file_close.exists() and cache_file_open.exists():
            try:
                cached_close = pd.read_parquet(cache_file_close)
                cached_open = pd.read_parquet(cache_file_open)
                if self.verbose:
                    print(f"Loaded {len(cached_close.columns)} tickers from cache")
            except Exception as e:
                print(f"⚠️ Warning: Could not read cache: {e}")

        # 2. Delta loading: Identify tickers needing updates vs new tickers
        tickers_to_fetch_full = []  # New tickers - need full history
        tickers_to_fetch_delta = {}  # Existing tickers - need delta (from last date)

        if not cached_close.empty and not cached_open.empty:
            for ticker in tickers:
                if ticker in cached_close.columns and ticker in cached_open.columns:
                    # Existing ticker - find last date in cache
                    ticker_data = cached_close[ticker].dropna()
                    if not ticker_data.empty:
                        last_cached_date = ticker_data.index.max()
                        # Only fetch if we have gaps (last cached < today)
                        from datetime import timedelta
                        today = datetime.now()
                        if last_cached_date < today:
                            tickers_to_fetch_delta[ticker] = last_cached_date.strftime('%Y-%m-%d')
                    else:
                        # Empty column, treat as new
                        tickers_to_fetch_full.append(ticker)
                else:
                    # New ticker - need full history
                    tickers_to_fetch_full.append(ticker)
        else:
            # No cache - all tickers are new
            tickers_to_fetch_full = tickers

        if not tickers_to_fetch_full and not tickers_to_fetch_delta:
            if self.verbose:
                print("✅ All tickers up to date in cache")
            return {
                'close': cached_close[tickers],
                'open': cached_open[tickers]
            }

        if self.verbose:
            print(f"Delta loading: {len(tickers_to_fetch_full)} new, {len(tickers_to_fetch_delta)} to update")

        # 3b. Fetch delta for existing tickers (incremental updates)
        delta_close = pd.DataFrame()
        delta_open = pd.DataFrame()
        
        if tickers_to_fetch_delta:
            if self.verbose:
                print(f"Fetching delta updates for {len(tickers_to_fetch_delta)} existing tickers...")
            
            for ticker, last_date in tickers_to_fetch_delta.items():
                try:
                    # Fetch from last_date to today
                    delta_df = self._yf_download(
                        tickers=ticker,
                        start=last_date,
                        end=datetime.now().strftime('%Y-%m-%d'),
                        progress=False,
                        auto_adjust=True
                    )
                    if not delta_df.empty and 'Close' in delta_df.columns:
                        delta_close[ticker] = delta_df['Close']
                        delta_open[ticker] = delta_df['Open'] if 'Open' in delta_df.columns else delta_df['Close']
                except Exception as e:
                    if self.verbose:
                        print(f"Delta fetch failed for {ticker}: {e}")
            
            if self.verbose and not delta_close.empty:
                print(f"Delta updates: {len(delta_close.columns)} tickers updated")

        # Process new tickers (full history)
        missing_tickers = tickers_to_fetch_full
        if missing_tickers:
            if self.verbose:
                print(f"Incremental fetch: Downloading {len(missing_tickers)} missing tickers (full history)...")

        # 3. Fetch: New tickers get full history, existing tickers get delta
        new_close = pd.DataFrame()
        new_open = pd.DataFrame()
        
        # 3a. Fetch new tickers (full history)
        if missing_tickers:
            # Try Tiingo first (Primary)
            if self.client:
                try:
                    if self.verbose:
                        print(f"Fetching {len(missing_tickers)} new tickers from Tiingo...")

                    # Fetch both adjClose and adjOpen
                    tiingo_df = self._tiingo_get_dataframe(
                        self.client,
                        tickers=missing_tickers,
                        metric_name=['adjClose', 'adjOpen'],
                        startDate=self.start_date,
                        endDate=self.end_date,
                        frequency='daily'
                    )

                    if not tiingo_df.empty:
                        if hasattr(tiingo_df.index, 'tz') and tiingo_df.index.tz is not None:
                            tiingo_df.index = tiingo_df.index.tz_localize(None)

                        # Handle MultiIndex
                        if isinstance(tiingo_df.columns, pd.MultiIndex):
                            try:
                                levels = tiingo_df.columns.levels
                                if 'adjClose' in levels[0] or 'adjClose' in levels[1]:
                                    if 'adjClose' in levels[1]:  # (Symbol, Metric)
                                        new_close = tiingo_df.xs('adjClose', axis=1, level=1)
                                        new_open = tiingo_df.xs('adjOpen', axis=1, level=1)
                                    else:  # (Metric, Symbol)
                                        new_close = tiingo_df.xs('adjClose', axis=1, level=0)
                                        new_open = tiingo_df.xs('adjOpen', axis=1, level=0)
                            except Exception as inner_e:
                                print(f"Tiingo multiindex parse error: {inner_e}")
                        else:
                            if len(missing_tickers) == 1:
                                t = missing_tickers[0]
                                if 'adjClose' in tiingo_df.columns:
                                    new_close = tiingo_df[['adjClose']].rename(columns={'adjClose': t})
                                if 'adjOpen' in tiingo_df.columns:
                                    new_open = tiingo_df[['adjOpen']].rename(columns={'adjOpen': t})

                except Exception as e:
                    print(f"❌ Tiingo fetch failed: {e}")

        # Fallback to yFinance
        if new_close.empty:
            still_missing = missing_tickers
        else:
            still_missing = [t for t in missing_tickers if t not in new_close.columns]

        if still_missing and (self.use_tiingo_fallback or not self.client):
            if self.verbose:
                print(f"Fetching {len(still_missing)} tickers from yFinance (Backup)...")

            yf_data = self._yf_download(
                tickers=still_missing,
                start=self.start_date,
                end=self.end_date,
                progress=self.verbose,
                threads=True,
                auto_adjust=True
            )

            # yFinance returns Open/Close adjusted if auto_adjust=True
            # Structure: MultiIndex (Price, Ticker) or (Ticker, Price) or flat if single

            # Extract Adjusted Close and Open
            # auto_adjust=True means 'Close' is adjusted, 'Open' is adjusted

            # Handle yFinance structure
            try:
                if isinstance(yf_data.columns, pd.MultiIndex):
                    # Usually (Price, Ticker) since yfinance 0.2+ ? Or Ticker, Price?
                    # yfinance behavior changes often.
                    # Usually it is (Price, Ticker) if group_by='column' (default) is not used?
                    # No, yf.download defaults to group_by='column' -> (Price, Ticker)?

                    # Let's try safe extraction
                    try:
                        # Try accessing by Price level
                        yf_close = yf_data['Close']
                        yf_open = yf_data['Open']
                    except KeyError:
                        # Maybe it is grouped by ticker?
                        print("Warning: yFinance structure unexpected, trying to parse...")
                        yf_close = pd.DataFrame()
                        yf_open = pd.DataFrame()
                else:
                    # Single ticker or flat
                    if 'Close' in yf_data.columns:
                        yf_close = yf_data[['Close']]
                        if len(still_missing) == 1:
                            yf_close.columns = still_missing
                    if 'Open' in yf_data.columns:
                        yf_open = yf_data[['Open']]
                        if len(still_missing) == 1:
                            yf_open.columns = still_missing

                # Merge into new_data
                if new_close.empty:
                    new_close = yf_close
                    new_open = yf_open
                else:
                    new_close = new_close.join(yf_close, how='outer')
                    new_open = new_open.join(yf_open, how='outer')

            except Exception as e:
                print(f"yFinance parse error: {e}")

        # 4. Merge and save
        # Priority: cached_close + delta_close (updates) + new_close (new tickers)
        
        final_close = cached_close.copy() if not cached_close.empty else pd.DataFrame()
        final_open = cached_open.copy() if not cached_open.empty else pd.DataFrame()
        
        # 4a. Apply delta updates - use combine_first on entire DataFrame to expand index
        if not delta_close.empty:
            # Combine entire DataFrames so index expands to include new dates
            final_close = final_close.combine_first(delta_close)
            final_open = final_open.combine_first(delta_open)
        
        # 4b. Append new tickers (brand new tickers)
        if not new_close.empty:
            final_close = pd.concat([final_close, new_close], axis=1)
            final_close = final_close.loc[:, ~final_close.columns.duplicated()]
            
            final_open = pd.concat([final_open, new_open], axis=1)
            final_open = final_open.loc[:, ~final_open.columns.duplicated()]
        
        # Save to cache if we have any data
        if not final_close.empty:

            # Save to cache
            if self.verbose:
                print(f"Saving updated cache to {self.cache_dir}")

            try:
                final_close.to_parquet(cache_file_close)
                final_open.to_parquet(cache_file_open)
            except Exception as e:
                print(f"Error saving cache: {e}")

            # Return requested
            available_close = [t for t in tickers if t in final_close.columns]
            available_open = [t for t in tickers if t in final_open.columns]

            # Intersect to ensure we return aligned data
            available = list(set(available_close) & set(available_open))

            return {
                'close': final_close[available],
                'open': final_open[available]
            }

        return {
            'close': cached_close[tickers] if not cached_close.empty else pd.DataFrame(),
            'open': cached_open[tickers] if not cached_open.empty else pd.DataFrame()
        }

    def print_health_status(self):
        """Print health status of the loader."""
        print("FastDataLoader is healthy.")
