"""
Quantitative Global Investing Strategy
=======================================

A comprehensive quantitative investing framework for Australian retail investors.

Package Structure (v2.0):
- infrastructure/: Configuration, backtesting, stock universes
- loaders/: Data ingestion from multiple sources
- quant1/: Production strategies (Momentum, OLMAR, Scanner, Hard Assets)
- quant2/: Advanced strategies (Regime Detection, NCO)
- pipeline/: VectorBT backtesting pipeline
- utils/: Utility functions

Usage (Recommended - New Import Paths):
    from strategy.infrastructure.config import CONFIG
    from strategy.loaders.fast import FastDataLoader
    from strategy.quant1.optimization import PortfolioOptimizer
    
Usage (Legacy - Still Supported):
    from strategy.config import CONFIG
    from strategy import DataLoader
"""

# =============================================================================
# INFRASTRUCTURE IMPORTS (Config - no external dependencies)
# =============================================================================
try:
    from strategy.infrastructure.config import CONFIG, BACKTEST_CONFIG, AssetConfig
    from strategy.infrastructure.config import is_us_ticker, get_us_tickers, get_asx_tickers, get_fx_cost
except ImportError:
    try:
        from strategy.config import CONFIG, BACKTEST_CONFIG, AssetConfig
        from strategy.config import is_us_ticker, get_us_tickers, get_asx_tickers, get_fx_cost
    except ImportError:
        CONFIG = None
        BACKTEST_CONFIG = None
        AssetConfig = None
        is_us_ticker = None
        get_us_tickers = None
        get_asx_tickers = None
        get_fx_cost = None

# =============================================================================
# LOADER IMPORTS (Optional - requires yfinance etc)
# =============================================================================
try:
    from strategy.loaders.base import DataLoader
except ImportError:
    DataLoader = None

# =============================================================================
# QUANT1 IMPORTS (SIGNALS & OPTIMIZATION)
# =============================================================================
# Optional imports - require pandas_ta which needs Python >= 3.12
try:
    from strategy.quant1.momentum.signals import MomentumSignals, TechnicalSignals, CompositeSignal
except ImportError:
    MomentumSignals = None
    TechnicalSignals = None
    CompositeSignal = None

try:
    from strategy.quant1.optimization.optimizer import PortfolioOptimizer, CostAwareOptimizer
except ImportError:
    PortfolioOptimizer = None
    CostAwareOptimizer = None

# =============================================================================
# BACKTEST IMPORTS (Optional - requires vectorbt)
# =============================================================================
try:
    from strategy.infrastructure.backtest import PortfolioBacktester, VectorBTBacktester
except ImportError:
    PortfolioBacktester = None
    VectorBTBacktester = None

# =============================================================================
# MAIN STRATEGY CLASS
# =============================================================================
try:
    from strategy.main import QuantStrategy
except ImportError:
    QuantStrategy = None

# =============================================================================
# PACKAGE METADATA
# =============================================================================
__version__ = "2.0.0"
__author__ = "Quantitative Strategy Team"

__all__ = [
    # Infrastructure
    'CONFIG',
    'BACKTEST_CONFIG',
    'AssetConfig',
    'is_us_ticker',
    'get_us_tickers',
    'get_asx_tickers',
    'get_fx_cost',
    # Loaders
    'DataLoader',
    # Signals
    'MomentumSignals',
    'TechnicalSignals',
    'CompositeSignal',
    # Optimization
    'PortfolioOptimizer',
    'CostAwareOptimizer',
    # Backtest
    'PortfolioBacktester',
    'VectorBTBacktester',
    # Main
    'QuantStrategy',
]
