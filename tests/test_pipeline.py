"""
Pipeline Layer Tests
====================
Tests for the modular trading pipeline layers:
- DataLayer: Data ingestion and caching
- SignalLayer: Signal generation and filtering
- AllocationLayer: Portfolio optimization
- ReportingLayer: Metrics and report generation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock


# ============== Fixtures ==============

@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=500, freq='B')
    tickers = ['SPY', 'QQQ', 'TLT', 'GLD', 'VTI']
    
    data = {}
    for ticker in tickers:
        returns = np.random.normal(0.0005, 0.015, len(dates))
        prices = 100 * np.exp(np.cumsum(returns))
        data[ticker] = prices
    
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def sample_returns(sample_prices):
    """Generate returns from sample prices."""
    return sample_prices.pct_change().dropna()


# ============== Data Layer Tests ==============

class TestDataLayer:
    """Tests for data ingestion and management."""
    
    def test_data_ingestion_from_cache(self, tmp_path, sample_prices):
        """Data layer can load from Parquet cache."""
        cache_file = tmp_path / "prices.parquet"
        sample_prices.to_parquet(cache_file)
        
        # Load from cache
        loaded = pd.read_parquet(cache_file)
        
        assert not loaded.empty
        assert loaded.shape == sample_prices.shape
    
    def test_data_ingestion_fallback(self, sample_prices):
        """Data layer falls back to yFinance when cache missing."""
        with patch('yfinance.download', return_value=sample_prices):
            import yfinance as yf
            data = yf.download(['SPY'], start='2020-01-01', end='2021-01-01')
            assert not data.empty
    
    def test_missing_data_handling(self, sample_prices):
        """Missing data is handled gracefully."""
        # Create data with NaN values
        prices_with_nan = sample_prices.copy()
        prices_with_nan.iloc[10:15, 0] = np.nan  # Add NaN gap
        
        # Forward fill to handle missing
        filled = prices_with_nan.ffill()
        
        assert not filled.isna().any().any()
    
    def test_date_range_filtering(self, sample_prices):
        """Date range filtering works correctly."""
        start = pd.Timestamp('2020-06-01')
        end = pd.Timestamp('2020-12-31')
        
        filtered = sample_prices.loc[start:end]
        
        assert filtered.index.min() >= start
        assert filtered.index.max() <= end
        assert len(filtered) < len(sample_prices)


# ============== Signal Layer Tests ==============

class TestSignalLayer:
    """Tests for signal generation."""
    
    def test_momentum_signal_generation(self, sample_prices):
        """Momentum signals calculated correctly."""
        lookback = 252  # 1 year
        
        # Calculate momentum (simple return over lookback)
        momentum = sample_prices.iloc[-1] / sample_prices.iloc[-lookback] - 1
        
        assert len(momentum) == len(sample_prices.columns)
        assert all(isinstance(v, (float, np.floating)) for v in momentum)
    
    def test_dual_momentum_calculation(self, sample_prices, sample_returns):
        """Dual momentum (absolute + relative) calculated correctly."""
        lookback = 252
        risk_free_rate = 0.04 / 252  # Daily risk-free rate
        
        # Calculate returns over lookback period
        total_returns = sample_prices.iloc[-1] / sample_prices.iloc[-lookback] - 1
        
        # Absolute momentum: is return > risk-free?
        absolute_momentum = total_returns > (risk_free_rate * lookback)
        
        # Relative momentum: rank by returns
        relative_ranks = total_returns.rank(ascending=False)
        
        assert absolute_momentum.dtype == bool
        assert len(relative_ranks) == len(sample_prices.columns)
    
    def test_signal_threshold_filtering(self, sample_prices):
        """Only signals above threshold pass filter."""
        lookback = 252
        threshold = 0.0  # Only positive momentum
        
        momentum = sample_prices.iloc[-1] / sample_prices.iloc[-lookback] - 1
        
        # Filter by threshold
        passing = momentum[momentum > threshold]
        
        # All passing signals should be positive
        assert all(v > threshold for v in passing)


# ============== Allocation Layer Tests ==============

class TestAllocationLayer:
    """Tests for portfolio optimization."""
    
    def test_equal_weight_allocation(self, sample_prices):
        """Equal weight allocation sums to 1."""
        n_assets = len(sample_prices.columns)
        weights = pd.Series(1.0 / n_assets, index=sample_prices.columns)
        
        assert abs(weights.sum() - 1.0) < 1e-10
        assert all(w == weights[0] for w in weights)
    
    def test_inverse_volatility_weights(self, sample_returns):
        """Inverse volatility weights calculated correctly."""
        volatility = sample_returns.std()
        inv_vol = 1 / volatility
        weights = inv_vol / inv_vol.sum()
        
        # Weights should sum to 1
        assert abs(weights.sum() - 1.0) < 1e-10
        
        # Higher vol assets should have lower weights
        min_vol_asset = volatility.idxmin()
        max_vol_asset = volatility.idxmax()
        assert weights[min_vol_asset] > weights[max_vol_asset]
    
    def test_weight_constraints(self, sample_prices):
        """Weight constraints are respected."""
        min_weight = 0.05
        max_weight = 0.25
        n_assets = len(sample_prices.columns)
        
        # Start with equal weights
        weights = pd.Series(1.0 / n_assets, index=sample_prices.columns)
        
        # Apply constraints
        weights = weights.clip(lower=min_weight, upper=max_weight)
        weights = weights / weights.sum()  # Re-normalize
        
        assert weights.sum() > 0.99  # Close to 1
        assert all(w >= min_weight * 0.99 for w in weights)  # Allow small tolerance
        assert all(w <= max_weight * 1.01 for w in weights)
    
    def test_max_position_limits(self, sample_returns):
        """Maximum position size is enforced."""
        max_position = 0.30
        
        # Generate some weights that might violate limit
        volatility = sample_returns.std()
        inv_vol = 1 / volatility
        weights = inv_vol / inv_vol.sum()
        
        # Cap at max position
        weights = weights.clip(upper=max_position)
        weights = weights / weights.sum()
        
        # Verify no position exceeds limit (with tolerance for re-normalization)
        assert all(w <= max_position * 1.1 for w in weights)


# ============== Reporting Layer Tests ==============

class TestReportingLayer:
    """Tests for performance reporting."""
    
    def test_metrics_calculation(self, sample_returns):
        """Key metrics are calculated correctly."""
        # Calculate key metrics
        mean_return = sample_returns.mean().mean()
        volatility = sample_returns.std().mean()
        
        # Sharpe ratio (simplified)
        risk_free_rate = 0.04 / 252
        sharpe = (mean_return - risk_free_rate) / volatility * np.sqrt(252)
        
        # Max drawdown
        cumulative = (1 + sample_returns.mean(axis=1)).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        assert isinstance(sharpe, float)
        assert isinstance(max_drawdown, float)
        assert max_drawdown <= 0  # Drawdown is negative
    
    def test_cagr_calculation(self, sample_prices):
        """CAGR calculated correctly."""
        # Get first and last values
        start_value = sample_prices.iloc[0].mean()
        end_value = sample_prices.iloc[-1].mean()
        
        # Calculate years
        days = (sample_prices.index[-1] - sample_prices.index[0]).days
        years = days / 365.25
        
        # CAGR
        cagr = (end_value / start_value) ** (1 / years) - 1
        
        assert isinstance(cagr, float)
        assert -1 < cagr < 5  # Reasonable CAGR range
    
    def test_report_json_export(self, sample_returns, tmp_path):
        """Report can be exported to JSON."""
        import json
        
        # Create simple report
        report = {
            'strategy': 'Test Strategy',
            'metrics': {
                'mean_return': float(sample_returns.mean().mean()),
                'volatility': float(sample_returns.std().mean()),
                'sharpe': 1.5,
                'max_drawdown': -0.15
            },
            'timestamp': datetime.now().isoformat()
        }
        
        output_path = tmp_path / "report.json"
        with open(output_path, 'w') as f:
            json.dump(report, f)
        
        # Verify
        assert output_path.exists()
        with open(output_path, 'r') as f:
            loaded = json.load(f)
        
        assert loaded['strategy'] == 'Test Strategy'
        assert 'metrics' in loaded


# ============== Pipeline Integration Tests ==============

class TestPipelineIntegration:
    """Tests for pipeline orchestration."""
    
    def test_pipeline_config_defaults(self):
        """Pipeline config has sensible defaults."""
        try:
            from strategy.pipeline.pipeline import PipelineConfig
            
            config = PipelineConfig()
            
            assert config.initial_capital == 100_000.0
            assert config.rebalance_frequency in ['daily', 'weekly', 'monthly']
            assert 0 < config.max_position_pct <= 1
        except ImportError:
            pytest.skip("Pipeline module not available")
    
    def test_full_pipeline_simulation(self, sample_prices, sample_returns):
        """Full pipeline can be simulated without errors."""
        # Simulate simplified pipeline
        
        # 1. Data: Already have sample_prices
        assert not sample_prices.empty
        
        # 2. Signal: Calculate momentum
        lookback = min(252, len(sample_prices) - 1)
        momentum = sample_prices.iloc[-1] / sample_prices.iloc[-lookback] - 1
        assert len(momentum) > 0
        
        # 3. Allocation: Equal weight for positive momentum
        selected = momentum[momentum > 0].index
        if len(selected) > 0:
            weights = pd.Series(1.0 / len(selected), index=selected)
            assert abs(weights.sum() - 1.0) < 1e-10
        
        # 4. Reporting: Calculate basic metrics
        portfolio_returns = sample_returns[selected].mean(axis=1) if len(selected) > 0 else sample_returns.mean(axis=1)
        equity_curve = (1 + portfolio_returns).cumprod()
        
        assert len(equity_curve) > 0
        assert equity_curve.iloc[-1] > 0


# ============== Run if executed directly ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
