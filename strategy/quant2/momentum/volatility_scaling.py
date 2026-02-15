"""
Volatility Scaling Module
=========================
Dynamic position sizing based on realized volatility.

This module implements the volatility scaling overlay described in:
Barroso and Santa-Clara (2015) - "Momentum Has Its Moments"

Key Concept:
    Instead of fixed 100% allocation, dynamically adjust exposure based on
    the ratio of target volatility to realized volatility:
    
    w_t = min(MaxLev, σ_target / σ_realized_{t-1})

Benefits:
    1. Reduces exposure during turbulent markets (before crashes)
    2. Increases exposure during calm, trending markets
    3. Reduces kurtosis (fat tails) of return distribution
    4. Improves long-term geometric returns

Usage:
    scaler = VolatilityScaling(target_vol=0.12, max_leverage=1.5)
    scaled_weights = scaler.apply(weights, portfolio_returns)
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Union
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class VolatilityScalingResult:
    """
    Result container for volatility scaling.
    
    Attributes:
        scaled_weights: DataFrame of scaled portfolio weights
        leverage_factors: Series of leverage/scaling factors over time
        realized_vol: Series of realized volatility
        metadata: Additional information
    """
    scaled_weights: pd.DataFrame
    leverage_factors: pd.Series
    realized_vol: pd.Series
    metadata: dict


class VolatilityScaling:
    """
    Volatility scaling overlay for momentum strategies.
    
    Scales portfolio exposure inversely with realized volatility to
    maintain a constant risk profile over time.
    
    Attributes:
        target_vol: Target annualized volatility (default: 12%)
        max_leverage: Maximum leverage factor (default: 1.5)
        vol_lookback: Days for volatility estimation (default: 126)
        vol_type: 'ewma' or 'simple' (default: 'ewma')
        halflife: EWMA halflife in days (default: 63)
    """
    
    def __init__(
        self,
        target_vol: float = 0.12,
        max_leverage: float = 1.5,
        min_leverage: float = 0.1,
        vol_lookback: int = 126,
        vol_type: str = 'ewma',
        halflife: int = 63,
        annualization: int = 252
    ):
        """
        Initialize Volatility Scaler.
        
        Args:
            target_vol: Target annualized volatility (e.g., 0.12 = 12%)
            max_leverage: Maximum leverage (cap on scaling factor)
            min_leverage: Minimum leverage (floor on scaling factor)
            vol_lookback: Rolling window for simple volatility
            vol_type: 'ewma' for exponential, 'simple' for rolling std
            halflife: EWMA halflife in days (only for vol_type='ewma')
            annualization: Trading days per year (default: 252)
        """
        self.target_vol = target_vol
        self.max_leverage = max_leverage
        self.min_leverage = min_leverage
        self.vol_lookback = vol_lookback
        self.vol_type = vol_type
        self.halflife = halflife
        self.annualization = annualization
    
    def calculate_realized_volatility(
        self,
        returns: pd.Series,
        annualize: bool = True
    ) -> pd.Series:
        """
        Calculate rolling realized volatility.
        
        Args:
            returns: Series of portfolio returns
            annualize: Whether to annualize (default: True)
            
        Returns:
            Series of realized volatility estimates
        """
        if self.vol_type == 'ewma':
            # Exponentially weighted volatility
            # More responsive to recent changes
            variance = returns.ewm(halflife=self.halflife).var()
            vol = np.sqrt(variance)
        else:
            # Simple rolling standard deviation
            vol = returns.rolling(window=self.vol_lookback).std()
        
        if annualize:
            vol = vol * np.sqrt(self.annualization)
        
        return vol
    
    def calculate_scaling_factors(
        self,
        realized_vol: pd.Series,
        lag: int = 1
    ) -> pd.Series:
        """
        Calculate volatility scaling factors.
        
        Factor = σ_target / σ_realized (lagged)
        
        We use lagged volatility to avoid look-ahead bias.
        
        Args:
            realized_vol: Series of realized volatility
            lag: Number of periods to lag volatility (default: 1)
            
        Returns:
            Series of scaling factors
        """
        # Lag the volatility estimate
        lagged_vol = realized_vol.shift(lag)
        
        # Calculate raw scaling factor
        raw_factor = self.target_vol / lagged_vol
        
        # Apply constraints
        scaling_factor = raw_factor.clip(
            lower=self.min_leverage,
            upper=self.max_leverage
        )
        
        return scaling_factor
    
    def apply(
        self,
        weights: Union[pd.DataFrame, pd.Series],
        portfolio_returns: pd.Series
    ) -> VolatilityScalingResult:
        """
        Apply volatility scaling to portfolio weights.
        
        Args:
            weights: DataFrame or Series of portfolio weights
            portfolio_returns: Series of portfolio returns for vol estimation
            
        Returns:
            VolatilityScalingResult with scaled weights and metadata
        """
        # Calculate realized volatility
        realized_vol = self.calculate_realized_volatility(portfolio_returns)
        
        # Calculate scaling factors
        leverage_factors = self.calculate_scaling_factors(realized_vol)
        
        # Apply scaling to weights
        if isinstance(weights, pd.DataFrame):
            # Scale each row (date) by its leverage factor
            scaled_weights = weights.multiply(leverage_factors, axis=0)
        else:
            # Single-period weights
            scaled_weights = weights * leverage_factors
        
        # Metadata
        metadata = {
            'target_vol': self.target_vol,
            'max_leverage': self.max_leverage,
            'min_leverage': self.min_leverage,
            'vol_type': self.vol_type,
            'avg_leverage': leverage_factors.mean(),
            'leverage_std': leverage_factors.std(),
            'current_leverage': leverage_factors.iloc[-1] if len(leverage_factors) > 0 else np.nan,
            'current_vol': realized_vol.iloc[-1] if len(realized_vol) > 0 else np.nan,
        }
        
        return VolatilityScalingResult(
            scaled_weights=scaled_weights,
            leverage_factors=leverage_factors,
            realized_vol=realized_vol,
            metadata=metadata
        )
    
    def backtest_scaling_effect(
        self,
        portfolio_returns: pd.Series
    ) -> pd.DataFrame:
        """
        Compare unscaled vs scaled portfolio performance.
        
        Args:
            portfolio_returns: Series of unscaled portfolio returns
            
        Returns:
            DataFrame with comparison metrics
        """
        # Calculate realized vol and scaling factors
        realized_vol = self.calculate_realized_volatility(portfolio_returns)
        scaling_factors = self.calculate_scaling_factors(realized_vol)
        
        # Calculate scaled returns
        scaled_returns = portfolio_returns * scaling_factors
        
        # Calculate cumulative returns
        unscaled_cum = (1 + portfolio_returns).cumprod()
        scaled_cum = (1 + scaled_returns).cumprod()
        
        # Calculate metrics
        def calc_metrics(returns, name):
            ann_return = returns.mean() * self.annualization
            ann_vol = returns.std() * np.sqrt(self.annualization)
            sharpe = ann_return / ann_vol if ann_vol > 0 else 0
            
            cum = (1 + returns).cumprod()
            drawdown = cum / cum.cummax() - 1
            max_dd = drawdown.min()
            
            return pd.Series({
                'Strategy': name,
                'Ann. Return': ann_return,
                'Ann. Volatility': ann_vol,
                'Sharpe Ratio': sharpe,
                'Max Drawdown': max_dd,
                'Skewness': returns.skew(),
                'Kurtosis': returns.kurtosis(),
            })
        
        unscaled_metrics = calc_metrics(portfolio_returns.dropna(), 'Unscaled')
        scaled_metrics = calc_metrics(scaled_returns.dropna(), 'Vol-Scaled')
        
        return pd.DataFrame([unscaled_metrics, scaled_metrics]).set_index('Strategy')
    
    def get_current_recommendation(
        self,
        portfolio_returns: pd.Series
    ) -> dict:
        """
        Get current volatility scaling recommendation.
        
        Args:
            portfolio_returns: Recent portfolio returns
            
        Returns:
            Dict with current scaling recommendation
        """
        realized_vol = self.calculate_realized_volatility(portfolio_returns)
        scaling_factor = self.calculate_scaling_factors(realized_vol)
        
        current_vol = realized_vol.iloc[-1]
        current_factor = scaling_factor.iloc[-1]
        
        # Determine regime
        if current_vol > self.target_vol * 1.5:
            regime = "HIGH_VOL"
            action = "REDUCE EXPOSURE"
        elif current_vol < self.target_vol * 0.7:
            regime = "LOW_VOL"
            action = "INCREASE EXPOSURE"
        else:
            regime = "NORMAL"
            action = "MAINTAIN"
        
        return {
            'current_realized_vol': current_vol,
            'target_vol': self.target_vol,
            'scaling_factor': current_factor,
            'capped_at_max': current_factor >= self.max_leverage,
            'floored_at_min': current_factor <= self.min_leverage,
            'regime': regime,
            'recommended_action': action,
            'recommended_exposure': f"{current_factor * 100:.1f}%"
        }


class AdaptiveVolatilityScaling(VolatilityScaling):
    """
    Adaptive volatility scaling with regime-aware adjustments.
    
    Extends basic volatility scaling with:
    - Multiple volatility estimators
    - Regime-conditional target volatility
    - Drawdown-based emergency de-risking
    """
    
    def __init__(
        self,
        target_vol: float = 0.12,
        crisis_target_vol: float = 0.08,
        max_leverage: float = 1.5,
        drawdown_threshold: float = -0.10,
        **kwargs
    ):
        """
        Initialize Adaptive Volatility Scaler.
        
        Args:
            target_vol: Normal target volatility
            crisis_target_vol: Target volatility during drawdowns
            max_leverage: Maximum leverage
            drawdown_threshold: Drawdown level to trigger crisis mode
            **kwargs: Additional arguments for parent class
        """
        super().__init__(target_vol=target_vol, max_leverage=max_leverage, **kwargs)
        self.crisis_target_vol = crisis_target_vol
        self.drawdown_threshold = drawdown_threshold
    
    def calculate_drawdown(
        self,
        portfolio_returns: pd.Series
    ) -> pd.Series:
        """
        Calculate rolling drawdown.
        
        Args:
            portfolio_returns: Series of returns
            
        Returns:
            Series of drawdown values (negative)
        """
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = cumulative / running_max - 1
        return drawdown
    
    def apply_adaptive(
        self,
        weights: pd.DataFrame,
        portfolio_returns: pd.Series
    ) -> VolatilityScalingResult:
        """
        Apply adaptive volatility scaling with drawdown awareness.
        
        During significant drawdowns, reduces target volatility to
        preserve capital and reduce sequence risk.
        
        Args:
            weights: DataFrame of portfolio weights
            portfolio_returns: Series of portfolio returns
            
        Returns:
            VolatilityScalingResult with adaptively scaled weights
        """
        # Calculate drawdown series
        drawdown = self.calculate_drawdown(portfolio_returns)
        
        # Calculate realized volatility
        realized_vol = self.calculate_realized_volatility(portfolio_returns)
        
        # Determine adaptive target (lower during drawdowns)
        in_crisis = drawdown < self.drawdown_threshold
        adaptive_target = pd.Series(
            np.where(in_crisis, self.crisis_target_vol, self.target_vol),
            index=drawdown.index
        )
        
        # Calculate scaling factors with adaptive target
        lagged_vol = realized_vol.shift(1)
        raw_factor = adaptive_target / lagged_vol
        leverage_factors = raw_factor.clip(
            lower=self.min_leverage,
            upper=self.max_leverage
        )
        
        # Apply scaling
        scaled_weights = weights.multiply(leverage_factors, axis=0)
        
        # Metadata
        metadata = {
            'target_vol': self.target_vol,
            'crisis_target_vol': self.crisis_target_vol,
            'drawdown_threshold': self.drawdown_threshold,
            'avg_leverage': leverage_factors.mean(),
            'current_leverage': leverage_factors.iloc[-1],
            'current_vol': realized_vol.iloc[-1],
            'current_drawdown': drawdown.iloc[-1],
            'in_crisis_mode': in_crisis.iloc[-1],
        }
        
        return VolatilityScalingResult(
            scaled_weights=scaled_weights,
            leverage_factors=leverage_factors,
            realized_vol=realized_vol,
            metadata=metadata
        )


def demo():
    """Demonstrate volatility scaling."""
    print("=" * 60)
    print("Volatility Scaling Demo")
    print("=" * 60)
    
    # Create sample returns
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    
    # Simulate returns with volatility clustering
    returns = pd.Series(
        np.random.randn(len(dates)) * 0.02,
        index=dates
    )
    # Add a high-vol period
    returns.iloc[200:250] *= 3
    
    # Create sample weights (equal weight 5 assets)
    weights = pd.DataFrame(
        0.2,
        index=dates,
        columns=['A', 'B', 'C', 'D', 'E']
    )
    
    print("\nSample portfolio returns:")
    print(returns.tail(10))
    
    # Apply volatility scaling
    scaler = VolatilityScaling(target_vol=0.12, max_leverage=1.5)
    result = scaler.apply(weights, returns)
    
    print("\nVolatility Scaling Result:")
    print(f"Current realized vol: {result.metadata['current_vol']:.2%}")
    print(f"Current leverage factor: {result.metadata['current_leverage']:.2f}")
    print(f"Average leverage: {result.metadata['avg_leverage']:.2f}")
    
    print("\nBacktest comparison:")
    comparison = scaler.backtest_scaling_effect(returns)
    print(comparison)
    
    print("\nCurrent recommendation:")
    rec = scaler.get_current_recommendation(returns)
    for key, value in rec.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    demo()
