"""
Central Configuration for Strategy Package
==========================================

This module contains all configuration settings for the strategy package.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import os

@dataclass
class AssetConfig:
    """Asset configuration."""
    ticker: str
    asset_type: str  # 'stock', 'etf', 'index', 'fx'
    currency: str
    exchange: str

@dataclass
class BacktestConfig:
    """Backtest configuration."""
    INITIAL_CAPITAL_AUD: float = 100000.0
    RISK_FREE_RATE: float = 0.04
    TRADING_DAYS_PER_YEAR: int = 252

class Config:
    """Global configuration."""
    RISK_FREE_RATE = 0.04

    # API Keys
    TIINGO_API_KEY = os.getenv("TIINGO_API_KEY")

    # Paths
    CACHE_DIR = "cache"
    DATA_DIR = "data"

    # Data Sources
    USE_TIINGO = True
    USE_YFINANCE = True
    USE_NORGATE = False

    # ============== MOMENTUM SIGNALS ==============
    # Lookback periods (in trading days)
    MOMENTUM_LOOKBACK_LONG = 252   # 1 year
    MOMENTUM_LOOKBACK_MEDIUM = 126  # 6 months
    MOMENTUM_LOOKBACK_SHORT = 21    # 1 month
    
    # Composite signal weights
    MOMENTUM_WEIGHT = 0.5
    TECHNICAL_WEIGHT = 0.3
    VOLATILITY_WEIGHT = 0.2
    
    # RSI Parameters
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    
    # MACD Parameters
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9

    # ============== OPTIMIZATION ==============
    EXPECTED_ALPHA = 0.02  # Expected alpha threshold for cost-benefit gate
    
    # Portfolio Constraints
    MIN_POSITION_WEIGHT = 0.01   # 1% minimum
    MAX_POSITION_WEIGHT = 0.25   # 25% maximum
    MAX_SECTOR_WEIGHT = 0.40    # 40% maximum per sector
    
    # Aliases for compatibility
    MIN_WEIGHT = MIN_POSITION_WEIGHT
    MAX_WEIGHT = MAX_POSITION_WEIGHT

CONFIG = Config()
BACKTEST_CONFIG = BacktestConfig()

def is_us_ticker(ticker: str) -> bool:
    """Check if ticker is a US ticker."""
    return not ticker.endswith('.AX')

def get_us_tickers() -> List[str]:
    """Get list of US tickers."""
    return []

def get_asx_tickers() -> List[str]:
    """Get list of ASX tickers."""
    return []

def get_nasdaq_100_tickers() -> List[str]:
    """Get list of Nasdaq 100 tickers."""
    return ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "PEP", "AVGO", "CSCO"]

def get_fx_cost(currency: str) -> float:
    """Get FX cost for currency."""
    if currency == 'AUD':
        return 0.0
    return 0.005  # 50 bps
