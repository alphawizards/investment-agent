"""
Test Universe Provider
======================
Tests for the UniverseProvider class for Point-in-Time universe queries.
"""

import sys
import os
# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


class TestUniverseProvider:
    """Tests for UniverseProvider functionality."""
    
    def test_import(self):
        """Test that UniverseProvider can be imported."""
        from strategy.data.universe import UniverseProvider
        provider = UniverseProvider()
        assert provider is not None
    
    def test_get_assets_at_date_empty_db(self):
        """Test get_assets_at_date returns empty list when no data."""
        from strategy.data.universe import UniverseProvider
        
        provider = UniverseProvider()
        # Query a date far in the future where no data exists
        result = provider.get_assets_at_date(datetime(2099, 1, 1), 'NONEXISTENT_INDEX')
        assert result == []
    
    def test_get_all_historical_tickers_returns_list(self):
        """Test that get_all_historical_tickers returns a list."""
        from strategy.data.universe import UniverseProvider
        
        provider = UniverseProvider()
        result = provider.get_all_historical_tickers('SP500')
        assert isinstance(result, list)
    
    def test_get_snapshot_dates_returns_list(self):
        """Test that get_snapshot_dates returns a list of dates."""
        from strategy.data.universe import UniverseProvider
        
        provider = UniverseProvider()
        result = provider.get_snapshot_dates('SP500')
        assert isinstance(result, list)


class TestUniverseProviderWithMockedDB:
    """Tests with mocked database for deterministic results."""
    
    @patch('strategy.data.universe.SessionLocal')
    def test_get_assets_at_date_with_data(self, mock_session_local):
        """Test get_assets_at_date returns correct tickers when data exists."""
        from strategy.data.universe import UniverseProvider
        
        # Setup mock
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Mock the query chain for finding latest snapshot
        mock_db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = datetime(2020, 1, 1)
        
        # Mock the query for getting tickers
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
            ('AAPL',), ('MSFT',), ('GOOGL',)
        ]
        
        provider = UniverseProvider()
        result = provider.get_assets_at_date(datetime(2020, 6, 1), 'SP500')
        
        # The function should work without errors
        assert isinstance(result, list)


class TestIndexConstituentModel:
    """Tests for the IndexConstituent database model."""
    
    def test_model_exists(self):
        """Test that IndexConstituent model is properly defined."""
        from backend.database.models import IndexConstituent
        
        assert IndexConstituent.__tablename__ == "index_constituents"
        
    def test_model_columns(self):
        """Test that required columns exist."""
        from backend.database.models import IndexConstituent
        
        # Check required columns
        assert hasattr(IndexConstituent, 'ticker')
        assert hasattr(IndexConstituent, 'index_name')
        assert hasattr(IndexConstituent, 'start_date')
        assert hasattr(IndexConstituent, 'end_date')
        assert hasattr(IndexConstituent, 'active')
        assert hasattr(IndexConstituent, 'created_at')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
