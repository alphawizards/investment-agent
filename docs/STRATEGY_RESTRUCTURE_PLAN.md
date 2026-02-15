# Strategy Package Restructuring Plan

> **Version:** 2.0 (Revised)  
> **Date:** December 2024  
> **Status:** Ready for Implementation  
> **Estimated Time:** 2-3 hours  
> **Risk Level:** Medium (mitigated by stub pattern)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Proposed Structure](#proposed-structure)
4. [Implementation Phases](#implementation-phases)
5. [Import Path Compatibility](#import-path-compatibility)
6. [Code Patterns](#code-patterns)
7. [Testing Checklist](#testing-checklist)
8. [Rollback Plan](#rollback-plan)

---

## Executive Summary

### Problem Statement
The `strategy/` package has **21 Python files at root level** (8,685 lines of code), making navigation difficult and violating separation of concerns principles.

### Solution
Reorganize files into logical subfolders while maintaining **100% backwards compatibility** through:
- Thin stub files at root level (deprecation redirects)
- Facade pattern in `__init__.py` for clean re-exports
- Phased migration with testing at each step

### Key Outcomes
| Metric | Before | After |
|--------|--------|-------|
| Root-level .py files | 21 | 8 (stubs only) |
| Organized modules | 3 | 6 |
| Breaking changes | N/A | 0 |
| Test coverage | Maintained | Maintained |

---

## Current State Analysis

### File Inventory

```
strategy/                           # 84 total files
├── olps/                          # Legacy (redirects to quant1)
├── pipeline/                      # VectorBT pipeline (11 files)
├── quant1/                        # Production strategies (15 files)
├── quant2/                        # Advanced strategies (23 files)
│
├── __init__.py                    # Package init
├── backtest.py                    # 523 lines
├── cache_health_monitor.py        # 342 lines
├── config.py                      # 135 lines ⭐ CRITICAL
├── data_loader.py                 # 404 lines ⭐ CRITICAL
├── fast_data_loader.py            # 944 lines ⭐ CRITICAL
├── fast_quallamaggie_scanner.py   # 99 lines
├── hard_asset_backtest.py         # 733 lines
├── hard_asset_optimizer.py        # 707 lines
├── hard_asset_signals.py          # 761 lines
├── main.py                        # 485 lines
├── optimizer.py                   # 19 lines (stub)
├── quallamaggie_backtest.py       # 919 lines
├── quallamaggie_scanner.py        # 19 lines (stub)
├── quallamaggie_tools.py          # 1010 lines
├── rebalance_config.py            # 209 lines
├── signals.py                     # 19 lines (stub)
├── stock_universe.py              # 283 lines ⭐ CRITICAL
├── tiingo_data_loader.py          # 219 lines
├── unified_asx_loader.py          # 635 lines
├── us_ticker_loader.py            # 169 lines
├── quallamaggie_strategy.md       # Documentation
├── research_notes.md              # Documentation
└── strategy_comparison.md         # Documentation
```

### Critical Dependencies

Files marked with ⭐ are imported by the **Backend API**:

```python
# backend/routers/data.py
from strategy.fast_data_loader import FastDataLoader      # ⭐
from strategy.stock_universe import get_screener_universe # ⭐

# backend/routers/scanner.py
from strategy.stock_universe import (...)                 # ⭐

# backend/dashboard_api.py
from strategy.pipeline.pipeline import TradingPipeline    # ✓ OK
```

### Dependency Graph

```
config.py (standalone)
    ↓
data_loader.py → imports config
    ↓
backtest.py → imports data_loader, config
    ↓
stock_universe.py (standalone)
    ↓
fast_data_loader.py → imports config, data_loader
```

---

## Proposed Structure

### Target Architecture (v2)

```
strategy/
│
├── __init__.py                          # FACADE: Re-exports everything
├── main.py                              # CLI entry point (unchanged)
│
│   ┌─────────────────────────────────────────────────────────────────┐
│   │  THIN STUB FILES AT ROOT (Backwards Compatibility)              │
│   └─────────────────────────────────────────────────────────────────┘
├── config.py                            # STUB → infrastructure/
├── data_loader.py                       # STUB → loaders/
├── fast_data_loader.py                  # STUB → loaders/
├── stock_universe.py                    # STUB → infrastructure/
├── backtest.py                          # STUB → infrastructure/
├── unified_asx_loader.py                # STUB → loaders/
├── optimizer.py                         # STUB → quant1/ (existing)
├── signals.py                           # STUB → quant1/ (existing)
├── quallamaggie_scanner.py              # STUB → quant1/ (existing)
│
│   ┌─────────────────────────────────────────────────────────────────┐
│   │  NEW ORGANIZED MODULES                                          │
│   └─────────────────────────────────────────────────────────────────┘
│
├── infrastructure/                      # Config & Core Services
│   ├── __init__.py
│   ├── config.py                        # Central configuration
│   ├── stock_universe.py                # Universe definitions
│   ├── backtest.py                      # Backtesting engine
│   └── rebalance.py                     # Rebalancing config
│
├── loaders/                             # Data Ingestion Layer
│   ├── __init__.py
│   ├── base.py                          # DataLoader class
│   ├── fast.py                          # FastDataLoader class
│   ├── asx.py                           # UnifiedASXLoader
│   ├── tiingo.py                        # TiingoDataLoader
│   └── us_tickers.py                    # US ticker utilities
│
├── quant1/                              # Production Strategies
│   ├── __init__.py
│   ├── momentum/                        # Dual Momentum signals
│   │   ├── __init__.py
│   │   └── signals.py
│   ├── optimization/                    # HRP Portfolio Optimizer
│   │   ├── __init__.py
│   │   └── optimizer.py
│   ├── olmar/                           # OLMAR Mean Reversion
│   │   ├── __init__.py
│   │   ├── kernels.py
│   │   ├── constraints.py
│   │   ├── olmar_strategy.py
│   │   └── backtest_olmar.py
│   ├── scanner/                         # Quallamaggie Scanner
│   │   ├── __init__.py
│   │   ├── scanner.py                   # Main scanner
│   │   ├── backtest.py                  # Scanner backtest
│   │   ├── tools.py                     # Utilities
│   │   └── fast.py                      # Optimized version
│   └── hard_assets/                     # Hard Asset Strategy
│       ├── __init__.py
│       ├── signals.py
│       ├── optimizer.py
│       └── backtest.py
│
├── quant2/                              # Advanced Strategies (UNCHANGED)
│   ├── regime/                          # HMM Regime Detection
│   ├── optimization/                    # NCO Optimizer
│   ├── momentum/                        # Residual Momentum
│   ├── stat_arb/                        # Pairs Trading
│   ├── volatility/                      # Options Strategies
│   └── meta_labeling/                   # ML Triple Barrier
│
├── pipeline/                            # VectorBT Pipeline (UNCHANGED)
│   ├── __init__.py
│   ├── pipeline.py
│   ├── config.py
│   ├── strategies/
│   └── ...
│
├── utils/                               # Utilities
│   ├── __init__.py
│   └── cache_monitor.py
│
└── docs/                                # Documentation
    ├── quallamaggie_strategy.md
    ├── research_notes.md
    └── strategy_comparison.md
```

---

## Implementation Phases

### Phase 1: Preparation (Pre-Migration)

```bash
# 1.1 Create feature branch
git checkout -b feature/strategy-restructure

# 1.2 Run baseline tests
pytest tests/ -v > baseline_tests.log

# 1.3 Backup current structure
cp -r strategy strategy_backup_$(date +%Y%m%d)

# 1.4 Document current state
find strategy -name "*.py" | wc -l
```

**Checkpoint:** All tests passing, backup created

---

### Phase 2: Create New Structure

```bash
# 2.1 Create infrastructure folder
mkdir -p strategy/infrastructure
touch strategy/infrastructure/__init__.py

# 2.2 Create loaders folder
mkdir -p strategy/loaders
touch strategy/loaders/__init__.py

# 2.3 Create hard_assets folder
mkdir -p strategy/quant1/hard_assets
touch strategy/quant1/hard_assets/__init__.py

# 2.4 Create utils folder
mkdir -p strategy/utils
touch strategy/utils/__init__.py

# 2.5 Create docs folder
mkdir -p strategy/docs
```

**Checkpoint:** New folders exist, no files moved yet

---

### Phase 3: Copy Files to New Locations

```bash
# 3.1 Infrastructure files
cp strategy/config.py strategy/infrastructure/config.py
cp strategy/stock_universe.py strategy/infrastructure/stock_universe.py
cp strategy/backtest.py strategy/infrastructure/backtest.py
cp strategy/rebalance_config.py strategy/infrastructure/rebalance.py

# 3.2 Loader files
cp strategy/data_loader.py strategy/loaders/base.py
cp strategy/fast_data_loader.py strategy/loaders/fast.py
cp strategy/unified_asx_loader.py strategy/loaders/asx.py
cp strategy/tiingo_data_loader.py strategy/loaders/tiingo.py
cp strategy/us_ticker_loader.py strategy/loaders/us_tickers.py

# 3.3 Hard assets files
cp strategy/hard_asset_signals.py strategy/quant1/hard_assets/signals.py
cp strategy/hard_asset_optimizer.py strategy/quant1/hard_assets/optimizer.py
cp strategy/hard_asset_backtest.py strategy/quant1/hard_assets/backtest.py

# 3.4 Scanner files (enhance existing)
cp strategy/quallamaggie_backtest.py strategy/quant1/scanner/backtest.py
cp strategy/quallamaggie_tools.py strategy/quant1/scanner/tools.py
cp strategy/fast_quallamaggie_scanner.py strategy/quant1/scanner/fast.py

# 3.5 Utils
cp strategy/cache_health_monitor.py strategy/utils/cache_monitor.py

# 3.6 Docs
mv strategy/*.md strategy/docs/
```

**Checkpoint:** Files copied, originals still in place

---

### Phase 4: Update Internal Imports

Update imports in the NEW files (not the stubs):

#### 4.1 infrastructure/config.py
No changes needed (standalone)

#### 4.2 loaders/base.py
```python
# OLD
from .config import CONFIG, get_us_tickers, get_asx_tickers, is_us_ticker

# NEW
from strategy.infrastructure.config import CONFIG, get_us_tickers, get_asx_tickers, is_us_ticker
```

#### 4.3 loaders/fast.py
```python
# OLD
from .config import CONFIG
from .data_loader import DataLoader

# NEW
from strategy.infrastructure.config import CONFIG
from strategy.loaders.base import DataLoader
```

#### 4.4 quant1/hard_assets/*.py
```python
# Update all imports from strategy.X to strategy.infrastructure.X or strategy.loaders.X
```

**Checkpoint:** New files have correct imports

---

### Phase 5: Create Backward-Compatible Stubs

Replace original files with thin stubs:

#### 5.1 strategy/config.py (STUB)
```python
"""
DEPRECATED: Implementation moved to strategy.infrastructure.config

This stub maintains backwards compatibility.
New code should import from: strategy.infrastructure.config
"""
import warnings
warnings.warn(
    "strategy.config is deprecated. Use strategy.infrastructure.config",
    DeprecationWarning,
    stacklevel=2
)
from strategy.infrastructure.config import *
```

#### 5.2 strategy/data_loader.py (STUB)
```python
"""
DEPRECATED: Implementation moved to strategy.loaders.base

This stub maintains backwards compatibility.
New code should import from: strategy.loaders.base
"""
import warnings
warnings.warn(
    "strategy.data_loader is deprecated. Use strategy.loaders.base",
    DeprecationWarning,
    stacklevel=2
)
from strategy.loaders.base import *
```

#### 5.3 strategy/fast_data_loader.py (STUB)
```python
"""
DEPRECATED: Implementation moved to strategy.loaders.fast

This stub maintains backwards compatibility.
New code should import from: strategy.loaders.fast
"""
import warnings
warnings.warn(
    "strategy.fast_data_loader is deprecated. Use strategy.loaders.fast",
    DeprecationWarning,
    stacklevel=2
)
from strategy.loaders.fast import *
```

#### 5.4 strategy/stock_universe.py (STUB)
```python
"""
DEPRECATED: Implementation moved to strategy.infrastructure.stock_universe
"""
import warnings
warnings.warn(
    "strategy.stock_universe is deprecated. Use strategy.infrastructure.stock_universe",
    DeprecationWarning,
    stacklevel=2
)
from strategy.infrastructure.stock_universe import *
```

#### 5.5 strategy/backtest.py (STUB)
```python
"""
DEPRECATED: Implementation moved to strategy.infrastructure.backtest
"""
import warnings
warnings.warn(
    "strategy.backtest is deprecated. Use strategy.infrastructure.backtest",
    DeprecationWarning,
    stacklevel=2
)
from strategy.infrastructure.backtest import *
```

#### 5.6 strategy/unified_asx_loader.py (STUB)
```python
"""
DEPRECATED: Implementation moved to strategy.loaders.asx
"""
import warnings
warnings.warn(
    "strategy.unified_asx_loader is deprecated. Use strategy.loaders.asx",
    DeprecationWarning,
    stacklevel=2
)
from strategy.loaders.asx import *
```

**Checkpoint:** All stubs created, old imports still work

---

### Phase 6: Update Main __init__.py Facade

```python
"""
Quantitative Trading Strategy Package
======================================

This package provides a complete quantitative trading system including:
- Infrastructure: Configuration, backtesting, stock universes
- Loaders: Data ingestion from multiple sources
- Quant1: Production strategies (Momentum, OLMAR, Scanner)
- Quant2: Advanced strategies (Regime Detection, NCO)
- Pipeline: VectorBT backtesting pipeline

Usage:
    # New recommended imports
    from strategy.infrastructure.config import CONFIG
    from strategy.loaders.fast import FastDataLoader
    from strategy.quant1.optimization import PortfolioOptimizer
    
    # Legacy imports (still work, but deprecated)
    from strategy.config import CONFIG
    from strategy import DataLoader
"""

# =============================================================================
# FACADE EXPORTS (for backwards compatibility)
# =============================================================================

# Infrastructure
try:
    from strategy.infrastructure.config import (
        CONFIG, AssetConfig, is_us_ticker, get_us_tickers, get_asx_tickers, get_fx_cost
    )
except ImportError:
    from strategy.config import CONFIG, AssetConfig, is_us_ticker, get_us_tickers, get_asx_tickers, get_fx_cost

try:
    from strategy.infrastructure.stock_universe import (
        get_screener_universe, get_sp500_tickers, get_nasdaq100_tickers,
        get_asx200_tickers, get_core_etfs, get_us_etfs, get_asx_etfs
    )
except ImportError:
    pass

try:
    from strategy.infrastructure.backtest import PortfolioBacktester, BacktestResult
except ImportError:
    pass

# Loaders
try:
    from strategy.loaders.base import DataLoader, get_nasdaq_100_tickers
except ImportError:
    from strategy.data_loader import DataLoader, get_nasdaq_100_tickers

try:
    from strategy.loaders.fast import FastDataLoader
except ImportError:
    from strategy.fast_data_loader import FastDataLoader

try:
    from strategy.loaders.asx import UnifiedASXLoader
except ImportError:
    pass

# Quant1 Strategies
try:
    from strategy.quant1.momentum.signals import MomentumSignals, TechnicalSignals, CompositeSignal
except ImportError:
    MomentumSignals = None
    TechnicalSignals = None
    CompositeSignal = None

from strategy.quant1.optimization.optimizer import PortfolioOptimizer, CostAwareOptimizer

from strategy.quant1.olmar import OLMARStrategy, OLMARConfig

from strategy.quant1.scanner import QuallamaggieScanner

# Quant2 Strategies
try:
    from strategy.quant2.regime import HMMRegimeDetector
except ImportError:
    HMMRegimeDetector = None

try:
    from strategy.quant2.optimization import NCOOptimizer
except ImportError:
    NCOOptimizer = None

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Infrastructure
    'CONFIG',
    'AssetConfig',
    'is_us_ticker',
    'get_screener_universe',
    'PortfolioBacktester',
    # Loaders
    'DataLoader',
    'FastDataLoader',
    'UnifiedASXLoader',
    # Quant1
    'MomentumSignals',
    'PortfolioOptimizer',
    'CostAwareOptimizer',
    'OLMARStrategy',
    'QuallamaggieScanner',
    # Quant2
    'HMMRegimeDetector',
    'NCOOptimizer',
]

__version__ = '2.0.0'
```

**Checkpoint:** `from strategy import CONFIG` works

---

### Phase 7: Testing & Validation

```bash
# 7.1 Test new import paths
python -c "from strategy.infrastructure.config import CONFIG; print('✅ infrastructure.config')"
python -c "from strategy.loaders.fast import FastDataLoader; print('✅ loaders.fast')"
python -c "from strategy.loaders.asx import UnifiedASXLoader; print('✅ loaders.asx')"

# 7.2 Test backward compatibility (stubs)
python -c "from strategy.config import CONFIG; print('✅ strategy.config (stub)')"
python -c "from strategy.data_loader import DataLoader; print('✅ strategy.data_loader (stub)')"
python -c "from strategy.fast_data_loader import FastDataLoader; print('✅ strategy.fast_data_loader (stub)')"

# 7.3 Test facade imports
python -c "from strategy import CONFIG, DataLoader, FastDataLoader; print('✅ facade imports')"

# 7.4 Run full test suite
pytest tests/ -v

# 7.5 Test backend startup
sudo supervisorctl restart backend
sleep 5
curl http://localhost:8001/api/health

# 7.6 Test external scripts
python fetch_asx_data.py --indices-only --start-date 2024-12-01
```

**Checkpoint:** All tests pass, backend starts, external scripts work

---

### Phase 8: Cleanup

```bash
# 8.1 Remove old olps folder (replaced by quant1/olmar)
rm -rf strategy/olps

# 8.2 Clear pycache
find strategy -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# 8.3 Verify final structure
find strategy -type f -name "*.py" | head -30

# 8.4 Commit changes
git add -A
git commit -m "refactor: restructure strategy package into organized modules

- Move config, backtest, stock_universe to infrastructure/
- Move data loaders to loaders/
- Move hard_asset_* to quant1/hard_assets/
- Enhance quant1/scanner/ with backtest and tools
- Add utils/ for cache_monitor
- Add docs/ for documentation
- Create backward-compatible stubs at root
- Update __init__.py facade for clean exports

BREAKING CHANGES: None (all old imports still work via stubs)
"
```

---

## Import Path Compatibility

### Compatibility Matrix

| Old Path (Still Works) | New Path (Recommended) | Status |
|------------------------|------------------------|--------|
| `from strategy.config import CONFIG` | `from strategy.infrastructure.config import CONFIG` | ✅ Deprecated |
| `from strategy.data_loader import DataLoader` | `from strategy.loaders.base import DataLoader` | ✅ Deprecated |
| `from strategy.fast_data_loader import FastDataLoader` | `from strategy.loaders.fast import FastDataLoader` | ✅ Deprecated |
| `from strategy.stock_universe import get_screener_universe` | `from strategy.infrastructure.stock_universe import get_screener_universe` | ✅ Deprecated |
| `from strategy.backtest import PortfolioBacktester` | `from strategy.infrastructure.backtest import PortfolioBacktester` | ✅ Deprecated |
| `from strategy.unified_asx_loader import UnifiedASXLoader` | `from strategy.loaders.asx import UnifiedASXLoader` | ✅ Deprecated |
| `from strategy.optimizer import PortfolioOptimizer` | `from strategy.quant1.optimization import PortfolioOptimizer` | ✅ Deprecated |
| `from strategy.signals import MomentumSignals` | `from strategy.quant1.momentum import MomentumSignals` | ✅ Deprecated |
| `from strategy import CONFIG` | `from strategy import CONFIG` | ✅ Works (facade) |

### Deprecation Timeline

| Phase | Timeline | Action |
|-------|----------|--------|
| Phase 1 | Now | Stubs emit `DeprecationWarning` |
| Phase 2 | +3 months | Add logging of deprecated imports |
| Phase 3 | +6 months | Consider removing stubs |

---

## Code Patterns

### Stub File Template

```python
"""
DEPRECATED: Implementation moved to strategy.{new_module}.{file}

This stub maintains backwards compatibility.
New code should import from: strategy.{new_module}.{file}

Deprecation Timeline:
- Current: DeprecationWarning emitted
- +6 months: Stub will be removed
"""
import warnings

warnings.warn(
    "strategy.{old_name} is deprecated. "
    "Use strategy.{new_module}.{file} instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backwards compatibility
from strategy.{new_module}.{file} import *
```

### __init__.py Template for New Modules

```python
"""
{Module Name}
=============
{Brief description}

Public API:
    - Class1: Description
    - Class2: Description
    - function1: Description
"""

from strategy.{module}.{file1} import Class1, Class2
from strategy.{module}.{file2} import function1

__all__ = [
    'Class1',
    'Class2',
    'function1',
]
```

---

## Testing Checklist

### Pre-Migration Tests
- [ ] `pytest tests/ -v` passes
- [ ] Backend starts successfully
- [ ] All API endpoints respond
- [ ] External scripts run without errors

### Post-Migration Tests
- [ ] New import paths work
- [ ] Old import paths work (via stubs)
- [ ] Facade imports work
- [ ] `pytest tests/ -v` passes
- [ ] Backend starts successfully
- [ ] All API endpoints respond
- [ ] External scripts run without errors
- [ ] No circular import errors

### Verification Commands

```bash
# Quick verification script
python << 'EOF'
import sys

tests = [
    ("strategy.infrastructure.config", "CONFIG"),
    ("strategy.loaders.base", "DataLoader"),
    ("strategy.loaders.fast", "FastDataLoader"),
    ("strategy.loaders.asx", "UnifiedASXLoader"),
    ("strategy.config", "CONFIG"),  # stub
    ("strategy.data_loader", "DataLoader"),  # stub
    ("strategy", "CONFIG"),  # facade
]

import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

for module, attr in tests:
    try:
        exec(f"from {module} import {attr}")
        print(f"✅ from {module} import {attr}")
    except Exception as e:
        print(f"❌ from {module} import {attr}: {e}")
        sys.exit(1)

print("\n🎉 All imports successful!")
EOF
```

---

## Rollback Plan

### If Issues Occur

```bash
# Option 1: Git revert (recommended)
git revert HEAD

# Option 2: Restore from backup
rm -rf strategy
cp -r strategy_backup_YYYYMMDD strategy

# Option 3: Cherry-pick specific fixes
git checkout HEAD~1 -- strategy/specific_file.py
```

### Rollback Triggers
- Backend fails to start
- More than 3 tests fail
- API endpoints return 500 errors
- External scripts fail with ImportError

---

## Appendix

### Files Being Moved

| Original Location | New Location | Lines |
|-------------------|--------------|-------|
| `strategy/config.py` | `strategy/infrastructure/config.py` | 135 |
| `strategy/stock_universe.py` | `strategy/infrastructure/stock_universe.py` | 283 |
| `strategy/backtest.py` | `strategy/infrastructure/backtest.py` | 523 |
| `strategy/rebalance_config.py` | `strategy/infrastructure/rebalance.py` | 209 |
| `strategy/data_loader.py` | `strategy/loaders/base.py` | 404 |
| `strategy/fast_data_loader.py` | `strategy/loaders/fast.py` | 944 |
| `strategy/unified_asx_loader.py` | `strategy/loaders/asx.py` | 635 |
| `strategy/tiingo_data_loader.py` | `strategy/loaders/tiingo.py` | 219 |
| `strategy/us_ticker_loader.py` | `strategy/loaders/us_tickers.py` | 169 |
| `strategy/hard_asset_signals.py` | `strategy/quant1/hard_assets/signals.py` | 761 |
| `strategy/hard_asset_optimizer.py` | `strategy/quant1/hard_assets/optimizer.py` | 707 |
| `strategy/hard_asset_backtest.py` | `strategy/quant1/hard_assets/backtest.py` | 733 |
| `strategy/quallamaggie_backtest.py` | `strategy/quant1/scanner/backtest.py` | 919 |
| `strategy/quallamaggie_tools.py` | `strategy/quant1/scanner/tools.py` | 1010 |
| `strategy/fast_quallamaggie_scanner.py` | `strategy/quant1/scanner/fast.py` | 99 |
| `strategy/cache_health_monitor.py` | `strategy/utils/cache_monitor.py` | 342 |

**Total: 8,092 lines being reorganized**

### External Dependencies

Files outside `strategy/` that import from it:

| File | Imports |
|------|---------|
| `backend/routers/data.py` | `FastDataLoader`, `stock_universe` |
| `backend/routers/scanner.py` | `stock_universe` |
| `backend/dashboard_api.py` | `pipeline` |
| `fetch_asx_data.py` | `UnifiedASXLoader`, `stock_universe` |
| `tests/test_olmar.py` | `quant1.olmar` |
| `tests/test_signals.py` | `pipeline` |
| + 15 more scripts | Various |

All these will continue to work via stubs.

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 2024 | Initial draft |
| 2.0 | Dec 2024 | Revised after weakness analysis |

---

*Generated by Strategy Restructuring Analysis Tool*
