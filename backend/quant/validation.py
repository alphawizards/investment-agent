"""
Validation Module
=================
Statistical validation for backtesting results.

2025 Standard Implementation:
- Deflated Sharpe Ratio (DSR) for p-hacking detection
- Combinatorial Purged Cross-Validation (CPCV) - Phase 2
"""

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
from typing import Tuple, Optional


def calculate_dsr(
    returns: pd.Series, 
    total_trials: int = 1,
    annualization_factor: int = 252
) -> float:
    """
    Calculates Deflated Sharpe Ratio (DSR) to validate strategy robustness.
    
    The DSR corrects for:
    1. Selection bias (p-hacking) from multiple strategy trials
    2. Non-normality of returns (skewness and kurtosis)
    
    A DSR > 0.95 suggests the strategy is likely NOT a statistical artifact.
    
    Args:
        returns: Series of portfolio returns (daily)
        total_trials: Number of parameter combinations tested
        annualization_factor: Trading days per year (default: 252)
        
    Returns:
        float: DSR probability (0-1) that true Sharpe > 0
        
    Reference:
        Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio"
    """
    # Handle edge cases
    if len(returns) < 20:
        return 0.0
    
    returns_clean = returns.dropna()
    if len(returns_clean) < 20:
        return 0.0
    
    # 1. Calculate observed Sharpe Ratio (annualized)
    T = len(returns_clean)
    mean_return = returns_clean.mean()
    std_return = returns_clean.std()
    
    if std_return < 1e-10:
        return 0.0
    
    sr_obs = mean_return / std_return * np.sqrt(annualization_factor)
    
    # 2. Calculate higher moments
    sk = skew(returns_clean)
    kt = kurtosis(returns_clean)  # Excess kurtosis
    
    # 3. Estimate Expected Maximum Sharpe from random trials
    # Uses Euler-Mascheroni constant approximation
    gamma = 0.57721566  # Euler-Mascheroni constant
    
    if total_trials <= 1:
        sr_expected = 0
    else:
        # Expected max Sharpe from N independent trials of random strategies
        sr_expected = ((1 - gamma) * norm.ppf(1 - 1/total_trials) + 
                       gamma * norm.ppf(1 - 1/(total_trials * np.e)))
    
    # 4. Calculate DSR
    # Adjust for non-normality in the standard error
    numerator = (sr_obs - sr_expected) * np.sqrt(T - 1)
    
    # Corrected variance accounting for skewness and kurtosis
    variance_adjustment = 1 - sk * sr_obs + ((kt - 1) / 4) * sr_obs**2
    
    if variance_adjustment <= 0:
        variance_adjustment = 1e-6
    
    denominator = np.sqrt(variance_adjustment)
    
    # Return probability that true Sharpe > 0
    return float(norm.cdf(numerator / denominator))


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    annualization_factor: int = 252
) -> float:
    """
    Calculate annualized Sharpe Ratio.
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate (default: 0)
        annualization_factor: Trading days per year
        
    Returns:
        float: Annualized Sharpe Ratio
    """
    if len(returns) < 2:
        return 0.0
    
    excess_return = returns.mean() * annualization_factor - risk_free_rate
    volatility = returns.std() * np.sqrt(annualization_factor)
    
    if volatility < 1e-10:
        return 0.0
    
    return float(excess_return / volatility)


def validate_backtest_result(
    returns: pd.Series,
    total_trials: int = 1,
    dsr_threshold: float = 0.95
) -> Tuple[bool, dict]:
    """
    Validate a backtest result using 2025 institutional standards.
    
    Args:
        returns: Series of portfolio returns
        total_trials: Number of parameter combinations tested
        dsr_threshold: Minimum DSR for validation (default: 0.95)
        
    Returns:
        Tuple of (is_valid, metrics_dict)
    """
    sharpe = calculate_sharpe_ratio(returns)
    dsr = calculate_dsr(returns, total_trials=total_trials)
    
    metrics = {
        'sharpe_ratio': sharpe,
        'dsr': dsr,
        'total_trials': total_trials,
        'dsr_threshold': dsr_threshold,
        'n_observations': len(returns),
        'is_valid': dsr >= dsr_threshold
    }
    
    return metrics['is_valid'], metrics


# Alias for backward compatibility with kernels.py
calculate_deflated_sharpe = calculate_dsr


# =============================================================================
# COMBINATORIAL PURGED CROSS-VALIDATION (CPCV)
# =============================================================================

from typing import List, Iterator, Generator
from itertools import combinations


class CombinatorialPurgedKFold:
    """
    Combinatorial Purged K-Fold Cross-Validation (CPCV).
    
    2025 Institutional Standard for time-series backtesting.
    Prevents look-ahead bias through:
    1. Purging: Removing training samples that overlap with test period
    2. Embargo: Additional buffer after test period
    3. Combinatorial: Tests all C(n,k) combinations of folds
    
    Reference:
        Lopez de Prado (2018), "Advances in Financial Machine Learning", Ch. 7
    
    Example:
        >>> cpcv = CombinatorialPurgedKFold(n_splits=5, n_test_splits=2, purge_gap=5, embargo_pct=0.01)
        >>> for train_idx, test_idx in cpcv.split(price_data):
        ...     train = price_data.iloc[train_idx]
        ...     test = price_data.iloc[test_idx]
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        n_test_splits: int = 2,
        purge_gap: int = 5,
        embargo_pct: float = 0.01
    ):
        """
        Initialize CPCV splitter.
        
        Args:
            n_splits: Number of folds to divide data into
            n_test_splits: Number of folds to use for testing in each combination
            purge_gap: Number of samples to purge around test boundaries
            embargo_pct: Percentage of data to embargo after test period
        """
        if n_test_splits >= n_splits:
            raise ValueError("n_test_splits must be less than n_splits")
        
        self.n_splits = n_splits
        self.n_test_splits = n_test_splits
        self.purge_gap = purge_gap
        self.embargo_pct = embargo_pct
    
    def get_n_splits(self) -> int:
        """Return total number of train/test combinations."""
        from math import comb
        return comb(self.n_splits, self.n_test_splits)
    
    def split(
        self, 
        X: pd.DataFrame,
        y: pd.Series = None,
        groups: pd.Series = None
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate train/test indices for CPCV.
        
        Args:
            X: Feature DataFrame with DatetimeIndex
            y: Optional target (unused, for sklearn compatibility)
            groups: Optional groups (unused)
            
        Yields:
            Tuple of (train_indices, test_indices)
        """
        n_samples = len(X)
        indices = np.arange(n_samples)
        
        # Calculate fold boundaries
        fold_size = n_samples // self.n_splits
        fold_boundaries = [(i * fold_size, (i + 1) * fold_size) for i in range(self.n_splits)]
        
        # Adjust last fold to include remaining samples
        fold_boundaries[-1] = (fold_boundaries[-1][0], n_samples)
        
        # Calculate embargo size
        embargo_size = int(n_samples * self.embargo_pct)
        
        # Generate all combinations of test folds
        for test_fold_indices in combinations(range(self.n_splits), self.n_test_splits):
            # Get test indices
            test_indices = []
            for fold_idx in test_fold_indices:
                start, end = fold_boundaries[fold_idx]
                test_indices.extend(range(start, end))
            
            test_indices = np.array(test_indices)
            test_start = test_indices.min()
            test_end = test_indices.max()
            
            # Get train indices with purging and embargo
            train_indices = []
            
            for fold_idx in range(self.n_splits):
                if fold_idx in test_fold_indices:
                    continue
                
                start, end = fold_boundaries[fold_idx]
                
                for idx in range(start, end):
                    # Purge: skip samples too close to test boundaries
                    if abs(idx - test_start) < self.purge_gap:
                        continue
                    if abs(idx - test_end) < self.purge_gap:
                        continue
                    
                    # Embargo: skip samples just after test period
                    if test_end < idx <= test_end + embargo_size:
                        continue
                    
                    train_indices.append(idx)
            
            train_indices = np.array(train_indices)
            
            yield train_indices, test_indices
    
    def get_path_info(self) -> dict:
        """Return information about the CPCV configuration."""
        from math import comb
        return {
            'n_splits': self.n_splits,
            'n_test_splits': self.n_test_splits,
            'n_combinations': comb(self.n_splits, self.n_test_splits),
            'purge_gap': self.purge_gap,
            'embargo_pct': self.embargo_pct
        }


def run_cpcv_backtest(
    prices: pd.DataFrame,
    strategy_func: callable,
    strategy_params: dict,
    n_splits: int = 5,
    n_test_splits: int = 2,
    purge_gap: int = 5,
    embargo_pct: float = 0.01
) -> dict:
    """
    Run a strategy with CPCV validation.
    
    Args:
        prices: Price DataFrame (Time x Assets)
        strategy_func: Function(prices, **params) -> weights DataFrame
        strategy_params: Parameters to pass to strategy function
        n_splits: Number of folds
        n_test_splits: Number of test folds per combination
        purge_gap: Purge gap in samples
        embargo_pct: Embargo percentage
        
    Returns:
        dict with CPCV results and statistics
    """
    cpcv = CombinatorialPurgedKFold(
        n_splits=n_splits,
        n_test_splits=n_test_splits,
        purge_gap=purge_gap,
        embargo_pct=embargo_pct
    )
    
    fold_results = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(cpcv.split(prices)):
        # Get train and test data
        train_prices = prices.iloc[train_idx]
        test_prices = prices.iloc[test_idx]
        
        try:
            # Run strategy on training data to get weights
            train_weights = strategy_func(train_prices, **strategy_params)
            
            # Get the last weights from training for test period
            final_weights = train_weights.iloc[-1]
            
            # Calculate test returns
            test_returns = test_prices.pct_change().dropna()
            
            # Apply weights (static hold during test period)
            portfolio_returns = (test_returns * final_weights).sum(axis=1)
            
            # Calculate metrics
            sharpe = calculate_sharpe_ratio(portfolio_returns)
            total_return = (1 + portfolio_returns).prod() - 1
            
            fold_results.append({
                'fold': fold_idx,
                'train_size': len(train_idx),
                'test_size': len(test_idx),
                'sharpe': sharpe,
                'total_return': total_return,
                'portfolio_returns': portfolio_returns
            })
            
        except Exception as e:
            fold_results.append({
                'fold': fold_idx,
                'train_size': len(train_idx),
                'test_size': len(test_idx),
                'sharpe': np.nan,
                'total_return': np.nan,
                'error': str(e)
            })
    
    # Aggregate results
    valid_sharpes = [r['sharpe'] for r in fold_results if not np.isnan(r.get('sharpe', np.nan))]
    valid_returns = [r['total_return'] for r in fold_results if not np.isnan(r.get('total_return', np.nan))]
    
    return {
        'n_folds': len(fold_results),
        'n_valid': len(valid_sharpes),
        'mean_sharpe': np.mean(valid_sharpes) if valid_sharpes else np.nan,
        'std_sharpe': np.std(valid_sharpes) if valid_sharpes else np.nan,
        'mean_return': np.mean(valid_returns) if valid_returns else np.nan,
        'std_return': np.std(valid_returns) if valid_returns else np.nan,
        'fold_results': fold_results,
        'cpcv_config': cpcv.get_path_info()
    }

