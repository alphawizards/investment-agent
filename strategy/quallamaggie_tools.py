"""
DEPRECATED: Implementation moved to strategy.quant1.scanner.tools

This stub maintains backwards compatibility.
New code should import from: strategy.quant1.scanner.tools

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.quallamaggie_tools is deprecated. "
    "Use strategy.quant1.scanner.tools instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.scanner.tools import *
