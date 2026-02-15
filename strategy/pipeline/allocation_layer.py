"""
Allocation Layer
================
Portfolio optimization using Riskfolio-Lib.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Try to import riskfolio
try:
    import riskfolio as rp
    HAS_RISKFOLIO = True
except ImportError:
    HAS_RISKFOLIO = False
    print("Warning: riskfolio-lib not installed. Using fallback optimization.")


@dataclass
class AllocationConfig:
    """Configuration for allocation layer."""
    
    # Constraints
    MIN_WEIGHT: float = 0.02  # 2% minimum
    MAX_WEIGHT: float = 0.30  # 30% maximum
    
    # Risk parameters
    RISK_MEASURE: str = "MV"  # Mean-Variance
    RISK_FREE_RATE: float = 0.04
    
    # HRP parameters
    LINKAGE: str = "ward"
    CODEPENDENCE: str = "pearson"


@dataclass
class AllocationResult:
    """Result from allocation optimization."""
    strategy_name: str
    weights: pd.Series
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class AllocationManager:
    """
    Portfolio allocation manager with multiple optimization methods.
    
    Methods:
    - HRP (Hierarchical Risk Parity)
    - MVO (Mean-Variance Optimization)
    - ERC (Equal Risk Contribution)
    - Equal Weight
    - Inverse Volatility
    """
    
    def __init__(self, config: AllocationConfig = None):
        self.config = config or AllocationConfig()
        self._results: Dict[str, AllocationResult] = {}
    
    def optimize_hrp(
        self,
        returns: pd.DataFrame,
        signals: pd.DataFrame = None
    ) -> AllocationResult:
        """
        Hierarchical Risk Parity optimization.
        
        Args:
            returns: DataFrame of asset returns
            signals: Optional signal filter (1=include, 0=exclude)
            
        Returns:
            AllocationResult with optimal weights
        """
        # Filter assets based on signals
        if signals is not None:
            latest_signals = signals.iloc[-1]
            active_assets = latest_signals[latest_signals == 1].index.tolist()
            returns = returns[active_assets]
        
        if returns.empty or len(returns.columns) < 2:
            return self._equal_weight_fallback(returns.columns.tolist())
        
        if HAS_RISKFOLIO:
            try:
                # Build portfolio
                port = rp.HCPortfolio(returns=returns)
                
                # Optimize
                weights = port.optimization(
                    model='HRP',
                    codependence=self.config.CODEPENDENCE,
                    rm='MV',
                    rf=self.config.RISK_FREE_RATE,
                    linkage=self.config.LINKAGE,
                    leaf_order=True
                )
                
                if weights is not None and not weights.empty:
                    weights = weights.squeeze()
                    weights = self._apply_constraints(weights)
                    
                    # Calculate metrics
                    exp_return, exp_risk, sharpe = self._calculate_metrics(
                        returns, weights
                    )
                    
                    result = AllocationResult(
                        strategy_name="HRP",
                        weights=weights,
                        expected_return=exp_return,
                        expected_risk=exp_risk,
                        sharpe_ratio=sharpe,
                        metadata={'method': 'riskfolio-lib'}
                    )
                    
                    self._results['HRP'] = result
                    return result
            except Exception as e:
                print(f"HRP optimization error: {e}")
        
        # Fallback to inverse volatility
        return self.optimize_inverse_volatility(returns)
    
    def optimize_mvo(
        self,
        returns: pd.DataFrame,
        signals: pd.DataFrame = None,
        target_return: float = None
    ) -> AllocationResult:
        """
        Mean-Variance Optimization (Markowitz).
        
        Args:
            returns: DataFrame of asset returns
            signals: Optional signal filter
            target_return: Optional target return constraint
            
        Returns:
            AllocationResult with optimal weights
        """
        if signals is not None:
            latest_signals = signals.iloc[-1]
            active_assets = latest_signals[latest_signals == 1].index.tolist()
            returns = returns[active_assets]
        
        if returns.empty or len(returns.columns) < 2:
            return self._equal_weight_fallback(returns.columns.tolist())
        
        if HAS_RISKFOLIO:
            try:
                port = rp.Portfolio(returns=returns)
                port.assets_stats(method_mu='hist', method_cov='hist')
                
                weights = port.optimization(
                    model='Classic',
                    rm='MV',
                    obj='Sharpe',
                    rf=self.config.RISK_FREE_RATE,
                    hist=True
                )
                
                if weights is not None and not weights.empty:
                    weights = weights.squeeze()
                    weights = self._apply_constraints(weights)
                    
                    exp_return, exp_risk, sharpe = self._calculate_metrics(
                        returns, weights
                    )
                    
                    result = AllocationResult(
                        strategy_name="MVO",
                        weights=weights,
                        expected_return=exp_return,
                        expected_risk=exp_risk,
                        sharpe_ratio=sharpe,
                        metadata={'method': 'riskfolio-lib', 'target': target_return}
                    )
                    
                    self._results['MVO'] = result
                    return result
            except Exception as e:
                print(f"MVO optimization error: {e}")
        
        return self.optimize_inverse_volatility(returns)
    
    def optimize_inverse_volatility(
        self,
        returns: pd.DataFrame
    ) -> AllocationResult:
        """
        Inverse Volatility weighting.
        
        Simple, robust alternative when optimization fails.
        """
        # Calculate volatility
        volatility = returns.std() * np.sqrt(252)
        
        # Inverse volatility weights
        inv_vol = 1 / volatility.replace(0, np.nan)
        weights = inv_vol / inv_vol.sum()
        weights = weights.fillna(0)
        weights = self._apply_constraints(weights)
        
        exp_return, exp_risk, sharpe = self._calculate_metrics(returns, weights)
        
        result = AllocationResult(
            strategy_name="InverseVol",
            weights=weights,
            expected_return=exp_return,
            expected_risk=exp_risk,
            sharpe_ratio=sharpe,
            metadata={'method': 'inverse_volatility'}
        )
        
        self._results['InverseVol'] = result
        return result
    
    def optimize_equal_weight(
        self,
        assets: List[str]
    ) -> AllocationResult:
        """Equal weight allocation."""
        n = len(assets)
        if n == 0:
            return AllocationResult(
                strategy_name="EqualWeight",
                weights=pd.Series(dtype=float),
                expected_return=0,
                expected_risk=0,
                sharpe_ratio=0,
                metadata={'method': 'equal_weight'}
            )
        
        weights = pd.Series(1/n, index=assets)
        
        result = AllocationResult(
            strategy_name="EqualWeight",
            weights=weights,
            expected_return=0,
            expected_risk=0,
            sharpe_ratio=0,
            metadata={'method': 'equal_weight', 'n_assets': n}
        )
        
        self._results['EqualWeight'] = result
        return result
    
    def _apply_constraints(self, weights: pd.Series) -> pd.Series:
        """Apply min/max weight constraints."""
        # Clip to constraints
        weights = weights.clip(lower=self.config.MIN_WEIGHT, upper=self.config.MAX_WEIGHT)
        
        # Remove very small weights
        weights[weights < self.config.MIN_WEIGHT] = 0
        
        # Renormalize
        if weights.sum() > 0:
            weights = weights / weights.sum()
        
        return weights
    
    def _calculate_metrics(
        self,
        returns: pd.DataFrame,
        weights: pd.Series
    ) -> tuple:
        """Calculate expected return, risk, and Sharpe."""
        # Align weights with returns
        common = weights.index.intersection(returns.columns)
        weights = weights[common]
        returns = returns[common]
        
        if len(common) == 0:
            return 0, 0, 0
        
        # Portfolio returns
        port_returns = (returns * weights).sum(axis=1)
        
        # Annualized metrics
        exp_return = port_returns.mean() * 252
        exp_risk = port_returns.std() * np.sqrt(252)
        
        if exp_risk > 0:
            sharpe = (exp_return - self.config.RISK_FREE_RATE) / exp_risk
        else:
            sharpe = 0
        
        return exp_return, exp_risk, sharpe
    
    def _equal_weight_fallback(self, assets: List[str]) -> AllocationResult:
        """Fallback to equal weight when optimization fails."""
        return self.optimize_equal_weight(assets)
    
    def get_latest_allocation(self, strategy_name: str) -> Optional[AllocationResult]:
        """Get the most recent allocation for a strategy."""
        return self._results.get(strategy_name)


# =============================================================================
# SCIPY-BASED UTILITY OPTIMIZATION WITH TURNOVER COSTS
# =============================================================================

from scipy.optimize import minimize


def optimize_utility_with_costs(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    current_weights: np.ndarray = None,
    lambda_risk: float = 1.0,
    cost_bps: float = 10.0,
    min_weight: float = 0.0,
    max_weight: float = 1.0
) -> np.ndarray:
    """
    Optimize portfolio weights with explicit transaction cost penalty.
    
    Maximizes: Expected Return - λ * Risk - Transaction Costs
    
    This is critical for small accounts where trading costs matter.
    
    Args:
        expected_returns: Array of expected returns for each asset
        cov_matrix: Covariance matrix of returns
        current_weights: Current portfolio weights (for turnover calc)
        lambda_risk: Risk aversion coefficient (higher = more conservative)
        cost_bps: Transaction cost in basis points per unit turnover
        min_weight: Minimum weight per asset (default: 0 = long only)
        max_weight: Maximum weight per asset (default: 1)
        
    Returns:
        Optimal portfolio weights as numpy array
        
    Example:
        >>> returns = np.array([0.08, 0.12, 0.06])  # 8%, 12%, 6% expected
        >>> cov = np.array([[0.04, 0.01, 0.005],
        ...                 [0.01, 0.09, 0.01],
        ...                 [0.005, 0.01, 0.02]])
        >>> current = np.array([0.33, 0.33, 0.34])
        >>> optimal = optimize_utility_with_costs(returns, cov, current)
    """
    n = len(expected_returns)
    
    # Initialize with current weights or equal weight
    if current_weights is None:
        w0 = np.ones(n) / n
    else:
        w0 = np.array(current_weights)
    
    # Convert cost from bps to decimal
    cost_decimal = cost_bps / 10000.0
    
    def objective(w):
        # 1. Portfolio Expected Return
        ret = np.dot(w, expected_returns)
        
        # 2. Portfolio Variance (Risk)
        risk = np.dot(w.T, np.dot(cov_matrix, w))
        
        # 3. Transaction Costs (L1 norm of weight change)
        turnover = np.sum(np.abs(w - w0))
        cost = turnover * cost_decimal
        
        # Maximize Utility = Return - λ*Risk - Cost
        # Minimize negative utility
        utility = ret - (lambda_risk * risk) - cost
        return -utility
    
    # Constraints: Fully invested (weights sum to 1)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    
    # Bounds: Long only (or custom min/max)
    bounds = tuple((min_weight, max_weight) for _ in range(n))
    
    # Optimize using SLSQP (Sequential Least Squares Programming)
    result = minimize(
        objective, 
        w0, 
        method='SLSQP', 
        bounds=bounds, 
        constraints=constraints,
        options={'maxiter': 1000, 'ftol': 1e-9}
    )
    
    if not result.success:
        print(f"⚠️ Optimization warning: {result.message}")
    
    return result.x


def calculate_optimal_weights_with_costs(
    returns: pd.DataFrame,
    current_weights: pd.Series = None,
    lambda_risk: float = 1.0,
    cost_bps: float = 10.0,
    lookback: int = 252
) -> pd.Series:
    """
    Convenience function: Calculate cost-aware optimal weights from returns.
    
    Args:
        returns: DataFrame of asset returns
        current_weights: Current portfolio weights
        lambda_risk: Risk aversion
        cost_bps: Transaction cost in basis points
        lookback: Lookback period for covariance estimation
        
    Returns:
        Optimal weights as pandas Series
    """
    # Use most recent data for estimation
    recent_returns = returns.iloc[-lookback:]
    
    # Expected returns (annualized mean)
    expected_returns = recent_returns.mean() * 252
    
    # Covariance matrix (annualized)
    cov_matrix = recent_returns.cov() * 252
    
    # Convert to numpy
    assets = returns.columns.tolist()
    exp_ret_arr = expected_returns.values
    cov_arr = cov_matrix.values
    
    if current_weights is not None:
        curr_w = current_weights.reindex(assets, fill_value=0).values
    else:
        curr_w = None
    
    # Optimize
    optimal_w = optimize_utility_with_costs(
        exp_ret_arr,
        cov_arr,
        curr_w,
        lambda_risk=lambda_risk,
        cost_bps=cost_bps
    )
    
    return pd.Series(optimal_w, index=assets)


def calculate_rebalance_trades(
    current_weights: pd.Series,
    target_weights: pd.Series,
    portfolio_value: float,
    min_trade_pct: float = 0.01
) -> pd.DataFrame:
    """
    Calculate trades needed to rebalance portfolio.
    
    Args:
        current_weights: Current portfolio weights
        target_weights: Target portfolio weights
        portfolio_value: Total portfolio value
        min_trade_pct: Minimum trade size as % of portfolio
        
    Returns:
        DataFrame with trades (ticker, action, shares, value)
    """
    # Align indices
    all_assets = current_weights.index.union(target_weights.index)
    current = current_weights.reindex(all_assets, fill_value=0)
    target = target_weights.reindex(all_assets, fill_value=0)
    
    # Calculate differences
    diff = target - current
    
    # Filter small trades
    diff = diff[abs(diff) >= min_trade_pct]
    
    trades = []
    for ticker, weight_diff in diff.items():
        value = weight_diff * portfolio_value
        action = 'BUY' if weight_diff > 0 else 'SELL'
        
        trades.append({
            'ticker': ticker,
            'action': action,
            'weight_change': round(weight_diff * 100, 2),
            'value': round(abs(value), 2)
        })
    
    return pd.DataFrame(trades)
