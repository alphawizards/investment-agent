"""
Triple Barrier Method Labeling
==============================
Implements the Triple Barrier Method for trade outcome labeling.

Reference: Alternative-Bars
https://github.com/Harkishan-99/Alternative-Bars

The Triple Barrier Method labels trades based on three barriers:
1. Upper barrier: Profit target (e.g., +5%)
2. Lower barrier: Stop loss (e.g., -3%)
3. Vertical barrier: Maximum holding period (e.g., 10 days)

Labels:
- 1 (Profit): Upper barrier hit first
- -1 (Loss): Lower barrier hit first
- 0 (Neutral): Vertical barrier hit (time expired)
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class TripleBarrierEvent:
    """Single triple barrier event."""
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    label: int  # 1, -1, or 0
    return_pct: float
    barrier_type: str  # 'profit', 'stop', 'time'
    holding_days: int


@dataclass
class TripleBarrierResult:
    """Result from triple barrier labeling."""
    events: List[TripleBarrierEvent]
    labels: pd.Series
    returns: pd.Series
    metadata: dict


class TripleBarrierLabeler:
    """
    Triple Barrier Method for trade labeling.
    
    Labels historical trade signals based on subsequent price action,
    creating targets for the meta-labeling ML model.
    
    Attributes:
        profit_take: Profit target as decimal (e.g., 0.05 = 5%)
        stop_loss: Stop loss as decimal (e.g., 0.03 = 3%)
        max_holding_days: Maximum holding period in trading days
        use_atr: If True, scale barriers by ATR
        atr_multiplier: Multiplier for ATR-based barriers
    """
    
    def __init__(
        self,
        profit_take: float = 0.05,
        stop_loss: float = 0.03,
        max_holding_days: int = 10,
        use_atr: bool = False,
        atr_multiplier: float = 2.0,
        atr_lookback: int = 14
    ):
        """
        Initialize Triple Barrier Labeler.
        
        Args:
            profit_take: Profit target as decimal
            stop_loss: Stop loss as decimal
            max_holding_days: Max holding period
            use_atr: Scale barriers by ATR
            atr_multiplier: ATR multiplier for dynamic barriers
            atr_lookback: Period for ATR calculation
        """
        self.profit_take = profit_take
        self.stop_loss = stop_loss
        self.max_holding_days = max_holding_days
        self.use_atr = use_atr
        self.atr_multiplier = atr_multiplier
        self.atr_lookback = atr_lookback
    
    def _calculate_atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> pd.Series:
        """Calculate Average True Range."""
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(self.atr_lookback).mean()
    
    def _get_barriers(
        self,
        entry_price: float,
        atr: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calculate profit and stop barriers.
        
        Args:
            entry_price: Trade entry price
            atr: ATR value at entry (if using ATR scaling)
            
        Returns:
            Tuple of (upper_barrier, lower_barrier) as prices
        """
        if self.use_atr and atr is not None:
            # ATR-scaled barriers
            upper = entry_price + (atr * self.atr_multiplier)
            lower = entry_price - (atr * self.atr_multiplier)
        else:
            # Percentage-based barriers
            upper = entry_price * (1 + self.profit_take)
            lower = entry_price * (1 - self.stop_loss)
        
        return upper, lower
    
    def label_single_trade(
        self,
        entry_date: pd.Timestamp,
        prices: pd.Series,
        high: Optional[pd.Series] = None,
        low: Optional[pd.Series] = None,
        atr: Optional[pd.Series] = None
    ) -> Optional[TripleBarrierEvent]:
        """
        Label a single trade using triple barrier method.
        
        Args:
            entry_date: Date of trade entry
            prices: Close price series
            high: High price series (for intraday barrier checks)
            low: Low price series (for intraday barrier checks)
            atr: ATR series (for dynamic barriers)
            
        Returns:
            TripleBarrierEvent or None if insufficient data
        """
        if entry_date not in prices.index:
            return None
        
        entry_idx = prices.index.get_loc(entry_date)
        entry_price = prices.iloc[entry_idx]
        
        # Get ATR at entry if using
        entry_atr = atr.iloc[entry_idx] if atr is not None and entry_date in atr.index else None
        
        # Calculate barriers
        upper_barrier, lower_barrier = self._get_barriers(entry_price, entry_atr)
        
        # Check each day from entry to max holding
        end_idx = min(entry_idx + self.max_holding_days, len(prices) - 1)
        
        for i in range(entry_idx + 1, end_idx + 1):
            current_date = prices.index[i]
            
            # Use high/low if available, else close
            if high is not None and low is not None:
                day_high = high.iloc[i]
                day_low = low.iloc[i]
            else:
                day_high = day_low = prices.iloc[i]
            
            # Check upper barrier (profit)
            if day_high >= upper_barrier:
                return TripleBarrierEvent(
                    entry_date=entry_date,
                    entry_price=entry_price,
                    exit_date=current_date,
                    exit_price=upper_barrier,
                    label=1,
                    return_pct=self.profit_take if not self.use_atr else (upper_barrier - entry_price) / entry_price,
                    barrier_type='profit',
                    holding_days=i - entry_idx
                )
            
            # Check lower barrier (stop loss)
            if day_low <= lower_barrier:
                return TripleBarrierEvent(
                    entry_date=entry_date,
                    entry_price=entry_price,
                    exit_date=current_date,
                    exit_price=lower_barrier,
                    label=-1,
                    return_pct=-self.stop_loss if not self.use_atr else (lower_barrier - entry_price) / entry_price,
                    barrier_type='stop',
                    holding_days=i - entry_idx
                )
        
        # Vertical barrier (time expired)
        exit_idx = end_idx
        exit_price = prices.iloc[exit_idx]
        exit_return = (exit_price - entry_price) / entry_price
        
        return TripleBarrierEvent(
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=prices.index[exit_idx],
            exit_price=exit_price,
            label=0,
            return_pct=exit_return,
            barrier_type='time',
            holding_days=exit_idx - entry_idx
        )
    
    def label_signals(
        self,
        signal_dates: List[pd.Timestamp],
        prices: pd.Series,
        high: Optional[pd.Series] = None,
        low: Optional[pd.Series] = None,
        atr: Optional[pd.Series] = None
    ) -> TripleBarrierResult:
        """
        Label multiple trade signals.
        
        Args:
            signal_dates: List of trade entry dates
            prices: Close price series
            high: High price series
            low: Low price series
            atr: ATR series
            
        Returns:
            TripleBarrierResult with labels and statistics
        """
        events = []
        
        for date in signal_dates:
            event = self.label_single_trade(date, prices, high, low, atr)
            if event is not None:
                events.append(event)
        
        # Create labels and returns series
        if events:
            labels = pd.Series(
                {e.entry_date: e.label for e in events},
                name='label'
            )
            returns = pd.Series(
                {e.entry_date: e.return_pct for e in events},
                name='return'
            )
        else:
            labels = pd.Series(dtype=int)
            returns = pd.Series(dtype=float)
        
        # Calculate statistics
        n_profit = sum(1 for e in events if e.label == 1)
        n_stop = sum(1 for e in events if e.label == -1)
        n_time = sum(1 for e in events if e.label == 0)
        
        metadata = {
            'n_signals': len(signal_dates),
            'n_labeled': len(events),
            'n_profit': n_profit,
            'n_stop': n_stop,
            'n_time': n_time,
            'win_rate': n_profit / len(events) if events else 0,
            'avg_holding_days': np.mean([e.holding_days for e in events]) if events else 0,
            'avg_return': returns.mean() if len(returns) > 0 else 0,
        }
        
        return TripleBarrierResult(
            events=events,
            labels=labels,
            returns=returns,
            metadata=metadata
        )
    
    def get_binary_labels(
        self,
        result: TripleBarrierResult,
        min_return: float = 0.0
    ) -> pd.Series:
        """
        Convert triple barrier labels to binary (profit/no profit).
        
        Useful for training binary classifiers.
        
        Args:
            result: TripleBarrierResult from label_signals
            min_return: Minimum return to consider as profit
            
        Returns:
            Binary labels (1 = profit, 0 = not profit)
        """
        binary = pd.Series(0, index=result.labels.index)
        
        for event in result.events:
            if event.label == 1 or (event.label == 0 and event.return_pct >= min_return):
                binary[event.entry_date] = 1
        
        return binary


def demo():
    """Demonstrate triple barrier labeling."""
    print("=" * 60)
    print("Triple Barrier Method Demo")
    print("=" * 60)
    
    # Create sample price data
    np.random.seed(42)
    n = 252
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    # Random walk with drift
    close = 100 + np.cumsum(np.random.randn(n) * 1.0 + 0.05)
    high = close + np.abs(np.random.randn(n) * 0.5)
    low = close - np.abs(np.random.randn(n) * 0.5)
    
    prices = pd.Series(close, index=dates)
    high_series = pd.Series(high, index=dates)
    low_series = pd.Series(low, index=dates)
    
    # Generate sample signals (random for demo)
    signal_dates = np.random.choice(dates[10:-20], size=20, replace=False)
    signal_dates = sorted(signal_dates)
    
    print(f"Sample: {n} days, {len(signal_dates)} signals")
    
    # Label signals
    labeler = TripleBarrierLabeler(
        profit_take=0.05,
        stop_loss=0.03,
        max_holding_days=10
    )
    
    result = labeler.label_signals(signal_dates, prices, high_series, low_series)
    
    print(f"\nTriple Barrier Results:")
    print(f"  Signals labeled: {result.metadata['n_labeled']}")
    print(f"  Profit (label=1): {result.metadata['n_profit']}")
    print(f"  Stop (label=-1): {result.metadata['n_stop']}")
    print(f"  Time (label=0): {result.metadata['n_time']}")
    print(f"  Win rate: {result.metadata['win_rate']:.2%}")
    print(f"  Avg holding: {result.metadata['avg_holding_days']:.1f} days")
    print(f"  Avg return: {result.metadata['avg_return']:.2%}")
    
    # Get binary labels
    binary = labeler.get_binary_labels(result)
    print(f"\nBinary labels:")
    print(f"  Profit (1): {binary.sum()}")
    print(f"  Not profit (0): {(1 - binary).sum()}")


if __name__ == "__main__":
    demo()
