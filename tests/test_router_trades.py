"""
Trade Router Tests
==================
Unit tests for the trades API endpoints.
Migrated to pytest-asyncio with httpx AsyncClient.
"""

import pytest
from datetime import datetime


class TestTradesCRUD:
    """Tests for trade CRUD operations."""

    async def test_create_trade_valid(self, async_client):
        """Create trade with valid data."""
        trade_data = {
            "trade_id": f"TEST-{datetime.now().timestamp()}",
            "ticker": "SPY",
            "direction": "BUY",
            "quantity": 100,
            "entry_price": 450.0,
            "entry_date": "2024-01-15T10:00:00",
            "strategy_name": "Momentum"
        }
        response = await async_client.post("/api/trades/", json=trade_data)
        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "SPY"
        assert data["direction"] == "BUY"

    async def test_create_trade_invalid_direction(self, async_client):
        """Create trade with invalid direction should fail."""
        trade_data = {
            "trade_id": "TEST-INVALID",
            "ticker": "SPY",
            "direction": "INVALID",
            "quantity": 100,
            "entry_price": 450.0,
            "entry_date": "2024-01-15T10:00:00"
        }
        response = await async_client.post("/api/trades/", json=trade_data)
        assert response.status_code == 422

    async def test_create_trade_negative_quantity(self, async_client):
        """Create trade with negative quantity should fail."""
        trade_data = {
            "trade_id": "TEST-NEG",
            "ticker": "SPY",
            "direction": "BUY",
            "quantity": -100,
            "entry_price": 450.0,
            "entry_date": "2024-01-15T10:00:00"
        }
        response = await async_client.post("/api/trades/", json=trade_data)
        assert response.status_code == 422

    async def test_get_trades_list(self, async_client):
        """Get paginated list of trades."""
        response = await async_client.get("/api/trades/")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert isinstance(data["trades"], list)

    async def test_get_trades_with_pagination(self, async_client):
        """Get trades with custom pagination."""
        response = await async_client.get("/api/trades/?page=1&page_size=10")
        assert response.status_code == 200

    async def test_get_trade_not_found(self, async_client):
        """Get non-existent trade returns 404."""
        response = await async_client.get("/api/trades/99999")
        assert response.status_code == 404

    async def test_update_trade_not_found(self, async_client):
        """Update non-existent trade returns 404."""
        response = await async_client.patch("/api/trades/99999", json={"notes": "test"})
        assert response.status_code == 404

    async def test_delete_trade_not_found(self, async_client):
        """Delete non-existent trade returns 404."""
        response = await async_client.delete("/api/trades/99999")
        assert response.status_code == 404


class TestTradeMetrics:
    """Tests for trade metrics endpoints."""

    async def test_get_portfolio_metrics(self, async_client):
        """Get portfolio metrics."""
        response = await async_client.get("/api/trades/metrics/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data

    async def test_get_portfolio_metrics_with_capital(self, async_client):
        """Get portfolio metrics with custom initial capital."""
        response = await async_client.get("/api/trades/metrics/portfolio?initial_capital=50000")
        assert response.status_code == 200

    async def test_get_dashboard_summary(self, async_client):
        """Get dashboard summary."""
        response = await async_client.get("/api/trades/metrics/dashboard")
        assert response.status_code == 200

    async def test_get_stats_by_ticker(self, async_client):
        """Get performance stats grouped by ticker."""
        response = await async_client.get("/api/trades/metrics/by-ticker")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTradeUtilities:
    """Tests for trade utility endpoints."""

    async def test_generate_trade_id(self, async_client):
        """Generate a unique trade ID."""
        response = await async_client.get("/api/trades/utils/generate-id")
        assert response.status_code == 200
        data = response.json()
        assert "trade_id" in data
        assert data["trade_id"].startswith("TRD")

    async def test_generate_trade_id_custom_prefix(self, async_client):
        """Generate trade ID with custom prefix."""
        response = await async_client.get("/api/trades/utils/generate-id?prefix=MOM")
        assert response.status_code == 200
        data = response.json()
        assert data["trade_id"].startswith("MOM")
