"""
Dashboard API
==============
FastAPI backend for the trading dashboard.

Security features:
- Rate limiting (slowapi)
- API key authentication with SHA256 hashing
- CORS restriction from environment
"""

import hashlib
import secrets
from functools import lru_cache

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from pathlib import Path

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import pipeline and config
from strategy.pipeline.pipeline import TradingPipeline, PipelineConfig, run_daily_scan
from strategy.pipeline.reporting_layer import ReportingManager
from strategy.pipeline.config import settings


# ============== Rate Limiting ==============
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="Trading Dashboard API",
    description="API for the Quantitative Trading Pipeline Dashboard",
    version="2.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS from environment config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)


# ============== Authentication ==============
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str) -> bool:
    """Verify API key using constant-time comparison to prevent timing attacks."""
    if not api_key:
        return False
    
    # Prefer hashed comparison
    if settings.API_KEY_HASH:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return secrets.compare_digest(key_hash, settings.API_KEY_HASH)
    
    # Fallback to plain comparison (dev only)
    return secrets.compare_digest(api_key, settings.API_KEY)


async def require_api_key(api_key: str = Depends(api_key_header)) -> str:
    """Dependency that requires valid API key."""
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


# ============== State Management ==============
class PipelineState:
    """Application state container (replaces global variables)."""
    def __init__(self):
        self.pipeline: Optional[TradingPipeline] = None
        self.last_scan_time: Optional[datetime] = None
        self.cached_results: Dict[str, Any] = {}


@lru_cache()
def get_pipeline_state() -> PipelineState:
    """Get singleton pipeline state."""
    return PipelineState()


# ============== Models ==============

class ScanRequest(BaseModel):
    strategies: Optional[List[str]] = None
    start_date: Optional[str] = "2020-01-01"
    
    @validator('start_date')
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Invalid date format. Use YYYY-MM-DD')
    

class StrategyMetrics(BaseModel):
    strategy_name: str
    final_value: float
    total_return: str
    cagr: str
    volatility: str
    sharpe_ratio: str
    sortino_ratio: str
    max_drawdown: str
    calmar_ratio: str
    win_rate: str
    rolling_sharpe_30d: str
    rolling_sharpe_90d: str


class DashboardData(BaseModel):
    last_updated: str
    strategies: List[StrategyMetrics]
    comparison_table: List[Dict[str, str]]
    equity_curves: Dict[str, List[float]]


# ============== Endpoints ==============

@app.get("/")
async def root():
    """Health check endpoint (no auth required)."""
    return {
        "status": "healthy",
        "service": "Trading Dashboard API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "security": "enabled"
    }


@app.get("/api/dashboard")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_dashboard_data(
    request: Request,
    state: PipelineState = Depends(get_pipeline_state),
    _: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """
    Get dashboard data including all strategy metrics.
    Requires API key authentication.
    """
    if not state.cached_results:
        # Try to load from file
        results_file = Path("reports/pipeline_results.json")
        if results_file.exists():
            try:
                with open(results_file) as f:
                    state.cached_results = json.load(f)
            except json.JSONDecodeError:
                raise HTTPException(500, "Corrupted results file")
    
    if not state.cached_results:
        return {
            "last_updated": None,
            "strategies": [],
            "comparison_table": [],
            "equity_curves": {},
            "message": "No scan results available. Run a scan first."
        }
    
    return {
        "last_updated": state.cached_results.get('generated_at'),
        "strategies": list(state.cached_results.get('strategies', {}).values()),
        "comparison_table": _format_comparison_table(state.cached_results),
        "config": state.cached_results.get('config', {})
    }


@app.post("/api/scan")
@limiter.limit(settings.RATE_LIMIT_SCAN)
async def run_scan(
    request: Request,
    scan_request: ScanRequest,
    state: PipelineState = Depends(get_pipeline_state),
    _: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """
    Run a strategy scan.
    Requires API key authentication.
    Rate limited to 5 requests per minute.
    """
    # Initialize pipeline
    config = PipelineConfig(
        start_date=scan_request.start_date
    )
    state.pipeline = TradingPipeline(config)
    
    try:
        if scan_request.strategies:
            # Run specific strategies
            for strategy in scan_request.strategies:
                state.pipeline.run(strategy)
        else:
            # Run all strategies
            state.pipeline.run_all_strategies()
        
        # Save results
        state.pipeline.save_results()
        state.cached_results = state.pipeline.export_results_json()
        state.last_scan_time = datetime.now()
        
        return {
            "status": "success",
            "message": f"Scan completed for {len(state.pipeline._results)} strategies",
            "timestamp": state.last_scan_time.isoformat(),
            "strategies": list(state.pipeline._results.keys())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategies")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_strategies(
    request: Request,
    state: PipelineState = Depends(get_pipeline_state)
) -> Dict[str, Any]:
    """Get list of available strategies (no auth required)."""
    if state.pipeline is None:
        # Create temporary pipeline to get strategies
        temp_pipeline = TradingPipeline()
        strategies = temp_pipeline.signal_manager.list_strategies()
    else:
        strategies = state.pipeline.signal_manager.list_strategies()
    
    return {
        "strategies": strategies
    }


@app.get("/api/strategy/{strategy_name}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_strategy_details(
    strategy_name: str,
    request: Request,
    state: PipelineState = Depends(get_pipeline_state),
    _: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Get detailed metrics for a specific strategy. Requires auth."""
    if not state.cached_results or strategy_name not in state.cached_results.get('strategies', {}):
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_name} not found")
    
    return state.cached_results['strategies'][strategy_name]


@app.get("/api/report/{strategy_name}")
async def get_strategy_report(strategy_name: str):
    """Get HTML report for a strategy (no auth for viewing reports)."""
    report_path = Path(f"reports/{strategy_name}_report.html")
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(report_path, media_type="text/html")


@app.get("/api/comparison")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_comparison(
    request: Request,
    state: PipelineState = Depends(get_pipeline_state),
    _: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Get strategy comparison table. Requires auth."""
    if not state.cached_results:
        return {"comparison": []}
    
    return {
        "comparison": _format_comparison_table(state.cached_results)
    }


@app.get("/api/rolling/{strategy_name}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_rolling_metrics(
    strategy_name: str,
    request: Request,
    window: int = 30,
    state: PipelineState = Depends(get_pipeline_state),
    _: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Get rolling metrics for a strategy. Requires auth."""
    if state.pipeline is None or strategy_name not in state.pipeline._results:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    result = state.pipeline._results[strategy_name]
    returns = result.portfolio_returns
    
    # Calculate rolling metrics
    reporting = ReportingManager()
    rolling = reporting.calculate_rolling_metrics(returns, windows=[window])
    
    return {
        "strategy_name": strategy_name,
        "window": window,
        "rolling_metrics": rolling.tail(20).to_dict()
    }


# ============== Helper Functions ==============

def _format_comparison_table(results: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format results into comparison table."""
    comparison = []
    
    for name, data in results.get('strategies', {}).items():
        metrics = data.get('metrics', {})
        comparison.append({
            'Strategy': name,
            'Final Value': f"${data.get('final_value', 0):,.0f}",
            **metrics
        })
    
    return comparison


# ============== Main ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # nosec B104
