"""
Quantitative Trading Dashboard API
===================================
Unified FastAPI application entry point.

Features:
- RESTful API for trade tracking
- Portfolio metrics calculation
- Dashboard data aggregation
- Strategy backtesting
- Stock scanning
- Data management (Tiingo + yFinance)

API Routes:
- /api/trades/* - Trade management
- /api/data/* - Data refresh & status
- /api/strategies/* - Strategy backtesting
- /api/dashboard/* - Dashboard data
- /api/scanner/* - Stock scanning
"""

import sys
import importlib
from pathlib import Path

# Add paths for imports
_backend_dir = Path(__file__).parent
_app_dir = _backend_dir.parent

sys.path.insert(0, str(_app_dir))
sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime

# Dynamic imports to handle both module and direct execution
def _import_module(module_name):
    """Import module with fallback for both execution modes."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return importlib.import_module(f"backend.{module_name}")

# Import all required modules
config_module = _import_module("config")
db_module = _import_module("database.connection")
trades_module = _import_module("routers.trades")
data_module = _import_module("routers.data")
strategies_module = _import_module("routers.strategies")
dashboard_module = _import_module("routers.dashboard")
scanner_module = _import_module("routers.scanner")

settings = config_module.settings
init_db = db_module.init_db
init_async_db = db_module.init_async_db
trades_router = trades_module.router
data_router = data_module.router
strategies_router = strategies_module.router
dashboard_router = dashboard_module.router
scanner_router = scanner_module.router

# Import universes router
universes_module = _import_module("routers.universes")
universes_router = universes_module.router

# Import quant2 router
quant2_module = _import_module("routers.quant2")
quant2_router = quant2_module.router

# Import validation router (DSR/PSR)
validation_module = _import_module("routers.validation")
validation_router = validation_module.router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("\n" + "="*60)
    print("Starting Quant Trading Dashboard API v2.0")
    print("="*60)
    
    await init_async_db()
    print("[OK] Database initialized (Async)")
    
    # Check Tiingo API key
    if settings.TIINGO_API_KEY:
        print(f"[OK] Tiingo API configured (Premium: {settings.TIINGO_IS_PREMIUM})")
    else:
        print("[!] Tiingo API key not configured - US data will use yFinance fallback")
    
    print(f"[OK] CORS origins: {settings.cors_origins_list}")
    print(f"[OK] Server ready at http://{settings.HOST}:{settings.PORT}")
    print("="*60 + "\n")
    
    yield
    
    # Shutdown
    print("\nbye Shutting down API...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Quantitative Trading Dashboard API v2.0
    
    A comprehensive API for algorithmic trading strategy management.
    
    ### Features
    - **Trade Management**: Create, read, update, delete trades
    - **Portfolio Metrics**: Real-time P&L, win rate, Sharpe ratio
    - **Strategy Backtesting**: Run and compare trading strategies
    - **Stock Scanning**: Find trading opportunities
    - **Data Management**: Refresh market data from Tiingo/yFinance
    
    ### Data Sources
    - **Tiingo** (Premium): US Stocks, ETFs, Mutual Funds, Gold
    - **yFinance**: ASX Stocks, ASX ETFs, VIX, BTC
    
    ### Strategy Categories
    - **Quant 1.0**: Momentum, HRP, Dual Momentum, Inverse Volatility
    - **Quant 2.0**: Regime Detection, Stat Arb, Residual Momentum, Meta-Labeling
    - **Mean Reversion**: OLMAR
    - **Breakout**: Quallamaggie
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(trades_router)
app.include_router(data_router)
app.include_router(strategies_router)
app.include_router(dashboard_router)
app.include_router(scanner_router)
app.include_router(universes_router)
app.include_router(quant2_router)
app.include_router(validation_router)

# Mount production dashboard build
dashboard_dist_path = _app_dir / "dashboard" / "dist"
if dashboard_dist_path.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_dist_path), html=True), name="dashboard")
    print(f"[OK] Dashboard mounted at /dashboard from {dashboard_dist_path}")
else:
    print(f"[!] Dashboard dist not found at {dashboard_dist_path} - run 'npm run build' in dashboard/")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions - masks details in production."""
    import traceback
    import uuid
    
    # Generate request ID for correlation
    request_id = str(uuid.uuid4())[:8]
    
    # Log full exception server-side (always)
    print(f"ERROR [{request_id}] {request.url}: {traceback.format_exc()}")
    
    # Return safe response - mask details in production
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "request_id": request_id,
            "path": str(request.url)
        }
    )


# Health check endpoint
@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/", tags=["root"])
def root():
    """Root endpoint with API information."""
    return {
        "message": "Quant Trading Dashboard API v2.0",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "trades": "/api/trades",
            "data": "/api/data",
            "strategies": "/api/strategies",
            "dashboard": "/api/dashboard",
            "scanner": "/api/scanner",
            "universes": "/api/universes"
        },
        "data_sources": {
            "tiingo": "US Stocks, ETFs, Mutual Funds, Gold (Premium)",
            "yfinance": "ASX Stocks, ASX ETFs, VIX, BTC"
        }
    }


@app.get("/api", tags=["root"])
def api_root():
    """API root with available endpoints."""
    return {
        "api_version": "2.0.0",
        "endpoints": [
            {"path": "/api/trades", "description": "Trade management"},
            {"path": "/api/data", "description": "Data refresh & status"},
            {"path": "/api/strategies", "description": "Strategy backtesting"},
            {"path": "/api/dashboard", "description": "Dashboard data"},
            {"path": "/api/scanner", "description": "Stock scanning"}
        ]
    }


def start_server():
    """Start the API server."""
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    start_server()
