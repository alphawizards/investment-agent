# Run Investment Analysis

Analyze stocks, run backtests, and get portfolio recommendations.

## Usage

```
/invest <command> [options]
```

## Commands

### analyze <ticker>
Analyze a single stock's performance.

```
/invest analyze AAPL
/invest analyze BHP
```

Shows:
- Price history and returns
- Volatility metrics
- Recent momentum signals

### backtest <strategy> [tickers]
Run a backtest on a strategy.

```
/invest backtest momentum AAPL MSFT GOOGL
/invest backtest olmar
/invest backtest dual_momentum
```

### portfolio <tickers> [weights]
Analyze a portfolio's risk characteristics.

```
/invest portfolio SPY QQQ GLD
/invest portfolio SPY QQQ GLD --weights 0.6 0.3 0.1
```

Shows:
- Portfolio returns
- Volatility and Sharpe ratio
- Risk contribution by asset
- Correlation matrix

### scan
Scan for trading opportunities across your stock universe.

```
/vest scan --momentum
/invest scan --value
```

### report
Generate a comprehensive investment report.

```
/invest report --portfolio SPY QQQ GLD --value 100000
```

## Examples

### Analyze a stock
```
/invest analyze TSLA
```

### Backtest momentum strategy
```
/invest backtest momentum SPY QQQ VOO
```

### Analyze portfolio risk
```
/invest portfolio AAPL MSFT GOOGL --weights 0.4 0.3 0.3
```

## Notes

- Default analysis uses 1 year of data
- Backtests use your local database (run `data_gatherer setup` first)
- Use `--help` with any command for more options
