"""
Portfolio Optimization Package
==============================
Implements portfolio optimization using Riskfolio-Lib.

Methods:
1. Mean-Variance Optimization (MVO)
2. Hierarchical Risk Parity (HRP) - RECOMMENDED
3. Black-Litterman with Views
4. Risk Parity
"""

from strategy.quant1.optimization.optimizer import (
    PortfolioOptimizer,
    CostAwareOptimizer,
    SectorConstrainedOptimizer
)

__all__ = [
    'PortfolioOptimizer',
    'CostAwareOptimizer',
    'SectorConstrainedOptimizer',
]
