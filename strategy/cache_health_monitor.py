"""
DEPRECATED: Implementation moved to strategy.utils.cache_monitor

This stub maintains backwards compatibility.
New code should import from: strategy.utils.cache_monitor

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.cache_health_monitor is deprecated. "
    "Use strategy.utils.cache_monitor instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.utils.cache_monitor import *
