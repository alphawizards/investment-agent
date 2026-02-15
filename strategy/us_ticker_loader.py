"""
DEPRECATED: Implementation moved to strategy.loaders.us_tickers

This stub maintains backwards compatibility.
New code should import from: strategy.loaders.us_tickers

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.us_ticker_loader is deprecated. "
    "Use strategy.loaders.us_tickers instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.loaders.us_tickers import *
