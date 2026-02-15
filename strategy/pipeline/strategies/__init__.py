"""
Strategy Plugins Package
==========================
Pre-built strategy implementations for the trading pipeline.
"""

from .quallamaggie import (
    QuallamaggieStrategy,
    QuallamaggieConfig,
    create_quallamaggie_1m,
    create_quallamaggie_3m,
    create_quallamaggie_6m
)

__all__ = [
    'QuallamaggieStrategy',
    'QuallamaggieConfig',
    'create_quallamaggie_1m',
    'create_quallamaggie_3m',
    'create_quallamaggie_6m'
]
