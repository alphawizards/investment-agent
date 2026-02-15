"""
Point-in-Time (PIT) Query Helpers
=================================
Utilities for querying data as it was known at a specific point in time.

2025 Bi-Temporal Schema:
- knowledge_timestamp: When the system learned about this data
- event_timestamp: When the event actually occurred

This prevents look-ahead bias in backtesting by ensuring we only use
data that was available at the time of the simulated decision.
"""

from datetime import datetime
from typing import Optional, TypeVar, List
from sqlalchemy import and_
from sqlalchemy.orm import Session

# Generic type for models
T = TypeVar('T')


def query_as_of(
    session: Session,
    model: type,
    as_of_date: datetime,
    event_date: Optional[datetime] = None
) -> List:
    """
    Query records as they were known at a specific point in time.
    
    This is the core PIT query pattern that ensures no look-ahead bias.
    
    Args:
        session: SQLAlchemy session
        model: ORM model class (must have knowledge_timestamp column)
        as_of_date: The "knowledge" point in time (what we knew at this moment)
        event_date: Optional filter for event_timestamp
        
    Returns:
        List of records that were known at as_of_date
        
    Example:
        >>> # Get all trades as they were known on 2024-01-15
        >>> trades = query_as_of(session, Trade, datetime(2024, 1, 15))
        
        >>> # Get trades for events in January 2024, as known on Feb 1
        >>> trades = query_as_of(session, Trade, 
        ...     as_of_date=datetime(2024, 2, 1),
        ...     event_date=datetime(2024, 1, 31))
    """
    query = session.query(model).filter(
        model.knowledge_timestamp <= as_of_date
    )
    
    if event_date is not None:
        query = query.filter(model.event_timestamp <= event_date)
    
    return query.all()


def get_latest_records(
    session: Session,
    model: type,
    group_by_column: str,
    as_of_date: Optional[datetime] = None
) -> List:
    """
    Get the latest version of each record grouped by a column.
    
    Useful for getting current state when records are append-only.
    
    Args:
        session: SQLAlchemy session
        model: ORM model class
        group_by_column: Column to group by (e.g., 'ticker', 'trade_id')
        as_of_date: Optional PIT filter
        
    Returns:
        List of latest records for each group
    """
    from sqlalchemy import func
    
    # Subquery to get max knowledge_timestamp per group
    subq = session.query(
        getattr(model, group_by_column),
        func.max(model.knowledge_timestamp).label('max_kt')
    )
    
    if as_of_date is not None:
        subq = subq.filter(model.knowledge_timestamp <= as_of_date)
    
    subq = subq.group_by(getattr(model, group_by_column)).subquery()
    
    # Join back to get full records
    query = session.query(model).join(
        subq,
        and_(
            getattr(model, group_by_column) == getattr(subq.c, group_by_column),
            model.knowledge_timestamp == subq.c.max_kt
        )
    )
    
    return query.all()


def simulate_knowledge_at(
    session: Session,
    model: type,
    simulation_date: datetime,
    lookback_days: int = 365
) -> List:
    """
    Simulate what data was available for backtesting at a given date.
    
    This is the key function for preventing look-ahead bias:
    - Only returns records with knowledge_timestamp <= simulation_date
    - Only returns events within the lookback window
    
    Args:
        session: SQLAlchemy session
        model: ORM model class
        simulation_date: The point in time we're simulating
        lookback_days: Number of days of historical data to include
        
    Returns:
        List of records available at simulation_date
    """
    from datetime import timedelta
    
    event_start = simulation_date - timedelta(days=lookback_days)
    
    query = session.query(model).filter(
        and_(
            model.knowledge_timestamp <= simulation_date,
            model.event_timestamp >= event_start,
            model.event_timestamp <= simulation_date
        )
    )
    
    return query.all()


class PointInTimeContext:
    """
    Context manager for PIT queries.
    
    Example:
        >>> with PointInTimeContext(session, as_of=datetime(2024, 1, 15)) as pit:
        ...     trades = pit.query(Trade).all()  # Only trades known at 2024-01-15
    """
    
    def __init__(self, session: Session, as_of: datetime):
        self.session = session
        self.as_of = as_of
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def query(self, model: type):
        """Return query filtered by as_of date."""
        return self.session.query(model).filter(
            model.knowledge_timestamp <= self.as_of
        )
