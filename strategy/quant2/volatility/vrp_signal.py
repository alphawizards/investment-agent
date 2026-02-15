"""
VRP Signal Module
=================
VIX-based signals for short volatility strategies.

Uses VIX index as proxy since options data is not freely available.

Features:
- VIX term structure (contango/backwardation via VIX vs VIX3M)
- VIX percentile (current level vs history)
- VIX mean reversion signals
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class VRPSignalResult:
    """Result from VRP signal generation."""
    signals: pd.DataFrame
    current_signal: str
    term_structure: str
    vix_percentile: float
    metadata: dict


class VRPSignal:
    """
    Volatility Risk Premium signal generator.
    
    Since options data is not freely available, this uses VIX index
    as a proxy for implied volatility and generates signals based on:
    
    1. VIX term structure (VIX vs VIX3M ratio)
    2. VIX percentile rank (current vs historical)
    3. VIX mean reversion (SMA crossover)
    
    Signals:
    - HARVEST: Conditions favorable for short volatility
    - NEUTRAL: No clear signal
    - HEDGE: Elevated volatility risk
    
    Attributes:
        vix_sma_period: SMA period for VIX
        high_percentile: Threshold for "high VIX"
        low_percentile: Threshold for "low VIX"
        lookback_days: Days for percentile calculation
    """
    
    def __init__(
        self,
        vix_sma_period: int = 21,
        high_percentile: float = 80,
        low_percentile: float = 30,
        lookback_days: int = 252
    ):
        """
        Initialize VRP Signal generator.
        
        Args:
            vix_sma_period: Period for VIX SMA
            high_percentile: Percentile above which VIX is "high"
            low_percentile: Percentile below which VIX is "low"
            lookback_days: Historical lookback for percentile
        """
        self.vix_sma_period = vix_sma_period
        self.high_percentile = high_percentile
        self.low_percentile = low_percentile
        self.lookback_days = lookback_days
    
    def calculate_percentile(
        self,
        vix: pd.Series
    ) -> pd.Series:
        """
        Calculate rolling percentile of VIX.
        
        Args:
            vix: VIX index series
            
        Returns:
            Percentile rank (0-100)
        """
        def percentile_rank(x):
            if len(x) < 10:
                return 50
            current = x.iloc[-1]
            return (x < current).sum() / len(x) * 100
        
        return vix.rolling(self.lookback_days).apply(percentile_rank)
    
    def calculate_term_structure(
        self,
        vix: pd.Series,
        vix3m: Optional[pd.Series] = None
    ) -> pd.Series:
        """
        Calculate VIX term structure (contango/backwardation).
        
        Contango (VIX < VIX3M): Normal, favorable for short vol
        Backwardation (VIX > VIX3M): Elevated risk, unfavorable
        
        Args:
            vix: Spot VIX
            vix3m: 3-month VIX (if available)
            
        Returns:
            Term structure ratio (< 1 = contango, > 1 = backwardation)
        """
        if vix3m is None:
            # Estimate from VIX SMA as proxy
            vix_smooth = vix.rolling(21).mean()
            return vix / vix_smooth
        
        return vix / vix3m
    
    def generate_signals(
        self,
        vix: pd.Series,
        vix3m: Optional[pd.Series] = None,
        spy_returns: Optional[pd.Series] = None
    ) -> VRPSignalResult:
        """
        Generate VRP signals.
        
        Decision rules:
        - HARVEST: VIX < 70th percentile AND in contango AND below SMA
        - HEDGE: VIX > 90th percentile OR in backwardation
        - NEUTRAL: Otherwise
        
        Args:
            vix: VIX index series
            vix3m: Optional VIX3M series
            spy_returns: Optional SPY returns for realized vol
            
        Returns:
            VRPSignalResult with signals and current state
        """
        signals = pd.DataFrame(index=vix.index)
        
        # Features
        signals['vix'] = vix
        signals['vix_sma'] = vix.rolling(self.vix_sma_period).mean()
        signals['vix_percentile'] = self.calculate_percentile(vix)
        signals['term_structure'] = self.calculate_term_structure(vix, vix3m)
        
        # Realized volatility (if SPY returns provided)
        if spy_returns is not None:
            signals['realized_vol'] = spy_returns.rolling(21).std() * np.sqrt(252) * 100
            signals['vrp'] = signals['vix'] - signals['realized_vol']
        
        # Signal logic
        def get_signal(row):
            if pd.isna(row['vix_percentile']) or pd.isna(row['term_structure']):
                return 'NEUTRAL'
            
            # HARVEST conditions
            if (row['vix_percentile'] < 70 and 
                row['term_structure'] < 1.05 and
                row['vix'] < row['vix_sma']):
                return 'HARVEST'
            
            # HEDGE conditions
            if (row['vix_percentile'] > 90 or 
                row['term_structure'] > 1.15):
                return 'HEDGE'
            
            return 'NEUTRAL'
        
        signals['signal'] = signals.apply(get_signal, axis=1)
        
        # Current state
        current = signals.iloc[-1] if len(signals) > 0 else {}
        
        # Determine term structure state
        term_ratio = current.get('term_structure', 1.0)
        if term_ratio < 0.95:
            term_state = 'CONTANGO'
        elif term_ratio > 1.05:
            term_state = 'BACKWARDATION'
        else:
            term_state = 'FLAT'
        
        metadata = {
            'n_observations': len(signals),
            'harvest_pct': (signals['signal'] == 'HARVEST').mean(),
            'hedge_pct': (signals['signal'] == 'HEDGE').mean(),
            'current_vix': current.get('vix', np.nan),
            'current_sma': current.get('vix_sma', np.nan),
        }
        
        return VRPSignalResult(
            signals=signals,
            current_signal=current.get('signal', 'NEUTRAL'),
            term_structure=term_state,
            vix_percentile=current.get('vix_percentile', 50),
            metadata=metadata
        )
    
    def get_recommendation(
        self,
        result: VRPSignalResult
    ) -> Dict:
        """
        Get actionable recommendation.
        
        Args:
            result: VRPSignalResult from generate_signals
            
        Returns:
            Dict with recommendation
        """
        signal = result.current_signal
        
        if signal == 'HARVEST':
            action = "SHORT VOLATILITY"
            description = "Conditions favor premium selling (Iron Condors, put spreads)"
            risk_level = "MODERATE"
        elif signal == 'HEDGE':
            action = "BUY TAIL PROTECTION"
            description = "Elevated risk - consider VIX calls or reducing exposure"
            risk_level = "HIGH"
        else:
            action = "WAIT"
            description = "No clear signal - avoid new volatility positions"
            risk_level = "NEUTRAL"
        
        return {
            'action': action,
            'description': description,
            'risk_level': risk_level,
            'vix_percentile': result.vix_percentile,
            'term_structure': result.term_structure,
            'signal': signal,
        }


def demo():
    """Demonstrate VRP signal generation."""
    print("=" * 60)
    print("VRP Signal Demo")
    print("=" * 60)
    
    # Create sample VIX data
    np.random.seed(42)
    n = 252
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    # Mean-reverting VIX simulation
    vix = pd.Series(index=dates, dtype=float)
    vix.iloc[0] = 15
    for i in range(1, n):
        vix.iloc[i] = max(10, min(40, 
            vix.iloc[i-1] + (15 - vix.iloc[i-1]) * 0.1 + np.random.randn() * 1.5
        ))
    
    print(f"Sample: {n} days of VIX data")
    print(f"VIX range: {vix.min():.1f} to {vix.max():.1f}")
    
    # Generate signals
    generator = VRPSignal()
    result = generator.generate_signals(vix)
    
    print(f"\nCurrent Signal: {result.current_signal}")
    print(f"Term Structure: {result.term_structure}")
    print(f"VIX Percentile: {result.vix_percentile:.0f}")
    
    print(f"\nSignal Distribution:")
    print(f"  HARVEST: {result.metadata['harvest_pct']:.1%}")
    print(f"  HEDGE: {result.metadata['hedge_pct']:.1%}")
    print(f"  NEUTRAL: {1 - result.metadata['harvest_pct'] - result.metadata['hedge_pct']:.1%}")
    
    # Get recommendation
    rec = generator.get_recommendation(result)
    print(f"\nRecommendation:")
    print(f"  Action: {rec['action']}")
    print(f"  {rec['description']}")
    print(f"  Risk Level: {rec['risk_level']}")


if __name__ == "__main__":
    demo()
