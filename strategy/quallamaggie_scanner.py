"""
DEPRECATED: This module has been moved to strategy.quant1.scanner.quallamaggie_scanner

This file is kept for backwards compatibility.
Please update your imports to use:
    from strategy.quant1.scanner.quallamaggie_scanner import QuallamaggieScanner
"""

import warnings

warnings.warn(
    "strategy.quallamaggie_scanner is deprecated. "
    "Import from strategy.quant1.scanner.quallamaggie_scanner instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.scanner.quallamaggie_scanner import *
