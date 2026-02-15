"""
Momentum Module
===============
Residual Momentum and Volatility Scaling components.
"""

from .fama_french_loader import FamaFrenchLoader
from .residual_momentum import ResidualMomentum
from .volatility_scaling import VolatilityScaling

__all__ = [
    "FamaFrenchLoader",
    "ResidualMomentum",
    "VolatilityScaling",
]
