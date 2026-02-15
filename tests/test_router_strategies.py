"""
Strategies Router Tests
======================
Unit tests for the strategies API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestStrategyListAndDetails:
    """Tests for strategy listing and details."""
    
    @pytest.fixture
    def strategies_client(self):
        """Create test client for strategies API."""
        from backend.main import app
        return TestClient(app)
    
    def test_list_strategies(self, strategies_client):
        """List all available strategies."""
        response = strategies_client.get("/api/strategies/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Each strategy should have required fields
        for strategy in data:
            assert "name" in strategy
            assert "category" in strategy
            assert "description" in strategy
    
    def test_get_strategy_details_valid(self, strategies_client):
        """Get details of a valid strategy."""
        response = strategies_client.get("/api/strategies/Momentum")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Momentum"
        assert "category" in data
        assert "parameters" in data
    
    def test_get_strategy_details_not_found(self, strategies_client):
        """Get details of non-existent strategy returns 404."""
        response = strategies_client.get("/api/strategies/NonExistentStrategy")
        assert response.status_code == 404
    
    def test_list_strategies_includes_quant2(self, strategies_client):
        """Strategy list includes Quant 2.0 strategies."""
        response = strategies_client.get("/api/strategies/")
        data = response.json()
        
        strategy_names = [s["name"] for s in data]
        assert "Regime_Detection" in strategy_names or "HRP" in strategy_names


class TestBacktestExecution:
    """Tests for backtest execution endpoints."""
    
    @pytest.fixture
    def strategies_client(self):
        """Create test client for strategies API."""
        from backend.main import app
        return TestClient(app)
    
    def test_run_backtest_valid_strategy(self, strategies_client):
        """Run backtest for a valid strategy."""
        request_data = {
            "strategy_name": "Momentum",
            "start_date": "2020-01-01",
            "initial_capital": 100000.0
        }
        response = strategies_client.post("/api/strategies/run", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "backtest_id" in data
        assert data["status"] == "started"
    
    def test_run_backtest_invalid_strategy(self, strategies_client):
        """Run backtest for invalid strategy returns 404."""
        request_data = {
            "strategy_name": "InvalidStrategy",
            "start_date": "2020-01-01"
        }
        response = strategies_client.post("/api/strategies/run", json=request_data)
        assert response.status_code == 404
    
    def test_run_backtest_custom_capital(self, strategies_client):
        """Run backtest with custom initial capital."""
        request_data = {
            "strategy_name": "HRP",
            "start_date": "2021-01-01",
            "initial_capital": 500000.0,
            "optimization_method": "HRP"
        }
        response = strategies_client.post("/api/strategies/run", json=request_data)
        assert response.status_code == 200


class TestBacktestStatusAndResults:
    """Tests for backtest status and results endpoints."""
    
    @pytest.fixture
    def strategies_client(self):
        """Create test client for strategies API."""
        from backend.main import app
        return TestClient(app)
    
    def test_get_backtest_status(self, strategies_client):
        """Get status of a strategy backtest."""
        response = strategies_client.get("/api/strategies/Momentum/status")
        assert response.status_code == 200
        data = response.json()
        assert "strategy_name" in data
        assert "status" in data
    
    def test_get_backtest_results_not_found(self, strategies_client):
        """Get results when no backtest has been run."""
        response = strategies_client.get("/api/strategies/NonExistentTest/results")
        assert response.status_code == 404


class TestStrategyComparison:
    """Tests for strategy comparison endpoint."""
    
    @pytest.fixture
    def strategies_client(self):
        """Create test client for strategies API."""
        from backend.main import app
        return TestClient(app)
    
    def test_compare_all_strategies(self, strategies_client):
        """Compare all strategies that have been run."""
        response = strategies_client.get("/api/strategies/compare/all")
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data
        assert "generated_at" in data
        assert "strategies_compared" in data
