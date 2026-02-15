"""
DEPRECATED: Implementation moved to strategy.quant1.scanner.fast

This stub maintains backwards compatibility.
New code should import from: strategy.quant1.scanner.fast

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.fast_quallamaggie_scanner is deprecated. "
    "Use strategy.quant1.scanner.fast instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.scanner.fast import *
