# Quallamaggie Swing Trading Strategy

## Executive Summary

A systematic **momentum breakout swing trading pipeline** based on Kristjan Kullamägi's methodology, implemented in Python using `pandas` for vectorized filtering and `Riskfolio-Lib` for portfolio optimization.

> **Key Insight**: Focus on capturing explosive moves in leading stocks through precise pattern recognition, strict filtering criteria, and Mean-Variance optimized position sizing.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QullamaggieStrategy Pipeline                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│   │  DATA INGESTION  │ -> │  MODULE 1:       │ -> │  MODULE 2:   │  │
│   │                  │    │  FILTERING       │    │  OPTIMIZATION│  │
│   │  MultiIndex      │    │                  │    │              │  │
│   │  Panel Data      │    │  Liquidity +     │    │  Riskfolio   │  │
│   │  (Ticker, Date)  │    │  Momentum +      │    │  Mean-Var    │  │
│   │                  │    │  Trend +         │    │  Sharpe Max  │  │
│   │                  │    │  Consolidation   │    │              │  │
│   └──────────────────┘    └──────────────────┘    └──────────────┘  │
│                                                                      │
│   Output: {ticker: final_weight} dictionary                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Input Data Specification

### Data Structure

```python
# Required Format: Pandas DataFrame with MultiIndex
# Level 0: 'Ticker'
# Level 1: 'Date'
# Columns: ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
```

### Critical Price Column Rules

| Calculation Type | Use Column | Rationale |
|------------------|------------|-----------|
| Momentum & Returns | **Adj Close** | Accounts for dividends/splits |
| Moving Averages | **Adj Close** | Consistent with return calculations |
| Price Level Filters (>$5) | **Close (Raw)** | Actual tradeable price |
| Dollar Volume | **Close × Volume** | Real market liquidity |

> **⚠️ WARNING**: Mixing adjusted/raw prices incorrectly causes look-ahead bias and split-adjustment errors.

---

## Module 1: Filtering Logic

All filters applied sequentially using vectorized pandas operations.

### 1.1 Liquidity Filters

| Rule | Implementation |
|------|----------------|
| Raw Close > $5.00 | `df['Close'] > 5.0` |
| 20-Day Avg Dollar Volume > $20M | `(df['Close'] * df['Volume']).rolling(20).mean() > 20_000_000` |

### 1.2 Momentum Filters (The Engine)

| Rule | Threshold | Implementation |
|------|-----------|----------------|
| 3-Month Return | ≥ 30% | `df['Adj Close'].pct_change(63) >= 0.30` |
| 1-Month Return | ≥ 10% | `df['Adj Close'].pct_change(21) >= 0.10` |
| Relative Strength vs SPY | Stock > SPY | `stock_3m_return > spy_3m_return` |

### 1.3 Trend Architecture Filters

| Rule | Description |
|------|-------------|
| **Perfect EMA Alignment** | Adj Close > SMA_10 > SMA_20 > SMA_50 |
| **Above 200 SMA** | Adj Close > SMA_200 |
| **Smooth Uptrend** | Linear regression slope of SMA_50 over 10 days > 0 |

```python
# Perfect Alignment Check
perfect_alignment = (
    (adj_close > sma_10) & 
    (sma_10 > sma_20) & 
    (sma_20 > sma_50) & 
    (adj_close > sma_200)
)

# SMA_50 Slope (regression over 10 days)
from scipy.stats import linregress
slope = linregress(range(10), sma_50.iloc[-10:]).slope
valid_slope = slope > 0
```

### 1.4 Consolidation Filters (The Setup)

| Pattern | Rule | Implementation |
|---------|------|----------------|
| **High Tight Flag** | Current ≥ 85% of 126-day High | `adj_close >= 0.85 * high.rolling(126).max()` |
| **Volatility Contraction** | Current ATR(14) < 20-day Avg ATR | `atr_14 < atr_14.rolling(20).mean()` |

```python
# Volatility Contraction Pattern (VCP)
current_atr = df['ATR_14']
avg_atr = df['ATR_14'].rolling(20).mean()
volatility_contracting = current_atr < avg_atr
```

---

## Module 2: Portfolio Optimization

### Trigger Condition
Run optimization ONLY on tickers that pass ALL Module 1 filters.

### Methodology

| Parameter | Value |
|-----------|-------|
| **Library** | Riskfolio-Lib |
| **Data Input** | Adj Close returns for valid tickers |
| **Lookback Window** | 126 trading days (6 months) |
| **Model** | Mean-Variance (MV) |
| **Objective** | Maximize Sharpe Ratio |

### Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Max weight per asset | 20% | Diversification limit |
| Short selling | Prohibited | Long-only strategy |
| Min weight | 0% | Can exclude assets |

### Risk Control Layer (Post-Optimization)

After optimization, apply a **Technical Risk Check**:

```python
# For each asset:
technical_risk = (entry_price - stop_loss) / entry_price

# Risk budget check:
position_risk = optimized_weight * technical_risk

# Constraint: Position risk must not exceed 1% of account
if position_risk > 0.01:
    scaled_weight = 0.01 / technical_risk
else:
    scaled_weight = optimized_weight
```

**Example:**

| Ticker | Opt Weight | Technical Risk | Position Risk | Action |
|--------|------------|----------------|---------------|--------|
| NVDA | 20% | 6% | 1.2% | Scale to 16.7% |
| AAPL | 15% | 4% | 0.6% | Keep 15% |
| TSLA | 20% | 8% | 1.6% | Scale to 12.5% |

---

## Implementation Blueprint

### Class Structure

```python
class QullamaggieStrategy:
    """
    Systematic Quallamaggie swing trading pipeline.
    
    Modules:
    1. filter_universe() - Apply momentum/consolidation filters
    2. optimize_weights() - Riskfolio-Lib MV optimization
    """
    
    def __init__(self, 
                 min_price: float = 5.0,
                 min_dollar_volume: float = 20_000_000,
                 momentum_3m_threshold: float = 0.30,
                 momentum_1m_threshold: float = 0.10,
                 htf_threshold: float = 0.85,
                 max_weight: float = 0.20,
                 max_position_risk: float = 0.01):
        """Initialize with configurable thresholds."""
        pass
    
    def filter_universe(self, df: pd.DataFrame) -> List[str]:
        """
        Apply all filtering rules to multi-asset universe.
        
        Args:
            df: MultiIndex DataFrame (Ticker, Date)
            
        Returns:
            List of valid tickers passing all criteria
        """
        pass
    
    def optimize_weights(self, 
                         valid_tickers: List[str],
                         returns_data: pd.DataFrame) -> Dict[str, float]:
        """
        Run Mean-Variance optimization on filtered universe.
        
        Args:
            valid_tickers: Tickers passing Module 1 filters
            returns_data: Adj Close returns DataFrame
            
        Returns:
            Dictionary {ticker: final_weight} after risk adjustments
        """
        pass
```

### Helper Functions

```python
def fetch_data(tickers: List[str], 
               start: str = '2023-01-01',
               end: str = None) -> pd.DataFrame:
    """
    Fetch and format data into required MultiIndex structure.
    
    Args:
        tickers: List of ticker symbols
        start: Start date string
        end: End date (default: today)
        
    Returns:
        MultiIndex DataFrame (Ticker, Date) with OHLCV columns
    """
    import yfinance as yf
    
    data = yf.download(tickers, start=start, end=end)
    
    # Reshape to MultiIndex
    df = data.stack(level=1).reset_index()
    df.columns = ['Date', 'Ticker', 'Adj Close', 'Close', 
                  'High', 'Low', 'Open', 'Volume']
    df = df.set_index(['Ticker', 'Date'])
    
    return df
```

---

## Entry & Exit Rules

### Entry Criteria (Opening Range High)

| Timeframe | Use Case |
|-----------|----------|
| 1-min ORH | Aggressive entries, episodic pivots |
| 5-min ORH | Standard breakouts |
| 30-min ORH | Conservative, fewer shakeouts |
| 60-min ORH | Confirmed breakouts |

**Entry Checklist:**
- [ ] All Module 1 filters passed
- [ ] Price breaking pivot on volume (1.5x+ average)
- [ ] RS Line at/near 52-week high
- [ ] Market regime favorable (uptrend/neutral)

### Exit Strategy (Tiered EMA)

| Trigger | Action | Position |
|---------|--------|----------|
| Daily close < 10 EMA | Sell 25% | 75% remaining |
| Daily close < 20 EMA | Sell 50% of remaining | 37.5% remaining |
| Daily close < 50 EMA | Close 100% | 0% |

> **Rule**: Exit on CLOSE below EMA, not intraday touches.

---

## Expected Performance

| Metric | Expected Range |
|--------|----------------|
| Win Rate | 25-35% |
| Average Winner | +15% to +30% |
| Average Loser | -3% to -7% |
| Win/Loss Ratio | 3:1 to 5:1 |
| Profit Factor | 2.0 - 4.0 |
| Max Drawdown | 15-30% |
| Annual Return | 50-200%+ (momentum markets) |

> **Note**: Strategy excels in strong uptrends (2020, 2021) but struggles in choppy/bear markets.

---

## Implementation Files

| File | Description |
|------|-------------|
| `strategy/quallamaggie_tools.py` | Core `QullamaggieStrategy` class |
| `strategy/quallamaggie_backtest.py` | Backtesting framework |
| `strategy/pipeline/signal_layer.py` | Integration with signal pipeline |

---

## References

1. **Qullamaggie YouTube/Twitch** - Original methodology
2. **Mark Minervini** - SEPA methodology (similar)
3. **William O'Neil** - CAN SLIM foundations
4. **Riskfolio-Lib** - Portfolio optimization library

---

## Version History

- **v2.0.0** (2024-12-25): Refactored with systematic filtering and Riskfolio optimization
- **v1.0.0** (2024-12-25): Initial documentation from video analysis
