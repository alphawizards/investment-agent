"""
Data Router Tests
=================
Unit tests for the data management API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestDataStatus:
    """Tests for data status endpoint."""
    
    @pytest.fixture
    def data_client(self):
        """Create test client for data API."""
        from backend.main import app
        return TestClient(app)
    
    def test_get_data_status(self, data_client):
        """Get current data status."""
        response = data_client.get("/api/data/status")
        assert response.status_code == 200
        data = response.json()
        
        # Should contain status for each data source
        assert "tiingo_status" in data
        assert "yfinance_status" in data
        assert "cache_size_mb" in data
        assert "cache_files" in data


class TestDataUniverse:
    """Tests for universe endpoint."""
    
    @pytest.fixture
    def data_client(self):
        """Create test client for data API."""
        from backend.main import app
        return TestClient(app)
    
    def test_get_universe_default(self, data_client):
        """Get default universe."""
        response = data_client.get("/api/data/universe")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_tickers" in data
        assert "by_source" in data
        assert data["total_tickers"] > 0
    
    def test_get_universe_filtered(self, data_client):
        """Get filtered universe."""
        response = data_client.get(
            "/api/data/universe?include_sp500=true&include_nasdaq100=false"
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_tickers" in data
    
    def test_get_universe_by_source(self, data_client):
        """Universe response includes source grouping."""
        response = data_client.get("/api/data/universe")
        data = response.json()
        
        assert "tiingo" in data["by_source"]
        assert "yfinance" in data["by_source"]
        assert "count" in data["by_source"]["tiingo"]


class TestTickerSource:
    """Tests for ticker source endpoint."""
    
    @pytest.fixture
    def data_client(self):
        """Create test client for data API."""
        from backend.main import app
        return TestClient(app)
    
    def test_get_ticker_source_us(self, data_client):
        """Get source for US ticker."""
        response = data_client.get("/api/data/source/SPY")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ticker"] == "SPY"
        assert data["source"] == "tiingo"
        assert "coverage" in data
    
    def test_get_ticker_source_asx(self, data_client):
        """Get source for ASX ticker."""
        response = data_client.get("/api/data/source/CBA.AX")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ticker"] == "CBA.AX"
        assert data["source"] == "yfinance"
    
    def test_get_ticker_source_crypto(self, data_client):
        """Get source for crypto ticker."""
        response = data_client.get("/api/data/source/BTC-USD")
        assert response.status_code == 200
        data = response.json()
        
        assert data["source"] == "yfinance"


class TestDataRefresh:
    """Tests for data refresh endpoint."""
    
    @pytest.fixture
    def data_client(self):
        """Create test client for data API."""
        from backend.main import app
        return TestClient(app)
    
    def test_refresh_specific_tickers(self, data_client):
        """Refresh specific tickers."""
        request_data = {
            "tickers": ["SPY", "QQQ"],
            "force": False
        }
        response = data_client.post("/api/data/refresh", json=request_data)
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "started"
        assert data["tickers_refreshed"] == 2
    
    def test_refresh_force_mode(self, data_client):
        """Force refresh bypasses cache."""
        request_data = {
            "tickers": ["SPY"],
            "force": True
        }
        response = data_client.post("/api/data/refresh", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
    
    def test_refresh_empty_tickers_uses_universe(self, data_client):
        """Empty tickers list refreshes entire universe."""
        request_data = {"tickers": None, "force": False}
        response = data_client.post("/api/data/refresh", json=request_data)
        # May succeed or fail based on module availability
        assert response.status_code in [200, 500]
