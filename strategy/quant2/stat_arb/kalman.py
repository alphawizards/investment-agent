"""
Kalman Filter Hedge Ratio
=========================
Dynamic hedge ratio estimation for pairs trading.

Uses Kalman Filter to model the time-varying relationship between
two cointegrated assets, adapting to structural changes in real-time.

Reference: QuantConnect Research
https://github.com/QuantConnect/Research/blob/master/Analysis/02%20Kalman%20Filter%20Based%20Pairs%20Trading.ipynb
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

try:
    from filterpy.kalman import KalmanFilter
    from filterpy.common import Q_discrete_white_noise
    HAS_FILTERPY = True
except ImportError:
    HAS_FILTERPY = False
    print("Warning: filterpy not installed. Install with: pip install filterpy")


@dataclass
class KalmanResult:
    """
    Result container for Kalman filter estimation.
    
    Attributes:
        hedge_ratio: Time series of estimated hedge ratios (beta)
        intercept: Time series of estimated intercepts (alpha)
        spread: Time series of spread values
        spread_zscore: Z-score of spread for trading signals
        state_covariance: Estimation uncertainty over time
        metadata: Additional information
    """
    hedge_ratio: pd.Series
    intercept: pd.Series
    spread: pd.Series
    spread_zscore: pd.Series
    state_covariance: pd.Series
    metadata: dict


class KalmanHedgeRatio:
    """
    Kalman Filter for dynamic hedge ratio estimation.
    
    Models the relationship between two assets as:
        y_t = alpha_t + beta_t * x_t + epsilon_t
    
    where alpha and beta are time-varying states estimated by the Kalman filter.
    
    Key advantages over OLS:
    1. Adapts to changing relationships in real-time
    2. Provides uncertainty estimates
    3. No fixed lookback window required
    
    Attributes:
        observation_noise: R (measurement noise variance)
        transition_noise: Q (state transition noise)
        delta: Process noise multiplier
    """
    
    def __init__(
        self,
        observation_noise: float = 1.0,
        delta: float = 1e-4,
        initial_hedge_ratio: float = 1.0,
        initial_intercept: float = 0.0,
        initial_covariance: float = 1.0,
        zscore_lookback: int = 21
    ):
        """
        Initialize Kalman Hedge Ratio estimator.
        
        Args:
            observation_noise: Measurement noise variance (R)
            delta: Process noise scale (higher = more adaptive)
            initial_hedge_ratio: Initial beta estimate
            initial_intercept: Initial alpha estimate
            initial_covariance: Initial state uncertainty
            zscore_lookback: Window for spread z-score calculation
        """
        if not HAS_FILTERPY:
            raise ImportError(
                "filterpy is required for Kalman filtering. "
                "Install with: pip install filterpy"
            )
        
        self.observation_noise = observation_noise
        self.delta = delta
        self.initial_hedge_ratio = initial_hedge_ratio
        self.initial_intercept = initial_intercept
        self.initial_covariance = initial_covariance
        self.zscore_lookback = zscore_lookback
    
    def _create_kalman_filter(self) -> KalmanFilter:
        """
        Create and initialize Kalman Filter.
        
        State vector: [intercept, hedge_ratio]
        
        Returns:
            Configured KalmanFilter object
        """
        kf = KalmanFilter(dim_x=2, dim_z=1)
        
        # State transition matrix (random walk model)
        kf.F = np.array([[1.0, 0.0],
                         [0.0, 1.0]])
        
        # Initial state
        kf.x = np.array([[self.initial_intercept],
                         [self.initial_hedge_ratio]])
        
        # Initial covariance
        kf.P = np.eye(2) * self.initial_covariance
        
        # Process noise (state transition uncertainty)
        kf.Q = np.eye(2) * self.delta
        
        # Measurement noise
        kf.R = np.array([[self.observation_noise]])
        
        return kf
    
    def estimate(
        self,
        y: pd.Series,
        x: pd.Series
    ) -> KalmanResult:
        """
        Estimate dynamic hedge ratio using Kalman Filter.
        
        Model: y_t = alpha_t + beta_t * x_t + noise
        
        Args:
            y: Dependent variable (e.g., Stock A prices)
            x: Independent variable (e.g., Stock B prices)
            
        Returns:
            KalmanResult with hedge ratios, spreads, and z-scores
        """
        # Align series
        common_idx = y.index.intersection(x.index)
        y = y.loc[common_idx].values
        x = x.loc[common_idx].values
        
        n = len(y)
        
        # Storage for results
        hedge_ratios = np.zeros(n)
        intercepts = np.zeros(n)
        spreads = np.zeros(n)
        covariances = np.zeros(n)
        
        # Initialize Kalman Filter
        kf = self._create_kalman_filter()
        
        # Run filter forward
        for t in range(n):
            # Observation matrix: H = [1, x_t]
            kf.H = np.array([[1.0, x[t]]])
            
            # Predict step
            kf.predict()
            
            # Update step with observation y_t
            kf.update(y[t])
            
            # Store results
            intercepts[t] = kf.x[0, 0]
            hedge_ratios[t] = kf.x[1, 0]
            covariances[t] = kf.P[1, 1]  # Variance of hedge ratio
            
            # Calculate spread
            spreads[t] = y[t] - intercepts[t] - hedge_ratios[t] * x[t]
        
        # Convert to Series
        idx = common_idx
        hedge_ratio_series = pd.Series(hedge_ratios, index=idx, name='hedge_ratio')
        intercept_series = pd.Series(intercepts, index=idx, name='intercept')
        spread_series = pd.Series(spreads, index=idx, name='spread')
        covariance_series = pd.Series(covariances, index=idx, name='state_cov')
        
        # Calculate z-score
        spread_mean = spread_series.rolling(self.zscore_lookback).mean()
        spread_std = spread_series.rolling(self.zscore_lookback).std()
        zscore = (spread_series - spread_mean) / spread_std
        zscore = zscore.fillna(0)
        
        # Metadata
        metadata = {
            'n_observations': n,
            'final_hedge_ratio': hedge_ratios[-1],
            'final_intercept': intercepts[-1],
            'hedge_ratio_mean': np.mean(hedge_ratios),
            'hedge_ratio_std': np.std(hedge_ratios),
            'spread_mean': np.mean(spreads),
            'spread_std': np.std(spreads),
        }
        
        return KalmanResult(
            hedge_ratio=hedge_ratio_series,
            intercept=intercept_series,
            spread=spread_series,
            spread_zscore=zscore,
            state_covariance=covariance_series,
            metadata=metadata
        )
    
    def generate_signals(
        self,
        result: KalmanResult,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5
    ) -> pd.DataFrame:
        """
        Generate trading signals from Kalman spread z-score.
        
        Strategy:
        - Long spread (long Y, short X) when z-score < -entry_zscore
        - Short spread (short Y, long X) when z-score > entry_zscore
        - Exit when z-score crosses exit_zscore towards zero
        
        Args:
            result: KalmanResult from estimate()
            entry_zscore: Z-score threshold to enter trade
            exit_zscore: Z-score threshold to exit trade
            
        Returns:
            DataFrame with position signals
        """
        z = result.spread_zscore
        
        signals = pd.DataFrame(index=z.index)
        signals['zscore'] = z
        signals['position'] = 0
        
        position = 0
        
        for i in range(len(z)):
            zscore = z.iloc[i]
            
            if np.isnan(zscore):
                signals.iloc[i, 1] = 0
                continue
            
            # Entry logic
            if position == 0:
                if zscore < -entry_zscore:
                    position = 1  # Long spread
                elif zscore > entry_zscore:
                    position = -1  # Short spread
            
            # Exit logic
            elif position == 1:
                if zscore > -exit_zscore:
                    position = 0
            elif position == -1:
                if zscore < exit_zscore:
                    position = 0
            
            signals.iloc[i, 1] = position
        
        return signals
    
    def calculate_pair_returns(
        self,
        y: pd.Series,
        x: pd.Series,
        signals: pd.DataFrame,
        result: KalmanResult
    ) -> pd.Series:
        """
        Calculate returns from pair trading strategy.
        
        Args:
            y: Dependent asset prices
            x: Independent asset prices
            signals: DataFrame with position signals
            result: KalmanResult with hedge ratios
            
        Returns:
            Series of strategy returns
        """
        # Calculate returns
        y_ret = y.pct_change()
        x_ret = x.pct_change()
        
        # Align
        common = signals.index.intersection(y_ret.index).intersection(x_ret.index)
        
        positions = signals.loc[common, 'position'].shift(1)  # Lag signals
        hedge = result.hedge_ratio.loc[common]
        
        # Strategy return = position * (y_return - hedge_ratio * x_return)
        spread_return = y_ret.loc[common] - hedge * x_ret.loc[common]
        strategy_return = positions * spread_return
        
        return strategy_return.fillna(0)


def demo():
    """Demonstrate Kalman Filter hedge ratio estimation."""
    print("=" * 60)
    print("Kalman Filter Hedge Ratio Demo")
    print("=" * 60)
    
    # Create sample cointegrated pair
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2022-01-01', periods=n, freq='D')
    
    # Stock X: random walk
    x = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5), index=dates)
    
    # Stock Y: cointegrated with X (time-varying relationship)
    true_beta = 1.5 + 0.3 * np.sin(np.linspace(0, 4*np.pi, n))  # Varying beta
    noise = np.random.randn(n) * 2
    y = pd.Series(50 + true_beta * x.values + noise, index=dates)
    
    print("\nSample data:")
    print(f"  X range: {x.min():.1f} to {x.max():.1f}")
    print(f"  Y range: {y.min():.1f} to {y.max():.1f}")
    
    # Run Kalman Filter
    kf = KalmanHedgeRatio(delta=1e-4)
    result = kf.estimate(y, x)
    
    print(f"\nKalman Filter results:")
    print(f"  Final hedge ratio: {result.metadata['final_hedge_ratio']:.4f}")
    print(f"  Hedge ratio mean: {result.metadata['hedge_ratio_mean']:.4f}")
    print(f"  Hedge ratio std: {result.metadata['hedge_ratio_std']:.4f}")
    print(f"  Spread std: {result.metadata['spread_std']:.4f}")
    
    # Generate signals
    signals = kf.generate_signals(result, entry_zscore=1.5, exit_zscore=0.5)
    
    n_trades = (signals['position'].diff().abs() > 0).sum()
    print(f"\nTrading signals:")
    print(f"  Number of position changes: {n_trades}")
    print(f"  Current position: {signals['position'].iloc[-1]}")
    print(f"  Current z-score: {signals['zscore'].iloc[-1]:.2f}")


if __name__ == "__main__":
    demo()
