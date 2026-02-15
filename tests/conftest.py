"""
Pytest Configuration and Fixtures
==================================
Shared fixtures for all tests.
"""

import pytest
import pytest_asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport

import os

# Set environment variable to use SQLite for tests
os.environ["USE_NEON"] = "False"
os.environ["DATABASE_URL"] = "sqlite:///./data/test_trades.db"


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


# ============== Async API Client Fixture ==============

@pytest_asyncio.fixture
async def async_client():
    """Async test client for API tests."""
    from backend.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


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
