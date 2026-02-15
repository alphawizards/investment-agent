"""
OLMAR Cost Constraints
=======================
Cost-aware weight adjustment layer (the "Portwine filter").

This module ensures OLMAR weights are adjusted for transaction cost reality:
1. Turnover calculation: How much are we trading?
2. Turnover capping: Limit trading to prevent cost drag
3. Cost validation: Warn if costs are unrealistically low

These constraints prevent the "1222% return" illusion that comes from
ignoring transaction costs in OLPS backtests.
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple
import warnings


def calculate_turnover(
    old_weights: Union[np.ndarray, pd.Series],
    new_weights: Union[np.ndarray, pd.Series]
) -> float:
    """
    Calculate total portfolio turnover.
    
    Turnover = sum of absolute weight changes / 2
    (Divided by 2 because buys = sells in a rebalance)
    
    A turnover of 1.0 means we've completely replaced the portfolio.
    A turnover of 0.2 means we've traded 20% of the portfolio.
    
    Args:
        old_weights: Current portfolio weights
        new_weights: Target portfolio weights
        
    Returns:
        float: Turnover (0 to 1 for normal portfolios)
    """
    if isinstance(old_weights, pd.Series):
        old_weights = old_weights.values
    if isinstance(new_weights, pd.Series):
        new_weights = new_weights.values
    
    # Handle NaN
    old_weights = np.nan_to_num(old_weights, nan=0.0)
    new_weights = np.nan_to_num(new_weights, nan=0.0)
    
    # Calculate turnover (one-way)
    turnover = np.sum(np.abs(new_weights - old_weights)) / 2
    
    return float(turnover)


def apply_turnover_cap(
    old_weights: np.ndarray,
    new_weights: np.ndarray,
    max_turnover: float = 0.5
) -> np.ndarray:
    """
    Apply turnover cap by blending old and new weights.
    
    If the raw OLMAR update would cause excessive turnover,
    we blend the new weights with old weights to cap turnover.
    
    Formula:
        alpha = min(1, max_turnover / raw_turnover)
        adjusted = (1 - alpha) * old + alpha * new
    
    Args:
        old_weights: Current portfolio weights
        new_weights: Target OLMAR weights
        max_turnover: Maximum allowed turnover (default: 50%)
        
    Returns:
        np.ndarray: Adjusted weights with turnover <= max_turnover
    """
    raw_turnover = calculate_turnover(old_weights, new_weights)
    
    if raw_turnover <= max_turnover or raw_turnover < 1e-10:
        return new_weights
    
    # Calculate blending factor
    alpha = max_turnover / raw_turnover
    
    # Blend weights
    adjusted = (1 - alpha) * old_weights + alpha * new_weights
    
    # Ensure still on simplex (should be close, but numerical issues)
    adjusted = adjusted / adjusted.sum() if adjusted.sum() > 0 else old_weights
    
    return adjusted


def apply_cost_penalty(
    weights: pd.DataFrame,
    transaction_cost_bps: float = 15.0,
    min_holding_period: int = 5
) -> pd.DataFrame:
    """
    Apply transaction cost penalty to discourage excessive trading.
    
    If a position wasn't held for min_holding_period days,
    we smooth the weight change to reduce trading.
    
    Args:
        weights: DataFrame of weights over time
        transaction_cost_bps: Transaction cost in basis points
        min_holding_period: Minimum days before allowing full rebalance
        
    Returns:
        pd.DataFrame: Cost-penalized weights
    """
    warn_if_zero_costs(transaction_cost_bps)
    
    # Calculate holding periods
    # A position is "new" if it was 0 in the previous period
    is_new_position = (weights.shift(1) == 0) & (weights > 0)
    
    # Calculate days held
    days_held = weights.apply(
        lambda col: (col > 0).astype(int).groupby(
            (col == 0).cumsum()
        ).cumsum()
    )
    
    # Apply smoothing for short-held positions
    smoothing_factor = np.minimum(days_held / min_holding_period, 1.0)
    
    # Penalize positions held less than min_holding_period
    # by moving them toward equal weight
    n_assets = len(weights.columns)
    equal_weight = 1.0 / n_assets
    
    penalized = smoothing_factor * weights + (1 - smoothing_factor) * equal_weight
    
    # Renormalize
    penalized = penalized.div(penalized.sum(axis=1), axis=0)
    
    return penalized


def smooth_weights_over_time(
    weights: pd.DataFrame,
    smoothing_window: int = 5
) -> pd.DataFrame:
    """
    Apply exponential smoothing to weights to reduce turnover.
    
    Args:
        weights: DataFrame of raw OLMAR weights
        smoothing_window: Window for exponential moving average
        
    Returns:
        pd.DataFrame: Smoothed weights
    """
    smoothed = weights.ewm(span=smoothing_window, adjust=False).mean()
    
    # Renormalize to ensure weights sum to 1
    smoothed = smoothed.div(smoothed.sum(axis=1), axis=0)
    
    return smoothed


def warn_if_zero_costs(transaction_cost_bps: float) -> None:
    """
    Raise warning if transaction costs are set to zero or very low.
    
    This is the "cost-first architecture" principle:
    We explicitly warn when costs are unrealistic.
    
    Args:
        transaction_cost_bps: Transaction cost in basis points
    
    Raises:
        UserWarning if costs are 0 or below minimum threshold
    """
    MIN_REALISTIC_COST_BPS = 5.0  # 5 bps minimum
    
    if transaction_cost_bps <= 0:
        warnings.warn(
            "OLMAR: Transaction costs set to 0. "
            "Results will be unrealistically optimistic. "
            "Consider setting transaction_cost_bps >= 10 for realistic results.",
            UserWarning
        )
    elif transaction_cost_bps < MIN_REALISTIC_COST_BPS:
        warnings.warn(
            f"OLMAR: Transaction costs ({transaction_cost_bps} bps) are very low. "
            f"Consider using >= {MIN_REALISTIC_COST_BPS} bps for realistic results.",
            UserWarning
        )


def calculate_cost_drag(
    weights_history: pd.DataFrame,
    transaction_cost_bps: float = 15.0
) -> Tuple[pd.Series, float]:
    """
    Calculate the cumulative cost drag from turnover.
    
    Args:
        weights_history: DataFrame of weights over time
        transaction_cost_bps: Transaction cost in basis points per side
        
    Returns:
        Tuple of (daily_cost_series, total_cost)
    """
    warn_if_zero_costs(transaction_cost_bps)
    
    # Calculate daily turnover
    weight_changes = weights_history.diff().abs()
    daily_turnover = weight_changes.sum(axis=1) / 2
    
    # Convert bps to decimal
    cost_per_unit = transaction_cost_bps / 10000
    
    # Daily cost = turnover * cost_per_unit * 2 (buy and sell)
    daily_cost = daily_turnover * cost_per_unit * 2
    
    # Total cost as percentage
    total_cost = daily_cost.sum()
    
    return daily_cost, total_cost


def get_turnover_stats(weights_history: pd.DataFrame) -> dict:
    """
    Calculate turnover statistics for the weight history.
    
    Args:
        weights_history: DataFrame of weights over time
        
    Returns:
        Dict with turnover statistics
    """
    # Calculate daily turnover
    weight_changes = weights_history.diff().abs()
    daily_turnover = weight_changes.sum(axis=1) / 2
    
    # Remove first period (no change from nothing)
    daily_turnover = daily_turnover.iloc[1:]
    
    return {
        'mean_daily_turnover': daily_turnover.mean(),
        'median_daily_turnover': daily_turnover.median(),
        'max_daily_turnover': daily_turnover.max(),
        'total_turnover': daily_turnover.sum(),
        'annualized_turnover': daily_turnover.mean() * 252,
        'rebalance_days': (daily_turnover > 0.01).sum()  # Days with > 1% turnover
    }
