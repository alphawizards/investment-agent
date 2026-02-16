"""
Scanner Router
==============
Endpoints for stock scanning and signal generation.
Refactored to support full async operations.

Scanners:
- Quallamaggie High Tight Flag
- Momentum Breakout
- Mean Reversion
"""

import sys
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import aiofiles
import random

# Add parent path for strategy imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import authentication
try:
    from backend.auth import get_current_user
except ImportError:
    from auth import get_current_user

router = APIRouter(prefix="/api/scanner", tags=["scanner"])

# In-memory storage for scan results
_scan_results: Dict[str, Any] = {}
_scan_status: str = "idle"


class ScanRequest(BaseModel):
    """Request model for running a scan."""
    scanner_type: str = Field(
        default="quallamaggie",
        description="Type of scanner"
    )
    universe: str = Field(
        default="sp500",
        description="Stock universe"
    )
    min_price: float = Field(default=5.0)
    max_price: float = Field(default=500.0)
    min_volume: int = Field(default=100000)
    min_score: float = Field(default=0.0, description="Minimum score threshold")
    custom_tickers: Optional[List[str]] = Field(default=None)


async def load_scan_results_async() -> Optional[Dict]:
    """Load scan results from JSON file asynchronously."""
    scan_file = Path("dashboard/scan_results.json")
    if scan_file.exists():
        try:
            async with aiofiles.open(scan_file, mode='r') as f:
                content = await f.read()
                return json.loads(content)
        except:
            pass
    return None


@router.get("/")
async def get_scanner_info() -> Dict[str, Any]:
    """Get information about available scanners."""
    return {
        "scanners": [
            {
                "name": "quallamaggie",
                "description": "High Tight Flag pattern scanner",
                "signals": ["BUY", "WATCH", "HOLD"]
            },
            {
                "name": "momentum",
                "description": "12-month momentum with relative strength",
                "signals": ["STRONG_BUY", "BUY", "HOLD", "SELL"]
            }
        ],
        "universes": ["sp500", "nasdaq100", "asx200", "all"],
        "last_scan": _scan_results.get("generated_at"),
        "status": _scan_status
    }


@router.get("/results")
async def get_scan_results(
    scanner_type: Optional[str] = None,
    signal: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """Get latest scan results."""
    global _scan_results
    
    # Try to load from memory first, then file
    results = _scan_results
    if not results:
        results = await load_scan_results_async()
    
    if not results:
        return {
            "results": [],
            "message": "No scan results available.",
            "generated_at": None
        }
    
    # Get stocks from results
    stocks = results.get("stocks", results.get("results", []))
    
    # Apply filters
    filtered = []
    for stock in stocks:
        if signal and stock.get("signal", "").upper() != signal.upper():
            continue
        if min_score and stock.get("score", 0) < min_score:
            continue
        filtered.append(stock)
    
    filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
    filtered = filtered[:limit]
    
    return {
        "results": filtered,
        "total_found": len(filtered),
        "generated_at": results.get("generated_at"),
        "scanner_type": results.get("scanner_type", "quallamaggie")
    }


@router.post("/run")
async def run_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Run a stock scan in the background."""
    global _scan_status
    _scan_status = "running"
    
    async def execute_scan_task():
        global _scan_results, _scan_status
        try:
            # CPU intensive/synchronous part
            def _scan_logic():
                import os
                from strategy.quant1.scanner.quallamaggie_scanner import QuallamaggieScanner
                from strategy.fast_data_loader import FastDataLoader
                
                # Get tickers
                if request.custom_tickers:
                    tickers = request.custom_tickers
                else:
                    from strategy.stock_universe import get_sp500_tickers, get_nasdaq100_tickers, get_asx200_tickers, get_screener_universe
                    universe_map = {"sp500": get_sp500_tickers, "nasdaq100": get_nasdaq100_tickers, "asx200": get_asx200_tickers, "all": get_screener_universe}
                    get_tickers = universe_map.get(request.universe, get_sp500_tickers)
                    tickers = get_tickers()
                
                # Use FastDataLoader to fetch prices for all tickers efficiently
                # This enables scanning 500+ stocks in under 60 seconds
                data_loader = FastDataLoader(
                    tiingo_api_token=os.getenv("TIINGO_API_KEY"),
                    verbose=False
                )
                
                # Fetch recent price data for all tickers
                price_data = data_loader.fetch_prices_fast(
                    tickers,
                    use_cache=True
                )
                
                # Run the actual Quallamaggie scanner with real data
                scanner = QuallamaggieScanner()
                results = scanner.scan(tickers)
                
                # Filter by score threshold
                min_score = request.min_score if hasattr(request, 'min_score') else 0
                filtered_results = [r for r in results if r.get('score', 0) >= min_score]
                
                # Add price data to results if available
                if 'close' in price_data and not price_data['close'].empty:
                    close_prices = price_data['close']
                    for r in filtered_results:
                        ticker = r.get('ticker')
                        if ticker and ticker in close_prices.columns:
                            series = close_prices[ticker].dropna()
                            if not series.empty:
                                r['price'] = round(float(series.iloc[-1]), 2)
                                if len(series) > 1:
                                    prev_price = float(series.iloc[-2])
                                    curr_price = float(series.iloc[-1])
                                    r['change_pct'] = round(((curr_price - prev_price) / prev_price) * 100, 2)
                
                # Sort by score descending
                filtered_results.sort(key=lambda x: x.get('score', 0), reverse=True)
                
                return tickers, filtered_results

            tickers, results = await run_in_threadpool(_scan_logic)
            
            _scan_results = {
                "generated_at": datetime.now().isoformat(),
                "scanner_type": request.scanner_type,
                "universe": request.universe,
                "tickers_scanned": len(tickers),
                "results_found": len(results),
                "stocks": results
            }
            
            # Save to file asynchronously
            scan_file = Path("dashboard/scan_results.json")
            scan_file.parent.mkdir(exist_ok=True)
            async with aiofiles.open(scan_file, mode='w') as f:
                await f.write(json.dumps(_scan_results, indent=2))
            
            _scan_status = "completed"
        except Exception as e:
            _scan_status = f"failed: {str(e)}"

    background_tasks.add_task(execute_scan_task)
    
    return {
        "status": "started",
        "scanner_type": request.scanner_type,
        "message": "Scan started.",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status")
async def get_scan_status() -> Dict[str, Any]:
    """Get the status of the current/last scan."""
    return {
        "status": _scan_status,
        "has_results": bool(_scan_results),
        "last_scan": _scan_results.get("generated_at") if _scan_results else None
    }


@router.get("/quallamaggie")
async def get_quallamaggie_results() -> Dict[str, Any]:
    """Get Quallamaggie scanner results specifically."""
    results = await load_scan_results_async()
    if results:
        results["retrieved_at"] = datetime.now().isoformat()
        return results
    
    if _scan_results and _scan_results.get("scanner_type") == "quallamaggie":
        return _scan_results
    
    return {"results": [], "message": "No Quallamaggie results found."}
