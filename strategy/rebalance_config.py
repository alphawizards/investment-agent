"""
DEPRECATED: Implementation moved to strategy.infrastructure.rebalance

This stub maintains backwards compatibility.
New code should import from: strategy.infrastructure.rebalance

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.rebalance_config is deprecated. "
    "Use strategy.infrastructure.rebalance instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.infrastructure.rebalance import *
