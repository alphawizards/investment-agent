"""
DEPRECATED: Implementation moved to strategy.quant1.hard_assets.signals

This stub maintains backwards compatibility.
New code should import from: strategy.quant1.hard_assets.signals

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.hard_asset_signals is deprecated. "
    "Use strategy.quant1.hard_assets.signals instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.hard_assets.signals import *
