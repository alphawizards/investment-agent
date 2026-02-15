"""
DEPRECATED: The strategy.olps package has been moved to strategy.quant1.olmar

This file is kept for backwards compatibility.
Please update your imports to use:
    from strategy.quant1.olmar import OLMARStrategy, OLMARConfig
"""

import warnings

warnings.warn(
    "strategy.olps is deprecated. "
    "Import from strategy.quant1.olmar instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.olmar import *
