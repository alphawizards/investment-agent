"""
DEPRECATED: This module has been moved to strategy.quant1.optimization.optimizer

This file is kept for backwards compatibility.
Please update your imports to use:
    from strategy.quant1.optimization.optimizer import PortfolioOptimizer, CostAwareOptimizer
"""

import warnings

warnings.warn(
    "strategy.optimizer is deprecated. "
    "Import from strategy.quant1.optimization.optimizer instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.optimization.optimizer import *
