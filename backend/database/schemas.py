"""
Pydantic Schemas (DTOs)
=======================
Request/Response validation schemas with strict typing.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TradeDirection(str, Enum):
    """Trade direction enum."""
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, Enum):
    """Trade status enum."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


# ============== Trade Schemas ==============

class TradeBase(BaseModel):
    """Base trade schema with common fields."""
    ticker: str = Field(..., min_length=1, max_length=20, description="Asset ticker symbol")
    asset_name: Optional[str] = Field(None, max_length=100)
    asset_class: Optional[str] = Field(None, max_length=50)
    direction: TradeDirection
    quantity: float = Field(..., gt=0, description="Trade quantity")
    entry_price: float = Field(..., gt=0, description="Entry price per unit")
    commission: float = Field(default=3.0, ge=0, description="Commission in AUD")
    currency: str = Field(default="AUD", max_length=3)
    strategy_name: str = Field(default="dual_momentum", max_length=100)
    signal_score: Optional[float] = Field(None, ge=0, le=1)
    notes: Optional[str] = None
    
    @field_validator('ticker')
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()


class TradeCreate(TradeBase):
    """Schema for creating a new trade."""
    trade_id: str = Field(..., min_length=1, max_length=50, description="Unique trade identifier")
    entry_date: datetime
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "trade_id": "TRD-2024-001",
            "ticker": "SPY",
            "asset_name": "S&P 500 ETF",
            "asset_class": "US_EQUITY",
            "direction": "BUY",
            "quantity": 10,
            "entry_price": 450.50,
            "entry_date": "2024-01-15T10:30:00",
            "commission": 3.0,
            "currency": "AUD",
            "strategy_name": "dual_momentum",
            "signal_score": 0.75,
            "notes": "Strong momentum signal"
        }
    })


class TradeUpdate(BaseModel):
    """Schema for updating an existing trade."""
    exit_price: Optional[float] = Field(None, gt=0)
    exit_date: Optional[datetime] = None
    status: Optional[TradeStatus] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "exit_price": 465.25,
            "exit_date": "2024-02-15T14:00:00",
            "status": "CLOSED",
            "notes": "Closed on momentum reversal"
        }
    })


class TradeResponse(TradeBase):
    """Schema for trade response."""
    id: int
    trade_id: str
    entry_date: datetime
    exit_price: Optional[float] = None
    exit_date: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    status: TradeStatus
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TradeListResponse(BaseModel):
    """Paginated trade list response."""
    trades: List[TradeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "trades": [],
            "total": 100,
            "page": 1,
            "page_size": 50,
            "total_pages": 2
        }
    })


# ============== Metrics Schemas ==============

class PortfolioMetrics(BaseModel):
    """Portfolio performance metrics."""
    total_value: float = Field(..., description="Total portfolio value in AUD")
    cash_balance: float = Field(..., description="Available cash")
    invested_value: float = Field(..., description="Value invested in positions")
    
    # Returns
    daily_return: Optional[float] = Field(None, description="Daily return percentage")
    total_return: Optional[float] = Field(None, description="Total return percentage")
    
    # Risk metrics
    volatility: Optional[float] = Field(None, description="Annualized volatility")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown percentage")
    
    # Trade stats
    total_trades: int = Field(..., description="Total number of trades")
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    win_rate: Optional[float] = Field(None, description="Win rate percentage")
    
    # P&L
    total_pnl: float = Field(default=0, description="Total P&L in AUD")
    avg_pnl_per_trade: Optional[float] = None
    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None


class DashboardSummary(BaseModel):
    """Dashboard summary combining key metrics."""
    # Portfolio overview
    portfolio: PortfolioMetrics
    
    # Recent activity
    recent_trades: List[TradeResponse]
    open_positions: int
    
    # Time-based metrics
    today_pnl: float = Field(default=0)
    week_pnl: float = Field(default=0)
    month_pnl: float = Field(default=0)
    
    # Timestamp
    last_updated: datetime


class TradeStatsResponse(BaseModel):
    """Aggregated trade statistics."""
    ticker: str
    total_trades: int
    total_pnl: float
    avg_pnl: float
    win_rate: float
    avg_holding_days: Optional[float] = None


class EquityCurvePoint(BaseModel):
    """Single point on equity curve."""
    date: datetime
    value: float
    daily_return: Optional[float] = None
    cumulative_return: Optional[float] = None


class EquityCurveResponse(BaseModel):
    """Equity curve response."""
    points: List[EquityCurvePoint]
    start_value: float
    end_value: float
    total_return: float
