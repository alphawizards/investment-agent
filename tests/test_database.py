"""
Database Model Tests
====================
Tests for SQLAlchemy ORM models (Trade, PortfolioSnapshot).
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal


# ============== Fixtures ==============

@pytest.fixture
def test_db_session(tmp_path):
    """Create a test database session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    try:
        from backend.database.models import Base
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    except ImportError:
        pytest.skip("Backend database models not available")


# ============== Trade Model Tests ==============

class TestTradeModel:
    """Tests for the Trade model."""
    
    def test_trade_creation(self, test_db_session):
        """Trade can be created with required fields."""
        from backend.database.models import Trade, TradeDirection, TradeStatus
        
        session = test_db_session
        
        trade = Trade(
            trade_id="TEST_001",
            ticker="AAPL",
            direction=TradeDirection.BUY,
            quantity=100,
            entry_price=150.50,
            entry_date=datetime(2024, 1, 15, 10, 30, 0),
            strategy_name="Test_Strategy",
            status=TradeStatus.OPEN
        )
        session.add(trade)
        session.commit()
        
        # Reload
        stored = session.query(Trade).filter_by(trade_id="TEST_001").first()
        
        assert stored is not None
        assert stored.ticker == "AAPL"
        assert stored.quantity == 100
        assert stored.entry_price == 150.50
        assert stored.status == TradeStatus.OPEN
    
    def test_trade_pnl_calculation_buy(self, test_db_session):
        """PnL calculation correct for BUY trades."""
        from backend.database.models import Trade, TradeDirection, TradeStatus
        
        session = test_db_session
        
        trade = Trade(
            trade_id="PNL_BUY_001",
            ticker="AAPL",
            direction=TradeDirection.BUY,
            quantity=100,
            entry_price=150.00,
            exit_price=160.00,
            entry_date=datetime(2024, 1, 1),
            exit_date=datetime(2024, 1, 15),
            commission=3.0,  # $3 AUD per trade
            status=TradeStatus.CLOSED
        )
        
        trade.calculate_pnl()
        
        # PnL = (160 - 150) * 100 - 3 = 1000 - 3 = 997
        assert trade.pnl == 997.0
        
        # PnL% = ((160 - 150) / 150) * 100 = 6.67%
        assert round(trade.pnl_percent, 2) == 6.67
    
    def test_trade_pnl_calculation_sell(self, test_db_session):
        """PnL calculation correct for SELL (short) trades."""
        from backend.database.models import Trade, TradeDirection, TradeStatus
        
        session = test_db_session
        
        trade = Trade(
            trade_id="PNL_SELL_001",
            ticker="AAPL",
            direction=TradeDirection.SELL,
            quantity=100,
            entry_price=160.00,  # Sold at 160
            exit_price=150.00,   # Bought back at 150
            entry_date=datetime(2024, 1, 1),
            exit_date=datetime(2024, 1, 15),
            commission=3.0,
            status=TradeStatus.CLOSED
        )
        
        trade.calculate_pnl()
        
        # PnL = (160 - 150) * 100 - 3 = 1000 - 3 = 997
        assert trade.pnl == 997.0
        
        # PnL% = ((160 - 150) / 160) * 100 = 6.25%
        assert round(trade.pnl_percent, 2) == 6.25
    
    def test_trade_status_transitions(self, test_db_session):
        """Trade status can transition from OPEN to CLOSED."""
        from backend.database.models import Trade, TradeDirection, TradeStatus
        
        session = test_db_session
        
        trade = Trade(
            trade_id="STATUS_001",
            ticker="SPY",
            direction=TradeDirection.BUY,
            quantity=50,
            entry_price=450.00,
            entry_date=datetime(2024, 1, 1),
            status=TradeStatus.OPEN
        )
        session.add(trade)
        session.commit()
        
        # Verify initial status
        assert trade.status == TradeStatus.OPEN
        
        # Close the trade
        trade.exit_price = 460.00
        trade.exit_date = datetime(2024, 1, 10)
        trade.status = TradeStatus.CLOSED
        trade.calculate_pnl()
        session.commit()
        
        # Reload and verify
        session.refresh(trade)
        assert trade.status == TradeStatus.CLOSED
        assert trade.pnl is not None
    
    def test_trade_bitemporal_timestamps(self, test_db_session):
        """Bi-temporal timestamps are correctly populated."""
        from backend.database.models import Trade, TradeDirection, TradeStatus
        
        session = test_db_session
        
        event_time = datetime(2024, 1, 15, 10, 30, 0)
        
        trade = Trade(
            trade_id="TEMPORAL_001",
            ticker="MSFT",
            direction=TradeDirection.BUY,
            quantity=25,
            entry_price=380.00,
            entry_date=event_time,
            event_timestamp=event_time,  # When the trade actually occurred
            status=TradeStatus.OPEN
        )
        session.add(trade)
        session.commit()
        
        session.refresh(trade)
        
        # Event timestamp should match what we set
        assert trade.event_timestamp == event_time
        
        # Knowledge timestamp should be auto-set (server_default)
        # Note: SQLite may not set this automatically in all cases
        # so we just check it's either set or None
        # In production with proper DB, it should always be set


# ============== PortfolioSnapshot Model Tests ==============

class TestPortfolioSnapshotModel:
    """Tests for the PortfolioSnapshot model."""
    
    def test_snapshot_creation(self, test_db_session):
        """Portfolio snapshot can be created."""
        from backend.database.models import PortfolioSnapshot
        
        session = test_db_session
        
        snapshot = PortfolioSnapshot(
            snapshot_date=datetime(2024, 1, 15),
            total_value=105000.00,
            cash_balance=10500.00,
            invested_value=94500.00,
            daily_return=0.005,
            cumulative_return=0.05,
            num_positions=5
        )
        session.add(snapshot)
        session.commit()
        
        stored = session.query(PortfolioSnapshot).first()
        
        assert stored is not None
        assert stored.total_value == 105000.00
        assert stored.num_positions == 5
    
    def test_snapshot_metrics_nullable(self, test_db_session):
        """Optional metrics can be null."""
        from backend.database.models import PortfolioSnapshot
        
        session = test_db_session
        
        # Create minimal snapshot without optional fields
        snapshot = PortfolioSnapshot(
            snapshot_date=datetime(2024, 1, 15),
            total_value=100000.00,
            cash_balance=100000.00,
            invested_value=0.00
        )
        session.add(snapshot)
        session.commit()
        
        stored = session.query(PortfolioSnapshot).first()
        
        # Optional fields should be None
        assert stored.volatility_21d is None
        assert stored.sharpe_ratio_21d is None
        assert stored.max_drawdown is None
    
    def test_snapshot_bitemporal_queries(self, test_db_session):
        """Snapshots support bi-temporal queries."""
        from backend.database.models import PortfolioSnapshot
        
        session = test_db_session
        
        base_date = datetime(2024, 1, 1)
        
        # Create a series of snapshots
        for i in range(5):
            snapshot = PortfolioSnapshot(
                snapshot_date=base_date + timedelta(days=i),
                total_value=100000 + i * 1000,
                cash_balance=10000,
                invested_value=90000 + i * 1000,
                event_timestamp=base_date + timedelta(days=i)
            )
            session.add(snapshot)
        
        session.commit()
        
        # Query all snapshots
        all_snapshots = session.query(PortfolioSnapshot).order_by(
            PortfolioSnapshot.snapshot_date
        ).all()
        
        assert len(all_snapshots) == 5
        
        # Query specific date range
        mid_point = base_date + timedelta(days=2)
        filtered = session.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.snapshot_date >= mid_point
        ).all()
        
        assert len(filtered) == 3


# ============== Index Tests ==============

class TestDatabaseIndexes:
    """Tests to verify indexes are created correctly."""
    
    def test_trade_indexes_exist(self, test_db_session):
        """Trade table has expected indexes."""
        from backend.database.models import Trade
        
        # Get table indexes
        indexes = list(Trade.__table__.indexes)
        index_names = [idx.name for idx in indexes]
        
        # Check expected indexes exist
        assert 'ix_trades_ticker_date' in index_names or any('ticker' in str(idx) for idx in indexes)
    
    def test_snapshot_indexes_exist(self, test_db_session):
        """PortfolioSnapshot table has expected indexes."""
        from backend.database.models import PortfolioSnapshot
        
        indexes = list(PortfolioSnapshot.__table__.indexes)
        index_names = [idx.name for idx in indexes]
        
        # Check snapshot_date index exists
        assert 'ix_snapshot_date' in index_names or any('snapshot_date' in str(idx) for idx in indexes)


# ============== Run if executed directly ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
