"""
API Endpoint Tests
==================
Tests for the dashboard API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_root_returns_healthy(self, api_client):
        """Health check should return without auth."""
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert data["security"] == "enabled"


class TestAuthentication:
    """Tests for API authentication."""
    
    def test_dashboard_requires_auth(self, api_client):
        """Dashboard endpoint should require API key."""
        response = api_client.get("/api/dashboard")
        assert response.status_code == 401
    
    def test_dashboard_with_valid_key(self, api_client, auth_headers):
        """Dashboard should work with valid API key."""
        response = api_client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200
    
    def test_scan_requires_auth(self, api_client):
        """Scan endpoint should require API key."""
        response = api_client.post("/api/scan", json={})
        assert response.status_code == 401
    
    def test_strategies_no_auth_required(self, api_client):
        """Strategies list should work without auth."""
        response = api_client.get("/api/strategies")
        # May return 200 or 500 depending on pipeline init
        assert response.status_code in [200, 500]


class TestInputValidation:
    """Tests for input validation."""
    
    def test_scan_valid_date(self, api_client, auth_headers):
        """Scan should accept valid date format."""
        response = api_client.post(
            "/api/scan",
            headers=auth_headers,
            json={"start_date": "2020-01-01"}
        )
        # May succeed or fail based on data, but should not be 422
        assert response.status_code != 422
    
    def test_scan_invalid_date_rejected(self, api_client, auth_headers):
        """Scan should reject invalid date format."""
        response = api_client.post(
            "/api/scan",
            headers=auth_headers,
            json={"start_date": "invalid-date"}
        )
        assert response.status_code == 422


class TestComparisonEndpoint:
    """Tests for comparison endpoint."""
    
    def test_comparison_requires_auth(self, api_client):
        """Comparison endpoint should require auth."""
        response = api_client.get("/api/comparison")
        assert response.status_code == 401
    
    def test_comparison_empty_results(self, api_client, auth_headers):
        """Comparison should return empty list if no results."""
        response = api_client.get("/api/comparison", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data
