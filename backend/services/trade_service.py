"""
Trade Service
=============
Business logic layer for trade operations.
Orchestrates repository calls and computes derived metrics.
Refactored to support full async operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
import math
import os

from ..repositories.trade_repository import TradeRepository
from ..database.models import Trade, TradeStatus

# Import FastDataLoader for Mark-to-Market calculations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "strategy"))
from fast_data_loader import FastDataLoader

from ..database.schemas import (
    TradeCreate, TradeUpdate, TradeResponse, TradeListResponse,
    PortfolioMetrics, DashboardSummary
)


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
                data_loader = FastDataLoader(
                    cache_dir=Path("cache"),
                    use_tiingo=os.getenv("TIINGO_API_KEY") is not None,
                    use_yfinance=True,
                    verbose=False
                )
                
                # Fetch latest prices (delta loading will get most recent)
                price_data = data_loader.fetch_prices_fast(tickers, use_cache=True)
                
                if 'close' in price_data and not price_data['close'].empty:
                    close_prices = price_data['close']
                    
                    # Calculate unrealized P&L for each open position
                    for trade in open_positions:
                        if trade.ticker in close_prices.columns:
                            current_price = close_prices[trade.ticker].iloc[-1]  # Latest close
                            position_value = current_price * trade.quantity
                            entry_value = trade.entry_price * trade.quantity
                            unrealized_pnl += position_value - entry_value
                            current_market_value += position_value
            except Exception as e:
                # If price fetch fails, fall back to entry price calculation
                print(f"Warning: Failed to fetch live prices for MtM: {e}")
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
