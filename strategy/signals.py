"""
DEPRECATED: This module has been moved to strategy.quant1.momentum.signals

This file is kept for backwards compatibility.
Please update your imports to use:
    from strategy.quant1.momentum.signals import MomentumSignals, CompositeSignal
"""

import warnings

warnings.warn(
    "strategy.signals is deprecated. "
    "Import from strategy.quant1.momentum.signals instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.momentum.signals import *
