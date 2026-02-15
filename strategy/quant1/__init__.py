"""
Quant 1 Strategy Package
========================
Consolidated package for HRP, OLMAR, and Quallamaggie strategies.

This package contains:
- momentum: Dual Momentum and Technical signal generation
- optimization: Portfolio optimization using Riskfolio-Lib (HRP, MVO, etc.)
- olmar: OLMAR (On-Line Moving Average Reversion) strategy
- scanner: Quallamaggie momentum breakout scanner

Usage:
    from strategy.quant1.momentum.signals import MomentumSignals, CompositeSignal
    from strategy.quant1.optimization.optimizer import PortfolioOptimizer
    from strategy.quant1.olmar import OLMARStrategy
    from strategy.quant1.scanner import QuallamaggieScanner
"""

# Momentum signals (optional - requires pandas_ta which needs Python 3.12)
try:
    from strategy.quant1.momentum.signals import MomentumSignals, TechnicalSignals, CompositeSignal
except ImportError:
    MomentumSignals = None
    TechnicalSignals = None
    CompositeSignal = None

# Optimization (requires riskfolio-lib)
from strategy.quant1.optimization.optimizer import PortfolioOptimizer, CostAwareOptimizer, SectorConstrainedOptimizer

# OLMAR strategy
from strategy.quant1.olmar.olmar_strategy import OLMARStrategy, OLMARConfig, create_olmar_weekly, create_olmar_monthly

# Scanner
from strategy.quant1.scanner.quallamaggie_scanner import QuallamaggieScanner, run_scanner

__all__ = [
    # Momentum (may be None if pandas_ta not available)
    'MomentumSignals',
    'TechnicalSignals', 
    'CompositeSignal',
    # Optimization
    'PortfolioOptimizer',
    'CostAwareOptimizer',
    'SectorConstrainedOptimizer',
    # OLMAR
    'OLMARStrategy',
    'OLMARConfig',
    'create_olmar_weekly',
    'create_olmar_monthly',
    # Scanner
    'QuallamaggieScanner',
    'run_scanner',
]
