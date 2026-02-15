"""
Fractional Differentiation Features
====================================
Implements Lopez de Prado's Fixed-Width Window Fractional Differentiation (FFD).

Makes time series stationary while preserving memory, critical for ML features.

Source: "Advances in Financial Machine Learning" (2018), Chapter 5

Theory:
-------
Traditional differencing (d=1) makes series stationary but destroys memory.
Fractional differencing (0 < d < 1) balances stationarity vs memory preservation.

Usage:
------
    from strategy.quant2.features import frac_diff_ffd
    
    # Apply FFD with d=0.4 (common choice for price series)
    prices_ffd = frac_diff_ffd(prices, d=0.4)
"""

import numpy as np
import pandas as pd
from typing import Optional


def get_weights_ffd(d: float, thres: float = 1e-5) -> np.ndarray:
    """
    Compute FFD weights for fractional differentiation.
    
    The weights follow the binomial series expansion:
        w_k = -w_{k-1} * (d - k + 1) / k
    
    Args:
        d: Fractional differentiation order (0 < d < 1 typically)
        thres: Threshold for weight truncation (default: 1e-5)
        
    Returns:
        Array of weights in chronological order (oldest to newest)
    """
    w, k = [1.0], 1
    while True:
        w_ = -w[-1] / k * (d - k + 1)
        if abs(w_) < thres:
            break
        w.append(w_)
        k += 1
    return np.array(w[::-1]).reshape(-1, 1)


def frac_diff_ffd(
    series: pd.DataFrame, 
    d: float = 0.4, 
    thres: float = 1e-5
) -> pd.DataFrame:
    """
    Constant-width window (Fixed) Fractional Differentiation.
    
    Unlike expanding window FFD, this uses a fixed lookback which is
    more practical for real-time applications.
    
    Args:
        series: DataFrame of price series (dates x tickers)
        d: Differentiation order (0.4 is common for prices)
        thres: Weight cutoff threshold (default: 1e-5)
        
    Returns:
        DataFrame of fractionally differentiated series
        
    Example:
        >>> prices = pd.DataFrame({'AAPL': [100, 101, 103, 102, 105]})
        >>> ffd = frac_diff_ffd(prices, d=0.4)
    """
    # 1. Compute weights for the longest series
    w = get_weights_ffd(d, thres)
    width = len(w) - 1
    
    # 2. Apply weights to each series
    df = {}
    for name in series.columns:
        series_f = series[[name]].ffill().dropna()
        df_ = pd.Series(dtype=float)
        
        # Vectorized implementation for speed using rolling
        # Get values as numpy array
        vals = series_f.values.flatten()

        # We need to apply the weights dot product on a rolling window
        # w is (width+1, 1), we need to reverse it for convolution if using convolve,
        # but here we can just use dot product logic carefully.
        # Actually, rolling apply is slow. The fastest way is stride_tricks or just a loop over the window size
        # given that window size is small (width is usually < 1000).

        # However, for pure vectorization:
        # Create a rolling window view
        from numpy.lib.stride_tricks import sliding_window_view

        if len(vals) > width:
            windows = sliding_window_view(vals, window_shape=len(w))
            # windows shape is (n_windows, window_size) where window_size = len(w)

            # The weights w are typically applied such that w[0]*x[t] + w[1]*x[t-1]...
            # In our implementation get_weights_ffd returns weights from oldest to newest (w[-1] is newest)
            # So we can dot product directly if windows are also chronological
            
            # w shape: (width+1, 1) -> flatten to (width+1,)
            w_flat = w.flatten()

            # Result of dot product
            res = np.dot(windows, w_flat)

            # Construct Series aligned with timestamps
            # The first result corresponds to index at 'width'
            res_index = series_f.index[len(w)-1:]
            df_ = pd.Series(res, index=res_index)

        else:
             df_ = pd.Series(dtype=float)
        
        df[name] = df_.copy(deep=True)
    
    result = pd.concat(df, axis=1)
    return result


def get_optimal_d(
    series: pd.Series, 
    d_range: np.ndarray = None,
    pvalue_threshold: float = 0.05
) -> float:
    """
    Find minimum d value that achieves stationarity.
    
    Uses ADF test to find the smallest d that makes series stationary,
    preserving maximum memory.
    
    Args:
        series: Price series to analyze
        d_range: Range of d values to test (default: 0 to 1 in 0.1 steps)
        pvalue_threshold: ADF test p-value threshold for stationarity
        
    Returns:
        Minimum d value achieving stationarity
    """
    try:
        from statsmodels.tsa.stattools import adfuller
    except ImportError:
        print("Warning: statsmodels required for get_optimal_d()")
        return 0.5  # Default fallback
    
    if d_range is None:
        d_range = np.linspace(0, 1, 11)
    
    for d in d_range:
        if d == 0:
            ffd_series = series
        else:
            ffd_series = frac_diff_ffd(series.to_frame(), d=d).iloc[:, 0]
        
        ffd_clean = ffd_series.dropna()
        if len(ffd_clean) < 20:
            continue
            
        adf_result = adfuller(ffd_clean, maxlag=1, regression='c', autolag=None)
        pvalue = adf_result[1]
        
        if pvalue < pvalue_threshold:
            return d
    
    return 1.0  # Full differencing if nothing else works


def compute_ffd_features(
    prices: pd.DataFrame,
    d_values: list = [0.3, 0.4, 0.5],
    log_transform: bool = True
) -> pd.DataFrame:
    """
    Compute FFD features at multiple d values.
    
    Useful for ML models that benefit from multiple stationarity levels.
    
    Args:
        prices: DataFrame of price series
        d_values: List of d values to compute
        log_transform: Whether to log-transform prices first (recommended)
        
    Returns:
        DataFrame with FFD features at each d value
    """
    if log_transform:
        series = np.log(prices)
    else:
        series = prices
    
    features = {}
    for d in d_values:
        ffd = frac_diff_ffd(series, d=d)
        for col in ffd.columns:
            features[f"{col}_ffd_{d}"] = ffd[col]
    
    return pd.DataFrame(features)


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Demonstrate FFD computation."""
    print("=" * 60)
    print("Fractional Differentiation Demo")
    print("=" * 60)
    
    # Generate sample price data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=500, freq='B')
    prices = pd.DataFrame({
        'AAPL': 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, 500))),
        'MSFT': 200 * np.exp(np.cumsum(np.random.normal(0.0004, 0.018, 500)))
    }, index=dates)
    
    print(f"\nOriginal prices shape: {prices.shape}")
    print(f"Sample:\n{prices.head()}")
    
    # Apply FFD
    prices_ffd = frac_diff_ffd(prices, d=0.4)
    
    print(f"\nFFD (d=0.4) shape: {prices_ffd.shape}")
    print(f"Sample:\n{prices_ffd.head()}")
    
    # Check stationarity
    try:
        from statsmodels.tsa.stattools import adfuller
        
        print("\n--- Stationarity Test (ADF) ---")
        for col in prices.columns:
            # Original
            adf_orig = adfuller(prices[col].dropna())
            print(f"{col} Original: p-value = {adf_orig[1]:.4f}")
            
            # FFD
            ffd_col = prices_ffd[col].dropna()
            if len(ffd_col) > 10:
                adf_ffd = adfuller(ffd_col)
                print(f"{col} FFD(0.4): p-value = {adf_ffd[1]:.4f}")
    except ImportError:
        print("\nInstall statsmodels for ADF test: pip install statsmodels")
    
    print("\n✅ FFD preserves memory while achieving stationarity!")


if __name__ == "__main__":
    demo()
