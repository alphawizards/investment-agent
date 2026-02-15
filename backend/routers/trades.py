"""
Trade API Routes
================
RESTful API endpoints for trade operations.
Refactored to support full async operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from ..database.connection import get_async_db
from ..database.schemas import (
    TradeCreate, TradeUpdate, TradeResponse, TradeListResponse,
    PortfolioMetrics, DashboardSummary, TradeStatsResponse
)
from ..services.trade_service import TradeService

router = APIRouter(prefix="/api/trades", tags=["trades"])


# ============== Dependencies ==============

async def get_trade_service(db: AsyncSession = Depends(get_async_db)) -> TradeService:
    """Dependency injection for TradeService (Async)."""
    return TradeService(db)


# ============== CRUD Endpoints ==============

@router.post("/", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def create_trade(
    trade_data: TradeCreate,
    service: TradeService = Depends(get_trade_service)
):
    """
    Create a new trade.
    """
    try:
        trade = await service.create_trade(trade_data)
        return TradeResponse.model_validate(trade)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=TradeListResponse)
async def get_trades(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, CLOSED, CANCELLED)"),
    strategy: Optional[str] = Query(None, description="Filter by strategy name"),
    start_date: Optional[datetime] = Query(None, description="Filter trades after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter trades before this date"),
    sort_by: str = Query("entry_date", description="Sort by field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    service: TradeService = Depends(get_trade_service)
):
    """
    Get paginated list of trades with optional filters.
    """
    return await service.get_trades(
        page=page,
        page_size=page_size,
        ticker=ticker,
        status=status,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_desc=sort_desc
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    service: TradeService = Depends(get_trade_service)
):
    """Get a single trade by ID."""
    trade = await service.get_trade(trade_id)
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade with ID {trade_id} not found"
        )
    return TradeResponse.model_validate(trade)


@router.patch("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_data: TradeUpdate,
    service: TradeService = Depends(get_trade_service)
):
    """
    Update an existing trade.
    """
    trade = await service.update_trade(trade_id, trade_data)
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade with ID {trade_id} not found"
        )
    return TradeResponse.model_validate(trade)


@router.post("/{trade_id}/close", response_model=TradeResponse)
async def close_trade(
    trade_id: int,
    exit_price: float = Query(..., gt=0, description="Exit price"),
    exit_date: Optional[datetime] = Query(None, description="Exit date (defaults to now)"),
    service: TradeService = Depends(get_trade_service)
):
    """
    Close an open trade.
    """
    trade = await service.close_trade(trade_id, exit_price, exit_date)
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade with ID {trade_id} not found or already closed"
        )
    return TradeResponse.model_validate(trade)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: int,
    service: TradeService = Depends(get_trade_service)
):
    """Delete a trade by ID."""
    success = await service.delete_trade(trade_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade with ID {trade_id} not found"
        )


# ============== Metrics Endpoints ==============

@router.get("/metrics/portfolio", response_model=PortfolioMetrics)
async def get_portfolio_metrics(
    initial_capital: float = Query(100000.0, gt=0, description="Initial capital in AUD"),
    service: TradeService = Depends(get_trade_service)
):
    """
    Get portfolio performance metrics.
    """
    return await service.get_portfolio_metrics(initial_capital)


@router.get("/metrics/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(
    initial_capital: float = Query(100000.0, gt=0, description="Initial capital in AUD"),
    service: TradeService = Depends(get_trade_service)
):
    """
    Get complete dashboard summary.
    """
    return await service.get_dashboard_summary(initial_capital)


@router.get("/metrics/by-ticker", response_model=list[TradeStatsResponse])
async def get_stats_by_ticker(
    service: TradeService = Depends(get_trade_service)
):
    """
    Get performance statistics grouped by ticker.
    """
    stats = await service.get_stats_by_ticker()
    
    # Calculate win rate for each ticker if possible, or leave as placeholder
    return [
        TradeStatsResponse(
            ticker=s['ticker'],
            total_trades=s['total_trades'],
            total_pnl=s['total_pnl'],
            avg_pnl=s['avg_pnl'],
            win_rate=0  # Placeholder as before, but now async
        )
        for s in stats
    ]


# ============== Utility Endpoints ==============

@router.get("/utils/generate-id")
async def generate_trade_id(
    prefix: str = Query("TRD", description="Trade ID prefix"),
    service: TradeService = Depends(get_trade_service)
):
    """Generate a unique trade ID."""
    return {"trade_id": await service.generate_trade_id(prefix)}
