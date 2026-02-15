"""
Fama-French Factor Data Loader
==============================
Fetches Fama-French 3-Factor data from Ken French Data Library.

The Fama-French 3 factors are:
- MKT-RF: Market excess return (Rm - Rf)
- SMB: Small Minus Big (size factor)
- HML: High Minus Low (value factor)

Data source: Ken French Data Library (free)
URL: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

Usage:
    loader = FamaFrenchLoader()
    factors = loader.get_factors()  # Returns DataFrame with MKT-RF, SMB, HML, RF
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# Try pandas-datareader for Ken French data
try:
    import pandas_datareader.data as web
    HAS_DATAREADER = True
except ImportError:
    HAS_DATAREADER = False
    print("Warning: pandas-datareader not installed. Install with: pip install pandas-datareader")


class FamaFrenchLoader:
    """
    Load Fama-French factor data for residual momentum calculations.
    
    This loader fetches the Fama-French 3-Factor model data which is used
    to regress out systematic risk factors from stock returns, isolating
    the idiosyncratic (residual) component.
    
    Attributes:
        cache_dir: Directory for caching factor data
        cache_expiry_days: Days before cache expires
    """
    
    # Ken French data library dataset names
    FF3_DAILY = "F-F_Research_Data_Factors_daily"
    FF3_MONTHLY = "F-F_Research_Data_Factors"
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_expiry_days: int = 7
    ):
        """
        Initialize Fama-French loader.
        
        Args:
            cache_dir: Directory to cache factor data (default: data/ff_factors/)
            cache_expiry_days: Number of days before refreshing cache
        """
        if cache_dir is None:
            # Default cache location
            self.cache_dir = Path(__file__).parent.parent.parent.parent / "data" / "ff_factors"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_expiry_days = cache_expiry_days
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Column name mapping
        self.factor_columns = ['Mkt-RF', 'SMB', 'HML', 'RF']
    
    def _cache_path(self, dataset: str) -> Path:
        """Get cache file path for a dataset."""
        return self.cache_dir / f"{dataset.replace('-', '_')}.parquet"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired."""
        if not cache_path.exists():
            return False
        
        # Check file modification time
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry = datetime.now() - timedelta(days=self.cache_expiry_days)
        
        return mtime > expiry
    
    def _fetch_from_source(self, dataset: str) -> pd.DataFrame:
        """
        Fetch factor data from Ken French Data Library.
        
        Args:
            dataset: Name of the dataset to fetch
            
        Returns:
            DataFrame with factor returns (in decimal form, not percentage)
        """
        if not HAS_DATAREADER:
            raise ImportError(
                "pandas-datareader is required for fetching Fama-French data. "
                "Install with: pip install pandas-datareader"
            )
        
        print(f"Fetching {dataset} from Ken French Data Library...")
        
        try:
            # Fetch from Ken French library
            data = web.DataReader(dataset, 'famafrench')
            
            # The returned data is a dict-like object with multiple tables
            # Index 0 typically contains the main factor returns
            factors = data[0]
            
            # Convert from percentage to decimal (FF data is in %)
            factors = factors / 100.0
            
            # Ensure datetime index
            factors.index = pd.to_datetime(factors.index.astype(str))
            
            # Standardize column names
            factors.columns = [col.strip() for col in factors.columns]
            
            print(f"Successfully fetched {len(factors)} observations")
            return factors
            
        except Exception as e:
            print(f"Error fetching Fama-French data: {e}")
            raise
    
    def _load_from_cache(self, cache_path: Path) -> pd.DataFrame:
        """Load factor data from cache."""
        return pd.read_parquet(cache_path)
    
    def _save_to_cache(self, factors: pd.DataFrame, cache_path: Path) -> None:
        """Save factor data to cache."""
        factors.to_parquet(cache_path)
        print(f"Cached factor data to {cache_path}")
    
    def get_factors(
        self,
        frequency: str = 'monthly',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Get Fama-French 3-Factor data.
        
        Args:
            frequency: 'daily' or 'monthly' (default: 'monthly')
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            DataFrame with columns: Mkt-RF, SMB, HML, RF
            - Mkt-RF: Market excess return
            - SMB: Small Minus Big (size factor)
            - HML: High Minus Low (value factor)
            - RF: Risk-free rate
            
        Note:
            Returns are in decimal form (0.01 = 1%)
        """
        # Select dataset based on frequency
        if frequency.lower() == 'daily':
            dataset = self.FF3_DAILY
        else:
            dataset = self.FF3_MONTHLY
        
        cache_path = self._cache_path(dataset)
        
        # Check cache
        if not force_refresh and self._is_cache_valid(cache_path):
            print(f"Loading {frequency} factors from cache...")
            factors = self._load_from_cache(cache_path)
        else:
            # Fetch from source
            factors = self._fetch_from_source(dataset)
            self._save_to_cache(factors, cache_path)
        
        # Apply date filters
        if start_date:
            factors = factors[factors.index >= pd.to_datetime(start_date)]
        if end_date:
            factors = factors[factors.index <= pd.to_datetime(end_date)]
        
        return factors
    
    def get_monthly_factors(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Convenience method for monthly factor data.
        
        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            Monthly Fama-French 3-Factor data
        """
        return self.get_factors('monthly', start_date, end_date)
    
    def get_daily_factors(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Convenience method for daily factor data.
        
        Note: Daily data is less commonly used for residual momentum
        since the standard approach uses monthly data.
        
        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            Daily Fama-French 3-Factor data
        """
        return self.get_factors('daily', start_date, end_date)
    
    def interpolate_to_daily(
        self,
        monthly_factors: pd.DataFrame,
        daily_dates: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """
        Interpolate monthly factors to daily frequency.
        
        This is useful when you need daily factor exposures but only have
        monthly factor data. Uses forward-fill to assign monthly values
        to all days within that month.
        
        Args:
            monthly_factors: Monthly factor DataFrame
            daily_dates: DatetimeIndex of daily dates to interpolate to
            
        Returns:
            Daily factor DataFrame (forward-filled from monthly)
        """
        # Ensure monthly index is datetime
        monthly_factors.index = pd.to_datetime(monthly_factors.index)
        
        # Create daily DataFrame with NaN
        daily_factors = pd.DataFrame(
            index=daily_dates,
            columns=monthly_factors.columns
        )
        
        # Forward fill monthly values to daily
        # First, resample monthly to daily
        monthly_factors_daily = monthly_factors.resample('D').ffill()
        
        # Align with requested daily_dates
        daily_factors = monthly_factors_daily.reindex(daily_dates).ffill()
        
        return daily_factors
    
    def get_factor_premium_stats(
        self,
        frequency: str = 'monthly'
    ) -> pd.DataFrame:
        """
        Get summary statistics for factor premiums.
        
        Useful for understanding the historical risk premiums.
        
        Args:
            frequency: 'daily' or 'monthly'
            
        Returns:
            DataFrame with factor statistics (mean, std, Sharpe, etc.)
        """
        factors = self.get_factors(frequency)
        
        # Annualization factor
        if frequency == 'daily':
            ann_factor = 252
        else:
            ann_factor = 12
        
        stats = pd.DataFrame({
            'Mean (Ann.)': factors.mean() * ann_factor,
            'Std (Ann.)': factors.std() * np.sqrt(ann_factor),
            'Sharpe': (factors.mean() * ann_factor) / (factors.std() * np.sqrt(ann_factor)),
            'Min': factors.min(),
            'Max': factors.max(),
            'Skew': factors.skew(),
            'Kurtosis': factors.kurtosis(),
        })
        
        return stats


def demo():
    """Demonstrate Fama-French data loading."""
    print("=" * 60)
    print("Fama-French Factor Loader Demo")
    print("=" * 60)
    
    loader = FamaFrenchLoader()
    
    # Get monthly factors
    print("\nFetching monthly factors...")
    factors = loader.get_monthly_factors(start_date='2020-01-01')
    
    print(f"\nFactor data shape: {factors.shape}")
    print(f"Date range: {factors.index[0]} to {factors.index[-1]}")
    print("\nRecent factor returns:")
    print(factors.tail())
    
    print("\nFactor premium statistics:")
    stats = loader.get_factor_premium_stats('monthly')
    print(stats)


if __name__ == "__main__":
    demo()
