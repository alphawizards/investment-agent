# Data Gatherer

Stock data collection system using Yahoo Finance (free data source).

## Quick Start

```bash
# Setup database and add tickers
python data_gatherer/__main__.py setup

# Fetch historical data (10 years)
python data_gatherer/__main__.py fetch --verbose

# Daily update (incremental)
python data_gatherer/__main__.py update

# Check data freshness
python data_gatherer/__main__.py freshness
```

## Commands

| Command | Description |
|---------|-------------|
| `setup` | Initialize database and add default tickers |
| `fetch` | Fetch historical data for all tickers |
| `update` | Fetch latest daily prices (incremental) |
| `freshness` | Show data quality report |

## Options

- `--exchange all/us/asx` - Filter by exchange
- `--workers N` - Parallel workers (default: 5)
- `--verbose` - Show detailed progress
- `--start-date YYYY-MM-DD` - Custom start date

## Database Schema

- `tickers` - Stock universe (US + ASX)
- `daily_prices` - OHLCV data
- `data_quality_log` - Quality issues
- `update_history` - Update tracking

## Data Quality Checks

- Price sanity (High >= Low, Close in range)
- Zero volume detection
- Negative price detection

## Scheduled Updates

Add to crontab for daily updates:
```bash
0 6 * * * cd /path/to/investment-agent && python data_gatherer/__main__.py update
```
