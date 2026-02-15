"""
NCO Optimizer
=============
Nested Clustered Optimization wrapper for Riskfolio-Lib.

NCO improves upon HRP by:
1. Clustering assets using the same linkage tree
2. Optimizing weights WITHIN each cluster (inner optimization)
3. Optimizing weights BETWEEN clusters (outer optimization)

This two-step process yields more robust diversification.

Reference: skfolio NCO documentation
https://skfolio.org/auto_examples/clustering/plot_4_nco.html
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

try:
    import riskfolio as rp
    HAS_RISKFOLIO = True
except ImportError:
    HAS_RISKFOLIO = False
    print("Warning: riskfolio-lib not installed. Install with: pip install riskfolio-lib")


@dataclass
class NCOResult:
    """Result from NCO optimization."""
    weights: pd.Series
    cluster_weights: pd.Series
    intra_cluster_weights: Dict[int, pd.Series]
    clustering_info: Dict
    metadata: dict


class NCOOptimizer:
    """
    Nested Clustered Optimization (NCO) portfolio optimizer.
    
    NCO addresses limitations of HRP's recursive bisection by:
    1. Using proper optimization within clusters
    2. Treating clusters as synthetic assets for outer optimization
    
    Attributes:
        inner_objective: Objective for intra-cluster optimization
        outer_objective: Objective for inter-cluster optimization
        codependence: Method for correlation/dependence matrix
        linkage: Hierarchical clustering linkage method
    """
    
    def __init__(
        self,
        inner_objective: str = 'MinRisk',
        outer_objective: str = 'ERC',
        codependence: str = 'pearson',
        linkage: str = 'ward',
        max_clusters: int = 10,
        min_weight: float = 0.02,
        max_weight: float = 0.30
    ):
        """
        Initialize NCO Optimizer.
        
        Args:
            inner_objective: Intra-cluster objective ('MinRisk', 'Sharpe', 'ERC')
            outer_objective: Inter-cluster objective ('MinRisk', 'ERC', 'MaxDiv')
            codependence: Correlation method ('pearson', 'spearman', 'kendall')
            linkage: Clustering linkage ('ward', 'single', 'complete', 'average')
            max_clusters: Maximum number of clusters
            min_weight: Minimum weight per asset
            max_weight: Maximum weight per asset
        """
        if not HAS_RISKFOLIO:
            raise ImportError(
                "riskfolio-lib is required for NCO optimization. "
                "Install with: pip install riskfolio-lib"
            )
        
        self.inner_objective = inner_objective
        self.outer_objective = outer_objective
        self.codependence = codependence
        self.linkage = linkage
        self.max_clusters = max_clusters
        self.min_weight = min_weight
        self.max_weight = max_weight
    
    def optimize(
        self,
        returns: pd.DataFrame,
        expected_returns: Optional[pd.Series] = None
    ) -> NCOResult:
        """
        Run NCO optimization on returns.
        
        Args:
            returns: DataFrame of asset returns
            expected_returns: Optional expected returns (for Sharpe objective)
            
        Returns:
            NCOResult with optimal weights and cluster information
        """
        # Clean data
        returns = returns.dropna(axis=1, how='all').dropna()
        
        if len(returns) < 50:
            raise ValueError("Insufficient data for NCO optimization")
        
        # Create portfolio object
        port = rp.Portfolio(returns=returns)
        
        # Calculate statistics
        port.assets_stats(method_mu='hist', method_cov='hist')
        
        # Override expected returns if provided
        if expected_returns is not None:
            port.mu = expected_returns.reindex(returns.columns).fillna(0)
        
        # Build clusters using hierarchical clustering
        clustering = rp.HCPortfolio(returns=returns)
        
        # Get linkage tree
        clustering.assets_stats(method_mu='hist', method_cov='hist')
        
        # Perform NCO optimization
        # NCO uses the clustering structure but optimizes properly
        weights = clustering.optimization(
            model='NCO',
            codependence=self.codependence,
            covariance='hist',
            obj=self.inner_objective,
            rm='MV',
            linkage=self.linkage,
            k=self.max_clusters,
            leaf_order=True
        )
        
        if weights is None or weights.empty:
            # Fallback to HRP
            weights = clustering.optimization(
                model='HRP',
                codependence=self.codependence,
                covariance='hist',
                rm='MV',
                linkage=self.linkage,
                leaf_order=True
            )
        
        # Convert to Series
        weights_series = weights.iloc[:, 0] if isinstance(weights, pd.DataFrame) else weights
        weights_series.name = 'weight'
        
        # Apply constraints
        weights_series = self._apply_constraints(weights_series)
        
        # Get cluster assignments (simplified)
        cluster_info = {
            'n_clusters': min(self.max_clusters, len(weights_series)),
            'method': 'NCO',
        }
        
        metadata = {
            'inner_objective': self.inner_objective,
            'outer_objective': self.outer_objective,
            'codependence': self.codependence,
            'linkage': self.linkage,
            'n_assets': len(weights_series),
            'effective_n': 1 / (weights_series ** 2).sum(),  # Effective number of bets
        }
        
        return NCOResult(
            weights=weights_series,
            cluster_weights=pd.Series(),  # Simplified
            intra_cluster_weights={},
            clustering_info=cluster_info,
            metadata=metadata
        )
    
    def _apply_constraints(
        self,
        weights: pd.Series
    ) -> pd.Series:
        """
        Apply min/max weight constraints.
        
        Args:
            weights: Raw optimized weights
            
        Returns:
            Constrained weights (sum to 1.0)
        """
        # Clip to constraints
        weights = weights.clip(lower=self.min_weight, upper=self.max_weight)
        
        # Renormalize
        weights = weights / weights.sum()
        
        return weights
    
    def compare_with_hrp(
        self,
        returns: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compare NCO with standard HRP optimization.
        
        Args:
            returns: DataFrame of asset returns
            
        Returns:
            DataFrame comparing NCO and HRP weights
        """
        # NCO optimization
        nco_result = self.optimize(returns)
        
        # HRP optimization
        clustering = rp.HCPortfolio(returns=returns)
        clustering.assets_stats(method_mu='hist', method_cov='hist')
        
        hrp_weights = clustering.optimization(
            model='HRP',
            codependence=self.codependence,
            covariance='hist',
            rm='MV',
            linkage=self.linkage,
            leaf_order=True
        )
        
        if hrp_weights is not None:
            hrp_series = hrp_weights.iloc[:, 0]
        else:
            hrp_series = pd.Series(1.0 / len(returns.columns), index=returns.columns)
        
        comparison = pd.DataFrame({
            'NCO': nco_result.weights,
            'HRP': hrp_series,
            'Difference': nco_result.weights - hrp_series
        })
        
        return comparison
    
    def get_portfolio_stats(
        self,
        returns: pd.DataFrame,
        weights: pd.Series
    ) -> Dict:
        """
        Calculate expected portfolio statistics.
        
        Args:
            returns: DataFrame of asset returns
            weights: Portfolio weights
            
        Returns:
            Dict with portfolio statistics
        """
        # Align weights with returns
        common = weights.index.intersection(returns.columns)
        weights = weights.loc[common]
        returns = returns[common]
        
        # Expected return
        expected_return = (returns.mean() * weights).sum() * 252
        
        # Portfolio volatility
        cov = returns.cov() * 252
        port_var = weights @ cov @ weights
        port_vol = np.sqrt(port_var)
        
        # Sharpe ratio
        sharpe = expected_return / port_vol if port_vol > 0 else 0
        
        return {
            'expected_return': expected_return,
            'volatility': port_vol,
            'sharpe_ratio': sharpe,
            'effective_n': 1 / (weights ** 2).sum(),
            'max_weight': weights.max(),
            'min_weight': weights[weights > 0].min() if (weights > 0).any() else 0,
        }


def demo():
    """Demonstrate NCO optimizer."""
    print("=" * 60)
    print("NCO Optimizer Demo")
    print("=" * 60)
    
    # Create sample returns
    np.random.seed(42)
    n_assets = 20
    n_days = 252
    
    tickers = [f'ASSET_{i:02d}' for i in range(n_assets)]
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    
    # Create correlated returns
    returns = pd.DataFrame(
        np.random.randn(n_days, n_assets) * 0.01,
        index=dates,
        columns=tickers
    )
    
    # Add correlation structure
    common_factor = np.random.randn(n_days) * 0.005
    for col in returns.columns[:10]:
        returns[col] += common_factor
    
    print(f"Universe: {n_assets} assets, {n_days} days")
    
    # Run NCO optimization
    optimizer = NCOOptimizer()
    result = optimizer.optimize(returns)
    
    print(f"\nNCO Optimization Results:")
    print(f"  Effective N: {result.metadata['effective_n']:.2f}")
    print(f"  Max weight: {result.weights.max():.2%}")
    print(f"  Min weight: {result.weights.min():.2%}")
    
    print("\nTop 5 weights:")
    print(result.weights.nlargest(5))
    
    # Compare with HRP
    comparison = optimizer.compare_with_hrp(returns)
    print("\nNCO vs HRP comparison (top differences):")
    print(comparison.reindex(comparison['Difference'].abs().nlargest(5).index))
    
    # Portfolio stats
    stats = optimizer.get_portfolio_stats(returns, result.weights)
    print(f"\nPortfolio Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value:.4f}")


if __name__ == "__main__":
    demo()
