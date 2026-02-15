"""
DEPRECATED: Implementation moved to strategy.loaders.asx

This stub maintains backwards compatibility.
New code should import from: strategy.loaders.asx

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.unified_asx_loader is deprecated. "
    "Use strategy.loaders.asx instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.loaders.asx import *
