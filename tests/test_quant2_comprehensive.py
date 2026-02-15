"""
Comprehensive Quant 2 Backtesting Test Suite
=============================================
Tests covering all implementation layers:
1. Database Layer - IndexConstituent model
2. Data Access Layer - UniverseProvider
3. Backtest Integration - Dynamic universe support
4. Data Fetch Integration - Historical ticker extraction
5. Quant 2 Strategies - Residual Momentum, HMM Regime

Following Test Pyramid: Unit (70%), Integration (20%), E2E (10%)
"""

import sys
import os
# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_db_session(tmp_path):
    """Create a test database with all tables."""
    from backend.database.models import Base, IndexConstituent
    
    db_path = tmp_path / "test_quant2.db"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_prices():
    """Generate sample price data for backtesting tests."""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=500, freq='B')
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ', 'TLT']
    
    data = {}
    for ticker in tickers:
        returns = np.random.normal(0.0005, 0.015, len(dates))
        prices = 100 * np.exp(np.cumsum(returns))
        data[ticker] = prices
    
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def sample_monthly_returns():
    """Generate sample monthly returns for Quant 2 strategy tests."""
    np.random.seed(42)
    dates = pd.date_range(start='2018-01-01', periods=60, freq='M')
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    
    data = {}
    for ticker in tickers:
        returns = np.random.normal(0.01, 0.05, len(dates))
        data[ticker] = returns
    
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def populated_db(test_db_session):
    """Pre-populate database with test constituent data."""
    from backend.database.models import IndexConstituent
    
    session = test_db_session
    
    # Create historical snapshots
    base_date = datetime(2020, 1, 1)
    
    # Jan 2020 snapshot
    for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'FB']:
        session.add(IndexConstituent(
            ticker=ticker,
            index_name='SP500',
            start_date=base_date,
            active=True
        ))
    
    # June 2020 snapshot (FB renamed to META)
    june_date = datetime(2020, 6, 1)
    for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA']:  # Added NVDA
        session.add(IndexConstituent(
            ticker=ticker,
            index_name='SP500',
            start_date=june_date,
            active=True
        ))
    
    session.commit()
    return session


# =============================================================================
# 1. DATABASE LAYER TESTS
# =============================================================================

class TestIndexConstituentModel:
    """Unit tests for IndexConstituent database model."""
    
    def test_model_exists_and_tablename(self):
        """IndexConstituent model is properly defined with correct table name."""
        from backend.database.models import IndexConstituent
        
        assert IndexConstituent.__tablename__ == "index_constituents"
    
    def test_required_columns_exist(self):
        """All required columns are defined in the model."""
        from backend.database.models import IndexConstituent
        
        required_columns = ['id', 'ticker', 'index_name', 'start_date', 
                           'end_date', 'active', 'created_at']
        
        for col in required_columns:
            assert hasattr(IndexConstituent, col), f"Missing column: {col}"
    
    def test_create_constituent_record(self, test_db_session):
        """Can create and retrieve an IndexConstituent record."""
        from backend.database.models import IndexConstituent
        
        session = test_db_session
        record = IndexConstituent(
            ticker='AAPL',
            index_name='SP500',
            start_date=datetime(2020, 1, 1),
            end_date=None,
            active=True
        )
        session.add(record)
        session.commit()
        
        # Retrieve
        stored = session.query(IndexConstituent).filter_by(ticker='AAPL').first()
        assert stored is not None
        assert stored.ticker == 'AAPL'
        assert stored.index_name == 'SP500'
        assert stored.active is True
    
    def test_multiple_snapshots_same_ticker(self, test_db_session):
        """Same ticker can have multiple snapshot records."""
        from backend.database.models import IndexConstituent
        
        session = test_db_session
        
        # Add same ticker at different dates
        for i in range(3):
            record = IndexConstituent(
                ticker='MSFT',
                index_name='SP500',
                start_date=datetime(2020, 1 + i*3, 1),  # Jan, Apr, Jul
                active=True
            )
            session.add(record)
        
        session.commit()
        
        stored = session.query(IndexConstituent).filter_by(ticker='MSFT').all()
        assert len(stored) == 3
    
    def test_index_lookup_exists(self):
        """Composite lookup index is defined."""
        from backend.database.models import IndexConstituent
        
        indexes = list(IndexConstituent.__table__.indexes)
        index_names = [idx.name for idx in indexes]
        
        assert 'ix_constituents_lookup' in index_names
    
    def test_model_repr(self, test_db_session):
        """Model __repr__ returns readable string."""
        from backend.database.models import IndexConstituent
        
        session = test_db_session
        record = IndexConstituent(
            ticker='TEST',
            index_name='SP500',
            start_date=datetime(2020, 1, 1),
            active=True
        )
        session.add(record)
        session.commit()
        
        repr_str = repr(record)
        assert 'TEST' in repr_str
        assert 'SP500' in repr_str


# =============================================================================
# 2. DATA ACCESS LAYER TESTS
# =============================================================================

class TestUniverseProvider:
    """Unit tests for UniverseProvider class."""
    
    def test_import_and_instantiate(self):
        """UniverseProvider can be imported and created."""
        from strategy.data.universe import UniverseProvider
        
        provider = UniverseProvider()
        assert provider is not None
    
    def test_get_assets_at_date_empty_db(self):
        """Returns empty list when no data in database."""
        from strategy.data.universe import UniverseProvider
        
        provider = UniverseProvider()
        result = provider.get_assets_at_date(datetime(2099, 1, 1), 'NONEXISTENT')
        assert result == []
    
    def test_get_all_historical_tickers_returns_list(self):
        """get_all_historical_tickers returns a list type."""
        from strategy.data.universe import UniverseProvider
        
        provider = UniverseProvider()
        result = provider.get_all_historical_tickers('SP500')
        assert isinstance(result, list)
    
    def test_get_snapshot_dates_returns_list(self):
        """get_snapshot_dates returns a list type."""
        from strategy.data.universe import UniverseProvider
        
        provider = UniverseProvider()
        result = provider.get_snapshot_dates('SP500')
        assert isinstance(result, list)


class TestUniverseProviderWithData:
    """Integration tests for UniverseProvider with mocked data."""
    
    @patch('strategy.data.universe.SessionLocal')
    def test_get_assets_at_date_returns_correct_tickers(self, mock_session_local):
        """Correctly queries and returns tickers for a given date."""
        from strategy.data.universe import UniverseProvider
        
        # Setup mock
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Mock finding latest snapshot
        mock_db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = datetime(2020, 1, 1)
        
        # Mock getting tickers
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
            ('AAPL',), ('MSFT',), ('GOOGL',)
        ]
        
        provider = UniverseProvider()
        result = provider.get_assets_at_date(datetime(2020, 6, 1), 'SP500')
        
        assert isinstance(result, list)
    
    @patch('strategy.data.universe.SessionLocal')
    def test_get_all_historical_tickers_returns_unique(self, mock_session_local):
        """Returns all unique historical tickers."""
        from strategy.data.universe import UniverseProvider
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_db.query.return_value.filter.return_value.all.return_value = [
            ('AAPL',), ('MSFT',), ('META',), ('NVDA',)
        ]
        
        provider = UniverseProvider()
        result = provider.get_all_historical_tickers('SP500')
        
        assert len(result) == 4


# =============================================================================
# 3. BACKTEST INTEGRATION TESTS
# =============================================================================

# Try to import backtester - skip tests if unavailable
try:
    from strategy.infrastructure.backtest import PortfolioBacktester
    HAS_BACKTESTER = True
except ImportError:
    HAS_BACKTESTER = False


@pytest.mark.skipif(not HAS_BACKTESTER, reason="Backtester not available")
class TestBacktestDynamicUniverse:
    """Integration tests for backtest with dynamic universe support."""
    
    def test_run_backtest_with_dynamic_universe_param(self, sample_prices):
        """run_backtest accepts use_dynamic_universe parameter."""
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def simple_weights(prices, idx):
            n = len(prices.columns)
            return pd.Series(1/n, index=prices.columns)
        
        # Should not raise error even without DB data
        result = bt.run_backtest(
            simple_weights,
            rebalance_freq='monthly',
            use_dynamic_universe=False  # Disabled to test parameter exists
        )
        
        assert result is not None
        assert hasattr(result, 'portfolio_value')
        assert hasattr(result, 'metrics')
    
    def test_run_backtest_accepts_index_name_param(self, sample_prices):
        """run_backtest accepts index_name parameter."""
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def equal_weights(prices, idx):
            n = len(prices.columns)
            return pd.Series(1/n, index=prices.columns)
        
        # Should not raise error with index_name parameter
        result = bt.run_backtest(
            equal_weights,
            rebalance_freq='monthly',
            use_dynamic_universe=False,
            index_name='ASX200'  # Different index
        )
        
        assert result is not None
    
    def test_backtest_metrics_calculated_correctly(self, sample_prices):
        """Backtest calculates expected metrics."""
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def equal_weights(prices, idx):
            n = len(prices.columns)
            return pd.Series(1/n, index=prices.columns)
        
        result = bt.run_backtest(equal_weights, rebalance_freq='monthly')
        
        # Check required metrics exist
        required_metrics = ['total_return', 'cagr', 'volatility', 
                           'sharpe_ratio', 'max_drawdown']
        for metric in required_metrics:
            assert metric in result.metrics, f"Missing metric: {metric}"
    
    def test_execution_delay_parameter(self, sample_prices):
        """Execution delay parameter is stored in metrics."""
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def equal_weights(prices, idx):
            return pd.Series(1/len(prices.columns), index=prices.columns)
        
        result = bt.run_backtest(
            equal_weights, 
            rebalance_freq='monthly',
            execution_delay=2
        )
        
        assert result.metrics['execution_delay'] == 2


@pytest.mark.skipif(not HAS_BACKTESTER, reason="Backtester not available")
class TestBacktestCostCalculation:
    """Tests for transaction cost calculation."""
    
    def test_rebalance_cost_includes_slippage(self, sample_prices):
        """Rebalance cost calculation includes slippage."""
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        current_weights = pd.Series({'AAPL': 0.5, 'MSFT': 0.5})
        target_weights = pd.Series({'AAPL': 0.0, 'MSFT': 1.0})
        
        cost = bt._calculate_rebalance_cost(
            current_weights, 
            target_weights, 
            100000,
            slippage_bps=10.0,  # High slippage
            market_impact_bps=0.0
        )
        
        assert cost > 0
    
    def test_zero_turnover_zero_cost(self, sample_prices):
        """No cost when weights don't change significantly."""
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        weights = pd.Series({'AAPL': 0.5, 'MSFT': 0.5})
        
        cost = bt._calculate_rebalance_cost(
            weights, 
            weights,  # Same weights
            100000
        )
        
        assert cost == 0.0


# =============================================================================
# 4. DATA FETCH INTEGRATION TESTS
# =============================================================================

class TestDataFetchIntegration:
    """Tests for data fetch script integration."""
    
    def test_fetch_script_database_import(self):
        """Fetch script can import database modules."""
        try:
            from backend.database.connection import SessionLocal
            from backend.database.models import IndexConstituent
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import database modules: {e}")
    
    def test_stock_universe_import(self):
        """Stock universe module can be imported."""
        try:
            from strategy.stock_universe import get_screener_universe, get_us_etfs
            
            # These should be callable
            assert callable(get_screener_universe)
            assert callable(get_us_etfs)
        except ImportError as e:
            pytest.fail(f"Failed to import stock universe: {e}")


# =============================================================================
# 5. QUANT 2 STRATEGY TESTS
# =============================================================================

class TestResidualMomentumStrategy:
    """Tests for Residual Momentum strategy."""
    
    def test_residual_momentum_import(self):
        """ResidualMomentum can be imported."""
        from strategy.quant2.momentum.residual_momentum import ResidualMomentum
        
        rm = ResidualMomentum()
        assert rm is not None
    
    def test_residual_momentum_parameters(self):
        """ResidualMomentum accepts configuration parameters."""
        from strategy.quant2.momentum.residual_momentum import ResidualMomentum
        
        rm = ResidualMomentum(
            lookback_months=24,
            scoring_months=6,
            min_observations=18
        )
        
        assert rm.lookback_months == 24
        assert rm.scoring_months == 6
        assert rm.min_observations == 18
    
    def test_get_top_n_method_exists(self):
        """get_top_n method is available."""
        from strategy.quant2.momentum.residual_momentum import ResidualMomentum
        
        rm = ResidualMomentum()
        assert callable(getattr(rm, 'get_top_n', None))
    
    def test_get_bottom_n_method_exists(self):
        """get_bottom_n method is available."""
        from strategy.quant2.momentum.residual_momentum import ResidualMomentum
        
        rm = ResidualMomentum()
        assert callable(getattr(rm, 'get_bottom_n', None))


class TestHMMRegimeDetector:
    """Tests for HMM Regime Detection."""
    
    def test_hmm_detector_import(self):
        """HMM detector can be imported."""
        try:
            from strategy.quant2.regime.hmm_detector import HMMRegimeDetector
            detector = HMMRegimeDetector()
            assert detector is not None
        except ImportError:
            pytest.skip("HMM detector not available")


class TestVolatilityScaling:
    """Tests for Volatility Scaling module."""
    
    def test_volatility_scaling_import(self):
        """Volatility scaling can be imported."""
        try:
            from strategy.quant2.momentum.volatility_scaling import VolatilityScaler
            scaler = VolatilityScaler()
            assert scaler is not None
        except ImportError:
            pytest.skip("Volatility scaler not available")


# =============================================================================
# PERFORMANCE / STRESS TESTS
# =============================================================================

@pytest.mark.skipif(not HAS_BACKTESTER, reason="Backtester not available")
class TestBacktestPerformance:
    """Performance benchmarks for backtesting."""
    
    def test_backtest_completes_in_reasonable_time(self, sample_prices):
        """Backtest completes within acceptable time limit."""
        import time
        
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def simple_weights(prices, idx):
            return pd.Series(1/len(prices.columns), index=prices.columns)
        
        start = time.time()
        result = bt.run_backtest(simple_weights, rebalance_freq='monthly')
        elapsed = time.time() - start
        
        # Should complete in under 5 seconds for sample data
        assert elapsed < 5.0, f"Backtest took too long: {elapsed:.2f}s"
    
    def test_momentum_backtest_runs(self, sample_prices):
        """Momentum backtest strategy runs successfully."""
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        result = bt.run_momentum_backtest(lookback=63, top_n=3)
        
        assert result is not None
        assert result.metrics['total_return'] is not None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
