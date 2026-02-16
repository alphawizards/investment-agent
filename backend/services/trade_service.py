"""
Trade Service
=============
Business logic layer for trade operations.
Orchestrates repository calls and computes derived metrics.
Refactored to support full async operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.concurrency import run_in_threadpool
from typing import List, Optional
from datetime import datetime, timedelta
import math
import os
import logging

from ..repositories.trade_repository import TradeRepository
from ..database.models import Trade, TradeStatus, PortfolioSnapshot

# Import FastDataLoader for Mark-to-Market calculations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from strategy.fast_data_loader import FastDataLoader

from ..database.schemas import (
    TradeCreate, TradeUpdate, TradeResponse, TradeListResponse,
    PortfolioMetrics, DashboardSummary
)

logger = logging.getLogger(__name__)


class TradeService:
    """
    Service layer for trade business logic.
    
    Responsibilities:
    - Orchestrate repository operations
    - Compute derived metrics
    - Validate business rules
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = TradeRepository(db)
    
    # ============== TRADE OPERATIONS ==============
    
    async def create_trade(self, trade_data: TradeCreate) -> Trade:
        """Create a new trade with business validation."""
        # Check for duplicate trade_id
        existing = await self.repository.get_by_trade_id(trade_data.trade_id)
        if existing:
            raise ValueError(f"Trade with ID {trade_data.trade_id} already exists")
        
        return await self.repository.create(trade_data)
    
    async def get_trade(self, trade_id: int) -> Optional[Trade]:
        """Get a single trade by ID."""
        return await self.repository.get_by_id(trade_id)
    
    async def get_trades(
        self,
        page: int = 1,
        page_size: int = 50,
        ticker: Optional[str] = None,
        status: Optional[str] = None,
        strategy: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "entry_date",
        sort_desc: bool = True
    ) -> TradeListResponse:
        """Get paginated trade list with filters."""
        status_enum = TradeStatus(status) if status else None
        
        trades, total = await self.repository.get_all(
            page=page,
            page_size=page_size,
            ticker=ticker,
            status=status_enum,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_desc=sort_desc
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        return TradeListResponse(
            trades=[TradeResponse.model_validate(t) for t in trades],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    async def update_trade(self, trade_id: int, trade_data: TradeUpdate) -> Optional[Trade]:
        """Update an existing trade."""
        return await self.repository.update(trade_id, trade_data)
    
    async def close_trade(
        self, 
        trade_id: int, 
        exit_price: float,
        exit_date: datetime = None
    ) -> Optional[Trade]:
        """Close a trade with exit details."""
        return await self.repository.close_trade(trade_id, exit_price, exit_date)
    
    async def delete_trade(self, trade_id: int) -> bool:
        """Delete a trade."""
        return await self.repository.delete(trade_id)
    
    # ============== METRICS ==============
    
    async def get_portfolio_metrics(
        self, 
        initial_capital: float = 100000.0
    ) -> PortfolioMetrics:
        """
        Calculate portfolio performance metrics with Mark-to-Market (MtM) valuation.
        Uses FastDataLoader to fetch current prices for open positions.
        """
        stats = await self.repository.get_statistics()
        
        # Get open positions
        open_positions = await self.repository.get_open_positions()
        
        # === Mark-to-Market Calculation ===
        unrealized_pnl = 0.0
        current_market_value = 0.0
        
        if open_positions:
            # Get unique tickers from open positions
            tickers = list(set(t.ticker for t in open_positions))
            
            try:
                # Initialize FastDataLoader to get current prices
                # Use thread pool since data fetching/Parquet reading is blocking
                def _fetch_prices():
                    # Need AUD/USD for US stocks conversion
                    all_tickers = tickers.copy()
                    has_us_stocks = any(not t.endswith('.AX') for t in tickers)
                    if has_us_stocks:
                        all_tickers.append('AUDUSD=X')
                        
                    data_loader = FastDataLoader(
                        tiingo_api_token=os.getenv("TIINGO_API_KEY"),
                        verbose=False
                    )
                    return data_loader.fetch_prices_fast(all_tickers, use_cache=True)
                
                price_data = await run_in_threadpool(_fetch_prices)
                
                if 'close' in price_data and not price_data['close'].empty:
                    close_prices = price_data['close']
                    
                    # Get latest FX rate (default to 0.65 if fetch fails)
                    fx_rate = 0.65
                    if 'AUDUSD=X' in close_prices.columns:
                        fx_series = close_prices['AUDUSD=X'].dropna()
                        if not fx_series.empty:
                            fx_rate = float(fx_series.iloc[-1])
                    
                    # Calculate unrealized P&L for each open position
                    for trade in open_positions:
                        if trade.ticker in close_prices.columns:
                            # Get the most recent price that isn't NaN
                            series = close_prices[trade.ticker].dropna()
                            if not series.empty:
                                current_price = float(series.iloc[-1])
                                
                                # Convert USD price to AUD if needed
                                # Assumes trade.currency='AUD' but ticker is US
                                if not trade.ticker.endswith('.AX') and trade.currency == 'AUD':
                                    # Price is in USD, convert to AUD
                                    current_price_aud = current_price / fx_rate
                                else:
                                    current_price_aud = current_price
                                    
                                position_value = current_price_aud * trade.quantity
                                entry_value = trade.entry_price * trade.quantity
                                unrealized_pnl += position_value - entry_value
                                current_market_value += position_value
                            else:
                                # Fallback if series is empty after dropna
                                current_market_value += trade.entry_price * trade.quantity
                        else:
                            # Fallback for missing ticker in price data
                            current_market_value += trade.entry_price * trade.quantity
                else:
                    # Fallback if no price data returned
                    current_market_value = sum(t.entry_price * t.quantity for t in open_positions)
            except Exception as e:
                # If price fetch fails, fall back to entry price calculation
                logger.error(f"Error fetching live prices for MtM: {e}")
                current_market_value = sum(t.entry_price * t.quantity for t in open_positions)
        
        # Calculate total portfolio value with MtM
        realized_pnl = stats['total_pnl']
        total_value = initial_capital + realized_pnl + unrealized_pnl
        
        # Cash balance = Total Value - Current Market Value of Open Positions
        cash_balance = total_value - current_market_value
        
        # Total P&L = Realized + Unrealized
        total_pnl = realized_pnl + unrealized_pnl
        
        # Calculate returns based on MtM
        total_return = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0
        
        # Win rate
        win_rate = stats['win_rate']
        
        # Average P&L per trade
        avg_pnl = stats['avg_pnl'] if stats['closed_trades'] > 0 else None
        
        return PortfolioMetrics(
            total_value=total_value,
            cash_balance=cash_balance,
            invested_value=current_market_value,
            total_return=total_return,
            total_trades=stats['total_trades'],
            winning_trades=stats['winning_trades'],
            losing_trades=stats['losing_trades'],
            win_rate=win_rate,
            total_pnl=total_pnl,
            unrealized_pnl=unrealized_pnl,
            avg_pnl_per_trade=avg_pnl,
            best_trade=stats['best_trade'],
            worst_trade=stats['worst_trade']
        )
    
    async def get_dashboard_summary(
        self, 
        initial_capital: float = 100000.0
    ) -> DashboardSummary:
        """
        Get complete dashboard summary.
        """
        # Portfolio metrics
        portfolio = await self.get_portfolio_metrics(initial_capital)
        
        # Recent trades
        recent_trades = await self.repository.get_recent(limit=10)
        
        # Open positions count
        open_positions_list = await self.repository.get_open_positions()
        open_positions_count = len(open_positions_list)
        
        # Period P&L
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        
        today_pnl = await self.repository.get_pnl_by_period(today_start, now)
        week_pnl = await self.repository.get_pnl_by_period(week_start, now)
        month_pnl = await self.repository.get_pnl_by_period(month_start, now)
        
        return DashboardSummary(
            portfolio=portfolio,
            recent_trades=[TradeResponse.model_validate(t) for t in recent_trades],
            open_positions=open_positions_count,
            today_pnl=today_pnl,
            week_pnl=week_pnl,
            month_pnl=month_pnl,
            last_updated=now
        )
    
    async def get_stats_by_ticker(self) -> List[dict]:
        """Get performance stats grouped by ticker."""
        return await self.repository.get_stats_by_ticker()
    
    # ============== UTILITY ==============
    
    async def generate_trade_id(self, prefix: str = "TRD") -> str:
        """Generate a unique trade ID."""
        now = datetime.utcnow()
        stats = await self.repository.get_statistics()
        seq = stats['total_trades'] + 1
        return f"{prefix}-{now.strftime('%Y%m%d')}-{seq:04d}"
    
    # ============== PORTFOLIO SNAPSHOT ==============
    
    async def take_portfolio_snapshot(
        self,
        initial_capital: float = 100000.0,
        save_to_db: bool = True
    ) -> PortfolioSnapshot:
        """
        Take a snapshot of the current portfolio state.
        
        Calculates current Mark-to-Market (MtM) value and optionally saves
        to the database for historical tracking.
        
        Args:
            initial_capital: Starting capital for return calculations
            save_to_db: Whether to persist the snapshot to database
            
        Returns:
            PortfolioSnapshot object with current portfolio state
        """
        # Get current portfolio metrics (includes MtM calculation)
        metrics = await self.get_portfolio_metrics(initial_capital)
        
        # Get current positions for position count
        open_positions = await self.repository.get_open_positions()
        
        # Calculate daily return (simplified - compare to previous snapshot if exists)
        daily_return = None
        cumulative_return = metrics.total_return / 100.0 if metrics.total_return else 0
        
        # Get latest snapshot for daily return calculation
        latest_snapshot = await self.repository.get_latest_snapshot()
        if latest_snapshot:
            # Calculate daily return as percentage change
            if latest_snapshot.total_value > 0:
                daily_return = (metrics.total_value - latest_snapshot.total_value) / latest_snapshot.total_value
        
        now = datetime.utcnow()
        
        # Create snapshot object
        snapshot = PortfolioSnapshot(
            snapshot_date=now,
            total_value=metrics.total_value,
            cash_balance=metrics.cash_balance,
            invested_value=metrics.invested_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            num_positions=len(open_positions),
            event_timestamp=now
        )
        
        if save_to_db:
            # Save to database
            self.db.add(snapshot)
            await self.db.commit()
            await self.db.refresh(snapshot)
            logger.info(f"Portfolio snapshot saved: ${metrics.total_value:,.2f}")
        else:
            logger.info(f"Portfolio snapshot calculated (not saved): ${metrics.total_value:,.2f}")
        
        return snapshot
