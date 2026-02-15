"""
OLMAR Mathematical Kernels
===========================
Pure mathematical functions for OLMAR algorithm.

These functions are stateless and have no dependencies on backtesting infrastructure.
All inputs are NumPy arrays or Pandas DataFrames; outputs are the same.

OLMAR Algorithm:
1. Calculate price relatives: x_t = p_t / p_{t-1}
2. Predict next price relative using moving average: x̃_{t+1} = MA(p_t) / p_t
3. Update portfolio: b_{t+1} = argmax E[log(b · x_{t+1})] subject to simplex
4. Project onto simplex: sum(b) = 1, b >= 0

Reference:
- Li & Hoi, "On-Line Portfolio Selection with Moving Average Reversion"
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple
import warnings
from scipy.stats import norm, skew, kurtosis


def calculate_price_relatives(
    prices: pd.DataFrame,
    handle_zeros: bool = True
) -> pd.DataFrame:
    """
    Calculate price relatives: x_t = p_t / p_{t-1}
    
    Price relatives represent the ratio of today's price to yesterday's price.
    A value > 1 means price went up, < 1 means price went down.
    
    Args:
        prices: DataFrame of asset prices (rows=dates, cols=assets)
        handle_zeros: If True, replace zeros with NaN before calculation
        
    Returns:
        pd.DataFrame: Price relatives (same shape as input, first row is NaN)
    """
    if handle_zeros:
        # Replace zeros with NaN to avoid division by zero
        prices = prices.replace(0, np.nan)
    
    # Calculate price relatives
    price_relatives = prices / prices.shift(1)
    
    # Handle any remaining infinities
    price_relatives = price_relatives.replace([np.inf, -np.inf], np.nan)
    
    return price_relatives


def predict_ma_reversion(
    prices: pd.DataFrame,
    window: int = 5
) -> pd.DataFrame:
    """
    Predict next price relative using moving average reversion.
    
    The prediction assumes prices will revert to their moving average:
    x̃_{t+1} = MA_w(p_t) / p_t
    
    If current price is below MA, we expect price to go up (x̃ > 1).
    If current price is above MA, we expect price to go down (x̃ < 1).
    
    Args:
        prices: DataFrame of asset prices
        window: Moving average window (default: 5 days)
        
    Returns:
        pd.DataFrame: Predicted price relatives
    """
    # Calculate simple moving average
    ma = prices.rolling(window=window, min_periods=1).mean()
    
    # Predict next price relative
    # x̃_{t+1} = MA(p_t) / p_t
    prediction = ma / prices
    
    # Handle edge cases
    prediction = prediction.replace([np.inf, -np.inf], np.nan)
    prediction = prediction.fillna(1.0)  # Neutral prediction if no data
    
    return prediction


def predict_ema_reversion(
    prices: pd.DataFrame,
    span: int = 5
) -> pd.DataFrame:
    """
    Predict next price relative using EXPONENTIAL moving average reversion.
    
    Same as predict_ma_reversion but uses EMA instead of SMA.
    EMA gives more weight to recent prices, making it more responsive.
    
    Args:
        prices: DataFrame of asset prices
        span: EMA span parameter (similar to window, default: 5)
        
    Returns:
        pd.DataFrame: Predicted price relatives
    """
    # Calculate exponential moving average
    ema = prices.ewm(span=span, min_periods=1, adjust=False).mean()
    
    # Predict next price relative
    # x̃_{t+1} = EMA(p_t) / p_t
    prediction = ema / prices
    
    # Handle edge cases
    prediction = prediction.replace([np.inf, -np.inf], np.nan)
    prediction = prediction.fillna(1.0)  # Neutral prediction if no data
    
    return prediction


def project_simplex(weights: np.ndarray) -> np.ndarray:
    """
    Project weights onto the probability simplex.
    
    Ensures: sum(weights) = 1 and all weights >= 0
    
    Uses the algorithm from:
    "Efficient Projections onto the l1-Ball for Learning in High Dimensions"
    by Duchi et al.
    
    Args:
        weights: Array of weights (can be negative or not sum to 1)
        
    Returns:
        np.ndarray: Projected weights on simplex
    """
    n = len(weights)
    
    # Handle NaN/Inf
    weights = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Sort in descending order
    sorted_weights = np.sort(weights)[::-1]
    
    # Find the threshold
    cumsum = np.cumsum(sorted_weights)
    rho = np.where(sorted_weights + (1 - cumsum) / (np.arange(n) + 1) > 0)[0]
    
    if len(rho) == 0:
        # Edge case: return uniform weights
        return np.ones(n) / n
    
    rho_max = rho[-1]
    theta = (cumsum[rho_max] - 1) / (rho_max + 1)
    
    # Project
    projected = np.maximum(weights - theta, 0)
    
    # Ensure exact sum to 1 (handle floating point errors)
    if projected.sum() > 0:
        projected = projected / projected.sum()
    else:
        projected = np.ones(n) / n
    
    return projected


def olmar_update(
    current_weights: np.ndarray,
    prediction: np.ndarray,
    epsilon: float = 10.0
) -> np.ndarray:
    """
    Single OLMAR portfolio update step.
    
    Updates portfolio weights based on predicted price relatives.
    The update is aggressive when prediction differs from current portfolio.
    
    Args:
        current_weights: Current portfolio weights (must be on simplex)
        prediction: Predicted price relatives (x̃_{t+1})
        epsilon: Sensitivity parameter (higher = more aggressive)
        
    Returns:
        np.ndarray: Updated weights (on simplex)
    """
    n = len(current_weights)
    
    # Handle NaN in prediction
    prediction = np.nan_to_num(prediction, nan=1.0)
    
    # Mean of prediction
    pred_mean = np.mean(prediction)
    
    # Deviation from mean
    deviation = prediction - pred_mean
    
    # Current portfolio's expected return
    expected_return = np.dot(current_weights, prediction)
    
    # Calculate lambda (step size)
    denominator = np.dot(deviation, deviation)
    
    if denominator < 1e-10:
        # No update if predictions are all the same
        return current_weights
    
    # Lambda calculation: how much to move toward predicted winners
    numerator = epsilon - expected_return
    lambd = max(0, numerator / denominator)
    
    # Update weights
    new_weights = current_weights + lambd * deviation
    
    # Project onto simplex
    new_weights = project_simplex(new_weights)
    
    return new_weights


def olmar_weights(
    prices: pd.DataFrame,
    window: int = 5,
    epsilon: float = 10.0,
    initial_weights: np.ndarray = None
) -> pd.DataFrame:
    """
    Calculate OLMAR portfolio weights over time.
    
    This is the main function that runs OLMAR over the entire price history.
    
    Args:
        prices: DataFrame of asset prices (rows=dates, cols=assets)
        window: Moving average window for price prediction
        epsilon: Sensitivity parameter (higher = more aggressive rebalancing)
        initial_weights: Starting weights (default: equal weight)
        
    Returns:
        pd.DataFrame: Portfolio weights over time (same index as prices)
    """
    n_assets = len(prices.columns)
    n_periods = len(prices)
    
    # Initialize weights
    if initial_weights is None:
        weights = np.ones(n_assets) / n_assets
    else:
        weights = initial_weights.copy()
    
    # Storage for weight history
    weights_history = np.zeros((n_periods, n_assets))
    weights_history[0] = weights
    
    # Get predictions for each period
    predictions = predict_ma_reversion(prices, window)
    
    # Run OLMAR update at each timestep
    for t in range(1, n_periods):
        # Get prediction for this period
        pred = predictions.iloc[t].values
        
        # Skip if prediction has NaN
        if np.any(np.isnan(pred)):
            weights_history[t] = weights
            continue
        
        # Update weights
        weights = olmar_update(weights, pred, epsilon)
        weights_history[t] = weights
    
    # Convert to DataFrame
    weights_df = pd.DataFrame(
        weights_history,
        index=prices.index,
        columns=prices.columns
    )
    
    return weights_df


def olmar_weights_ema(
    prices: pd.DataFrame,
    span: int = 5,
    epsilon: float = 10.0,
    initial_weights: np.ndarray = None
) -> pd.DataFrame:
    """
    Calculate OLMAR portfolio weights using EMA (Exponential Moving Average).
    
    This is the EMA variant of OLMAR. Uses exponential moving average
    instead of simple moving average for more responsive predictions.
    
    Args:
        prices: DataFrame of asset prices (rows=dates, cols=assets)
        span: EMA span parameter (similar to SMA window)
        epsilon: Sensitivity parameter (higher = more aggressive rebalancing)
        initial_weights: Starting weights (default: equal weight)
        
    Returns:
        pd.DataFrame: Portfolio weights over time (same index as prices)
    """
    n_assets = len(prices.columns)
    n_periods = len(prices)
    
    # Initialize weights
    if initial_weights is None:
        weights = np.ones(n_assets) / n_assets
    else:
        weights = initial_weights.copy()
    
    # Storage for weight history
    weights_history = np.zeros((n_periods, n_assets))
    weights_history[0] = weights
    
    # Get EMA-based predictions for each period
    predictions = predict_ema_reversion(prices, span)
    
    # Run OLMAR update at each timestep
    for t in range(1, n_periods):
        # Get prediction for this period
        pred = predictions.iloc[t].values
        
        # Skip if prediction has NaN
        if np.any(np.isnan(pred)):
            weights_history[t] = weights
            continue
        
        # Update weights
        weights = olmar_update(weights, pred, epsilon)
        weights_history[t] = weights
    
    # Convert to DataFrame
    weights_df = pd.DataFrame(
        weights_history,
        index=prices.index,
        columns=prices.columns
    )
    
    return weights_df


def validate_weights(weights: Union[np.ndarray, pd.Series]) -> Tuple[bool, str]:
    """
    Validate that weights satisfy simplex constraints.
    
    Args:
        weights: Portfolio weights to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if isinstance(weights, pd.Series):
        weights = weights.values
    
    # Check sum to 1
    weight_sum = np.sum(weights)
    if not np.isclose(weight_sum, 1.0, atol=1e-6):
        return False, f"Weights sum to {weight_sum:.6f}, not 1.0"
    
    # Check non-negative
    if np.any(weights < -1e-6):
        min_weight = np.min(weights)
        return False, f"Minimum weight is {min_weight:.6f}, should be >= 0"
    
    # Check for NaN/Inf
    if np.any(np.isnan(weights)) or np.any(np.isinf(weights)):
        return False, "Weights contain NaN or Inf"
    
    return True, "Valid"


def calculate_dsr(returns: pd.Series, total_trials: int = 1) -> float:
    """
    Calculates Deflated Sharpe Ratio (DSR) to validate strategy robustness.
    Required by 2025 Framework to penalize 'p-hacking'.
    
    Args:
        returns: Series of portfolio returns
        total_trials: Number of parameter combinations tested
        
    Returns:
        float: DSR value (0-1 probability that true Sharpe > 0)
    """
    # 1. Standard Metrics
    T = len(returns)
    sr_obs = returns.mean() / returns.std() * np.sqrt(252)
    sk = skew(returns)
    kt = kurtosis(returns)
    
    # 2. Estimate Expected Maximum Sharpe (from noise)
    # Euler-Mascheroni constant
    gamma = 0.57721566
    
    # Expected Max Sharpe from N independent trials
    # simplified approx for N > 1
    if total_trials <= 1:
        sr_expected = 0
    else:
        sr_expected = ((1 - gamma) * norm.ppf(1 - 1/total_trials) + 
                       gamma * norm.ppf(1 - 1/(total_trials * np.e)))
    
    # 3. Deflate the Sharpe Ratio
    numerator = (sr_obs - sr_expected) * np.sqrt(T - 1)
    denominator = np.sqrt(1 - sk * sr_obs + ((kt - 1) / 4) * sr_obs**2)
    
    return norm.cdf(numerator / denominator)
