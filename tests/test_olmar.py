"""
OLMAR Strategy Tests
====================
Unit tests for OLMAR kernels, constraints, and strategy.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings


class TestOLMARKernels:
    """Tests for OLMAR mathematical kernels."""
    
    @pytest.fixture
    def sample_prices(self):
        """Create sample price data for testing."""
        np.random.seed(42)
        n_days = 100
        n_assets = 5
        
        dates = pd.date_range('2023-01-01', periods=n_days, freq='B')
        
        # Simulated prices with random walk
        prices_data = np.zeros((n_days, n_assets))
        prices_data[0] = 100  # Start at 100
        
        for i in range(1, n_days):
            returns = np.random.normal(0.0005, 0.02, n_assets)
            prices_data[i] = prices_data[i-1] * (1 + returns)
        
        return pd.DataFrame(
            prices_data,
            index=dates,
            columns=['A', 'B', 'C', 'D', 'E']
        )
    
    def test_price_relatives_shape(self, sample_prices):
        """Price relatives should have same shape as input."""
        from strategy.quant1.olmar.kernels import calculate_price_relatives
        
        result = calculate_price_relatives(sample_prices)
        
        assert result.shape == sample_prices.shape
        assert list(result.columns) == list(sample_prices.columns)
    
    def test_price_relatives_first_row_nan(self, sample_prices):
        """First row should be NaN (no previous price)."""
        from strategy.quant1.olmar.kernels import calculate_price_relatives
        
        result = calculate_price_relatives(sample_prices)
        
        assert result.iloc[0].isna().all()
    
    def test_price_relatives_values(self, sample_prices):
        """Price relatives should be p_t / p_{t-1}."""
        from strategy.quant1.olmar.kernels import calculate_price_relatives
        
        result = calculate_price_relatives(sample_prices)
        
        # Check a few values manually
        for i in range(1, min(5, len(sample_prices))):
            expected = sample_prices.iloc[i] / sample_prices.iloc[i-1]
            np.testing.assert_array_almost_equal(
                result.iloc[i].values,
                expected.values,
                decimal=10
            )
    
    def test_price_relatives_no_nan_inf(self, sample_prices):
        """After first row, there should be no NaN or Inf."""
        from strategy.quant1.olmar.kernels import calculate_price_relatives
        
        result = calculate_price_relatives(sample_prices)
        
        # Skip first row (expected to be NaN)
        data = result.iloc[1:]
        
        assert not data.isna().any().any(), "Unexpected NaN values"
        assert not np.isinf(data.values).any(), "Unexpected Inf values"
    
    def test_ma_prediction_shape(self, sample_prices):
        """MA prediction should have same shape as input."""
        from strategy.quant1.olmar.kernels import predict_ma_reversion
        
        result = predict_ma_reversion(sample_prices, window=5)
        
        assert result.shape == sample_prices.shape
    
    def test_ma_prediction_values(self, sample_prices):
        """MA prediction should be MA / current price."""
        from strategy.quant1.olmar.kernels import predict_ma_reversion
        
        window = 5
        result = predict_ma_reversion(sample_prices, window=window)
        
        # Manual calculation for verification
        ma = sample_prices.rolling(window=window, min_periods=1).mean()
        expected = ma / sample_prices
        expected = expected.fillna(1.0)
        
        np.testing.assert_array_almost_equal(
            result.values,
            expected.values,
            decimal=10
        )
    
    def test_simplex_projection_sums_to_one(self):
        """Projected weights should sum to 1."""
        from strategy.quant1.olmar.kernels import project_simplex
        
        # Test cases
        test_vectors = [
            np.array([0.5, 0.3, 0.2]),  # Already on simplex
            np.array([1.0, 1.0, 1.0]),  # Needs normalization
            np.array([-0.5, 0.8, 0.7]),  # Has negative
            np.array([0.0, 0.0, 0.0]),  # All zeros
        ]
        
        for vec in test_vectors:
            result = project_simplex(vec)
            assert abs(result.sum() - 1.0) < 1e-6, f"Sum is {result.sum()}, not 1.0"
    
    def test_simplex_projection_non_negative(self):
        """Projected weights should all be >= 0."""
        from strategy.quant1.olmar.kernels import project_simplex
        
        # Test with negative values
        vec = np.array([-0.5, 0.8, 0.3, -0.2, 0.6])
        result = project_simplex(vec)
        
        assert (result >= -1e-10).all(), f"Minimum weight is {result.min()}"
    
    def test_olmar_update_on_simplex(self):
        """Updated weights should be on simplex."""
        from strategy.quant1.olmar.kernels import olmar_update
        
        current = np.array([0.2, 0.3, 0.5])
        prediction = np.array([1.1, 0.9, 1.05])  # Different predictions
        
        result = olmar_update(current, prediction, epsilon=10)
        
        # Check simplex constraints
        assert abs(result.sum() - 1.0) < 1e-6, f"Sum is {result.sum()}"
        assert (result >= -1e-10).all(), f"Min weight is {result.min()}"
    
    def test_olmar_weights_shape(self, sample_prices):
        """OLMAR weights should have same shape as prices."""
        from strategy.quant1.olmar.kernels import olmar_weights
        
        result = olmar_weights(sample_prices, window=5, epsilon=10)
        
        assert result.shape == sample_prices.shape
        assert list(result.columns) == list(sample_prices.columns)
    
    def test_olmar_weights_sum_to_one(self, sample_prices):
        """All weight rows should sum to 1."""
        from strategy.quant1.olmar.kernels import olmar_weights
        
        result = olmar_weights(sample_prices, window=5, epsilon=10)
        
        row_sums = result.sum(axis=1)
        
        for i, s in enumerate(row_sums):
            assert abs(s - 1.0) < 1e-6, f"Row {i} sums to {s}"
    
    def test_olmar_weights_non_negative(self, sample_prices):
        """All weights should be >= 0."""
        from strategy.quant1.olmar.kernels import olmar_weights
        
        result = olmar_weights(sample_prices, window=5, epsilon=10)
        
        assert (result.values >= -1e-10).all(), f"Min weight is {result.values.min()}"


class TestOLMARConstraints:
    """Tests for OLMAR cost constraints."""
    
    def test_turnover_calculation(self):
        """Turnover should be half the sum of absolute weight changes."""
        from strategy.quant1.olmar.constraints import calculate_turnover
        
        old = np.array([0.2, 0.3, 0.5])
        new = np.array([0.4, 0.1, 0.5])
        
        result = calculate_turnover(old, new)
        
        # Expected: |0.2-0.4| + |0.3-0.1| + |0.5-0.5| = 0.2 + 0.2 + 0 = 0.4
        # Turnover = 0.4 / 2 = 0.2
        expected = 0.2
        
        assert abs(result - expected) < 1e-10
    
    def test_turnover_cap_reduces_turnover(self):
        """Turnover cap should reduce turnover to max level."""
        from strategy.quant1.olmar.constraints import apply_turnover_cap, calculate_turnover
        
        old = np.array([0.2, 0.3, 0.5])
        new = np.array([0.5, 0.0, 0.5])  # High turnover
        
        max_turnover = 0.1
        result = apply_turnover_cap(old, new, max_turnover)
        
        actual_turnover = calculate_turnover(old, result)
        
        assert actual_turnover <= max_turnover + 1e-6
    
    def test_turnover_cap_preserves_simplex(self):
        """Capped weights should still be on simplex."""
        from strategy.quant1.olmar.constraints import apply_turnover_cap
        
        old = np.array([0.2, 0.3, 0.5])
        new = np.array([0.5, 0.0, 0.5])
        
        result = apply_turnover_cap(old, new, max_turnover=0.1)
        
        assert abs(result.sum() - 1.0) < 1e-6
        assert (result >= -1e-10).all()
    
    def test_zero_cost_warning(self):
        """Should warn when transaction costs are zero."""
        from strategy.quant1.olmar.constraints import warn_if_zero_costs
        
        with pytest.warns(UserWarning, match="Transaction costs set to 0"):
            warn_if_zero_costs(0)
    
    def test_low_cost_warning(self):
        """Should warn when transaction costs are very low."""
        from strategy.quant1.olmar.constraints import warn_if_zero_costs
        
        with pytest.warns(UserWarning, match="very low"):
            warn_if_zero_costs(2)
    
    def test_reasonable_cost_no_warning(self):
        """Should not warn with reasonable costs."""
        from strategy.quant1.olmar.constraints import warn_if_zero_costs
        
        # This should not raise a warning
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            warn_if_zero_costs(15)  # 15 bps is reasonable


class TestOLMARStrategy:
    """Tests for OLMAR strategy integration."""
    
    @pytest.fixture
    def sample_prices(self):
        """Create sample price data."""
        np.random.seed(42)
        n_days = 100
        n_assets = 5
        
        dates = pd.date_range('2023-01-01', periods=n_days, freq='B')
        
        prices_data = np.zeros((n_days, n_assets))
        prices_data[0] = 100
        
        for i in range(1, n_days):
            returns = np.random.normal(0.0005, 0.02, n_assets)
            prices_data[i] = prices_data[i-1] * (1 + returns)
        
        return pd.DataFrame(
            prices_data,
            index=dates,
            columns=['A', 'B', 'C', 'D', 'E']
        )
    
    def test_strategy_creation(self):
        """Strategy should be created with default config."""
        from strategy.quant1.olmar.olmar_strategy import OLMARStrategy, OLMARConfig
        
        strategy = OLMARStrategy()
        
        assert strategy.config.window == 5
        assert strategy.config.epsilon == 10.0
        assert strategy.config.rebalance_freq == 'weekly'
    
    def test_factory_weekly(self):
        """Factory should create weekly strategy."""
        from strategy.quant1.olmar.olmar_strategy import create_olmar_weekly
        
        strategy = create_olmar_weekly()
        
        assert strategy.config.rebalance_freq == 'weekly'
    
    def test_factory_monthly(self):
        """Factory should create monthly strategy."""
        from strategy.quant1.olmar.olmar_strategy import create_olmar_monthly
        
        strategy = create_olmar_monthly()
        
        assert strategy.config.rebalance_freq == 'monthly'
    
    def test_generate_weights_shape(self, sample_prices):
        """Generated weights should match price shape."""
        from strategy.quant1.olmar.olmar_strategy import OLMARStrategy
        
        strategy = OLMARStrategy()
        result = strategy.generate_weights(sample_prices)
        
        assert result.weights.shape == sample_prices.shape
    
    def test_generate_weights_simplex(self, sample_prices):
        """Generated weights should be on simplex."""
        from strategy.quant1.olmar.olmar_strategy import OLMARStrategy
        
        strategy = OLMARStrategy()
        result = strategy.generate_weights(sample_prices)
        
        # Check all rows sum to 1
        row_sums = result.weights.sum(axis=1)
        for s in row_sums:
            assert abs(s - 1.0) < 1e-6
        
        # Check all values non-negative
        assert (result.weights.values >= -1e-10).all()
    
    def test_turnover_stats_present(self, sample_prices):
        """Result should include turnover statistics."""
        from strategy.quant1.olmar.olmar_strategy import OLMARStrategy
        
        strategy = OLMARStrategy()
        result = strategy.generate_weights(sample_prices)
        
        assert 'mean_daily_turnover' in result.turnover_stats
        assert 'annualized_turnover' in result.turnover_stats
    
    def test_config_validation(self):
        """Invalid config should raise error."""
        from strategy.quant1.olmar.olmar_strategy import OLMARConfig
        
        with pytest.raises(ValueError):
            OLMARConfig(window=-1)
        
        with pytest.raises(ValueError):
            OLMARConfig(epsilon=0)
        
        with pytest.raises(ValueError):
            OLMARConfig(max_turnover=2.0)
        
        with pytest.raises(ValueError):
            OLMARConfig(rebalance_freq='invalid')
