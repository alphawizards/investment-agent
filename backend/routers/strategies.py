"""
Strategies Router
=================
Endpoints for strategy management and backtest execution.
Refactored to support full async operations.

Strategies:
- Quant 1.0: Momentum, HRP, Dual Momentum, Inverse Volatility
- Quant 2.0: Regime Detection, Stat Arb, Residual Momentum, Meta-Labeling
- OLMAR: Online Learning Mean Reversion
"""

import sys
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import aiofiles
import asyncio
import logging

logger = logging.getLogger(__name__)

# Add parent path for strategy imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

# In-memory storage for backtest results
_backtest_results: Dict[str, Any] = {}
_backtest_status: Dict[str, str] = {}


class BacktestRequest(BaseModel):
    """Request model for backtest execution."""
    strategy_name: str = Field(..., description="Name of the strategy to run")
    start_date: str = Field(default="2020-01-01", description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD), defaults to today")
    initial_capital: float = Field(default=100000.0, description="Initial capital in AUD")
    tickers: Optional[List[str]] = Field(default=None, description="Custom ticker list (overrides universe)")
    universe: str = Field(default="SPX500", description="Stock universe")
    optimization_method: str = Field(default="HRP", description="Optimization method")


class BacktestResponse(BaseModel):
    """Response model for backtest execution."""
    backtest_id: str
    status: str
    strategy_name: str
    message: str
    timestamp: str


class StrategyInfo(BaseModel):
    """Information about a strategy."""
    name: str
    category: str
    description: str
    parameters: Dict[str, Any]
    status: str


# Strategy catalog (static metadata)
STRATEGY_CATALOG = {
    # Quant 1.0 Strategies
    "Momentum": {
        "category": "Quant 1.0",
        "description": "12-month momentum with 1-month skip.",
        "parameters": {"lookback": 252, "skip": 21, "top_n": 10},
        "status": "active"
    },
    "Dual_Momentum": {
        "category": "Quant 1.0",
        "description": "Combines absolute and relative momentum.",
        "parameters": {"abs_lookback": 252, "rel_lookback": 126},
        "status": "active"
    },
    "HRP": {
        "category": "Quant 1.0",
        "description": "Hierarchical Risk Parity.",
        "parameters": {"lookback": 252, "linkage": "ward"},
        "status": "active"
    },
    "InverseVolatility": {
        "category": "Quant 1.0",
        "description": "Weight inversely proportional to volatility.",
        "parameters": {"lookback": 63},
        "status": "active"
    },
    "Regime_Detection": {
        "category": "Quant 2.0",
        "description": "HMM-based market regime detection.",
        "parameters": {"n_states": 3, "lookback": 504},
        "status": "active"
    },
    "Stat_Arb": {
        "category": "Quant 2.0",
        "description": "Statistical arbitrage with Kalman filter.",
        "parameters": {"zscore_entry": 2.0, "zscore_exit": 0.5},
        "status": "active"
    },
    "OLMAR": {
        "category": "Mean Reversion",
        "description": "Online Learning for Portfolio Selection.",
        "parameters": {"window": 5, "epsilon": 10},
        "status": "active"
    }
}


@router.get("/", response_model=List[StrategyInfo])
async def list_strategies():
    """List all available strategies."""
    return [
        StrategyInfo(name=name, **info) 
        for name, info in STRATEGY_CATALOG.items()
    ]


@router.get("/{strategy_name}")
async def get_strategy_details(strategy_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific strategy."""
    if strategy_name not in STRATEGY_CATALOG:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    info = STRATEGY_CATALOG[strategy_name]
    
    # Check for cached results
    results = _backtest_results.get(strategy_name)
    if not results:
        # Try to load from file asynchronously
        results_path = Path(f"reports/{strategy_name}_results.json")
        if results_path.exists():
            try:
                async with aiofiles.open(results_path, mode='r') as f:
                    content = await f.read()
                    results = json.loads(content)
            except:
                pass
    
    return {
        "name": strategy_name,
        **info,
        "last_results": results,
        "has_results": results is not None
    }


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    background_tasks: BackgroundTasks
):
    """Execute a backtest for a strategy in the background."""
    if request.strategy_name not in STRATEGY_CATALOG:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    backtest_id = f"{request.strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    _backtest_status[request.strategy_name] = "running"
    
    async def execute_backtest_task():
        """Helper to run the heavy pipeline in a threadpool and save results."""
        try:
            from strategy.pipeline.pipeline import TradingPipeline, PipelineConfig
            
            # This is synchronous/CPU-heavy, so run in threadpool
            def _run_pipeline():
                config = PipelineConfig(
                    tickers=request.tickers,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    initial_capital=request.initial_capital
                )
                pipeline = TradingPipeline(config)
                return pipeline.run(
                    strategy_name=request.strategy_name,
                    optimization_method=request.optimization_method
                )
            
            result = await run_in_threadpool(_run_pipeline)
            
            results_data = {
                "backtest_id": backtest_id,
                "strategy_name": request.strategy_name,
                "completed_at": datetime.now().isoformat(),
                "config": {
                    "start_date": request.start_date,
                    "end_date": request.end_date or datetime.now().strftime("%Y-%m-%d"),
                    "initial_capital": request.initial_capital,
                    "optimization_method": request.optimization_method
                },
                "metrics": result.report.metrics.to_dict() if hasattr(result.report.metrics, 'to_dict') else {},
                "final_value": result.final_value,
                "weights": result.allocation.weights.to_dict() if hasattr(result.allocation.weights, 'to_dict') else {},
                "execution_time": result.execution_time_seconds
            }
            
            _backtest_results[request.strategy_name] = results_data
            _backtest_status[request.strategy_name] = "completed"
            
            # Save to file asynchronously
            results_path = Path(f"reports/{request.strategy_name}_results.json")
            results_path.parent.mkdir(exist_ok=True)
            async with aiofiles.open(results_path, mode='w') as f:
                await f.write(json.dumps(results_data, indent=2, default=str))
            
            logger.info(f"✅ Backtest completed: {request.strategy_name}")
            
        except Exception as e:
            _backtest_status[request.strategy_name] = f"failed: {str(e)}"
            logger.exception(f"Backtest {request.strategy_name} failed")

    background_tasks.add_task(execute_backtest_task)
    
    return BacktestResponse(
        backtest_id=backtest_id,
        status="started",
        strategy_name=request.strategy_name,
        message=f"Backtest started.",
        timestamp=datetime.now().isoformat()
    )


@router.get("/{strategy_name}/status")
async def get_backtest_status(strategy_name: str) -> Dict[str, Any]:
    """Get the status of a running backtest."""
    return {
        "strategy_name": strategy_name,
        "status": _backtest_status.get(strategy_name, "not_started"),
        "has_results": strategy_name in _backtest_results,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/{strategy_name}/results")
async def get_backtest_results(strategy_name: str) -> Dict[str, Any]:
    """Get the results of a completed backtest."""
    results = _backtest_results.get(strategy_name)
    if not results:
        results_path = Path(f"reports/{strategy_name}_results.json")
        if results_path.exists():
            try:
                async with aiofiles.open(results_path, mode='r') as f:
                    content = await f.read()
                    return json.loads(content)
            except:
                pass
        
        raise HTTPException(status_code=404, detail="No results found")
    
    return results


@router.get("/compare/all")
async def compare_all_strategies() -> Dict[str, Any]:
    """Compare performance of all strategies."""
    comparison = []
    
    async def _load_strategy_result(name):
        res = _backtest_results.get(name)
        if not res:
            p = Path(f"reports/{name}_results.json")
            if p.exists():
                try:
                    async with aiofiles.open(p, mode='r') as f:
                        content = await f.read()
                        res = json.loads(content)
                except:
                    return None
        return name, res

    tasks = [_load_strategy_result(name) for name in STRATEGY_CATALOG.keys()]
    loaded = await asyncio.gather(*tasks)
    
    for name, results in loaded:
        if results and "metrics" in results:
            metrics = results["metrics"]
            comparison.append({
                "strategy": name,
                "category": STRATEGY_CATALOG[name]["category"],
                "final_value": results.get("final_value", 0),
                "total_return": metrics.get("total_return", "N/A"),
                "cagr": metrics.get("cagr", "N/A"),
                "sharpe_ratio": metrics.get("sharpe_ratio", "N/A")
            })
    
    return {
        "comparison": comparison,
        "generated_at": datetime.now().isoformat(),
        "strategies_compared": len(comparison)
    }
