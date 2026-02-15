"""
VectorBT Signal Utilities
=========================
Vectorized signal generation with pandas fallback.

Provides:
- VectorBT-accelerated signal generation
- Automatic fallback to pandas if VectorBT fails
- Feature flag to disable VectorBT
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Check VectorBT availability
try:
    import vectorbt as vbt
    HAS_VECTORBT = True
except ImportError:
    HAS_VECTORBT = False
    logger.warning("VectorBT not available, using pandas fallback")


def generate_momentum_signals_vectorbt(
    prices: pd.DataFrame,
    lookback: int,
    threshold: float = 0.9
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate momentum signals using VectorBT (vectorized).
    
    Args:
        prices: Price DataFrame (columns=tickers, index=dates)
        lookback: Lookback period in days
        threshold: Percentile threshold for top stocks (0.9 = top 10%)
        
    Returns:
        (signals, strength) DataFrames
    """
    import vectorbt as vbt
    
    # Calculate returns using VectorBT
    returns = prices.pct_change(lookback)
    
    # Rank returns cross-sectionally
    ranks = returns.rank(axis=1, pct=True)
    
    # Generate signals (1 = buy, 0 = hold)
    signals = (ranks >= threshold).astype(int)
    
    # Strength is the normalized rank
    strength = ranks.clip(lower=0, upper=1).fillna(0)
    
    return signals, strength


def generate_momentum_signals_pandas(
    prices: pd.DataFrame,
    lookback: int,
    threshold: float = 0.9
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate momentum signals using pure pandas (fallback).
    
    Args:
        prices: Price DataFrame (columns=tickers, index=dates)
        lookback: Lookback period in days
        threshold: Percentile threshold for top stocks
        
    Returns:
        (signals, strength) DataFrames
    """
    # Calculate returns
    returns = prices.pct_change(lookback)
    
    # Rank returns cross-sectionally
    ranks = returns.rank(axis=1, pct=True)
    
    # Generate signals
    signals = (ranks >= threshold).astype(int)
    
    # Strength is the normalized rank
    strength = ranks.clip(lower=0, upper=1).fillna(0)
    
    return signals, strength


def generate_momentum_signals(
    prices: pd.DataFrame,
    lookback: int,
    threshold: float = 0.9
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Router for momentum signal generation with automatic fallback.
    
    Uses VectorBT if available and enabled, otherwise falls back to pandas.
    
    Args:
        prices: Price DataFrame
        lookback: Lookback period in days
        threshold: Percentile threshold
        
    Returns:
        (signals, strength) DataFrames
    """
    if settings.USE_VECTORBT and HAS_VECTORBT:
        try:
            return generate_momentum_signals_vectorbt(prices, lookback, threshold)
        except Exception as e:
            logger.warning(f"VectorBT failed, using pandas fallback: {e}")
    
    return generate_momentum_signals_pandas(prices, lookback, threshold)


def generate_dual_momentum_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    defensive_assets: list = None,
    risk_free_rate: float = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate Dual Momentum signals (Antonacci style).
    
    Args:
        prices: Price DataFrame
        lookback: Lookback period (default 252 = 1 year)
        defensive_assets: List of defensive asset tickers
        risk_free_rate: Risk-free rate threshold
        
    Returns:
        (signals, strength) DataFrames
    """
    defensive_assets = defensive_assets or ['TLT', 'IEF', 'BND']
    risk_free_rate = risk_free_rate or settings.RISK_FREE_RATE
    
    returns = prices.pct_change(lookback)
    rf_threshold = risk_free_rate * (lookback / 252)
    
    signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
    strength = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    
    risky_assets = [c for c in prices.columns if c not in defensive_assets]
    
    for i in range(lookback, len(prices)):
        date = prices.index[i]
        row_returns = returns.iloc[i].dropna()
        
        # Get best risky asset
        risky_returns = row_returns.reindex([r for r in risky_assets if r in row_returns.index])
        if len(risky_returns) == 0:
            continue
        
        best_risky = risky_returns.idxmax()
        best_return = risky_returns[best_risky]
        
        # Absolute momentum check
        if best_return > rf_threshold:
            signals.loc[date, best_risky] = 1
            strength.loc[date, best_risky] = min(1.0, best_return / rf_threshold / 2)
        else:
            # Defensive allocation
            def_returns = row_returns.reindex([d for d in defensive_assets if d in row_returns.index])
            if len(def_returns) > 0:
                best_def = def_returns.idxmax()
                signals.loc[date, best_def] = 1
                strength.loc[date, best_def] = 0.5
    
    return signals, strength


def calculate_moving_averages(
    prices: pd.DataFrame,
    windows: list = None,
    use_ema: bool = False
) -> dict:
    """
    Calculate moving averages, optionally using VectorBT.
    
    Args:
        prices: Price DataFrame
        windows: List of window sizes
        use_ema: Use EMA instead of SMA
        
    Returns:
        Dict with window sizes as keys, MA DataFrames as values
    """
    windows = windows or [10, 20, 50, 200]
    result = {}
    
    if settings.USE_VECTORBT and HAS_VECTORBT:
        try:
            import vectorbt as vbt
            for window in windows:
                ma = vbt.MA.run(prices, window=window, ewm=use_ema)
                result[window] = ma.ma
            return result
        except Exception as e:
            logger.warning(f"VectorBT MA failed: {e}")
    
    # Pandas fallback
    for window in windows:
        if use_ema:
            result[window] = prices.ewm(span=window, adjust=False).mean()
        else:
            result[window] = prices.rolling(window=window).mean()
    
    return result
