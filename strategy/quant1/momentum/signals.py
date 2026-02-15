"""
Signal Generation Module
========================
Implements Dual Momentum and Factor signals for portfolio selection.

Signals:
1. Absolute Momentum: Is the asset trending up?
2. Relative Momentum: Is the asset outperforming peers?
3. Composite: Combination of both
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, List
import pandas_ta as ta

from strategy.config import CONFIG


class MomentumSignals:
    """
    Generate momentum signals for asset selection.
    
    Implements Gary Antonacci's Dual Momentum approach:
    - Absolute Momentum: Compare asset return to risk-free rate
    - Relative Momentum: Rank assets by return within universe
    """
    
    def __init__(self, 
                 lookback_days: int = None,
                 risk_free_rate: float = None):
        """
        Initialize signal generator.
        
        Args:
            lookback_days: Lookback period for momentum (default: from config)
            risk_free_rate: Annualized risk-free rate (default: from config)
        """
        self.lookback = lookback_days or CONFIG.MOMENTUM_LOOKBACK_LONG
        self.rf_rate = risk_free_rate or CONFIG.RISK_FREE_RATE
        
    def calculate_returns(self, prices: pd.DataFrame, periods: int = None) -> pd.DataFrame:
        """
        Calculate rolling returns over specified period.
        
        Args:
            prices: DataFrame of prices
            periods: Number of periods (default: self.lookback)
            
        Returns:
            pd.DataFrame: Rolling returns
        """
        periods = periods or self.lookback
        returns = prices.pct_change(periods)
        return returns
    
    def absolute_momentum(self, 
                          prices: pd.DataFrame,
                          threshold: float = None) -> pd.DataFrame:
        """
        Calculate Absolute Momentum signal.
        
        Signal = 1 if 12-month return > risk-free rate, else 0
        
        This is the "trend filter" - we only invest in assets that are
        trending upward (above risk-free rate).
        
        Args:
            prices: DataFrame of prices (AUD-normalized)
            threshold: Minimum return threshold (default: risk-free rate)
            
        Returns:
            pd.DataFrame: Binary signal (1 = in trend, 0 = not)
        """
        threshold = threshold or (self.rf_rate * self.lookback / 252)
        
        # Calculate lookback returns
        returns = self.calculate_returns(prices, self.lookback)
        
        # Signal: 1 if return > threshold
        signal = (returns > threshold).astype(int)
        
        return signal
    
    def relative_momentum(self, 
                          prices: pd.DataFrame,
                          top_pct: float = 0.5) -> pd.DataFrame:
        """
        Calculate Relative Momentum signal.
        
        Signal = 1 if asset ranks in top 50% by return, else 0
        
        This is the "cross-sectional momentum" - we prefer assets that
        are outperforming their peers.
        
        Args:
            prices: DataFrame of prices (AUD-normalized)
            top_pct: Percentage of top performers to select (default: 0.5)
            
        Returns:
            pd.DataFrame: Binary signal (1 = top performer, 0 = not)
        """
        # Calculate lookback returns
        returns = self.calculate_returns(prices, self.lookback)
        
        # Rank assets (1 = worst, N = best)
        ranks = returns.rank(axis=1, pct=True)
        
        # Signal: 1 if in top percentage
        signal = (ranks >= (1 - top_pct)).astype(int)
        
        return signal
    
    def dual_momentum(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Dual Momentum signal (Antonacci).
        
        Signal = Absolute_Momentum AND Relative_Momentum
        
        An asset must BOTH:
        1. Be trending up (absolute momentum)
        2. Outperform peers (relative momentum)
        
        Args:
            prices: DataFrame of prices (AUD-normalized)
            
        Returns:
            pd.DataFrame: Binary signal (1 = include, 0 = exclude)
        """
        abs_signal = self.absolute_momentum(prices)
        rel_signal = self.relative_momentum(prices)
        
        # Combine: must pass BOTH filters
        dual_signal = abs_signal * rel_signal
        
        return dual_signal
    
    def momentum_score(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate continuous momentum score (0 to 1).
        
        More nuanced than binary signal - useful for weighting.
        
        Score combines:
        - 12-month return rank (50%)
        - 6-month return rank (30%)
        - 1-month return rank (20%)
        
        Args:
            prices: DataFrame of prices
            
        Returns:
            pd.DataFrame: Momentum score (0 to 1)
        """
        # Multiple timeframes from config
        ret_12m = self.calculate_returns(prices, CONFIG.MOMENTUM_LOOKBACK_LONG)
        ret_6m = self.calculate_returns(prices, CONFIG.MOMENTUM_LOOKBACK_MEDIUM)
        ret_1m = self.calculate_returns(prices, CONFIG.MOMENTUM_LOOKBACK_SHORT)
        
        # Rank each (percentile)
        rank_12m = ret_12m.rank(axis=1, pct=True)
        rank_6m = ret_6m.rank(axis=1, pct=True)
        rank_1m = ret_1m.rank(axis=1, pct=True)
        
        # Weighted combination from config
        score = (CONFIG.MOMENTUM_WEIGHT * rank_12m) + (CONFIG.TECHNICAL_WEIGHT * rank_6m) + (CONFIG.VOLATILITY_WEIGHT * rank_1m)
        
        return score


class TechnicalSignals:
    """
    Generate technical analysis signals using pandas-ta.
    
    These can be used as additional filters or alpha factors.
    """
    
    @staticmethod
    def calculate_rsi(prices: pd.DataFrame, length: int = 14) -> pd.DataFrame:
        """
        Calculate RSI for each asset.
        
        Args:
            prices: DataFrame of prices
            length: RSI period
            
        Returns:
            pd.DataFrame: RSI values (0-100)
        """
        rsi_df = pd.DataFrame(index=prices.index)
        
        for col in prices.columns:
            rsi = ta.rsi(prices[col], length=length)
            rsi_df[col] = rsi
            
        return rsi_df
    
    @staticmethod
    def calculate_macd_signal(prices: pd.DataFrame,
                               fast: int = 12,
                               slow: int = 26,
                               signal: int = 9) -> pd.DataFrame:
        """
        Calculate MACD signal (1 if MACD > Signal line, else 0).
        
        Args:
            prices: DataFrame of prices
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            pd.DataFrame: Binary signal
        """
        signal_df = pd.DataFrame(index=prices.index)
        
        for col in prices.columns:
            macd = ta.macd(prices[col], fast=fast, slow=slow, signal=signal)
            if macd is not None and len(macd.columns) >= 3:
                # MACD > Signal = bullish
                macd_line = macd.iloc[:, 0]
                signal_line = macd.iloc[:, 2]
                signal_df[col] = (macd_line > signal_line).astype(int)
            else:
                signal_df[col] = np.nan
                
        return signal_df
    
    @staticmethod
    def calculate_sma_crossover(prices: pd.DataFrame,
                                 fast: int = 50,
                                 slow: int = 200) -> pd.DataFrame:
        """
        Calculate SMA crossover signal (Golden Cross / Death Cross).
        
        Signal = 1 if fast SMA > slow SMA, else 0
        
        Args:
            prices: DataFrame of prices
            fast: Fast SMA period
            slow: Slow SMA period
            
        Returns:
            pd.DataFrame: Binary signal
        """
        signal_df = pd.DataFrame(index=prices.index)
        
        for col in prices.columns:
            sma_fast = ta.sma(prices[col], length=fast)
            sma_slow = ta.sma(prices[col], length=slow)
            signal_df[col] = (sma_fast > sma_slow).astype(int)
            
        return signal_df
    
    @staticmethod
    def calculate_volatility(returns: pd.DataFrame, 
                             window: int = 21) -> pd.DataFrame:
        """
        Calculate rolling volatility (annualized).
        
        Args:
            returns: DataFrame of returns
            window: Rolling window (default: 21 days = 1 month)
            
        Returns:
            pd.DataFrame: Annualized volatility
        """
        vol = returns.rolling(window=window).std() * np.sqrt(252)
        return vol
    
    @staticmethod
    def calculate_drawdown(prices: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate current drawdown from peak.
        
        Args:
            prices: DataFrame of prices
            
        Returns:
            pd.DataFrame: Drawdown (negative values)
        """
        rolling_max = prices.cummax()
        drawdown = (prices - rolling_max) / rolling_max
        return drawdown


class CompositeSignal:
    """
    Combine multiple signals into a single composite signal.
    """
    
    def __init__(self, 
                 momentum_weight: float = None,
                 technical_weight: float = None):
        """
        Initialize composite signal generator.
        
        Args:
            momentum_weight: Weight for momentum signals (default: from config)
            technical_weight: Weight for technical signals (default: from config)
        """
        self.mom_weight = momentum_weight or CONFIG.MOMENTUM_WEIGHT
        self.tech_weight = technical_weight or CONFIG.TECHNICAL_WEIGHT
        self.momentum = MomentumSignals()
        self.technical = TechnicalSignals()
        
    def generate(self, 
                 prices: pd.DataFrame,
                 returns: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate composite signal and scores.
        
        Args:
            prices: DataFrame of prices (AUD-normalized)
            returns: DataFrame of returns
            
        Returns:
            Tuple of:
            - binary_signal: DataFrame of 1/0 signals
            - signal_score: DataFrame of continuous scores (0-1)
        """
        # Momentum signals
        dual_mom = self.momentum.dual_momentum(prices)
        mom_score = self.momentum.momentum_score(prices)
        
        # Technical signals
        sma_signal = self.technical.calculate_sma_crossover(prices)
        rsi = self.technical.calculate_rsi(prices)
        
        # RSI signal: 1 if RSI between 30 and 70 (not overbought/oversold)
        rsi_signal = ((rsi > 30) & (rsi < 70)).astype(int)
        
        # Combine technical signals
        tech_signal = (sma_signal * 0.6 + rsi_signal * 0.4).round().astype(int)
        
        # Composite binary signal
        binary_signal = dual_mom * tech_signal
        
        # Composite score (continuous)
        rsi_normalized = (100 - np.abs(rsi - 50)) / 100  # 1 at RSI=50, 0 at extremes
        signal_score = (
            self.mom_weight * mom_score + 
            self.tech_weight * rsi_normalized
        )
        
        return binary_signal, signal_score
    
    def get_tradeable_assets(self, 
                              prices: pd.DataFrame,
                              returns: pd.DataFrame,
                              min_score: float = 0.5) -> List[str]:
        """
        Get list of assets that pass signal filters.
        
        Args:
            prices: DataFrame of prices
            returns: DataFrame of returns
            min_score: Minimum signal score to be tradeable
            
        Returns:
            List of ticker symbols that pass filters
        """
        binary_signal, score = self.generate(prices, returns)
        
        # Get latest signals
        latest_binary = binary_signal.iloc[-1]
        latest_score = score.iloc[-1]
        
        # Filter: must have binary signal = 1 AND score >= min_score
        tradeable = latest_binary[
            (latest_binary == 1) & (latest_score >= min_score)
        ].index.tolist()
        
        return tradeable


def demo():
    """Demonstrate signal generation."""
    print("=" * 60)
    print("Signal Generation Demo")
    print("=" * 60)
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2024-12-01', freq='B')
    
    # Simulated prices with different trends
    prices = pd.DataFrame({
        'UPTREND': 100 * np.exp(np.cumsum(np.random.randn(len(dates)) * 0.01 + 0.0005)),
        'DOWNTREND': 100 * np.exp(np.cumsum(np.random.randn(len(dates)) * 0.01 - 0.0003)),
        'SIDEWAYS': 100 * np.exp(np.cumsum(np.random.randn(len(dates)) * 0.015)),
        'VOLATILE': 100 * np.exp(np.cumsum(np.random.randn(len(dates)) * 0.025)),
    }, index=dates)
    
    returns = prices.pct_change().dropna()
    
    # Generate signals
    mom = MomentumSignals()
    
    print("\n12-Month Returns:")
    print(mom.calculate_returns(prices, 252).iloc[-1].round(4))
    
    print("\nAbsolute Momentum Signal (latest):")
    print(mom.absolute_momentum(prices).iloc[-1])
    
    print("\nRelative Momentum Signal (latest):")
    print(mom.relative_momentum(prices).iloc[-1])
    
    print("\nDual Momentum Signal (latest):")
    print(mom.dual_momentum(prices).iloc[-1])
    
    print("\nMomentum Score (latest):")
    print(mom.momentum_score(prices).iloc[-1].round(3))
    
    # Composite signal
    composite = CompositeSignal()
    binary, score = composite.generate(prices, returns)
    
    print("\nComposite Signal Score (latest):")
    print(score.iloc[-1].round(3))
    
    print("\nTradeable Assets:")
    tradeable = composite.get_tradeable_assets(prices, returns, min_score=0.4)
    print(tradeable)


if __name__ == "__main__":
    demo()
