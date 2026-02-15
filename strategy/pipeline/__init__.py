"""
Trading Pipeline
================
Modular 4-layer trading pipeline for strategy-agnostic investing.

Layers:
1. Data Layer - OpenBB/yfinance for market data
2. Signal Layer - VectorBT for fast indicator calculation
3. Allocation Layer - Riskfolio-Lib for portfolio optimization
4. Reporting Layer - QuantStats for performance analysis
"""

from .data_layer import DataManager
from .signal_layer import SignalManager, BaseStrategy
from .allocation_layer import AllocationManager
from .reporting_layer import ReportingManager
from .pipeline import TradingPipeline

__all__ = [
    'DataManager',
    'SignalManager',
    'BaseStrategy',
    'AllocationManager',
    'ReportingManager',
    'TradingPipeline'
]
