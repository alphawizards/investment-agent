"""
Pytest Configuration and Fixtures
==================================
Shared fixtures for all tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


# ============== Sample Data Fixtures ==============

@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=500, freq='B')
    tickers = ['SPY', 'QQQ', 'TLT', 'GLD', 'VTI']
    
    # Generate correlated random walks
    n = len(dates)
    data = {}
    for ticker in tickers:
        returns = np.random.normal(0.0005, 0.015, n)
        prices = 100 * np.exp(np.cumsum(returns))
        data[ticker] = prices
    
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def sample_returns(sample_prices):
    """Generate returns from sample prices."""
    return sample_prices.pct_change().dropna()


# ============== Mock Fixtures ==============

@pytest.fixture
def mock_yfinance(sample_prices):
    """Mock yfinance.download to return sample data."""
    with patch('yfinance.download') as mock:
        mock.return_value = sample_prices
        yield mock


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('strategy.pipeline.config.settings') as mock:
        mock.API_KEY = 'test-api-key'
        mock.API_KEY_HASH = ''
        mock.CORS_ORIGINS = 'http://localhost:3000'
        mock.cors_origins_list = ['http://localhost:3000']
        mock.USE_VECTORBT = True
        mock.VECTORBT_TIMEOUT = 30
        mock.RISK_FREE_RATE = 0.04
        mock.RATE_LIMIT_DEFAULT = '100/minute'
        mock.RATE_LIMIT_SCAN = '10/minute'
        yield mock


# ============== API Client Fixtures ==============

@pytest.fixture
def api_client(mock_settings):
    """Create test client for API."""
    from backend.dashboard_api import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Headers with valid API key."""
    return {'X-API-Key': 'test-api-key'}


# ============== Pipeline Fixtures ==============

@pytest.fixture
def pipeline_config():
    """Create test pipeline config."""
    from strategy.pipeline.pipeline import PipelineConfig
    return PipelineConfig(
        start_date='2020-01-01',
        initial_capital=100_000.0
    )


# ============== File Fixtures ==============

@pytest.fixture
def temp_results_file(tmp_path):
    """Create temporary results JSON file."""
    import json
    results = {
        'generated_at': datetime.now().isoformat(),
        'strategies': {
            'Test_Strategy': {
                'final_value': 110000,
                'metrics': {
                    'CAGR': '10.00%',
                    'Sharpe Ratio': '1.500'
                }
            }
        }
    }
    file_path = tmp_path / 'pipeline_results.json'
    with open(file_path, 'w') as f:
        json.dump(results, f)
    return file_path
