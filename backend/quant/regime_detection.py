"""
Regime Detection Module
=======================
Volatility regime detection for adaptive backtesting.

2025 Institutional Standard:
- Volatility-based regime classification
- Optional HMM-based regime detection
- Regime-adjusted cost modeling

Reference:
    Hamilton (1989), "A New Approach to Economic Analysis of Time Series"
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List
from enum import IntEnum
from dataclasses import dataclass


class VolatilityRegime(IntEnum):
    """Volatility regime classification."""
    LOW = 0      # VIX < 15: Low volatility, calm markets
    NORMAL = 1   # VIX 15-25: Normal market conditions
    HIGH = 2     # VIX 25-35: Elevated volatility
    CRISIS = 3   # VIX > 35: Crisis/panic levels


# Regime-dependent volatility multipliers for cost modeling
REGIME_VOL_MULTIPLIERS = {
    VolatilityRegime.LOW: 0.7,
    VolatilityRegime.NORMAL: 1.0,
    VolatilityRegime.HIGH: 1.8,
    VolatilityRegime.CRISIS: 3.0,
}


@dataclass
class RegimeDetectionResult:
    """Result from regime detection."""
    regimes: pd.Series
    regime_probs: Optional[pd.DataFrame]
    transitions: int
    regime_counts: dict
    mean_duration: dict


def detect_volatility_regime(
    returns: pd.Series,
    window: int = 21,
    annualization: int = 252,
    thresholds: Tuple[float, float, float] = (0.10, 0.18, 0.28)
) -> RegimeDetectionResult:
    """
    Detect volatility regime using rolling realized volatility.
    
    Simple threshold-based regime detection:
    - LOW: vol < threshold[0]
    - NORMAL: threshold[0] <= vol < threshold[1]
    - HIGH: threshold[1] <= vol < threshold[2]
    - CRISIS: vol >= threshold[2]
    
    Args:
        returns: Daily returns series
        window: Rolling window for volatility calculation
        annualization: Trading days per year
        thresholds: Tuple of (low/normal, normal/high, high/crisis) thresholds
        
    Returns:
        RegimeDetectionResult with regime classifications
    """
    # Calculate rolling volatility
    rolling_vol = returns.rolling(window=window).std() * np.sqrt(annualization)
    rolling_vol = rolling_vol.dropna()
    
    # Classify regimes
    regimes = pd.Series(index=rolling_vol.index, dtype=int)
    
    regimes[rolling_vol < thresholds[0]] = VolatilityRegime.LOW
    regimes[(rolling_vol >= thresholds[0]) & (rolling_vol < thresholds[1])] = VolatilityRegime.NORMAL
    regimes[(rolling_vol >= thresholds[1]) & (rolling_vol < thresholds[2])] = VolatilityRegime.HIGH
    regimes[rolling_vol >= thresholds[2]] = VolatilityRegime.CRISIS
    
    # Calculate statistics
    regime_counts = regimes.value_counts().to_dict()
    transitions = (regimes.diff() != 0).sum() - 1
    
    # Mean duration per regime
    mean_duration = {}
    for regime in VolatilityRegime:
        regime_mask = regimes == regime
        if regime_mask.any():
            # Count consecutive days in regime
            changes = regime_mask.diff().fillna(True)
            run_ids = changes.cumsum()
            run_lengths = regime_mask.groupby(run_ids).sum()
            run_lengths = run_lengths[run_lengths > 0]
            mean_duration[regime.name] = float(run_lengths.mean()) if len(run_lengths) > 0 else 0
        else:
            mean_duration[regime.name] = 0
    
    return RegimeDetectionResult(
        regimes=regimes,
        regime_probs=None,  # No probabilities for threshold method
        transitions=int(transitions),
        regime_counts={VolatilityRegime(k).name: v for k, v in regime_counts.items()},
        mean_duration=mean_duration
    )


def get_regime_vol_multiplier(regime: VolatilityRegime) -> float:
    """Get volatility multiplier for a regime."""
    return REGIME_VOL_MULTIPLIERS.get(regime, 1.0)


def calculate_regime_adjusted_costs(
    returns: pd.Series,
    base_cost_bps: float = 15.0,
    window: int = 21
) -> pd.Series:
    """
    Calculate regime-adjusted transaction costs.
    
    Higher volatility regimes = higher transaction costs due to:
    - Wider bid-ask spreads
    - Higher market impact
    - Reduced liquidity
    
    Args:
        returns: Daily returns series
        base_cost_bps: Base cost in basis points
        window: Window for regime detection
        
    Returns:
        pd.Series: Daily cost multipliers
    """
    result = detect_volatility_regime(returns, window=window)
    
    # Map regimes to multipliers
    multipliers = result.regimes.map(
        lambda r: REGIME_VOL_MULTIPLIERS.get(VolatilityRegime(r), 1.0)
    )
    
    # Calculate adjusted costs
    adjusted_costs_bps = multipliers * base_cost_bps
    
    return adjusted_costs_bps


def print_regime_summary(result: RegimeDetectionResult):
    """Print regime detection summary."""
    print("\n" + "=" * 50)
    print("REGIME DETECTION SUMMARY")
    print("=" * 50)
    
    print(f"\nTotal transitions: {result.transitions}")
    
    print(f"\n{'Regime':<15}{'Count':<10}{'%':<10}{'Avg Duration':<15}")
    print("-" * 50)
    
    total = sum(result.regime_counts.values())
    
    for regime_name, count in result.regime_counts.items():
        pct = count / total * 100 if total > 0 else 0
        duration = result.mean_duration.get(regime_name, 0)
        print(f"{regime_name:<15}{count:<10}{pct:<10.1f}{duration:<15.1f} days")
    
    print("-" * 50)


# =============================================================================
# OPTIONAL: HMM-BASED REGIME DETECTION
# =============================================================================

def detect_regimes_hmm(
    returns: pd.Series,
    n_regimes: int = 3,
    n_iter: int = 100
) -> RegimeDetectionResult:
    """
    Detect regimes using Hidden Markov Model.
    
    Requires hmmlearn: pip install hmmlearn
    
    Args:
        returns: Daily returns series
        n_regimes: Number of hidden states
        n_iter: Number of EM iterations
        
    Returns:
        RegimeDetectionResult with HMM-detected regimes
    """
    try:
        from hmmlearn.hmm import GaussianHMM
    except ImportError:
        raise ImportError(
            "HMM regime detection requires hmmlearn. "
            "Install with: pip install hmmlearn"
        )
    
    # Prepare data
    returns_clean = returns.dropna()
    X = returns_clean.values.reshape(-1, 1)
    
    # Fit HMM
    model = GaussianHMM(
        n_components=n_regimes,
        covariance_type="full",
        n_iter=n_iter,
        random_state=42
    )
    model.fit(X)
    
    # Predict states
    states = model.predict(X)
    
    # Get state probabilities
    probs = model.predict_proba(X)
    
    # Create results
    regimes = pd.Series(states, index=returns_clean.index)
    regime_probs = pd.DataFrame(
        probs, 
        index=returns_clean.index,
        columns=[f"regime_{i}" for i in range(n_regimes)]
    )
    
    # Calculate statistics
    regime_counts = regimes.value_counts().to_dict()
    transitions = (regimes.diff() != 0).sum() - 1
    
    # Sort regimes by volatility (mean absolute return)
    regime_vols = {}
    for i in range(n_regimes):
        mask = regimes == i
        if mask.any():
            regime_vols[i] = returns_clean[mask].std()
    
    # Mean duration
    mean_duration = {}
    for regime in range(n_regimes):
        regime_mask = regimes == regime
        if regime_mask.any():
            changes = regime_mask.diff().fillna(True)
            run_ids = changes.cumsum()
            run_lengths = regime_mask.groupby(run_ids).sum()
            run_lengths = run_lengths[run_lengths > 0]
            mean_duration[f"regime_{regime}"] = float(run_lengths.mean()) if len(run_lengths) > 0 else 0
        else:
            mean_duration[f"regime_{regime}"] = 0
    
    return RegimeDetectionResult(
        regimes=regimes,
        regime_probs=regime_probs,
        transitions=int(transitions),
        regime_counts={f"regime_{k}": v for k, v in regime_counts.items()},
        mean_duration=mean_duration
    )
