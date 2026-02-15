"""
Feature Engineering for Meta-Labeling
======================================
Extract features at each Quallamaggie signal for ML-based filtering.

Features extracted:
1. Volatility (VIX, ATR)
2. Volume trends (RVOL, Volume Volatility)
3. Sector momentum
4. Price distance from moving averages
5. Bid-ask proxy (intraday range)
6. Fractional Differentiation (FFD)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings
from strategy.quant2.features import frac_diff_ffd

warnings.filterwarnings('ignore')


@dataclass
class FeatureSet:
    """Feature set for meta-labeling."""
    features: pd.DataFrame
    feature_names: List[str]
    metadata: dict


class FeatureEngineer:
    """
    Feature extraction for meta-labeling.
    
    Extracts context features at each trade signal to help
    the meta-model predict probability of success.
    
    Feature categories:
    - Volatility: Market and stock-level volatility
    - Volume: Relative volume and trends
    - Momentum: Multi-timeframe momentum indicators
    - Technical: Distance from MAs, ATR
    - Stationarity: FFD features
    
    Attributes:
        vix_ticker: Ticker for VIX data (default: ^VIX)
        lookback_atr: ATR period
        lookback_momentum: Momentum calculation period
    """
    
    def __init__(
        self,
        vix_ticker: str = '^VIX',
        lookback_atr: int = 14,
        lookback_momentum: int = 21,
        lookback_volume: int = 20
    ):
        """
        Initialize Feature Engineer.
        
        Args:
            vix_ticker: Ticker for VIX data
            lookback_atr: Period for ATR calculation
            lookback_momentum: Period for momentum features
            lookback_volume: Period for volume features
        """
        self.vix_ticker = vix_ticker
        self.lookback_atr = lookback_atr
        self.lookback_momentum = lookback_momentum
        self.lookback_volume = lookback_volume
    
    def calculate_atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> pd.Series:
        """
        Calculate Average True Range.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            
        Returns:
            ATR series
        """
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.lookback_atr).mean()
        
        return atr
    
    def calculate_rvol(
        self,
        volume: pd.Series
    ) -> pd.Series:
        """
        Calculate Relative Volume.
        
        RVOL = Today's Volume / Average Volume
        
        Args:
            volume: Volume series
            
        Returns:
            RVOL series
        """
        avg_volume = volume.rolling(self.lookback_volume).mean()
        rvol = volume / avg_volume
        return rvol.fillna(1.0)
    
    def calculate_momentum(
        self,
        close: pd.Series,
        periods: List[int] = None
    ) -> pd.DataFrame:
        """
        Calculate multi-timeframe momentum.
        
        Args:
            close: Close prices
            periods: List of momentum periods
            
        Returns:
            DataFrame with momentum features
        """
        if periods is None:
            periods = [5, 10, 21, 63]
        
        momentum = pd.DataFrame(index=close.index)
        
        for period in periods:
            momentum[f'mom_{period}d'] = close.pct_change(period)
        
        return momentum
    
    def calculate_ma_distances(
        self,
        close: pd.Series,
        periods: List[int] = None
    ) -> pd.DataFrame:
        """
        Calculate distance from moving averages.
        
        Args:
            close: Close prices
            periods: MA periods
            
        Returns:
            DataFrame with MA distance features
        """
        if periods is None:
            periods = [10, 21, 50, 200]
        
        distances = pd.DataFrame(index=close.index)
        
        for period in periods:
            ma = close.rolling(period).mean()
            distances[f'dist_ma{period}'] = (close - ma) / ma
        
        return distances
    
    def extract_features(
        self,
        ohlcv: pd.DataFrame,
        vix: Optional[pd.Series] = None,
        sector_returns: Optional[pd.DataFrame] = None
    ) -> FeatureSet:
        """
        Extract all features for meta-labeling.
        
        Args:
            ohlcv: DataFrame with Open, High, Low, Close, Volume columns
            vix: Optional VIX series
            sector_returns: Optional sector ETF returns for sector momentum
            
        Returns:
            FeatureSet with all extracted features
        """
        features = pd.DataFrame(index=ohlcv.index)
        
        # Ensure column names are consistent
        close = ohlcv['Close'] if 'Close' in ohlcv.columns else ohlcv['close']
        high = ohlcv['High'] if 'High' in ohlcv.columns else ohlcv.get('high', close)
        low = ohlcv['Low'] if 'Low' in ohlcv.columns else ohlcv.get('low', close)
        volume = ohlcv['Volume'] if 'Volume' in ohlcv.columns else ohlcv.get('volume')
        
        # 1. Volatility features
        atr = self.calculate_atr(high, low, close)
        features['atr'] = atr
        features['atr_pct'] = atr / close
        
        # Historical volatility
        returns = close.pct_change()
        features['volatility_10d'] = returns.rolling(10).std() * np.sqrt(252)
        features['volatility_21d'] = returns.rolling(21).std() * np.sqrt(252)
        
        # VIX if provided
        if vix is not None:
            aligned_vix = vix.reindex(ohlcv.index).ffill()
            features['vix'] = aligned_vix
            features['vix_sma20'] = aligned_vix.rolling(20).mean()
            # Optimized VIX Percentile using vectorized ranking
            # Use min_periods=1 to get values earlier
            features['vix_percentile'] = aligned_vix.rolling(252, min_periods=1).rank(pct=True)
            features['vix_percentile'] = features['vix_percentile'].fillna(0.5)
        
        # 2. Volume features
        if volume is not None:
            features['rvol'] = self.calculate_rvol(volume)
            features['volume_trend'] = volume.rolling(5).mean() / volume.rolling(20).mean()

            # Volume Volatility (Coefficient of Variation)
            vol_mean = volume.rolling(20).mean()
            vol_std = volume.rolling(20).std()
            features['volume_cv'] = vol_std / vol_mean
        
        # 3. Momentum features
        momentum_df = self.calculate_momentum(close)
        features = pd.concat([features, momentum_df], axis=1)
        
        # 4. MA distance features
        ma_dist_df = self.calculate_ma_distances(close)
        features = pd.concat([features, ma_dist_df], axis=1)
        
        # 5. Intraday range (bid-ask proxy)
        features['intraday_range'] = (high - low) / close
        
        # 6. High-to-close ratio (strength indicator)
        features['high_close_ratio'] = (high - close) / (high - low + 1e-10)
        
        # 7. Gap (overnight move)
        prev_close = close.shift(1)
        open_price = ohlcv['Open'] if 'Open' in ohlcv.columns else ohlcv.get('open', close)
        features['gap'] = (open_price - prev_close) / prev_close
        
        # 8. Sector momentum (if provided)
        if sector_returns is not None:
            for col in sector_returns.columns:
                aligned = sector_returns[col].reindex(ohlcv.index).ffill()
                features[f'sector_{col}_mom'] = aligned.rolling(21).sum()

        # 9. Fractional Differentiation (FFD)
        # Apply to Close prices
        # Log-transform first to stabilize variance
        log_close = np.log(close)
        ffd_close = frac_diff_ffd(log_close.to_frame(), d=0.4).iloc[:, 0]
        features['ffd_close'] = ffd_close

        if volume is not None:
            # Apply to Volume (log transformed)
            # Adding 1 to avoid log(0)
            log_volume = np.log(volume + 1)
            ffd_volume = frac_diff_ffd(log_volume.to_frame(), d=0.4).iloc[:, 0]
            features['ffd_volume'] = ffd_volume
        
        # Drop rows with NaN
        features = features.dropna()
        
        metadata = {
            'n_features': len(features.columns),
            'n_samples': len(features),
            'date_range': f"{features.index[0]} to {features.index[-1]}" if len(features) > 0 else "N/A",
        }
        
        return FeatureSet(
            features=features,
            feature_names=features.columns.tolist(),
            metadata=metadata
        )
    
    def extract_at_signals(
        self,
        ohlcv: pd.DataFrame,
        signal_dates: List[pd.Timestamp],
        vix: Optional[pd.Series] = None
    ) -> FeatureSet:
        """
        Extract features only at signal dates.
        
        Args:
            ohlcv: OHLCV data
            signal_dates: List of dates when signals occurred
            vix: Optional VIX series
            
        Returns:
            FeatureSet at signal dates only
        """
        # Extract all features
        full_features = self.extract_features(ohlcv, vix)
        
        # Filter to signal dates
        valid_dates = [d for d in signal_dates if d in full_features.features.index]

        # Handle empty features (e.g., if FFD failed or dropped all data)
        if full_features.features.empty:
             return FeatureSet(
                features=pd.DataFrame(columns=full_features.feature_names),
                feature_names=full_features.feature_names,
                metadata={'n_signals': 0, 'n_features': len(full_features.feature_names)}
            )

        signal_features = full_features.features.loc[valid_dates]
        
        return FeatureSet(
            features=signal_features,
            feature_names=full_features.feature_names,
            metadata={
                'n_signals': len(valid_dates),
                'n_features': len(full_features.feature_names),
            }
        )


def demo():
    """Demonstrate feature engineering."""
    print("=" * 60)
    print("Feature Engineering Demo")
    print("=" * 60)
    
    # Create sample OHLCV data
    np.random.seed(42)
    n = 252
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    volume = np.random.randint(1_000_000, 10_000_000, n)
    
    ohlcv = pd.DataFrame({
        'Open': close + np.random.randn(n) * 0.1,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume,
    }, index=dates)
    
    # Create sample VIX
    vix = pd.Series(15 + np.random.randn(n) * 3, index=dates)
    
    print(f"Sample data: {n} days")
    
    # Extract features
    engineer = FeatureEngineer()
    feature_set = engineer.extract_features(ohlcv, vix)
    
    print(f"\nExtracted {feature_set.metadata['n_features']} features:")
    print(f"  Samples: {feature_set.metadata['n_samples']}")
    
    print("\nFeature names:")
    for name in feature_set.feature_names[:10]:
        print(f"  - {name}")
    if len(feature_set.feature_names) > 10:
        print(f"  ... and {len(feature_set.feature_names) - 10} more")
    
    print("\nSample features (last row):")
    print(feature_set.features.iloc[-1])


if __name__ == "__main__":
    demo()
