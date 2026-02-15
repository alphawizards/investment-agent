"""
OLMAR Strategy Adapter
=======================
Integrates OLMAR algorithm with existing pipeline infrastructure.

Follows the same pattern as QuallamaggieStrategy to maintain consistency.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .kernels import olmar_weights, validate_weights
from .constraints import (
    apply_turnover_cap,
    calculate_turnover,
    warn_if_zero_costs,
    get_turnover_stats
)


@dataclass
class OLMARConfig:
    """
    Configuration for OLMAR strategy.
    
    Attributes:
        window: Moving average window for price prediction (default: 5)
        epsilon: Sensitivity parameter - higher = more aggressive (default: 10)
        max_turnover: Maximum daily turnover allowed (default: 0.5 = 50%)
        min_weight: Minimum weight per asset (default: 0.0)
        transaction_cost_bps: Transaction cost in basis points (default: 15)
        rebalance_freq: 'daily', 'weekly', or 'monthly' (default: 'weekly')
    """
    window: int = 5
    epsilon: float = 10.0
    max_turnover: float = 0.5
    min_weight: float = 0.0
    transaction_cost_bps: float = 15.0
    rebalance_freq: str = 'weekly'
    
    def __post_init__(self):
        """Validate configuration."""
        if self.window < 1:
            raise ValueError("Window must be >= 1")
        if self.epsilon <= 0:
            raise ValueError("Epsilon must be > 0")
        if self.max_turnover <= 0 or self.max_turnover > 1:
            raise ValueError("Max turnover must be in (0, 1]")
        if self.rebalance_freq not in ['daily', 'weekly', 'monthly']:
            raise ValueError("Rebalance frequency must be 'daily', 'weekly', or 'monthly'")
        
        # Warn if costs are unrealistic
        warn_if_zero_costs(self.transaction_cost_bps)


@dataclass
class OLMARSignalResult:
    """
    Result from OLMAR signal generation.
    
    Attributes:
        weights: DataFrame of portfolio weights over time
        raw_weights: DataFrame of raw OLMAR weights (before cost adjustment)
        turnover_stats: Dict of turnover statistics
        metadata: Additional information
    """
    weights: pd.DataFrame
    raw_weights: pd.DataFrame
    turnover_stats: Dict
    metadata: Dict = field(default_factory=dict)


class OLMARStrategy:
    """
    OLMAR (On-Line Moving Average Reversion) Strategy.
    
    This strategy assumes prices will revert to their moving average.
    It overweights assets that are below their MA and underweights
    assets that are above their MA.
    
    Key Features:
    - Mean reversion based on moving average prediction
    - Cost-aware turnover constraints
    - Simplex-projected weights (sum to 1, all >= 0)
    
    Example:
        >>> config = OLMARConfig(window=5, epsilon=10, rebalance_freq='weekly')
        >>> strategy = OLMARStrategy(config)
        >>> result = strategy.generate_weights(prices)
        >>> print(result.weights.tail())
    """
    
    def __init__(self, config: OLMARConfig = None):
        """
        Initialize OLMAR strategy.
        
        Args:
            config: OLMARConfig instance (uses defaults if None)
        """
        self.config = config or OLMARConfig()
    
    @property
    def name(self) -> str:
        """Strategy name."""
        return f"OLMAR-{self.config.rebalance_freq.capitalize()}"
    
    @property
    def description(self) -> str:
        """Strategy description."""
        return (
            f"On-Line Moving Average Reversion with {self.config.window}-day window, "
            f"epsilon={self.config.epsilon}, {self.config.rebalance_freq} rebalancing"
        )
    
    def generate_weights(
        self,
        prices: pd.DataFrame,
        apply_cost_constraints: bool = True
    ) -> OLMARSignalResult:
        """
        Generate OLMAR portfolio weights.
        
        Args:
            prices: DataFrame of asset prices (rows=dates, cols=assets)
            apply_cost_constraints: Whether to apply turnover cap (default: True)
            
        Returns:
            OLMARSignalResult with weights, raw_weights, and statistics
        """
        # Calculate raw OLMAR weights
        raw_weights = olmar_weights(
            prices,
            window=self.config.window,
            epsilon=self.config.epsilon
        )
        
        # Apply rebalancing frequency mask
        rebalance_mask = self._get_rebalance_mask(prices.index)
        
        # Apply turnover constraints if requested
        if apply_cost_constraints:
            weights = self._apply_constraints(raw_weights, rebalance_mask)
        else:
            weights = self._apply_rebalance_mask(raw_weights, rebalance_mask)
        
        # Calculate turnover statistics
        turnover_stats = get_turnover_stats(weights)
        
        # Metadata
        metadata = {
            'window': self.config.window,
            'epsilon': self.config.epsilon,
            'max_turnover': self.config.max_turnover,
            'rebalance_freq': self.config.rebalance_freq,
            'cost_constraints_applied': apply_cost_constraints,
            'n_assets': len(prices.columns),
            'n_periods': len(prices)
        }
        
        return OLMARSignalResult(
            weights=weights,
            raw_weights=raw_weights,
            turnover_stats=turnover_stats,
            metadata=metadata
        )
    
    def _get_rebalance_mask(self, dates: pd.DatetimeIndex) -> pd.Series:
        """
        Create mask indicating which dates are rebalance dates.
        
        Args:
            dates: DatetimeIndex of price dates
            
        Returns:
            pd.Series: Boolean mask (True = rebalance day)
        """
        freq = self.config.rebalance_freq
        
        if freq == 'daily':
            return pd.Series(True, index=dates)
        elif freq == 'weekly':
            # Rebalance on Mondays (or first trading day of week)
            dates_series = pd.Series(dates, index=dates)
            is_monday = dates_series.dt.weekday == 0
            is_first_of_week = dates_series.dt.isocalendar().week != dates_series.shift(1).dt.isocalendar().week
            return is_monday | is_first_of_week
        elif freq == 'monthly':
            # Rebalance on first trading day of month
            dates_series = pd.Series(dates, index=dates)
            is_first_of_month = dates_series.dt.month != dates_series.shift(1).dt.month
            return is_first_of_month
        else:
            raise ValueError(f"Unknown rebalance frequency: {freq}")
    
    def _apply_rebalance_mask(
        self,
        weights: pd.DataFrame,
        rebalance_mask: pd.Series
    ) -> pd.DataFrame:
        """
        Apply rebalance mask - only update weights on rebalance days.
        
        Args:
            weights: DataFrame of OLMAR weights
            rebalance_mask: Boolean mask for rebalance days
            
        Returns:
            pd.DataFrame: Weights with non-rebalance days forward-filled
        """
        masked_weights = weights.copy()
        
        # On non-rebalance days, use previous day's weights
        for i in range(1, len(masked_weights)):
            if not rebalance_mask.iloc[i]:
                masked_weights.iloc[i] = masked_weights.iloc[i-1]
        
        return masked_weights
    
    def _apply_constraints(
        self,
        raw_weights: pd.DataFrame,
        rebalance_mask: pd.Series
    ) -> pd.DataFrame:
        """
        Apply turnover and rebalance constraints.
        
        Args:
            raw_weights: DataFrame of raw OLMAR weights
            rebalance_mask: Boolean mask for rebalance days
            
        Returns:
            pd.DataFrame: Constrained weights
        """
        constrained_weights = raw_weights.copy()
        
        for i in range(1, len(constrained_weights)):
            if rebalance_mask.iloc[i]:
                # Apply turnover cap on rebalance days
                old_w = constrained_weights.iloc[i-1].values
                new_w = raw_weights.iloc[i].values
                
                capped_w = apply_turnover_cap(
                    old_w, new_w, self.config.max_turnover
                )
                constrained_weights.iloc[i] = capped_w
            else:
                # Non-rebalance day: keep previous weights
                constrained_weights.iloc[i] = constrained_weights.iloc[i-1]
        
        return constrained_weights
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters as dict."""
        return {
            'window': self.config.window,
            'epsilon': self.config.epsilon,
            'max_turnover': self.config.max_turnover,
            'min_weight': self.config.min_weight,
            'transaction_cost_bps': self.config.transaction_cost_bps,
            'rebalance_freq': self.config.rebalance_freq
        }


# Factory functions for common configurations
def create_olmar_weekly(
    window: int = 5,
    epsilon: float = 10.0,
    max_turnover: float = 0.5
) -> OLMARStrategy:
    """
    Create OLMAR strategy with weekly rebalancing.
    
    Args:
        window: MA window (default: 5)
        epsilon: Sensitivity (default: 10)
        max_turnover: Max turnover per rebalance (default: 50%)
        
    Returns:
        OLMARStrategy configured for weekly rebalancing
    """
    config = OLMARConfig(
        window=window,
        epsilon=epsilon,
        max_turnover=max_turnover,
        rebalance_freq='weekly'
    )
    return OLMARStrategy(config)


def create_olmar_monthly(
    window: int = 5,
    epsilon: float = 10.0,
    max_turnover: float = 0.5
) -> OLMARStrategy:
    """
    Create OLMAR strategy with monthly rebalancing.
    
    Args:
        window: MA window (default: 5)
        epsilon: Sensitivity (default: 10)
        max_turnover: Max turnover per rebalance (default: 50%)
        
    Returns:
        OLMARStrategy configured for monthly rebalancing
    """
    config = OLMARConfig(
        window=window,
        epsilon=epsilon,
        max_turnover=max_turnover,
        rebalance_freq='monthly'
    )
    return OLMARStrategy(config)


def create_olmar_daily(
    window: int = 5,
    epsilon: float = 10.0,
    max_turnover: float = 0.2
) -> OLMARStrategy:
    """
    Create OLMAR strategy with daily rebalancing.
    
    WARNING: Daily rebalancing incurs high transaction costs.
    Use lower max_turnover to compensate.
    
    Args:
        window: MA window (default: 5)
        epsilon: Sensitivity (default: 10)
        max_turnover: Max turnover per rebalance (default: 20% - lower due to daily)
        
    Returns:
        OLMARStrategy configured for daily rebalancing
    """
    config = OLMARConfig(
        window=window,
        epsilon=epsilon,
        max_turnover=max_turnover,
        rebalance_freq='daily'
    )
    return OLMARStrategy(config)
