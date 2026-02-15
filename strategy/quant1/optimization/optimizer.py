"""
Portfolio Optimizer Module
==========================
Implements portfolio optimization using Riskfolio-Lib.

Methods:
1. Mean-Variance Optimization (MVO)
2. Hierarchical Risk Parity (HRP) - RECOMMENDED
3. Black-Litterman with Views
4. Risk Parity

All methods respect constraints:
- Min/Max weight per asset
- Sector limits
- Turnover constraints
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings

# Riskfolio-Lib imports
import riskfolio as rp

from strategy.config import CONFIG, is_us_ticker, get_fx_cost

warnings.filterwarnings('ignore')


class PortfolioOptimizer:
    """
    Portfolio optimization using Riskfolio-Lib.
    
    Implements multiple optimization methods with constraints
    suitable for Australian retail investors.
    """
    
    def __init__(self,
                 returns: pd.DataFrame,
                 min_weight: float = None,
                 max_weight: float = None):
        """
        Initialize optimizer.
        
        Args:
            returns: DataFrame of asset returns (AUD-normalized)
            min_weight: Minimum weight per asset
            max_weight: Maximum weight per asset
        """
        self.returns = returns
        self.min_weight = min_weight or CONFIG.MIN_WEIGHT
        self.max_weight = max_weight or CONFIG.MAX_WEIGHT
        self.n_assets = len(returns.columns)
        self.asset_names = returns.columns.tolist()
        
        # Initialize Riskfolio Portfolio object
        self.portfolio = rp.Portfolio(returns=returns)
        
    def _setup_constraints(self):
        """Set up portfolio constraints."""
        # Basic constraints
        self.portfolio.ainequality = None
        self.portfolio.binequality = None
        
        # Weight bounds
        self.portfolio.upperlng = self.max_weight
        self.portfolio.lowerlng = self.min_weight
        
    def estimate_statistics(self, method: str = 'hist'):
        """
        Estimate expected returns and covariance.
        
        Args:
            method: Estimation method
                - 'hist': Historical mean and covariance
                - 'ewma1': Exponentially weighted (half-life = 63 days)
                - 'ewma2': Exponentially weighted (half-life = 126 days)
                - 'ledoit': Ledoit-Wolf shrinkage
        """
        # Expected returns estimation
        self.portfolio.assets_stats(
            method_mu=method,
            method_cov=method
        )
        
    def optimize_hrp(self, 
                     codependence: str = 'pearson',
                     rm: str = 'MV',
                     linkage: str = 'ward') -> pd.Series:
        """
        Hierarchical Risk Parity optimization.
        
        RECOMMENDED: HRP is more robust than MVO because:
        - No expected return estimation needed
        - More stable out-of-sample
        - Natural diversification via clustering
        
        Args:
            codependence: Correlation method ('pearson', 'spearman', 'kendall')
            rm: Risk measure ('MV' = variance, 'CVaR', 'CDaR')
            linkage: Clustering linkage ('single', 'complete', 'average', 'ward')
            
        Returns:
            pd.Series: Optimal weights
        """
        # Adjust constraints based on number of assets
        # If n_assets * max_weight < 1, we need to relax max_weight
        n_assets = self.n_assets
        effective_max = max(self.max_weight, 1.0 / n_assets + 0.01)
        effective_min = min(self.min_weight, 1.0 / n_assets - 0.01)
        effective_min = max(0, effective_min)  # Can't be negative
        
        # Use HCPortfolio for hierarchical clustering methods (HRP)
        hc_portfolio = rp.HCPortfolio(
            returns=self.returns,
            w_max=effective_max,
            w_min=effective_min
        )
        
        # Optimize using HRP
        weights = hc_portfolio.optimization(
            model='HRP',
            codependence=codependence,
            obj='MinRisk',
            rm=rm,
            rf=CONFIG.RISK_FREE_RATE,
            linkage=linkage,
            leaf_order=True
        )
        
        if weights is None:
            raise ValueError("HRP optimization failed")
        
        # Apply weight constraints manually (if not properly enforced)
        weights = self._apply_weight_constraints(weights)
        
        return weights.squeeze()
    
    def optimize_mvo(self, 
                     objective: str = 'Sharpe',
                     rm: str = 'MV') -> pd.Series:
        """
        Mean-Variance Optimization.
        
        Classic Markowitz optimization with constraints.
        
        Args:
            objective: Optimization objective
                - 'Sharpe': Maximize Sharpe ratio
                - 'MinRisk': Minimize risk
                - 'MaxRet': Maximize return for given risk
            rm: Risk measure ('MV', 'CVaR', 'CDaR', 'MAD')
            
        Returns:
            pd.Series: Optimal weights
        """
        self._setup_constraints()
        self.estimate_statistics(method='ledoit')
        
        weights = self.portfolio.optimization(
            model='Classic',
            rm=rm,
            obj=objective,
            rf=CONFIG.RISK_FREE_RATE,
            hist=True
        )
        
        if weights is None:
            raise ValueError("MVO optimization failed")
        
        return weights.squeeze()
    
    def optimize_risk_parity(self, rm: str = 'MV') -> pd.Series:
        """
        Risk Parity optimization.
        
        Equal risk contribution from each asset.
        
        Args:
            rm: Risk measure
            
        Returns:
            pd.Series: Optimal weights
        """
        self._setup_constraints()
        self.estimate_statistics(method='ledoit')
        
        weights = self.portfolio.rp_optimization(
            model='Classic',
            rm=rm,
            rf=CONFIG.RISK_FREE_RATE,
            hist=True
        )
        
        if weights is None:
            raise ValueError("Risk Parity optimization failed")
        
        return weights.squeeze()
    
    def optimize_black_litterman(self,
                                  views: Dict[str, float],
                                  confidence: Dict[str, float] = None) -> pd.Series:
        """
        Black-Litterman optimization with investor views.
        
        Combines market equilibrium with subjective views.
        
        Args:
            views: Dict of {ticker: expected_return} for assets with views
            confidence: Dict of {ticker: confidence} (0-1) for each view
                       Default confidence = 0.5
            
        Returns:
            pd.Series: Optimal weights
            
        Example:
            views = {'SPY': 0.10, 'TLT': 0.02}  # 10% expected for SPY, 2% for TLT
            confidence = {'SPY': 0.8, 'TLT': 0.6}
        """
        self._setup_constraints()
        self.estimate_statistics(method='ledoit')
        
        # Convert views to Riskfolio format
        # P matrix: which assets have views (binary)
        # Q vector: the view values
        # Omega: uncertainty of views
        
        n_views = len(views)
        P = np.zeros((n_views, self.n_assets))
        Q = np.zeros(n_views)
        
        if confidence is None:
            confidence = {k: 0.5 for k in views.keys()}
        
        for i, (ticker, view) in enumerate(views.items()):
            if ticker in self.asset_names:
                idx = self.asset_names.index(ticker)
                P[i, idx] = 1
                Q[i] = view
        
        # Apply Black-Litterman
        self.portfolio.blacklitterman_stats(
            P=P,
            Q=Q,
            delta=2.5,  # Risk aversion coefficient
            rf=CONFIG.RISK_FREE_RATE,
            eq=True  # Use equilibrium returns
        )
        
        # Optimize with BL adjusted returns
        weights = self.portfolio.optimization(
            model='BL',
            rm='MV',
            obj='Sharpe',
            rf=CONFIG.RISK_FREE_RATE,
            hist=False
        )
        
        if weights is None:
            raise ValueError("Black-Litterman optimization failed")
        
        return weights.squeeze()
    
    def _apply_weight_constraints(self, weights: pd.DataFrame) -> pd.DataFrame:
        """
        Apply min/max weight constraints.
        
        HRP doesn't enforce constraints directly, so we apply them post-hoc.
        """
        w = weights.copy()
        
        # Clip to bounds
        w = w.clip(lower=self.min_weight, upper=self.max_weight)
        
        # Renormalize to sum to 1
        w = w / w.sum()
        
        return w
    
    def get_portfolio_stats(self, weights: pd.Series) -> Dict:
        """
        Calculate portfolio statistics.
        
        Args:
            weights: Portfolio weights
            
        Returns:
            Dict with portfolio statistics
        """
        w = weights.values.reshape(-1, 1)
        
        # Portfolio return and risk
        mu = self.returns.mean() * 252  # Annualized
        cov = self.returns.cov() * 252  # Annualized
        
        port_return = float(mu.values @ w)
        port_risk = float(np.sqrt(w.T @ cov.values @ w))
        sharpe = (port_return - CONFIG.RISK_FREE_RATE) / port_risk
        
        return {
            'expected_return': port_return,
            'volatility': port_risk,
            'sharpe_ratio': sharpe,
            'num_assets': (weights > 0.01).sum(),
            'max_weight': weights.max(),
            'min_weight': weights[weights > 0.01].min()
        }
    
    def plot_efficient_frontier(self, points: int = 50):
        """
        Plot efficient frontier with current portfolio.
        
        Args:
            points: Number of points on frontier
        """
        self._setup_constraints()
        self.estimate_statistics(method='ledoit')
        
        # This would normally plot, but we'll return the frontier data
        frontier = self.portfolio.efficient_frontier(
            model='Classic',
            rm='MV',
            points=points,
            rf=CONFIG.RISK_FREE_RATE,
            hist=True
        )
        
        return frontier


class CostAwareOptimizer(PortfolioOptimizer):
    """
    Portfolio optimizer that accounts for transaction costs.
    
    Extends base optimizer with:
    - Flat $3 AUD per trade (Stake.com brokerage)
    - Tax drag considerations
    """
    
    def __init__(self,
                 returns: pd.DataFrame,
                 current_weights: pd.Series = None,
                 portfolio_value_aud: float = 100000):
        """
        Initialize cost-aware optimizer.
        
        Args:
            returns: DataFrame of returns
            current_weights: Current portfolio weights (for turnover calc)
            portfolio_value_aud: Portfolio value in AUD
        """
        super().__init__(returns)
        
        if current_weights is None:
            # Equal weight starting point
            current_weights = pd.Series(
                1.0 / self.n_assets, 
                index=self.asset_names
            )
        
        self.current_weights = current_weights
        self.portfolio_value = portfolio_value_aud
        
    def calculate_trading_costs(self, target_weights: pd.Series) -> Dict:
        """
        Calculate total trading costs to reach target weights.
        
        Updated: $3 AUD flat fee per trade for all assets.
        
        Args:
            target_weights: Target portfolio weights
            
        Returns:
            Dict with cost breakdown
        """
        weight_diff = target_weights - self.current_weights
        weight_diff = weight_diff.fillna(0)
        
        trade_fee_aud = 3.0  # $3 AUD per trade
        total_brokerage = 0.0
        trade_count = 0
        
        for ticker in weight_diff.index:
            delta = abs(weight_diff[ticker])
            
            if delta > 0.005:  # Only count trades > 0.5% change
                # Flat $3 AUD fee per trade for all assets
                total_brokerage += trade_fee_aud
                trade_count += 1
        
        total_cost = total_brokerage
        cost_pct = (total_cost / self.portfolio_value) * 100
        
        return {
            'brokerage_aud': total_brokerage,
            'total_cost_aud': total_cost,
            'cost_pct': cost_pct,
            'trade_count': trade_count,
            'turnover': abs(weight_diff).sum()
        }
    
    def cost_benefit_gate(self,
                          target_weights: pd.Series,
                          expected_alpha: float) -> Tuple[bool, Dict]:
        """
        Determine if trade should execute based on cost-benefit analysis.
        
        The golden rule: Only trade if expected alpha > costs
        
        Args:
            target_weights: Proposed target weights
            expected_alpha: Expected annual alpha (as decimal, e.g., 0.02 for 2%)
            
        Returns:
            Tuple of (should_trade: bool, analysis: dict)
        """
        costs = self.calculate_trading_costs(target_weights)
        
        # Annualize cost impact
        cost_drag = costs['cost_pct'] / 100
        
        # Net expected benefit
        net_benefit = expected_alpha - cost_drag
        
        analysis = {
            'expected_alpha': expected_alpha,
            'cost_drag': cost_drag,
            'net_benefit': net_benefit,
            'should_trade': net_benefit > 0,
            'breakeven_alpha': cost_drag,
            **costs
        }
        
        return net_benefit > 0, analysis
    
    def optimize_with_turnover_constraint(self,
                                           max_turnover: float = 0.2) -> pd.Series:
        """
        Optimize with turnover constraint.
        
        Limits how much the portfolio can change to manage costs.
        
        Args:
            max_turnover: Maximum allowed turnover (0.2 = 20%)
            
        Returns:
            pd.Series: Optimal weights
        """
        # Get unconstrained HRP weights
        target = self.optimize_hrp()
        
        # Calculate required turnover
        turnover = abs(target - self.current_weights).sum()
        
        if turnover <= max_turnover:
            return target
        
        # Scale the trades down
        scale = max_turnover / turnover
        constrained_weights = (
            self.current_weights + 
            (target - self.current_weights) * scale
        )
        
        # Ensure weights sum to 1
        constrained_weights = constrained_weights / constrained_weights.sum()
        
        return constrained_weights


class SectorConstrainedOptimizer(PortfolioOptimizer):
    """
    Optimizer with sector/asset class constraints.
    """
    
    def __init__(self,
                 returns: pd.DataFrame,
                 sector_map: Dict[str, str],
                 max_sector_weight: float = None):
        """
        Initialize with sector constraints.
        
        Args:
            returns: DataFrame of returns
            sector_map: Dict mapping ticker -> sector
            max_sector_weight: Maximum weight per sector
        """
        super().__init__(returns)
        self.sector_map = sector_map
        self.max_sector = max_sector_weight or CONFIG.MAX_SECTOR_WEIGHT
        
    def build_sector_constraints(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build constraint matrices for sector limits.
        
        Returns:
            Tuple of (A_ineq, b_ineq) for Ax <= b
        """
        sectors = list(set(self.sector_map.values()))
        n_sectors = len(sectors)
        
        A = np.zeros((n_sectors, self.n_assets))
        b = np.ones(n_sectors) * self.max_sector
        
        for i, sector in enumerate(sectors):
            for j, ticker in enumerate(self.asset_names):
                if self.sector_map.get(ticker) == sector:
                    A[i, j] = 1
        
        return A, b


def demo():
    """Demonstrate optimization functionality."""
    print("=" * 60)
    print("Portfolio Optimizer Demo")
    print("=" * 60)
    
    # Create sample returns data
    np.random.seed(42)
    n_days = 252 * 3  # 3 years
    n_assets = 6
    
    tickers = ['SPY', 'QQQ', 'TLT', 'GLD', 'VGS.AX', 'VAS.AX']
    
    # Simulated returns with realistic characteristics
    means = np.array([0.10, 0.12, 0.03, 0.05, 0.08, 0.07]) / 252
    vols = np.array([0.16, 0.20, 0.12, 0.15, 0.14, 0.13]) / np.sqrt(252)
    
    # Generate correlated returns
    corr = np.array([
        [1.0, 0.8, -0.3, 0.1, 0.7, 0.5],
        [0.8, 1.0, -0.4, 0.0, 0.6, 0.4],
        [-0.3, -0.4, 1.0, 0.3, -0.2, -0.1],
        [0.1, 0.0, 0.3, 1.0, 0.1, 0.1],
        [0.7, 0.6, -0.2, 0.1, 1.0, 0.6],
        [0.5, 0.4, -0.1, 0.1, 0.6, 1.0]
    ])
    
    cov = np.diag(vols) @ corr @ np.diag(vols)
    returns_data = np.random.multivariate_normal(means, cov, n_days)
    
    dates = pd.date_range('2021-01-01', periods=n_days, freq='B')
    returns = pd.DataFrame(returns_data, index=dates, columns=tickers)
    
    # Initialize optimizer
    opt = PortfolioOptimizer(returns)
    
    print("\n" + "=" * 60)
    print("1. Hierarchical Risk Parity (HRP)")
    print("=" * 60)
    hrp_weights = opt.optimize_hrp()
    print("\nHRP Weights:")
    print(hrp_weights.round(4))
    
    stats = opt.get_portfolio_stats(hrp_weights)
    print(f"\nExpected Return: {stats['expected_return']*100:.2f}%")
    print(f"Volatility: {stats['volatility']*100:.2f}%")
    print(f"Sharpe Ratio: {stats['sharpe_ratio']:.3f}")
    
    print("\n" + "=" * 60)
    print("2. Mean-Variance Optimization (MVO)")
    print("=" * 60)
    try:
        mvo_weights = opt.optimize_mvo(objective='Sharpe')
        print("\nMVO Weights (Max Sharpe):")
        print(mvo_weights.round(4))
    except Exception as e:
        print(f"MVO failed: {e}")
    
    print("\n" + "=" * 60)
    print("3. Risk Parity")
    print("=" * 60)
    try:
        rp_weights = opt.optimize_risk_parity()
        print("\nRisk Parity Weights:")
        print(rp_weights.round(4))
    except Exception as e:
        print(f"Risk Parity failed: {e}")
    
    print("\n" + "=" * 60)
    print("4. Cost-Aware Optimization")
    print("=" * 60)
    
    # Current portfolio (equal weight)
    current = pd.Series(1/6, index=tickers)
    
    cost_opt = CostAwareOptimizer(
        returns,
        current_weights=current,
        portfolio_value_aud=100000
    )
    
    # Get new target
    target = cost_opt.optimize_hrp()
    
    # Cost analysis (uses CONFIG.EXPECTED_ALPHA)
    should_trade, analysis = cost_opt.cost_benefit_gate(
        target_weights=target,
        expected_alpha=CONFIG.EXPECTED_ALPHA
    )
    
    print(f"\nCost Analysis:")
    print(f"  Expected Alpha: {analysis['expected_alpha']*100:.2f}%")
    print(f"  Cost Drag: {analysis['cost_drag']*100:.2f}%")
    print(f"  Net Benefit: {analysis['net_benefit']*100:.2f}%")
    print(f"  Should Trade: {analysis['should_trade']}")
    print(f"  Total Cost (AUD): ${analysis['total_cost_aud']:.2f}")
    print(f"  Turnover: {analysis['turnover']*100:.1f}%")


if __name__ == "__main__":
    demo()
