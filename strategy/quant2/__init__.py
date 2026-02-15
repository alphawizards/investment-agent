"""
Quant 2.0 Strategy Package
==========================
Modern, regime-adaptive quantitative trading strategies.

This package implements the Quant 2.0 modernization roadmap:
- Residual Momentum (Fama-French factor-neutral momentum)
- Statistical Arbitrage (DBSCAN clustering + Kalman Filter pairs)
- Regime-Based Allocation (HMM-driven dynamic weights)
- Meta-Labeling (ML-filtered Quallamaggie signals)
- NCO Optimization (Nested Clustered Optimization)

Author: Alpha Wizards
Version: 2.0.0
"""

__version__ = "2.0.0"

# Lazy imports - only import when accessed to avoid dependency errors
def __getattr__(name):
    """Lazy import of submodules to handle missing dependencies gracefully."""
    
    if name == "ResidualMomentum":
        from .momentum.residual_momentum import ResidualMomentum
        return ResidualMomentum
    elif name == "FamaFrenchLoader":
        from .momentum.fama_french_loader import FamaFrenchLoader
        return FamaFrenchLoader
    elif name == "VolatilityScaling":
        from .momentum.volatility_scaling import VolatilityScaling
        return VolatilityScaling
    elif name == "ClusteringEngine":
        from .stat_arb.clustering import ClusteringEngine
        return ClusteringEngine
    elif name == "KalmanHedgeRatio":
        from .stat_arb.kalman import KalmanHedgeRatio
        return KalmanHedgeRatio
    elif name == "PairsStrategy":
        from .stat_arb.pairs_strategy import PairsStrategy
        return PairsStrategy
    elif name == "HMMRegimeDetector":
        from .regime.hmm_detector import HMMRegimeDetector
        return HMMRegimeDetector
    elif name == "RegimeAllocator":
        from .regime.regime_allocator import RegimeAllocator
        return RegimeAllocator
    elif name == "MetaLabelModel":
        from .meta_labeling.meta_model import MetaLabelModel
        return MetaLabelModel
    elif name == "FeatureEngineer":
        from .meta_labeling.feature_engineering import FeatureEngineer
        return FeatureEngineer
    elif name == "TripleBarrierLabeler":
        from .meta_labeling.triple_barrier import TripleBarrierLabeler
        return TripleBarrierLabeler
    elif name == "NCOOptimizer":
        from .optimization.nco_optimizer import NCOOptimizer
        return NCOOptimizer
    elif name == "VRPSignal":
        from .volatility.vrp_signal import VRPSignal
        return VRPSignal
    
    raise AttributeError(f"module 'strategy.quant2' has no attribute '{name}'")


__all__ = [
    "ResidualMomentum",
    "FamaFrenchLoader",
    "VolatilityScaling",
    "ClusteringEngine",
    "KalmanHedgeRatio",
    "PairsStrategy",
    "HMMRegimeDetector",
    "RegimeAllocator",
    "MetaLabelModel",
    "FeatureEngineer",
    "TripleBarrierLabeler",
    "NCOOptimizer",
    "VRPSignal",
]

