"""
DEPRECATED: Implementation moved to strategy.quant1.hard_assets.optimizer

This stub maintains backwards compatibility.
New code should import from: strategy.quant1.hard_assets.optimizer

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.hard_asset_optimizer is deprecated. "
    "Use strategy.quant1.hard_assets.optimizer instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.hard_assets.optimizer import *
