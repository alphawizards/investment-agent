"""
Infrastructure Config Re-Export
================================
This module re-exports config from the parent strategy package
for backward compatibility after the restructure.
"""

# Re-export from parent package
from strategy.config import (
    CONFIG,
    BACKTEST_CONFIG,
    Config,
    BacktestConfig,
    AssetConfig,
    is_us_ticker,
    get_us_tickers,
    get_asx_tickers,
    get_fx_cost
)

__all__ = [
    'CONFIG',
    'BACKTEST_CONFIG',
    'Config', 
    'BacktestConfig',
    'AssetConfig',
    'is_us_ticker',
    'get_us_tickers',
    'get_asx_tickers',
    'get_fx_cost'
]
