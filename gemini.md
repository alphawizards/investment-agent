# Investment Agent - Project Context

## Project Overview
- FastAPI-based quantitative trading dashboard
- Strategies: Dual Momentum, HRP, Mean Reversion, ML Meta-Labeling
- Data: Tiingo (primary), yFinance (fallback)

## Key Files
| File | Purpose |
|------|---------|
| backend/main.py | FastAPI entry point |
| backend/config.py | Settings (DB, API keys, CORS) |
| strategy/config.py | Strategy parameters |
| strategy/fast_data_loader.py | Data fetching with caching |

## How to Run
```powershell
# Backend (MUST use these exact commands)
$env:PYTHONPATH="C:\Users\ckr_4\01 Projects\investment-agent"
cd "C:\Users\ckr_4\01 Projects\investment-agent\backend"
python main.py

# API: http://localhost:8000
# Dashboard: http://localhost:8000/dashboard/
# API Docs: http://localhost:8000/docs
```

## Configuration
- API Keys: `backend/.env` (Tiingo, AWS)
- Database: SQLite - **MUST use** `sqlite:///../data/trades.db` in `.env` (critical!)
- Cache: Parquet files in `cache/`

## Additional Resources
- Detailed code review: See `review_notes.md` in project root
- Full documentation: See `README.md` in project root

## Recent Fixes
- **Async refactor complete**: All routers, services, and repositories now use async/await for high-performance, non-blocking I/O.
- **Config centralized**: Strategy parameters moved to `strategy/config.py` for easier tuning.
- **Fixed DB path issue**: Updated `.env` to use the correct relative path for the SQLite database.
- **Missing Imports**: Added `asyncio` and `aiofiles` where necessary for the async transition.

## Known Issues
- No incremental loading in `fast_data_loader.py` (fetches full history for missing tickers).
- Retry logic in `fast_data_loader.py` is defined in a class but not yet implemented in the fetch methods.
- ASX ticker handling (`.AX` suffix) is incomplete in the data gatherer.

## API Endpoints
- `/health` - Health check
- `/api/trades` - Trade management (CRUD + metrics)
- `/api/data` - Data refresh and status
- `/api/strategies` - Backtest execution and results
- `/api/dashboard` - Aggregated dashboard data
- `/api/scanner` - Stock scanning (Quallamaggie, etc.)
- `/api/universes` - Stock universe metadata
- `/api/validation` - Statistical significance (DSR/PSR)
