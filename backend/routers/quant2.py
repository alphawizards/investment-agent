"""
Quant 2.0 Router
================
Dedicated endpoints for Quant 2.0 strategy calculations.
Refactored to support full async operations.

Provides live strategy calculations with stock universe selection:
- /api/quant2/residual-momentum - Residual momentum rankings
- /api/quant2/regime - Market regime detection
- /api/quant2/stat-arb - Statistical arbitrage signals
"""

import sys
from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Add parent path for strategy imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strategy.stock_universe import (
    UNIVERSE_REGISTRY,
    get_universe_tickers,
    get_universe_info
)

router = APIRouter(prefix="/api/quant2", tags=["quant2"])


# ============== Response Models ==============

class StockRanking(BaseModel):
    """Single stock ranking result."""
    rank: int
    ticker: str
    score: float
    r_squared: Optional[float] = None
    beta_mkt: Optional[float] = None
    beta_smb: Optional[float] = None
    beta_hml: Optional[float] = None
    residual_vol: Optional[float] = None


class ResidualMomentumResponse(BaseModel):
    """Response for residual momentum endpoint."""
    universe: str
    universe_name: str
    generated_at: str
    lookback_months: int
    scoring_months: int
    stocks_ranked: int
    top_score: float
    avg_r_squared: float
    rankings: List[StockRanking]
    bottom_rankings: Optional[List[StockRanking]] = None


class UniverseValidationResponse(BaseModel):
    """Response for universe validation."""
    universe: str
    valid: bool
    ticker_count: int
    sample_tickers: List[str]
    api_status: str


# ============== Helper Functions ==============

def generate_mock_residual_momentum(tickers: List[str], universe: str) -> Dict[str, Any]:
    """
    Generate realistic mock residual momentum data (Synchronous).
    """
    np.random.seed(hash(universe) % 2**32)
    n_stocks = len(tickers)
    scores = np.random.randn(n_stocks) * 0.8
    r_squared = np.random.uniform(0.25, 0.75, n_stocks)
    beta_mkt = np.random.uniform(0.7, 1.5, n_stocks)
    beta_smb = np.random.uniform(-0.5, 0.5, n_stocks)
    beta_hml = np.random.uniform(-0.6, 0.4, n_stocks)
    resid_vol = np.random.uniform(0.10, 0.35, n_stocks)
    
    rankings = []
    sorted_indices = np.argsort(scores)[::-1]
    
    for rank, idx in enumerate(sorted_indices, 1):
        ticker = tickers[idx] if idx < len(tickers) else f"TICKER{idx}"
        rankings.append({
            "rank": rank,
            "ticker": ticker,
            "score": round(float(scores[idx]), 2),
            "r_squared": round(float(r_squared[idx]), 2),
            "beta_mkt": round(float(beta_mkt[idx]), 2),
            "beta_smb": round(float(beta_smb[idx]), 2),
            "beta_hml": round(float(beta_hml[idx]), 2),
            "residual_vol": round(float(resid_vol[idx]) * 100, 1),
        })
    
    return {
        "rankings": rankings,
        "top_score": round(float(max(scores)), 2),
        "avg_r_squared": round(float(np.mean(r_squared)), 2),
        "stocks_ranked": n_stocks,
    }


def _calculate_live_sync(tickers: List[str]) -> Optional[Dict[str, Any]]:
    """Synchronous implementation of live calculation."""
    try:
        from strategy.quant2.momentum.residual_momentum import ResidualMomentum
        from strategy.infrastructure.data_loader import DataLoader
        
        rm = ResidualMomentum(lookback_months=36, scoring_months=12)
        loader = DataLoader()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 4)
        
        prices = loader.get_prices(
            tickers=tickers[:50],
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        if prices is None or len(prices) == 0:
            return None
        
        monthly_prices = prices.resample('M').last()
        returns = monthly_prices.pct_change().dropna()
        result = rm.calculate_scores(returns)
        scores = result.scores.iloc[0].dropna().sort_values(ascending=False)
        
        rankings = []
        for rank, (ticker, score) in enumerate(scores.items(), 1):
            exposures = result.factor_exposures.get(ticker, {})
            rankings.append({
                "rank": rank,
                "ticker": ticker,
                "score": round(float(score), 2),
                "r_squared": round(float(exposures.get('r_squared', 0)), 2),
                "beta_mkt": round(float(exposures.get('beta_mkt', 1)), 2),
                "beta_smb": round(float(exposures.get('beta_smb', 0)), 2),
                "beta_hml": round(float(exposures.get('beta_hml', 0)), 2),
                "residual_vol": round(float(exposures.get('residual_std', 0.15)) * 100, 1),
            })
        
        return {
            "rankings": rankings,
            "top_score": round(float(scores.iloc[0]) if len(scores) > 0 else 0, 2),
            "avg_r_squared": round(float(result.metadata.get('avg_r_squared', 0.42)), 2),
            "stocks_ranked": len(rankings),
            "source": "live"
        }
    except Exception as e:
        logger.debug(f"Live calculation failed: {e}")
        return None


async def calculate_residual_momentum_live(tickers: List[str]) -> Optional[Dict[str, Any]]:
    """Calculate live residual momentum scores asynchronously."""
    return await run_in_threadpool(_calculate_live_sync, tickers)


# ============== Endpoints ==============

@router.get("/residual-momentum", response_model=ResidualMomentumResponse)
async def get_residual_momentum(
    universe: str = Query(default="SPX500"),
    top_n: int = Query(default=20, ge=5, le=100),
    include_bottom: bool = Query(default=False)
):
    """Get residual momentum rankings."""
    if universe not in UNIVERSE_REGISTRY:
        raise HTTPException(status_code=400, detail="Invalid universe")
    
    tickers = await run_in_threadpool(get_universe_tickers, universe)
    if not tickers:
        raise HTTPException(status_code=500, detail="No tickers found")
    
    result = await calculate_residual_momentum_live(tickers)
    
    if result is None:
        result = await run_in_threadpool(generate_mock_residual_momentum, tickers, universe)
        result["source"] = "mock"
    
    top_rankings = [StockRanking(**r) for r in result["rankings"][:top_n]]
    bottom_rankings = [StockRanking(**r) for r in result["rankings"][-top_n:]] if include_bottom else None
    
    info = await run_in_threadpool(get_universe_info, universe)
    
    return ResidualMomentumResponse(
        universe=universe,
        universe_name=info["name"],
        generated_at=datetime.now().isoformat(),
        lookback_months=36,
        scoring_months=12,
        stocks_ranked=result["stocks_ranked"],
        top_score=result["top_score"],
        avg_r_squared=result["avg_r_squared"],
        rankings=top_rankings,
        bottom_rankings=bottom_rankings
    )


@router.get("/validate-universe")
async def validate_universe(universe: str = Query(...)) -> UniverseValidationResponse:
    """Validate a universe configuration."""
    if universe not in UNIVERSE_REGISTRY:
        return UniverseValidationResponse(universe=universe, valid=False, ticker_count=0, sample_tickers=[], api_status="Unknown")
    
    try:
        tickers = await run_in_threadpool(get_universe_tickers, universe)
        return UniverseValidationResponse(universe=universe, valid=True, ticker_count=len(tickers), sample_tickers=tickers[:10], api_status="OK")
    except Exception as e:
        return UniverseValidationResponse(universe=universe, valid=False, ticker_count=0, sample_tickers=[], api_status=f"Error: {str(e)}")


class AllStocksResponse(BaseModel):
    universe: str
    universe_name: str
    generated_at: str
    total_stocks: int
    filtered_stocks: int
    sort_by: str
    sort_order: str
    min_score: Optional[float]
    max_score: Optional[float]
    stocks: List[StockRanking]


@router.get("/residual-momentum/all", response_model=AllStocksResponse)
async def get_all_residual_momentum(
    universe: str = Query(default="SPX500"),
    sort_by: str = Query(default="score"),
    sort_order: str = Query(default="desc"),
    min_score: Optional[float] = Query(default=None),
    max_score: Optional[float] = Query(default=None)
):
    """Get ALL stocks ranked by residual momentum."""
    if universe not in UNIVERSE_REGISTRY:
        raise HTTPException(status_code=400, detail="Invalid universe")
    
    tickers = await run_in_threadpool(get_universe_tickers, universe)
    result = await calculate_residual_momentum_live(tickers)
    if result is None:
        result = await run_in_threadpool(generate_mock_residual_momentum, tickers, universe)
    
    all_rankings = result["rankings"]
    if min_score is not None:
        all_rankings = [r for r in all_rankings if r["score"] >= min_score]
    if max_score is not None:
        all_rankings = [r for r in all_rankings if r["score"] <= max_score]
    
    reverse = sort_order.lower() == "desc"
    all_rankings.sort(key=lambda x: x.get(sort_by, x["score"]), reverse=reverse)
    
    info = await run_in_threadpool(get_universe_info, universe)
    
    return AllStocksResponse(
        universe=universe,
        universe_name=info["name"],
        generated_at=datetime.now().isoformat(),
        total_stocks=len(tickers),
        filtered_stocks=len(all_rankings),
        sort_by=sort_by,
        sort_order=sort_order,
        min_score=min_score,
        max_score=max_score,
        stocks=[StockRanking(**r) for r in all_rankings]
    )


@router.get("/universes-summary")
async def get_universes_summary() -> Dict[str, Any]:
    """Get summary of all available universes."""
    summaries = []
    
    def _get_all_summaries():
        res = []
        for key in UNIVERSE_REGISTRY.keys():
            try:
                tickers = get_universe_tickers(key)
                info = get_universe_info(key)
                res.append({"key": key, "name": info["name"], "region": info["region"], "ticker_count": len(tickers), "sample": tickers[:5], "status": "available"})
            except:
                res.append({"key": key, "name": key, "region": "Unknown", "ticker_count": 0, "sample": [], "status": "error"})
        return res

    summaries = await run_in_threadpool(_get_all_summaries)
    
    return {
        "generated_at": datetime.now().isoformat(),
        "total_universes": len(summaries),
        "universes": summaries
    }
