"""
Universe API Tests
==================
Tests for the stock universe endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestUniverseList:
    """Tests for listing universes."""
    
    def test_list_universes_returns_list(self, api_client):
        """Should return list of available universes."""
        response = api_client.get("/api/universes/")
        assert response.status_code == 200
        data = response.json()
        assert "universes" in data
        assert "count" in data
        assert isinstance(data["universes"], list)
        assert data["count"] > 0
    
    def test_list_universes_has_expected_keys(self, api_client):
        """Each universe should have key, name, region, ticker_count."""
        response = api_client.get("/api/universes/")
        assert response.status_code == 200
        data = response.json()
        
        for universe in data["universes"]:
            assert "key" in universe
            assert "name" in universe
            assert "region" in universe
            assert "ticker_count" in universe
    
    def test_list_includes_spx500(self, api_client):
        """SPX500 should be in the list."""
        response = api_client.get("/api/universes/")
        assert response.status_code == 200
        data = response.json()
        
        keys = [u["key"] for u in data["universes"]]
        assert "SPX500" in keys


class TestUniverseDetail:
    """Tests for getting universe details."""
    
    def test_get_spx500_details(self, api_client):
        """Should return SPX500 details with tickers."""
        response = api_client.get("/api/universes/SPX500")
        assert response.status_code == 200
        data = response.json()
        
        assert data["key"] == "SPX500"
        assert data["name"] == "S&P 500"
        assert data["region"] == "US"
        assert "tickers" in data
        assert len(data["tickers"]) > 0
    
    def test_get_nasdaq100_tickers(self, api_client):
        """Should return NASDAQ100 tickers."""
        response = api_client.get("/api/universes/NASDAQ100/tickers")
        assert response.status_code == 200
        data = response.json()
        
        assert data["universe"] == "NASDAQ100"
        assert "tickers" in data
        assert data["count"] > 0
    
    def test_invalid_universe_returns_404(self, api_client):
        """Invalid universe key should return 404."""
        response = api_client.get("/api/universes/INVALID_UNIVERSE")
        assert response.status_code == 404


class TestUniverseRegions:
    """Tests for filtering by region."""
    
    def test_filter_by_us_region(self, api_client):
        """Should return only US universes."""
        response = api_client.get("/api/universes/regions/US")
        assert response.status_code == 200
        data = response.json()
        
        assert data["region"] == "US"
        assert "universes" in data
        assert len(data["universes"]) > 0
        
        for u in data["universes"]:
            assert u["region"] == "US"
    
    def test_filter_by_au_region(self, api_client):
        """Should return only AU universes."""
        response = api_client.get("/api/universes/regions/AU")
        assert response.status_code == 200
        data = response.json()
        
        assert data["region"] == "AU"
        for u in data["universes"]:
            assert u["region"] == "AU"
    
    def test_invalid_region_returns_404(self, api_client):
        """Invalid region should return 404."""
        response = api_client.get("/api/universes/regions/MARS")
        assert response.status_code == 404


class TestQuant2DashboardWithUniverse:
    """Tests for quant2 dashboard with universe parameter."""
    
    def test_quant2_default_universe(self, api_client):
        """Quant2 dashboard should default to SPX500."""
        response = api_client.get("/api/dashboard/quant2")
        assert response.status_code == 200
        data = response.json()
        
        # Should have universe info
        assert "universe" in data or "universe_key" in data
    
    def test_quant2_with_nasdaq100(self, api_client):
        """Quant2 dashboard should accept NASDAQ100 universe."""
        response = api_client.get("/api/dashboard/quant2?universe=NASDAQ100")
        assert response.status_code == 200
        data = response.json()
        
        # Should have universe key or info
        if "universe_key" in data:
            assert data["universe_key"] == "NASDAQ100"


class TestQuant2ResidualMomentum:
    """Tests for the dedicated residual momentum endpoint."""
    
    def test_residual_momentum_default(self, api_client):
        """Residual momentum should return data for default universe."""
        response = api_client.get("/api/quant2/residual-momentum")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "universe" in data
        assert "universe_name" in data
        assert "rankings" in data
        assert "stocks_ranked" in data
        assert "top_score" in data
        assert "avg_r_squared" in data
        
        # Verify has rankings
        assert len(data["rankings"]) > 0
    
    def test_residual_momentum_spx500(self, api_client):
        """Residual momentum for SPX500 should return 500 stocks."""
        response = api_client.get("/api/quant2/residual-momentum?universe=SPX500&top_n=20")
        assert response.status_code == 200
        data = response.json()
        
        assert data["universe"] == "SPX500"
        assert data["universe_name"] == "S&P 500"
        assert len(data["rankings"]) == 20
        
        # Verify ranking structure
        first = data["rankings"][0]
        assert "rank" in first
        assert "ticker" in first
        assert "score" in first
        assert first["rank"] == 1
    
    def test_residual_momentum_nasdaq100(self, api_client):
        """Residual momentum for NASDAQ100."""
        response = api_client.get("/api/quant2/residual-momentum?universe=NASDAQ100")
        assert response.status_code == 200
        data = response.json()
        
        assert data["universe"] == "NASDAQ100"
        assert data["stocks_ranked"] > 0
    
    def test_residual_momentum_asx200(self, api_client):
        """Residual momentum for ASX200."""
        response = api_client.get("/api/quant2/residual-momentum?universe=ASX200")
        assert response.status_code == 200
        data = response.json()
        
        assert data["universe"] == "ASX200"
        # ASX tickers should have .AX suffix
        assert any(".AX" in r["ticker"] for r in data["rankings"])
    
    def test_residual_momentum_invalid_universe(self, api_client):
        """Invalid universe should return 400."""
        response = api_client.get("/api/quant2/residual-momentum?universe=INVALID")
        assert response.status_code == 400
    
    def test_residual_momentum_with_bottom(self, api_client):
        """Include bottom rankings when requested."""
        response = api_client.get("/api/quant2/residual-momentum?include_bottom=true&top_n=10")
        assert response.status_code == 200
        data = response.json()
        
        # Should have both top and bottom rankings
        assert "rankings" in data
        assert "bottom_rankings" in data
        assert len(data["bottom_rankings"]) == 10


class TestQuant2ValidateUniverse:
    """Tests for universe validation endpoint."""
    
    def test_validate_spx500(self, api_client):
        """Validate SPX500 universe."""
        response = api_client.get("/api/quant2/validate-universe?universe=SPX500")
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] == True
        assert data["ticker_count"] > 0
        assert len(data["sample_tickers"]) > 0
    
    def test_validate_invalid(self, api_client):
        """Invalid universe should return valid=False."""
        response = api_client.get("/api/quant2/validate-universe?universe=FAKE")
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] == False
