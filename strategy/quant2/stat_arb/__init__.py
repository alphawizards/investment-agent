"""
Statistical Arbitrage Module
============================
DBSCAN clustering and Kalman Filter pairs trading.
"""

from .clustering import ClusteringEngine
from .kalman import KalmanHedgeRatio
from .pairs_strategy import PairsStrategy

__all__ = [
    "ClusteringEngine",
    "KalmanHedgeRatio",
    "PairsStrategy",
]
