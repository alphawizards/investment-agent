"""
Strategy Validation Module
==========================
Statistical validation tools for backtesting results.

Implements:
- Deflated Sharpe Ratio (DSR) - Combats multiple testing bias
- Probabilistic Sharpe Ratio (PSR) - Confidence in SR estimates

Source: "Advances in Financial Machine Learning" (2018), Chapters 13-14

Why This Matters:
-----------------
When testing many strategies, some will appear profitable by chance.
DSR adjusts the Sharpe Ratio to account for the number of trials,
giving the probability that the strategy's performance is genuine.
"""

import numpy as np
import scipy.stats as ss
from typing import Optional, Dict, Any
import pandas as pd


def estimated_sharpe_ratio(returns: pd.Series) -> float:
    """
    Calculate the standard Sharpe Ratio estimator.
    
    Args:
        returns: Series of returns
        
    Returns:
        Non-annualized Sharpe Ratio
    """
    if returns.std() == 0:
        return 0.0
    return returns.mean() / returns.std()


def annualized_sharpe_ratio(
    returns: pd.Series, 
    periods_per_year: int = 252
) -> float:
    """
    Annualize the Sharpe Ratio.
    
    Args:
        returns: Series of returns
        periods_per_year: Trading periods per year (252 for daily)
        
    Returns:
        Annualized Sharpe Ratio
    """
    return estimated_sharpe_ratio(returns) * np.sqrt(periods_per_year)


def sharpe_ratio_std(returns: pd.Series) -> float:
    """
    Standard deviation of the Sharpe Ratio estimator.
    
    Accounts for non-normal return distributions (skewness, kurtosis).
    
    Args:
        returns: Series of returns
        
    Returns:
        Standard deviation of SR estimator
    """
    n = len(returns)
    if n < 2:
        return np.inf
        
    skew = ss.skew(returns)
    kurt = ss.kurtosis(returns)  # Excess kurtosis
    
    # Formula from Bailey & Lopez de Prado (2012)
    sr_std = np.sqrt((1 + (0.5 * skew**2) - ((kurt - 3) / 4)) / (n - 1))
    return sr_std


def probabilistic_sharpe_ratio(
    observed_sr: float,
    benchmark_sr: float,
    std_sr: float
) -> float:
    """
    Probabilistic Sharpe Ratio (PSR).
    
    Probability that the true SR exceeds a benchmark given sampling error.
    
    Args:
        observed_sr: Observed Sharpe Ratio
        benchmark_sr: Benchmark SR to beat (e.g., 0 or risk-free)
        std_sr: Standard deviation of SR estimator
        
    Returns:
        Probability that true SR > benchmark
    """
    if std_sr == 0 or np.isinf(std_sr):
        return 0.5
        
    z = (observed_sr - benchmark_sr) / std_sr
    return ss.norm.cdf(z)


def expected_max_sharpe_ratio(
    n_trials: int,
    var_trials: float,
    skew: float = 0.0,
    kurt: float = 3.0
) -> float:
    """
    Expected maximum Sharpe Ratio from N independent trials.
    
    When testing many strategies, some will have high SR by luck.
    This estimates the expected maximum SR from random trials.
    
    Args:
        n_trials: Number of independent backtests performed
        var_trials: Variance of SR across trials (typically ~1)
        skew: Skewness of SR distribution
        kurt: Kurtosis of SR distribution
        
    Returns:
        Expected maximum SR from N random trials
    """
    emc = 0.5772156649  # Euler-Mascheroni constant
    
    # Expected max from N samples of standard normal
    sr_max = np.sqrt(var_trials) * (
        (1 - emc) * ss.norm.ppf(1 - 1/n_trials) + 
        emc * ss.norm.ppf(1 - 1/(n_trials * np.e))
    )
    
    return sr_max


def deflated_sharpe_ratio(
    observed_sr: float,
    n_trials: int,
    returns: pd.Series,
    var_trials: float = 1.0
) -> float:
    """
    Deflated Sharpe Ratio (DSR).
    
    Probability that the observed SR is significant after accounting
    for the multiple testing problem.
    
    Args:
        observed_sr: The strategy's observed Sharpe Ratio
        n_trials: Number of strategy variations tested
        returns: Series of returns (for skew/kurt calculation)
        var_trials: Variance of SR across trials (default: 1.0)
        
    Returns:
        DSR: Probability that SR is genuine (not due to overfitting)
        
    Interpretation:
        DSR > 0.95: Strong evidence of true alpha
        DSR > 0.90: Moderate evidence
        DSR < 0.80: Likely overfitting / data snooping
    """
    n_samples = len(returns)
    
    if n_samples < 10:
        return 0.0
    
    skew = ss.skew(returns)
    kurt = ss.kurtosis(returns) + 3  # Convert to excess kurtosis
    
    # Expected maximum SR given number of trials
    sr_expected = expected_max_sharpe_ratio(n_trials, var_trials, skew, kurt)
    
    # Standard deviation of SR estimator
    sr_std = sharpe_ratio_std(returns)
    
    # DSR = Probability that observed SR beats expected max from luck
    if sr_std == 0 or np.isinf(sr_std):
        return 0.0
        
    dsr = ss.norm.cdf((observed_sr - sr_expected) / sr_std)
    
    return dsr


def validate_backtest(
    returns: pd.Series,
    n_trials: int = 1,
    benchmark_sr: float = 0.0,
    risk_free_rate: float = 0.0
) -> Dict[str, Any]:
    """
    Comprehensive backtest validation report.
    
    Args:
        returns: Strategy returns series
        n_trials: Number of strategy variations tested
        benchmark_sr: Benchmark Sharpe Ratio
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Dictionary with validation metrics
    """
    # Adjust for risk-free rate
    if risk_free_rate > 0:
        daily_rf = (1 + risk_free_rate) ** (1/252) - 1
        excess_returns = returns - daily_rf
    else:
        excess_returns = returns
    
    # Core metrics
    sr = estimated_sharpe_ratio(excess_returns)
    sr_annual = annualized_sharpe_ratio(excess_returns)
    sr_std = sharpe_ratio_std(excess_returns)
    
    # Probabilistic metrics
    psr = probabilistic_sharpe_ratio(sr, benchmark_sr, sr_std)
    dsr = deflated_sharpe_ratio(sr, n_trials, excess_returns)
    
    # Distribution metrics
    skew = ss.skew(returns)
    kurt = ss.kurtosis(returns)
    
    return {
        'sharpe_ratio': sr,
        'sharpe_ratio_annual': sr_annual,
        'sharpe_ratio_std': sr_std,
        'probabilistic_sr': psr,
        'deflated_sr': dsr,
        'n_samples': len(returns),
        'n_trials': n_trials,
        'skewness': skew,
        'excess_kurtosis': kurt,
        'is_significant': dsr > 0.95,
        'confidence_level': 'HIGH' if dsr > 0.95 else 'MEDIUM' if dsr > 0.80 else 'LOW'
    }


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Demonstrate DSR calculation."""
    print("=" * 60)
    print("Deflated Sharpe Ratio Demo")
    print("=" * 60)
    
    # Generate sample returns
    np.random.seed(42)
    
    # Strategy 1: Genuine alpha (mean > 0)
    genuine_returns = pd.Series(np.random.normal(0.001, 0.02, 500))
    
    # Strategy 2: Lucky backtest (mean = 0, but sample has positive SR)
    lucky_returns = pd.Series(np.random.normal(0.0001, 0.02, 500))
    
    print("\n--- Strategy 1: Genuine Alpha ---")
    result1 = validate_backtest(genuine_returns, n_trials=1)
    print(f"Annualized SR: {result1['sharpe_ratio_annual']:.2f}")
    print(f"Deflated SR: {result1['deflated_sr']:.3f}")
    print(f"Confidence: {result1['confidence_level']}")
    
    print("\n--- Strategy 2: After Testing 100 Variations ---")
    result2 = validate_backtest(lucky_returns, n_trials=100)
    print(f"Annualized SR: {result2['sharpe_ratio_annual']:.2f}")
    print(f"Deflated SR: {result2['deflated_sr']:.3f}")
    print(f"Confidence: {result2['confidence_level']}")
    
    print("\n⚠️  Notice how DSR drops when accounting for multiple testing!")


if __name__ == "__main__":
    demo()
