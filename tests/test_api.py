"""
API Endpoint Tests
==================
Tests for the main API endpoints using async httpx client.
"""

import pytest


class TestHealthCheck:
    """Tests for health check and root endpoints."""

    async def test_root_returns_api_info(self, async_client):
        """Root endpoint should return API information."""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data

    async def test_health_returns_healthy(self, async_client):
        """Health check should return healthy status."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_api_root_lists_endpoints(self, async_client):
        """API root should list available endpoints."""
        response = await async_client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert "api_version" in data
        assert "endpoints" in data


class TestDashboardEndpoints:
    """Tests for dashboard API endpoints."""

    async def test_dashboard_root(self, async_client):
        """GET /api/dashboard/ should return 200 with strategy list."""
        response = await async_client.get("/api/dashboard/")
        assert response.status_code == 200

    async def test_dashboard_quant1(self, async_client):
        """GET /api/dashboard/quant1 should return 200."""
        response = await async_client.get("/api/dashboard/quant1")
        assert response.status_code == 200

    async def test_dashboard_quant2(self, async_client):
        """GET /api/dashboard/quant2 should return 200."""
        response = await async_client.get("/api/dashboard/quant2")
        assert response.status_code == 200

    async def test_dashboard_data_status(self, async_client):
        """GET /api/dashboard/data-status should return 200."""
        response = await async_client.get("/api/dashboard/data-status")
        assert response.status_code == 200


class TestValidationEndpoints:
    """Tests for validation API endpoints."""

    async def test_validation_strategies(self, async_client):
        """GET /api/validation/strategies should return 200."""
        response = await async_client.get("/api/validation/strategies")
        assert response.status_code == 200

    async def test_validation_from_reports(self, async_client):
        """GET /api/validation/from-reports should return 200."""
        response = await async_client.get("/api/validation/from-reports")
        assert response.status_code == 200


class TestScannerEndpoints:
    """Tests for scanner API endpoints."""

    async def test_scanner_root(self, async_client):
        """GET /api/scanner/ should return 200."""
        response = await async_client.get("/api/scanner/")
        assert response.status_code == 200

    async def test_scanner_results(self, async_client):
        """GET /api/scanner/results should return 200."""
        response = await async_client.get("/api/scanner/results")
        assert response.status_code == 200

    async def test_scanner_status(self, async_client):
        """GET /api/scanner/status should return 200."""
        response = await async_client.get("/api/scanner/status")
        assert response.status_code == 200
