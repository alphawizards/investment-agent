"""
DBSCAN Clustering Engine
========================
Unsupervised learning for statistical arbitrage universe selection.

Uses PCA for dimensionality reduction followed by DBSCAN for
density-based clustering on factor loading vectors.

Reference: fin-ml_by_tatsath Chapter 8 (Unsupervised Learning)
https://github.com/sharavsambuu/fin-ml_by_tatsath
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

try:
    from sklearn.decomposition import PCA
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: scikit-learn not installed. Install with: pip install scikit-learn")


@dataclass
class ClusteringResult:
    """
    Result container for clustering analysis.
    
    Attributes:
        clusters: Dict mapping cluster_id to list of tickers
        labels: Series of cluster labels per ticker (-1 = noise)
        factor_loadings: DataFrame of PCA factor loadings
        explained_variance: Variance explained by each component
        metadata: Additional information
    """
    clusters: Dict[int, List[str]]
    labels: pd.Series
    factor_loadings: pd.DataFrame
    explained_variance: np.ndarray
    metadata: dict


class ClusteringEngine:
    """
    PCA + DBSCAN clustering for statistical arbitrage universe selection.
    
    This engine identifies groups of stocks with similar risk factor exposures,
    which are candidates for pairs/basket trading within clusters.
    
    Attributes:
        n_components: Number of PCA components (default: 10)
        eps: DBSCAN epsilon (neighborhood size)
        min_samples: DBSCAN minimum samples per cluster
        lookback_days: Rolling window for covariance estimation
    """
    
    def __init__(
        self,
        n_components: int = 10,
        variance_threshold: float = 0.9,
        eps: float = 0.5,
        min_samples: int = 3,
        lookback_days: int = 252
    ):
        """
        Initialize Clustering Engine.
        
        Args:
            n_components: Max number of PCA components to extract
            variance_threshold: Cumulative variance to explain (0.0 to 1.0)
            eps: DBSCAN neighborhood radius (lower = tighter clusters)
            min_samples: Minimum samples for a core point
            lookback_days: Days of return data for covariance
        """
        if not HAS_SKLEARN:
            raise ImportError(
                "scikit-learn is required for clustering. "
                "Install with: pip install scikit-learn"
            )
        
        self.n_components = n_components
        self.variance_threshold = variance_threshold
        self.eps = eps
        self.min_samples = min_samples
        self.lookback_days = lookback_days
        
        self.pca = None
        self.scaler = StandardScaler()
    
    def fit_pca(
        self,
        returns: pd.DataFrame,
        adaptive_components: bool = True
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Fit PCA on returns to extract factor loadings.
        
        Args:
            returns: DataFrame of stock returns (dates x tickers)
            adaptive_components: Auto-select components by variance threshold
            
        Returns:
            Tuple of (factor_loadings DataFrame, explained_variance array)
        """
        # Use most recent lookback_days
        if len(returns) > self.lookback_days:
            returns = returns.iloc[-self.lookback_days:]
        
        # Drop columns with too many NaNs
        valid_cols = returns.columns[returns.notna().sum() > len(returns) * 0.8]
        returns_clean = returns[valid_cols].dropna()
        
        # Reduced threshold to support small test data windows (e.g. 40 days)
        if len(returns_clean) < 30:
            raise ValueError(f"Insufficient data for PCA after cleaning: {len(returns_clean)} rows")
        
        # Standardize returns
        returns_scaled = self.scaler.fit_transform(returns_clean)
        
        # Fit PCA
        n_comp = min(self.n_components, len(valid_cols) - 1, len(returns_clean) - 1)
        self.pca = PCA(n_components=n_comp)
        self.pca.fit(returns_scaled)
        
        # Get factor loadings (how each stock loads on each factor)
        # Loadings = eigenvectors scaled by sqrt(eigenvalues)
        loadings = self.pca.components_.T * np.sqrt(self.pca.explained_variance_)
        
        factor_loadings = pd.DataFrame(
            loadings,
            index=valid_cols,
            columns=[f'PC{i+1}' for i in range(n_comp)]
        )
        
        # Optionally reduce to components explaining variance_threshold
        if adaptive_components:
            cumvar = np.cumsum(self.pca.explained_variance_ratio_)
            n_keep = np.argmax(cumvar >= self.variance_threshold) + 1
            n_keep = max(n_keep, 2)  # At least 2 components
            factor_loadings = factor_loadings.iloc[:, :n_keep]
        
        return factor_loadings, self.pca.explained_variance_ratio_
    
    def cluster_stocks(
        self,
        factor_loadings: pd.DataFrame
    ) -> Tuple[pd.Series, Dict[int, List[str]]]:
        """
        Apply DBSCAN clustering on factor loadings.
        
        Args:
            factor_loadings: DataFrame of factor loadings per stock
            
        Returns:
            Tuple of (labels Series, clusters Dict)
        """
        # Standardize loadings for clustering
        loadings_scaled = StandardScaler().fit_transform(factor_loadings)
        
        # Apply DBSCAN
        dbscan = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        labels = dbscan.fit_predict(loadings_scaled)
        
        labels_series = pd.Series(labels, index=factor_loadings.index, name='cluster')
        
        # Group tickers by cluster
        clusters = {}
        for cluster_id in np.unique(labels):
            if cluster_id == -1:
                continue  # Skip noise
            clusters[cluster_id] = factor_loadings.index[labels == cluster_id].tolist()
        
        return labels_series, clusters
    
    def fit_transform(
        self,
        returns: pd.DataFrame
    ) -> ClusteringResult:
        """
        Full pipeline: PCA -> DBSCAN -> Cluster identification.
        
        Args:
            returns: DataFrame of stock returns
            
        Returns:
            ClusteringResult with clusters and metadata
        """
        # Step 1: PCA
        factor_loadings, explained_var = self.fit_pca(returns)
        
        # Step 2: Clustering
        labels, clusters = self.cluster_stocks(factor_loadings)
        
        # Metadata
        metadata = {
            'n_stocks': len(factor_loadings),
            'n_components': factor_loadings.shape[1],
            'variance_explained': explained_var[:factor_loadings.shape[1]].sum(),
            'n_clusters': len(clusters),
            'n_noise': (labels == -1).sum(),
            'eps': self.eps,
            'min_samples': self.min_samples,
        }
        
        return ClusteringResult(
            clusters=clusters,
            labels=labels,
            factor_loadings=factor_loadings,
            explained_variance=explained_var,
            metadata=metadata
        )
    
    def get_pairs_within_cluster(
        self,
        cluster_id: int,
        result: ClusteringResult
    ) -> List[Tuple[str, str]]:
        """
        Get all possible pairs within a cluster.
        
        Args:
            cluster_id: Cluster ID to extract pairs from
            result: ClusteringResult from fit_transform
            
        Returns:
            List of (ticker1, ticker2) tuples
        """
        if cluster_id not in result.clusters:
            return []
        
        tickers = result.clusters[cluster_id]
        pairs = []
        
        for i, t1 in enumerate(tickers):
            for t2 in tickers[i+1:]:
                pairs.append((t1, t2))
        
        return pairs
    
    def get_all_tradable_pairs(
        self,
        result: ClusteringResult,
        min_cluster_size: int = 2
    ) -> List[Tuple[str, str, int]]:
        """
        Get all tradable pairs across all clusters.
        
        Args:
            result: ClusteringResult from fit_transform
            min_cluster_size: Minimum cluster size to consider
            
        Returns:
            List of (ticker1, ticker2, cluster_id) tuples
        """
        all_pairs = []
        
        for cluster_id, tickers in result.clusters.items():
            if len(tickers) < min_cluster_size:
                continue
            
            pairs = self.get_pairs_within_cluster(cluster_id, result)
            for t1, t2 in pairs:
                all_pairs.append((t1, t2, cluster_id))
        
        return all_pairs


def demo():
    """Demonstrate clustering engine."""
    print("=" * 60)
    print("Clustering Engine Demo")
    print("=" * 60)
    
    # Create sample returns
    np.random.seed(42)
    n_stocks = 50
    n_days = 252
    
    tickers = [f'STOCK_{i:02d}' for i in range(n_stocks)]
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    
    # Create returns with some cluster structure
    returns = pd.DataFrame(
        np.random.randn(n_days, n_stocks) * 0.02,
        index=dates,
        columns=tickers
    )
    
    # Add common factors to create clusters
    factor1 = np.random.randn(n_days) * 0.01
    factor2 = np.random.randn(n_days) * 0.01
    
    for i in range(10):
        returns.iloc[:, i] += factor1  # Cluster 1
    for i in range(10, 20):
        returns.iloc[:, i] += factor2  # Cluster 2
    
    print(f"\nInput: {n_stocks} stocks, {n_days} days of returns")
    
    # Run clustering
    engine = ClusteringEngine(eps=0.5, min_samples=3)
    result = engine.fit_transform(returns)
    
    print(f"\nClusters found: {result.metadata['n_clusters']}")
    print(f"Noise points: {result.metadata['n_noise']}")
    print(f"Variance explained: {result.metadata['variance_explained']:.2%}")
    
    for cluster_id, tickers in result.clusters.items():
        print(f"  Cluster {cluster_id}: {len(tickers)} stocks")
    
    # Get tradable pairs
    pairs = engine.get_all_tradable_pairs(result)
    print(f"\nTradable pairs: {len(pairs)}")
    if pairs:
        print(f"Sample pairs: {pairs[:5]}")


if __name__ == "__main__":
    demo()
