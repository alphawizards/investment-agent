"""
DEPRECATED: Implementation moved to strategy.infrastructure.backtest

This stub maintains backwards compatibility.
New code should import from: strategy.infrastructure.backtest

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.backtest is deprecated. "
    "Use strategy.infrastructure.backtest instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.infrastructure.backtest import *
