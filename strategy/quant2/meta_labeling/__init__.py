"""
Meta-Labeling Module
====================
ML-based trade filtering for Quallamaggie signals.
"""

from .feature_engineering import FeatureEngineer
from .triple_barrier import TripleBarrierLabeler
from .meta_model import MetaLabelModel

__all__ = [
    "FeatureEngineer",
    "TripleBarrierLabeler",
    "MetaLabelModel",
]
