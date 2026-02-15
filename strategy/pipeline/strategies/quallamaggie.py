"""
Quallamaggie Strategy Plugin
=============================
Implementation of Kristjan Kullamägi's momentum breakout strategy.

Strategy Components:
- 1M/3M/6M momentum screening (top performers)
- RS Line relative to SPY
- Pattern detection (VCP, HTF, consolidation)
- Breakout on volume
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..signal_layer import BaseStrategy, SignalResult


@dataclass
class QuallamaggieConfig:
    """Configuration for Quallamaggie strategy."""
    
    # Momentum settings
    momentum_lookback: int = 126  # 6 months default
    top_momentum_pct: float = 0.10  # Top 10%
    
    # Moving averages
    ema_10: int = 10
    ema_20: int = 20
    sma_50: int = 50
    sma_200: int = 200
    
    # Pattern detection
    consolidation_min_days: int = 10
    consolidation_max_range: float = 0.15  # 15% range
    breakout_volume_mult: float = 1.5  # 1.5x average
    
    # RS Line
    rs_benchmark: str = "SPY"
    
    # Position
    max_positions: int = 10


class QuallamaggieStrategy(BaseStrategy):
    """
    Quallamaggie Momentum Breakout Strategy.
    
    This strategy identifies stocks with:
    1. Strong momentum (top performers over lookback period)
    2. RS Line at or near new highs vs benchmark
    3. In consolidation/base pattern
    4. Breaking out on above-average volume
    """
    
    def __init__(self, config: QuallamaggieConfig = None):
        self.config = config or QuallamaggieConfig()
    
    @property
    def name(self) -> str:
        days = self.config.momentum_lookback
        months = days // 21
        return f"Quallamaggie_{months}M"
    
    @property
    def description(self) -> str:
        return f"Quallamaggie momentum breakout ({self.config.momentum_lookback}d lookback)"
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        volume: pd.DataFrame = None,
        **kwargs
    ) -> SignalResult:
        """
        Generate Quallamaggie trading signals.
        
        Signal logic:
        1. Calculate momentum over lookback period
        2. Filter for top performers (momentum filter)
        3. Check if in uptrend (above key MAs)
        4. Detect consolidation/base pattern
        5. Generate buy signal on breakout with volume
        """
        lookback = self.config.momentum_lookback
        
        # Initialize signal DataFrames
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
        strength = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        
        # Need enough history
        if len(prices) < lookback + 50:
            return SignalResult(
                strategy_name=self.name,
                signals=signals,
                strength=strength,
                metadata={'error': 'Insufficient data'}
            )
        
        # 1. Momentum Calculation
        momentum = self._calculate_momentum(prices, lookback)

        # 2. Moving Averages
        ema_10 = prices.ewm(span=self.config.ema_10).mean()
        ema_20 = prices.ewm(span=self.config.ema_20).mean()
        sma_50 = prices.rolling(self.config.sma_50).mean()
        # sma_200 = prices.rolling(self.config.sma_200).mean() # Not used in signal logic currently
        
        # 3. RS Line
        rs_line = self._calculate_rs_line(prices)
        
        # 4. Volume Analysis
        if volume is not None:
            avg_volume = volume.rolling(50).mean()
            relative_volume = volume / avg_volume
            vol_confirmed_mask = relative_volume >= self.config.breakout_volume_mult
        else:
            vol_confirmed_mask = pd.DataFrame(True, index=prices.index, columns=prices.columns)
            
        # --- Vectorized Logic ---

        # A. Top Momentum Mask (per day)
        # Use rank(pct=True) to get percentiles
        # Handle all-NaN rows by keeping them as NaN (rank propagates NaNs)
        mom_rank = momentum.rank(axis=1, pct=True)
        top_momentum_mask = mom_rank >= (1 - self.config.top_momentum_pct)

        # B. Trend Mask
        # price > ema10 and price > ema20 and ema10 > ema20 and (isna(sma50) or price > sma50)
        trend_mask = (
            (prices > ema_10) &
            (prices > ema_20) &
            (ema_10 > ema_20) &
            (sma_50.isna() | (prices > sma_50))
        )

        # C. Consolidation Mask
        # Rolling max/min over last 21 days (approx 1 month trading days)
        # Loop used max(0, i-20):i+1, which is window size 21
        roll_window = 21
        recent_max = prices.rolling(roll_window, min_periods=self.config.consolidation_min_days).max()
        recent_min = prices.rolling(roll_window, min_periods=self.config.consolidation_min_days).min()

        # Avoid division by zero
        price_range_pct = (recent_max - recent_min) / recent_min.replace(0, np.nan)
        consolidation_mask = price_range_pct <= self.config.consolidation_max_range

        # D. RS Strength Mask
        # RS line near 50-day high (within 5%)
        # Loop logic: if idx < 50 return True (insufficient data assumed good)
        rs_50d_high = rs_line.rolling(51, min_periods=1).max()
        rs_mask = rs_line >= (rs_50d_high * 0.95)

        # Emulate "if idx < 50: return True"
        # We set the first 50 rows to True for rs_mask
        rs_mask.iloc[:50] = True

        # Combine Signals
        # Signal = Top_Momentum AND Trend AND (Consolidation OR RS_Good)
        final_signal_mask = top_momentum_mask & trend_mask & (consolidation_mask | rs_mask)

        # Ensure we don't signal before lookback
        final_signal_mask.iloc[:lookback] = False

        # Set signals
        signals = final_signal_mask.astype(int)

        # --- Strength Calculation (Vectorized) ---
        base_strength = 0.5

        # Momentum Bonus
        # if momentum > 50: +0.2
        # elif momentum > 25: +0.1
        mom_bonus = np.select(
            [momentum > 50, momentum > 25],
            [0.2, 0.1],
            default=0.0
        )

        # RS Bonus (+0.15)
        rs_bonus = np.where(rs_mask, 0.15, 0.0)

        # Volume Bonus (+0.15)
        vol_bonus = np.where(vol_confirmed_mask, 0.15, 0.0)

        # Total Strength
        total_strength = base_strength + mom_bonus + rs_bonus + vol_bonus

        # Clip to 1.0 and apply only to valid signals
        # (Though strength is calculated for all, we usually only care where signal=1)
        strength = pd.DataFrame(total_strength, index=prices.index, columns=prices.columns).clip(upper=1.0)
        strength = strength * final_signal_mask # Zero out non-signal strength
        
        return SignalResult(
            strategy_name=self.name,
            signals=signals,
            strength=strength,
            metadata={
                'lookback': lookback,
                'top_pct': self.config.top_momentum_pct,
                'max_positions': self.config.max_positions
            }
        )
    
    def _calculate_momentum(
        self,
        prices: pd.DataFrame,
        lookback: int
    ) -> pd.DataFrame:
        """Calculate momentum (percentage return over lookback)."""
        return prices.pct_change(lookback) * 100
    
    def _calculate_rs_line(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Calculate RS Line vs benchmark."""
        benchmark = self.config.rs_benchmark
        
        if benchmark not in prices.columns:
            # Return normalized prices as proxy
            return prices / prices.iloc[0] * 100
        
        benchmark_prices = prices[benchmark]
        rs_lines = prices.div(benchmark_prices, axis=0)
        rs_lines = rs_lines / rs_lines.iloc[0] * 100
        
        return rs_lines
    
    def _check_rs_strength(
        self,
        rs_line: pd.DataFrame,
        date,
        ticker: str
    ) -> bool:
        """Check if RS Line is near new highs (Legacy helper, kept for interface compat if needed)."""
        # Note: This is now vectorized inside generate_signals and not used there.
        # Keeping it for potential external usage or testing.
        if ticker not in rs_line.columns:
            return False
        
        rs = rs_line[ticker]
        idx = rs_line.index.get_loc(date)
        
        if idx < 50:
            return True  # Not enough data, assume good
        
        current_rs = rs.iloc[idx]
        rs_50d_high = rs.iloc[max(0, idx-50):idx+1].max()
        
        # RS within 5% of 50-day high
        return current_rs >= rs_50d_high * 0.95
    
    def _detect_consolidation(self, prices: pd.Series) -> bool:
        """Detect if stock is in consolidation pattern (Legacy helper)."""
        # Note: This is now vectorized inside generate_signals and not used there.
        if len(prices) < self.config.consolidation_min_days:
            return False
        
        price_range = (prices.max() - prices.min()) / prices.min()
        return price_range <= self.config.consolidation_max_range
    
    def _calculate_signal_strength(
        self,
        momentum: float,
        rs_good: bool,
        vol_confirmed: bool
    ) -> float:
        """Calculate overall signal strength (Legacy helper)."""
        base_strength = 0.5
        
        # Momentum contribution
        if momentum > 50:
            base_strength += 0.2
        elif momentum > 25:
            base_strength += 0.1
        
        # RS Line contribution
        if rs_good:
            base_strength += 0.15
        
        # Volume contribution
        if vol_confirmed:
            base_strength += 0.15
        
        return min(1.0, base_strength)
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            'momentum_lookback': self.config.momentum_lookback,
            'top_momentum_pct': self.config.top_momentum_pct,
            'max_positions': self.config.max_positions
        }


# Factory functions for different Quallamaggie variants
def create_quallamaggie_1m() -> QuallamaggieStrategy:
    """Create 1-month Quallamaggie strategy."""
    return QuallamaggieStrategy(QuallamaggieConfig(momentum_lookback=21))


def create_quallamaggie_3m() -> QuallamaggieStrategy:
    """Create 3-month Quallamaggie strategy."""
    return QuallamaggieStrategy(QuallamaggieConfig(momentum_lookback=63))


def create_quallamaggie_6m() -> QuallamaggieStrategy:
    """Create 6-month Quallamaggie strategy."""
    return QuallamaggieStrategy(QuallamaggieConfig(momentum_lookback=126))
