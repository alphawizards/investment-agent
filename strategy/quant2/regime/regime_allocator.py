"""
Regime Allocator
================
Dynamic portfolio allocation based on regime probabilities.

Implements the formula from the Enhancement Report:
    W_strategy = Σ P(Regime) × W(Strategy|Regime)

This creates smooth transitions between strategy allocations
based on HMM-detected regime probabilities.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

from .hmm_detector import HMMRegimeDetector, RegimeDetectionResult, MarketRegime


@dataclass
class AllocationResult:
    """Result from regime-based allocation."""
    weights: pd.Series
    regime_contributions: Dict[str, pd.Series]
    current_regime: str
    regime_probabilities: Dict[str, float]
    metadata: dict


class RegimeAllocator:
    """
    Regime-based dynamic allocation manager.
    
    Maps strategies to regimes and blends allocations based on
    regime probabilities from HMM detection.
    
    Default strategy-regime affinity matrix:
    
    | Strategy         | BULL | BEAR | CHOP |
    |------------------|------|------|------|
    | Residual Momentum| 0.40 | 0.05 | 0.15 |
    | Stat Arb         | 0.20 | 0.15 | 0.40 |
    | Short Volatility | 0.25 | 0.00 | 0.30 |
    | Cash             | 0.15 | 0.80 | 0.15 |
    
    Attributes:
        regime_detector: HMMRegimeDetector instance
        affinity_matrix: Strategy allocations per regime
    """
    
    # Default affinity matrix
    DEFAULT_AFFINITY = {
        'BULL': {
            'residual_momentum': 0.40,
            'stat_arb': 0.20,
            'short_volatility': 0.25,
            'cash': 0.15,
        },
        'BEAR': {
            'residual_momentum': 0.05,
            'stat_arb': 0.15,
            'short_volatility': 0.00,
            'cash': 0.80,
        },
        'CHOP': {
            'residual_momentum': 0.15,
            'stat_arb': 0.40,
            'short_volatility': 0.30,
            'cash': 0.15,
        },
    }
    
    def __init__(
        self,
        regime_detector: Optional[HMMRegimeDetector] = None,
        affinity_matrix: Optional[Dict[str, Dict[str, float]]] = None,
        smooth_window: int = 5
    ):
        """
        Initialize Regime Allocator.
        
        Args:
            regime_detector: Pre-configured HMMRegimeDetector (creates new if None)
            affinity_matrix: Custom strategy-regime affinity (uses default if None)
            smooth_window: Rolling window for probability smoothing
        """
        self.regime_detector = regime_detector or HMMRegimeDetector(n_regimes=3)
        self.affinity_matrix = affinity_matrix or self.DEFAULT_AFFINITY
        self.smooth_window = smooth_window
        
        # Validate affinity matrix sums to 1.0 per regime
        self._validate_affinity_matrix()
    
    def _validate_affinity_matrix(self):
        """Ensure affinity matrix rows sum to 1.0."""
        for regime, allocations in self.affinity_matrix.items():
            total = sum(allocations.values())
            if not np.isclose(total, 1.0, atol=0.01):
                raise ValueError(
                    f"Affinity matrix for regime {regime} sums to {total}, not 1.0"
                )
    
    def _smooth_probabilities(
        self,
        probabilities: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Apply rolling window smoothing to probabilities.
        
        Reduces whipsaw from noisy regime transitions.
        
        Args:
            probabilities: DataFrame of regime probabilities
            
        Returns:
            Smoothed probabilities (still sum to 1.0)
        """
        smoothed = probabilities.rolling(
            self.smooth_window, 
            min_periods=1
        ).mean()
        
        # Renormalize to ensure sum = 1.0
        row_sums = smoothed.sum(axis=1)
        smoothed = smoothed.div(row_sums, axis=0)
        
        return smoothed
    
    def calculate_blended_weights(
        self,
        regime_probs: Dict[str, float]
    ) -> pd.Series:
        """
        Calculate blended strategy weights from regime probabilities.
        
        Formula: W_strategy = Σ P(Regime) × W(Strategy|Regime)
        
        Args:
            regime_probs: Dict of {regime: probability}
            
        Returns:
            Series of strategy weights
        """
        strategies = set()
        for allocs in self.affinity_matrix.values():
            strategies.update(allocs.keys())
        
        weights = pd.Series(0.0, index=sorted(strategies))
        
        for regime, prob in regime_probs.items():
            if regime in self.affinity_matrix:
                for strategy, weight in self.affinity_matrix[regime].items():
                    weights[strategy] += prob * weight
        
        return weights
    
    def allocate(
        self,
        returns: pd.Series,
        volume: Optional[pd.Series] = None,
        smooth: bool = True
    ) -> AllocationResult:
        """
        Calculate regime-based allocation.
        
        Args:
            returns: Series of returns for regime detection
            volume: Optional volume series
            smooth: Whether to smooth regime probabilities
            
        Returns:
            AllocationResult with blended weights
        """
        # Detect regimes
        regime_result = self.regime_detector.detect(returns, volume)
        
        # Get current probabilities
        current_probs = regime_result.probabilities.iloc[-1].to_dict()
        
        # Optionally smooth
        if smooth:
            smoothed_probs = self._smooth_probabilities(regime_result.probabilities)
            current_probs = smoothed_probs.iloc[-1].to_dict()
        
        # Calculate blended weights
        weights = self.calculate_blended_weights(current_probs)
        
        # Calculate contribution from each regime
        contributions = {}
        for regime, prob in current_probs.items():
            if regime in self.affinity_matrix:
                regime_weights = pd.Series(self.affinity_matrix[regime])
                contributions[regime] = regime_weights * prob
        
        metadata = {
            'detection_method': regime_result.metadata['method'],
            'n_observations': regime_result.metadata['n_observations'],
            'current_regime': regime_result.metadata['current_regime'],
            'smoothing_applied': smooth,
            'smooth_window': self.smooth_window if smooth else None,
        }
        
        return AllocationResult(
            weights=weights,
            regime_contributions=contributions,
            current_regime=regime_result.metadata['current_regime'],
            regime_probabilities=current_probs,
            metadata=metadata
        )
    
    def calculate_rolling_allocations(
        self,
        returns: pd.Series,
        volume: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        Calculate rolling regime-based allocations over time.
        
        Args:
            returns: Series of returns
            volume: Optional volume series
            
        Returns:
            DataFrame of strategy weights over time
        """
        # Detect regimes for full period
        regime_result = self.regime_detector.detect(returns, volume)
        
        # Smooth probabilities
        smoothed_probs = self._smooth_probabilities(regime_result.probabilities)
        
        # Calculate allocations for each date
        allocations = []
        
        for date in smoothed_probs.index:
            probs = smoothed_probs.loc[date].to_dict()
            weights = self.calculate_blended_weights(probs)
            weights.name = date
            allocations.append(weights)
        
        return pd.DataFrame(allocations)
    
    def get_recommendation(
        self,
        returns: pd.Series,
        volume: Optional[pd.Series] = None
    ) -> Dict:
        """
        Get current allocation recommendation.
        
        Args:
            returns: Recent returns series
            volume: Optional volume series
            
        Returns:
            Dict with recommendation details
        """
        result = self.allocate(returns, volume)
        
        # Determine dominant strategy
        dominant_strategy = result.weights.idxmax()
        dominant_weight = result.weights.max()
        
        return {
            'current_regime': result.current_regime,
            'regime_probabilities': result.regime_probabilities,
            'recommended_allocation': result.weights.to_dict(),
            'dominant_strategy': dominant_strategy,
            'dominant_weight': dominant_weight,
            'action': f"Allocate {dominant_weight:.0%} to {dominant_strategy}",
        }


def demo():
    """Demonstrate regime allocator."""
    print("=" * 60)
    print("Regime Allocator Demo")
    print("=" * 60)
    
    # Create sample returns
    np.random.seed(42)
    n = 300
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    # Simulate regime-switching
    returns = pd.Series(index=dates, dtype=float)
    returns.iloc[:100] = np.random.randn(100) * 0.01 + 0.001  # Bull
    returns.iloc[100:200] = np.random.randn(100) * 0.02 - 0.001  # Bear
    returns.iloc[200:] = np.random.randn(100) * 0.015  # Chop
    
    print(f"Sample: {n} days of returns")
    
    # Run regime allocation
    allocator = RegimeAllocator()
    result = allocator.allocate(returns)
    
    print(f"\nCurrent regime: {result.current_regime}")
    print(f"Detection method: {result.metadata['detection_method']}")
    
    print("\nRegime probabilities:")
    for regime, prob in result.regime_probabilities.items():
        print(f"  {regime}: {prob:.2%}")
    
    print("\nBlended allocation:")
    for strategy, weight in result.weights.items():
        print(f"  {strategy}: {weight:.2%}")
    
    # Get recommendation
    rec = allocator.get_recommendation(returns)
    print(f"\nRecommendation: {rec['action']}")


if __name__ == "__main__":
    demo()
