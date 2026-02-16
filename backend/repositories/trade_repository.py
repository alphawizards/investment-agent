"""
Trade Repository
================
Data access layer for trade operations using Repository Pattern.
All database queries are parameterized to prevent SQL injection.
Refactored to support full async operations (2025 standard).
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, delete as sa_delete
from typing import List, Optional, Tuple
from datetime import datetime

from ..database.models import Trade, TradeStatus, TradeDirection, PortfolioSnapshot
from ..database.schemas import TradeCreate, TradeUpdate
from ..config import settings


class TradeRepository:
    """
    Repository for trade CRUD operations.
    
    Implements:
    - Async database operations
    - Parameterized queries (SQL injection prevention)
    - Efficient pagination
    - Indexed query patterns
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============== CREATE ==============
    
    async def create(self, trade_data: TradeCreate) -> Trade:
        """
        Create a new trade record.
        
        Args:
            trade_data: Validated trade data from Pydantic schema
            
        Returns:
            Created Trade object
        """
        trade = Trade(
            trade_id=trade_data.trade_id,
            ticker=trade_data.ticker,
            asset_name=trade_data.asset_name,
            asset_class=trade_data.asset_class,
            direction=trade_data.direction,
            quantity=trade_data.quantity,
            entry_price=trade_data.entry_price,
            entry_date=trade_data.entry_date,
            commission=trade_data.commission,
            currency=trade_data.currency,
            strategy_name=trade_data.strategy_name,
            signal_score=trade_data.signal_score,
            notes=trade_data.notes,
            status=TradeStatus.OPEN
        )
        
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        
        return trade
    
    async def bulk_create(self, trades_data: List[TradeCreate]) -> List[Trade]:
        """Bulk create trades for efficiency."""
        trades = [
            Trade(
                trade_id=td.trade_id,
                ticker=td.ticker,
                asset_name=td.asset_name,
                asset_class=td.asset_class,
                direction=td.direction,
                quantity=td.quantity,
                entry_price=td.entry_price,
                entry_date=td.entry_date,
                commission=td.commission,
                currency=td.currency,
                strategy_name=td.strategy_name,
                signal_score=td.signal_score,
                notes=td.notes,
                status=TradeStatus.OPEN
            )
            for td in trades_data
        ]
        
        self.db.add_all(trades)
        await self.db.commit()
        
        # Refresh all in parallel isn't directly supported easily in async
        # so we refresh them sequentially or rely on the returned list
        for trade in trades:
            await self.db.refresh(trade)
        
        return trades
    
    # ============== READ ==============
    
    async def get_by_id(self, trade_id: int) -> Optional[Trade]:
        """Get trade by internal ID."""
        result = await self.db.execute(select(Trade).filter(Trade.id == trade_id))
        return result.scalars().first()
    
    async def get_by_trade_id(self, trade_id: str) -> Optional[Trade]:
        """Get trade by external trade_id."""
        result = await self.db.execute(select(Trade).filter(Trade.trade_id == trade_id))
        return result.scalars().first()
    
    async def get_all(
        self,
        page: int = 1,
        page_size: int = None,
        ticker: Optional[str] = None,
        status: Optional[TradeStatus] = None,
        strategy: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "entry_date",
        sort_desc: bool = True
    ) -> Tuple[List[Trade], int]:
        """
        Get paginated trades with filtering.
        """
        page_size = page_size or settings.DEFAULT_PAGE_SIZE
        page_size = min(page_size, settings.MAX_PAGE_SIZE)
        
        # Build query with filters
        query = select(Trade)
        
        if ticker:
            query = query.filter(Trade.ticker == ticker.upper())
        
        if status:
            query = query.filter(Trade.status == status)
        
        if strategy:
            query = query.filter(Trade.strategy_name == strategy)
        
        if start_date:
            query = query.filter(Trade.entry_date >= start_date)
        
        if end_date:
            query = query.filter(Trade.entry_date <= end_date)
            
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Apply sorting
        sort_column = getattr(Trade, sort_by, Trade.entry_date)
        if sort_desc:
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        trades = result.scalars().all()
        
        return list(trades), total or 0
    
    async def get_recent(self, limit: int = 10) -> List[Trade]:
        """Get most recent trades."""
        query = select(Trade).order_by(desc(Trade.entry_date)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_open_positions(self) -> List[Trade]:
        """Get all open positions."""
        query = select(Trade).filter(Trade.status == TradeStatus.OPEN).order_by(desc(Trade.entry_date))
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_ticker(self, ticker: str) -> List[Trade]:
        """Get all trades for a specific ticker."""
        query = select(Trade).filter(Trade.ticker == ticker.upper()).order_by(desc(Trade.entry_date))
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ============== UPDATE ==============
    
    async def update(self, trade_id: int, trade_data: TradeUpdate) -> Optional[Trade]:
        """Update an existing trade."""
        trade = await self.get_by_id(trade_id)
        
        if not trade:
            return None
        
        # Update only provided fields
        update_data = trade_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(trade, field, value)
        
        # Calculate P&L if closing trade
        if trade_data.status == TradeStatus.CLOSED and trade_data.exit_price:
            trade.calculate_pnl()
        
        await self.db.commit()
        await self.db.refresh(trade)
        
        return trade
    
    async def close_trade(
        self, 
        trade_id: int, 
        exit_price: float, 
        exit_date: datetime = None
    ) -> Optional[Trade]:
        """Close a trade with exit price."""
        trade = await self.get_by_id(trade_id)
        
        if not trade or trade.status != TradeStatus.OPEN:
            return None
        
        trade.exit_price = exit_price
        trade.exit_date = exit_date or datetime.utcnow()
        trade.status = TradeStatus.CLOSED
        trade.calculate_pnl()
        
        await self.db.commit()
        await self.db.refresh(trade)
        
        return trade
    
    # ============== DELETE ==============
    
    async def delete(self, trade_id: int) -> bool:
        """Delete a trade by ID."""
        trade = await self.get_by_id(trade_id)
        
        if not trade:
            return False
        
        await self.db.delete(trade)
        await self.db.commit()
        
        return True
    
    # ============== AGGREGATIONS ==============
    
    async def get_statistics(self) -> dict:
        """Get aggregate trade statistics."""
        # Total trades
        total_trades = await self.db.scalar(select(func.count(Trade.id)))
        
        # Closed trades with P&L
        result = await self.db.execute(select(Trade).filter(Trade.status == TradeStatus.CLOSED))
        closed_trades = result.scalars().all()
        
        if not closed_trades:
            return {
                'total_trades': total_trades or 0,
                'closed_trades': 0,
                'open_trades': total_trades or 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        pnls = [t.pnl for t in closed_trades if t.pnl is not None]
        winning = sum(1 for p in pnls if p > 0)
        losing = sum(1 for p in pnls if p <= 0)
        
        return {
            'total_trades': total_trades or 0,
            'closed_trades': len(closed_trades),
            'open_trades': (total_trades or 0) - len(closed_trades),
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': (winning / len(pnls) * 100) if pnls else 0,
            'total_pnl': sum(pnls) if pnls else 0,
            'avg_pnl': sum(pnls) / len(pnls) if pnls else 0,
            'best_trade': max(pnls) if pnls else 0,
            'worst_trade': min(pnls) if pnls else 0
        }
    
    async def get_pnl_by_period(
        self, 
        start_date: datetime, 
        end_date: datetime = None
    ) -> float:
        """Get total P&L for a time period."""
        end_date = end_date or datetime.utcnow()
        
        query = select(func.sum(Trade.pnl)).filter(
            and_(
                Trade.status == TradeStatus.CLOSED,
                Trade.exit_date >= start_date,
                Trade.exit_date <= end_date
            )
        )
        
        result = await self.db.scalar(query)
        return float(result or 0.0)
    
    async def get_stats_by_ticker(self) -> List[dict]:
        """Get aggregated stats grouped by ticker."""
        query = select(
            Trade.ticker,
            func.count(Trade.id).label('total_trades'),
            func.sum(Trade.pnl).label('total_pnl'),
            func.avg(Trade.pnl).label('avg_pnl')
        ).filter(Trade.status == TradeStatus.CLOSED).group_by(Trade.ticker)
        
        result = await self.db.execute(query)
        
        return [
            {
                'ticker': r.ticker,
                'total_trades': r.total_trades,
                'total_pnl': r.total_pnl or 0,
                'avg_pnl': r.avg_pnl or 0
            }
            for r in result.all()
        ]
    
    # ============== PORTFOLIO SNAPSHOTS ==============
    
    async def get_latest_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot."""
        query = select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(1)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_snapshots_in_period(
        self,
        start_date: datetime,
        end_date: datetime = None
    ) -> List[PortfolioSnapshot]:
        """Get all snapshots within a date range."""
        end_date = end_date or datetime.utcnow()
        query = select(PortfolioSnapshot).filter(
            and_(
                PortfolioSnapshot.snapshot_date >= start_date,
                PortfolioSnapshot.snapshot_date <= end_date
            )
        ).order_by(PortfolioSnapshot.snapshot_date)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
