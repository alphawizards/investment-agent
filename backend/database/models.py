"""
SQLAlchemy ORM Models
=====================
Database models for trade tracking and portfolio snapshots.

2025 Bi-Temporal Schema:
- knowledge_timestamp: When the system learned about this data
- event_timestamp: When the event actually occurred

This enables Point-in-Time (PIT) queries for accurate backtesting.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum, Index, Boolean, Text
)
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .connection import Base


class TradeDirection(str, enum.Enum):
    """Trade direction enum."""
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, enum.Enum):
    """Trade status enum."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Trade(Base):
    """
    Trade model for tracking all executed trades.
    
    Indexed on:
    - ticker (frequent filtering)
    - trade_date (sorting, range queries)
    - strategy_name (grouping)
    """
    __tablename__ = "trades"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Trade identification
    trade_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Asset information
    ticker = Column(String(20), nullable=False, index=True)
    asset_name = Column(String(100), nullable=True)
    asset_class = Column(String(50), nullable=True)  # e.g., "US_EQUITY", "COMMODITIES"
    
    # Trade details
    direction = Column(Enum(TradeDirection), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    
    # Costs
    commission = Column(Float, default=3.0)  # $3 AUD per trade
    currency = Column(String(3), default="AUD")
    
    # Timing
    entry_date = Column(DateTime, nullable=False, index=True)
    exit_date = Column(DateTime, nullable=True)
    
    # P&L (calculated)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    
    # Strategy information
    strategy_name = Column(String(100), default="dual_momentum", index=True)
    signal_score = Column(Float, nullable=True)
    
    # Status
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN)
    
    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Bi-Temporal Timestamps (2025 Standard)
    # knowledge_timestamp: When we learned about this trade (system time)
    # event_timestamp: When the trade actually occurred (business time)
    knowledge_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    event_timestamp = Column(DateTime, nullable=True)  # Same as entry_date for trades
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_trades_ticker_date', 'ticker', 'entry_date'),
        Index('ix_trades_strategy_status', 'strategy_name', 'status'),
        Index('ix_trades_date_range', 'entry_date', 'exit_date'),
        # Index for Point-in-Time queries
        Index('ix_trades_bitemporal', 'knowledge_timestamp', 'event_timestamp'),
    )
    
    def calculate_pnl(self) -> None:
        """Calculate P&L if trade is closed."""
        if self.exit_price is not None and self.status == TradeStatus.CLOSED:
            if self.direction == TradeDirection.BUY:
                self.pnl = (self.exit_price - self.entry_price) * self.quantity - self.commission
                self.pnl_percent = ((self.exit_price - self.entry_price) / self.entry_price) * 100
            else:  # SELL (short)
                self.pnl = (self.entry_price - self.exit_price) * self.quantity - self.commission
                self.pnl_percent = ((self.entry_price - self.exit_price) / self.entry_price) * 100
    
    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, ticker={self.ticker}, direction={self.direction}, status={self.status})>"


class PortfolioSnapshot(Base):
    """
    Portfolio snapshot for tracking portfolio value over time.
    
    Used for generating equity curves and performance metrics.
    """
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Snapshot timing
    snapshot_date = Column(DateTime, nullable=False, index=True)
    
    # Portfolio values
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    invested_value = Column(Float, nullable=False)
    
    # Performance metrics
    daily_return = Column(Float, nullable=True)
    cumulative_return = Column(Float, nullable=True)
    
    # Risk metrics
    volatility_21d = Column(Float, nullable=True)
    sharpe_ratio_21d = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    # Position summary
    num_positions = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    
    # Bi-Temporal Timestamps (2025 Standard)
    knowledge_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    event_timestamp = Column(DateTime, nullable=True)  # Same as snapshot_date
    
    __table_args__ = (
        Index('ix_snapshot_date', 'snapshot_date'),
        # Index for Point-in-Time queries
        Index('ix_snapshot_bitemporal', 'knowledge_timestamp', 'event_timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<PortfolioSnapshot(date={self.snapshot_date}, value={self.total_value})>"


class IndexConstituent(Base):
    """
    Tracks historical index membership for Point-in-Time universe selection.
    Solves Survivorship Bias by allowing us to know exactly which stocks were
    in the index on any given past date.
    """
    __tablename__ = "index_constituents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Composite unique key: (ticker, index_name, start_date)
    ticker = Column(String(20), nullable=False, index=True)
    index_name = Column(String(20), nullable=False, index=True)  # e.g., 'SP500', 'ASX200'
    
    # Validity period
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=True)  # Null = Currently in index
    
    # Metadata
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('ix_constituents_lookup', 'index_name', 'start_date', 'end_date'),
    )

    def __repr__(self):
        return f"<IndexConstituent({self.ticker}, {self.index_name}, {self.start_date} to {self.end_date})>"
