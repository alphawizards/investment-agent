"""
Fast Data Loader
================

High-performance data loader with caching and parallel processing.
"""

import pandas as pd
import yfinance as yf
from tiingo import TiingoClient
from typing import List, Optional, Dict, Union, Any
from datetime import datetime
import os
from pathlib import Path
from strategy.config import CONFIG

class RetryConfig:
    """Retry configuration for API calls."""
    def __init__(self, max_retries: int = 3, delay: int = 1):
        self.max_retries = max_retries
        self.delay = delay

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

    def fetch_prices_fast(self, tickers: List[str], use_cache: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Fetch adjusted close and open prices for multiple tickers.
        Uses caching to avoid re-fetching data.

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

        # 2. Identify missing tickers
        if not cached_close.empty and not cached_open.empty:
            # Check which tickers are already in cache
            available_tickers = [t for t in tickers if t in cached_close.columns and t in cached_open.columns]
            missing_tickers = [t for t in tickers if t not in available_tickers]
        else:
            available_tickers = []
            missing_tickers = tickers

        if not missing_tickers:
            if self.verbose:
                print("✅ All tickers found in cache")
            return {
                'close': cached_close[tickers],
                'open': cached_open[tickers]
            }

        if self.verbose:
            print(f"Incremental fetch: Downloading {len(missing_tickers)} missing tickers...")

        # 3. Fetch ONLY missing tickers
        new_close = pd.DataFrame()
        new_open = pd.DataFrame()

        # Try Tiingo first (Primary)
        if self.client:
            try:
                if self.verbose:
                    print(f"Fetching from Tiingo...")

                # Fetch both adjClose and adjOpen
                # We need to fetch full dataframe to get both
                tiingo_df = self.client.get_dataframe(
                    missing_tickers,
                    metric_name=['adjClose', 'adjOpen'], # Request both metrics
                    startDate=self.start_date,
                    endDate=self.end_date,
                    frequency='daily'
                )

                if not tiingo_df.empty:
                    # Tiingo with multiple metrics usually returns MultiIndex columns: (Symbol, Metric) or (Metric, Symbol)
                    # Let's inspect structure. Based on docs, if multiple tickers provided, it returns MultiIndex.
                    # If flat, we need to restructure.

                    if hasattr(tiingo_df.index, 'tz') and tiingo_df.index.tz is not None:
                         tiingo_df.index = tiingo_df.index.tz_localize(None)

                    # Handle MultiIndex
                    if isinstance(tiingo_df.columns, pd.MultiIndex):
                        # Assume level 0 is Symbol, level 1 is Metric (or vice versa)
                        # We need to standardize.
                        # Usually Tiingo returns (Symbol, Metric)

                        # Try to extract 'adjClose' and 'adjOpen'
                        try:
                            # Try xs assuming level 'metric' exists or is named
                            # Often it's un-named levels.
                            # Let's look at level values
                            levels = tiingo_df.columns.levels
                            if 'adjClose' in levels[0] or 'adjClose' in levels[1]:
                                # Found metrics
                                if 'adjClose' in levels[1]: # (Symbol, Metric)
                                    new_close = tiingo_df.xs('adjClose', axis=1, level=1)
                                    new_open = tiingo_df.xs('adjOpen', axis=1, level=1)
                                else: # (Metric, Symbol)
                                    new_close = tiingo_df.xs('adjClose', axis=1, level=0)
                                    new_open = tiingo_df.xs('adjOpen', axis=1, level=0)
                        except Exception as inner_e:
                            print(f"Tiingo multiindex parse error: {inner_e}")
                    else:
                        # If single ticker or flattened
                        # If single ticker, cols are ['adjClose', 'adjOpen', ...]
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

            yf_data = yf.download(
                still_missing,
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
        if not new_close.empty:
            if not cached_close.empty:
                # Merge Close
                common_index = cached_close.index.union(new_close.index).sort_values()
                cached_close = cached_close.reindex(common_index)
                new_close = new_close.reindex(common_index)
                final_close = pd.concat([cached_close, new_close], axis=1)
                final_close = final_close.loc[:, ~final_close.columns.duplicated()]

                # Merge Open
                cached_open = cached_open.reindex(common_index)
                new_open = new_open.reindex(common_index)
                final_open = pd.concat([cached_open, new_open], axis=1)
                final_open = final_open.loc[:, ~final_open.columns.duplicated()]
            else:
                final_close = new_close
                final_open = new_open

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
