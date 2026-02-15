"""
DEPRECATED: Implementation moved to strategy.loaders.tiingo

This stub maintains backwards compatibility.
New code should import from: strategy.loaders.tiingo

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.tiingo_data_loader is deprecated. "
    "Use strategy.loaders.tiingo instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.loaders.tiingo import *
