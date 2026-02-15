"""
DEPRECATED: Implementation moved to strategy.quant1.scanner.backtest

This stub maintains backwards compatibility.
New code should import from: strategy.quant1.scanner.backtest

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.quallamaggie_backtest is deprecated. "
    "Use strategy.quant1.scanner.backtest instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.quant1.scanner.backtest import *
