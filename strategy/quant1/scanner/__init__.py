"""
Quallamaggie Momentum Scanner Package
=====================================
Scans a large universe of stocks and applies Quallamaggie filter criteria
to find momentum breakout candidates.

Filter Criteria:
1. Liquidity: Price > $5, 20D Avg Dollar Volume > $20M
2. Momentum: 3M Return >= 30%, 1M Return >= 10%, RS > SPY
3. Trend: Perfect SMA alignment, above SMA200, positive SMA50 slope
4. Consolidation: Price >= 85% of 126D high, ATR contraction
"""

from strategy.quant1.scanner.quallamaggie_scanner import (
    QuallamaggieScanner,
    run_scanner,
    SP500_TICKERS,
    NASDAQ_ADDITIONS,
    MOMENTUM_ADDITIONS,
    FULL_UNIVERSE
)

__all__ = [
    'QuallamaggieScanner',
    'run_scanner',
    'SP500_TICKERS',
    'NASDAQ_ADDITIONS',
    'MOMENTUM_ADDITIONS',
    'FULL_UNIVERSE',
]
