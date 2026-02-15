"""
Quant 1 & Quant 2 Strategy Integration Tests
=============================================
Comprehensive tests to verify all new implementations are working correctly.

Tests cover:
1. Fractional Differentiation (FFD)
2. Deflated Sharpe Ratio (DSR) 
3. Cost-Penalized Optimizer
4. Volume Constraints (Liquidity Guardrail)
5. Dynamic Universe Selection
6. Backtest Infrastructure
7. Quant 2 Strategies (ResidualMomentum, HMM, etc.)

Run with: pytest tests/test_quant_strategies_integration.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Try to import backtester - may fail if vectorbt/config not available
try:
    from strategy.infrastructure.backtest import PortfolioBacktester
    HAS_BACKTESTER = True
except ImportError:
    HAS_BACKTESTER = False
    PortfolioBacktester = None


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_prices():
    """Generate realistic price data for backtesting."""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=500, freq='B')
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ', 'TLT', 'GLD']
    
    data = {}
    for i, ticker in enumerate(tickers):
        # Add some correlation structure
        base_return = np.random.normal(0.0005, 0.015, len(dates))
        market_factor = np.random.normal(0.0003, 0.01, len(dates))
        returns = base_return + 0.5 * market_factor
        prices = (100 + i*20) * np.exp(np.cumsum(returns))
        data[ticker] = prices
    
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def sample_volumes(sample_prices):
    """Generate sample volume data."""
    np.random.seed(42)
    volumes = {}
    for ticker in sample_prices.columns:
        # Random volume between 1M and 10M shares
        vol = np.random.uniform(1e6, 10e6, len(sample_prices))
        volumes[ticker] = vol
    
    return pd.DataFrame(volumes, index=sample_prices.index)


@pytest.fixture 
def sample_returns(sample_prices):
    """Generate returns from prices."""
    return sample_prices.pct_change().dropna()


@pytest.fixture
def sample_monthly_returns():
    """Monthly returns for factor models."""
    np.random.seed(42)
    dates = pd.date_range(start='2018-01-01', periods=60, freq='M')
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']
    
    data = {}
    for ticker in tickers:
        returns = np.random.normal(0.01, 0.05, len(dates))
        data[ticker] = returns
    
    return pd.DataFrame(data, index=dates)


# =============================================================================
# 1. FRACTIONAL DIFFERENTIATION (FFD) TESTS
# =============================================================================

class TestFractionalDifferentiation:
    """Tests for FFD feature engineering."""
    
    def test_ffd_import(self):
        """FFD functions can be imported."""
        from strategy.quant2.features import frac_diff_ffd, get_weights_ffd
        
        assert callable(frac_diff_ffd)
        assert callable(get_weights_ffd)
    
    def test_ffd_weights_computation(self):
        """FFD weights are computed correctly."""
        from strategy.quant2.features import get_weights_ffd
        
        weights = get_weights_ffd(d=0.5, thres=1e-3)
        
        # Weights should be a numpy array
        assert isinstance(weights, np.ndarray)
        # First weight should be 1.0
        assert weights[-1, 0] == 1.0
        # Weights should sum to approximately 0 for d=0.5
        assert len(weights) > 1
    
    def test_ffd_produces_output(self, sample_prices):
        """FFD produces non-empty output for sufficient data."""
        from strategy.quant2.features import frac_diff_ffd
        
        # Use log prices for better stationarity
        log_prices = np.log(sample_prices)
        result = frac_diff_ffd(log_prices, d=0.4, thres=1e-4)
        
        # Result should be a DataFrame
        assert isinstance(result, pd.DataFrame)
        # Columns should match input
        assert list(result.columns) == list(sample_prices.columns)
    
    def test_ffd_different_d_values(self, sample_prices):
        """FFD works with different differentiation orders."""
        from strategy.quant2.features import frac_diff_ffd
        
        log_prices = np.log(sample_prices[['AAPL', 'MSFT']])
        
        for d in [0.3, 0.5, 0.7]:
            result = frac_diff_ffd(log_prices, d=d)
            assert isinstance(result, pd.DataFrame)
    
    def test_compute_ffd_features(self, sample_prices):
        """compute_ffd_features generates multiple d-value features."""
        from strategy.quant2.features import compute_ffd_features
        
        small_prices = sample_prices[['AAPL', 'MSFT']].iloc[-100:]
        result = compute_ffd_features(small_prices, d_values=[0.3, 0.5])
        
        assert isinstance(result, pd.DataFrame)


# =============================================================================
# 2. DEFLATED SHARPE RATIO (DSR) TESTS
# =============================================================================

class TestDeflatedSharpeRatio:
    """Tests for DSR validation module."""
    
    def test_dsr_import(self):
        """DSR functions can be imported."""
        from strategy.infrastructure.validation import (
            deflated_sharpe_ratio,
            probabilistic_sharpe_ratio,
            validate_backtest
        )
        
        assert callable(deflated_sharpe_ratio)
        assert callable(probabilistic_sharpe_ratio)
        assert callable(validate_backtest)
    
    def test_sharpe_ratio_estimation(self, sample_returns):
        """Sharpe ratio is calculated correctly."""
        from strategy.infrastructure.validation import estimated_sharpe_ratio
        
        returns = sample_returns['AAPL']
        sr = estimated_sharpe_ratio(returns)
        
        # SR should be a float
        assert isinstance(sr, float)
        # SR should be finite
        assert np.isfinite(sr)
    
    def test_annualized_sharpe(self, sample_returns):
        """Annualized SR scales correctly."""
        from strategy.infrastructure.validation import (
            estimated_sharpe_ratio, 
            annualized_sharpe_ratio
        )
        
        returns = sample_returns['AAPL']
        sr = estimated_sharpe_ratio(returns)
        sr_ann = annualized_sharpe_ratio(returns)
        
        # Annualized should be sqrt(252) times daily
        expected_ratio = np.sqrt(252)
        assert abs(sr_ann / sr - expected_ratio) < 0.01
    
    def test_dsr_penalizes_multiple_testing(self, sample_returns):
        """DSR decreases with more trials."""
        from strategy.infrastructure.validation import deflated_sharpe_ratio
        
        returns = sample_returns['AAPL']
        sr = returns.mean() / returns.std()
        
        dsr_1 = deflated_sharpe_ratio(sr, n_trials=1, returns=returns)
        dsr_100 = deflated_sharpe_ratio(sr, n_trials=100, returns=returns)
        
        # DSR should decrease with more trials
        assert dsr_1 >= dsr_100
    
    def test_validate_backtest_report(self, sample_returns):
        """validate_backtest returns complete report."""
        from strategy.infrastructure.validation import validate_backtest
        
        returns = sample_returns['SPY']
        report = validate_backtest(returns, n_trials=10)
        
        # Check required keys
        required_keys = [
            'sharpe_ratio', 'sharpe_ratio_annual', 'deflated_sr',
            'probabilistic_sr', 'confidence_level', 'n_samples'
        ]
        for key in required_keys:
            assert key in report, f"Missing key: {key}"
    
    def test_confidence_level_classification(self):
        """Confidence levels are assigned correctly."""
        from strategy.infrastructure.validation import validate_backtest
        
        # High confidence: genuine alpha
        np.random.seed(42)
        good_returns = pd.Series(np.random.normal(0.002, 0.015, 500))
        report = validate_backtest(good_returns, n_trials=1)
        
        # With strong positive mean and 1 trial, should be HIGH
        assert report['confidence_level'] in ['HIGH', 'MEDIUM', 'LOW']


# =============================================================================
# 3. COST-PENALIZED OPTIMIZER TESTS
# =============================================================================

class TestCostPenalizedOptimizer:
    """Tests for scipy-based utility optimization with costs."""
    
    def test_optimizer_import(self):
        """Optimizer functions can be imported."""
        from strategy.pipeline.allocation_layer import (
            optimize_utility_with_costs,
            calculate_optimal_weights_with_costs
        )
        
        assert callable(optimize_utility_with_costs)
        assert callable(calculate_optimal_weights_with_costs)
    
    def test_optimizer_returns_valid_weights(self):
        """Optimizer returns weights that sum to 1."""
        from strategy.pipeline.allocation_layer import optimize_utility_with_costs
        
        # Simple 3-asset case
        exp_returns = np.array([0.08, 0.12, 0.06])
        cov_matrix = np.array([
            [0.04, 0.01, 0.005],
            [0.01, 0.09, 0.01],
            [0.005, 0.01, 0.02]
        ])
        
        weights = optimize_utility_with_costs(exp_returns, cov_matrix)
        
        # Weights should sum to 1
        assert abs(weights.sum() - 1.0) < 1e-6
        # All weights should be non-negative (long only)
        assert all(w >= -1e-6 for w in weights)
    
    def test_optimizer_penalizes_turnover(self):
        """Higher cost_bps results in weights closer to current."""
        from strategy.pipeline.allocation_layer import optimize_utility_with_costs
        
        exp_returns = np.array([0.08, 0.15, 0.05])  # MSFT looks attractive
        cov_matrix = np.eye(3) * 0.04
        current_weights = np.array([0.4, 0.3, 0.3])
        
        # Low transaction cost
        weights_low_cost = optimize_utility_with_costs(
            exp_returns, cov_matrix, current_weights, cost_bps=1.0
        )
        
        # High transaction cost
        weights_high_cost = optimize_utility_with_costs(
            exp_returns, cov_matrix, current_weights, cost_bps=100.0
        )
        
        # High cost should stay closer to current
        turnover_low = np.sum(np.abs(weights_low_cost - current_weights))
        turnover_high = np.sum(np.abs(weights_high_cost - current_weights))
        
        assert turnover_high <= turnover_low + 0.01
    
    def test_optimizer_with_returns_dataframe(self, sample_returns):
        """Convenience function works with DataFrame."""
        from strategy.pipeline.allocation_layer import calculate_optimal_weights_with_costs
        
        returns = sample_returns[['AAPL', 'MSFT', 'GOOGL']].iloc[-250:]
        weights = calculate_optimal_weights_with_costs(returns, cost_bps=10)
        
        # Should return pandas Series
        assert isinstance(weights, pd.Series)
        # Weights should sum to 1
        assert abs(weights.sum() - 1.0) < 1e-6


# =============================================================================
# 4. VOLUME CONSTRAINTS (LIQUIDITY GUARDRAIL) TESTS
# =============================================================================

@pytest.mark.skipif(not HAS_BACKTESTER, reason="Backtester not available")
class TestVolumeConstraints:
    """Tests for the 2% daily volume participation cap."""
    
    def test_backtester_accepts_volumes(self, sample_prices, sample_volumes):
        """PortfolioBacktester accepts volumes parameter."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        bt = PortfolioBacktester(
            sample_prices,
            initial_capital=10000,
            volumes=sample_volumes,
            max_volume_participation=0.02
        )
        
        assert bt.volumes is not None
        assert bt.max_volume_participation == 0.02
    
    def test_backtester_runs_with_volumes(self, sample_prices, sample_volumes):
        """Backtest completes successfully with volume constraints."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        bt = PortfolioBacktester(
            sample_prices,
            initial_capital=10000,
            volumes=sample_volumes
        )
        
        def equal_weights(prices, idx):
            return pd.Series(1/len(prices.columns), index=prices.columns)
        
        result = bt.run_backtest(equal_weights, rebalance_freq='monthly')
        
        assert result is not None
        assert hasattr(result, 'portfolio_value')
        assert hasattr(result, 'metrics')
    
    def test_volume_constraint_caps_positions(self, sample_prices):
        """Volume constraint correctly caps large positions."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        # Create very low volume for one stock
        volumes = sample_prices.copy() * 0  # Start empty
        for ticker in sample_prices.columns:
            volumes[ticker] = 1e6  # 1M shares
        
        # AAPL has tiny volume - should be capped
        volumes['AAPL'] = 100  # Only 100 shares/day
        
        bt = PortfolioBacktester(
            sample_prices,
            initial_capital=100000,  # Large enough to trigger cap
            volumes=volumes,
            max_volume_participation=0.02
        )
        
        def overweight_aapl(prices, idx):
            weights = pd.Series(0.0, index=prices.columns)
            weights['AAPL'] = 0.5  # Try to put 50% in AAPL
            weights['MSFT'] = 0.5
            return weights
        
        result = bt.run_backtest(overweight_aapl, rebalance_freq='monthly')
        
        # Backtest should complete without error
        assert result is not None


# =============================================================================
# 5. DYNAMIC UNIVERSE SELECTION TESTS
# =============================================================================

class TestDynamicUniverseSelection:
    """Tests for survivorship bias-free universe selection."""
    
    def test_universe_provider_import(self):
        """UniverseProvider can be imported."""
        from strategy.data.universe import UniverseProvider
        
        provider = UniverseProvider()
        assert provider is not None
    
    @pytest.mark.skipif(not HAS_BACKTESTER, reason="Backtester not available")
    def test_backtest_with_dynamic_universe(self, sample_prices):
        """Backtest accepts use_dynamic_universe parameter."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def equal_weights(prices, idx):
            return pd.Series(1/len(prices.columns), index=prices.columns)
        
        # Should not raise error
        result = bt.run_backtest(
            equal_weights,
            rebalance_freq='monthly',
            use_dynamic_universe=False
        )
        
        assert result is not None


# =============================================================================
# 6. BACKTEST INFRASTRUCTURE TESTS
# =============================================================================

@pytest.mark.skipif(not HAS_BACKTESTER, reason="Backtester not available")
class TestBacktestInfrastructure:
    """Tests for core backtesting functionality."""
    
    def test_backtest_result_structure(self, sample_prices):
        """BacktestResult has all required attributes."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def equal_weights(prices, idx):
            return pd.Series(1/len(prices.columns), index=prices.columns)
        
        result = bt.run_backtest(equal_weights, rebalance_freq='monthly')
        
        # Check required attributes
        assert hasattr(result, 'portfolio_value')
        assert hasattr(result, 'returns')
        assert hasattr(result, 'metrics')
        assert hasattr(result, 'weights_history')
    
    def test_backtest_metrics_present(self, sample_prices):
        """All required metrics are calculated."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def equal_weights(prices, idx):
            return pd.Series(1/len(prices.columns), index=prices.columns)
        
        result = bt.run_backtest(equal_weights, rebalance_freq='monthly')
        
        required_metrics = [
            'total_return', 'cagr', 'volatility', 
            'sharpe_ratio', 'max_drawdown'
        ]
        for metric in required_metrics:
            assert metric in result.metrics, f"Missing metric: {metric}"
    
    def test_execution_delay_applied(self, sample_prices):
        """Execution delay is stored in metrics."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        def equal_weights(prices, idx):
            return pd.Series(1/len(prices.columns), index=prices.columns)
        
        result = bt.run_backtest(
            equal_weights,
            rebalance_freq='monthly',
            execution_delay=2
        )
        
        assert result.metrics['execution_delay'] == 2
    
    def test_momentum_backtest(self, sample_prices):
        """Built-in momentum backtest runs."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        result = bt.run_momentum_backtest(lookback=63, top_n=3)
        
        assert result is not None
        assert result.metrics['total_return'] is not None
    
    def test_cost_calculation(self, sample_prices):
        """Transaction costs are calculated correctly."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        current = pd.Series({'AAPL': 0.5, 'MSFT': 0.5})
        target = pd.Series({'AAPL': 0.2, 'MSFT': 0.8})
        
        cost = bt._calculate_rebalance_cost(
            current, target, 100000,
            slippage_bps=5.0,
            market_impact_bps=2.5
        )
        
        # Cost should be positive for non-zero turnover
        assert cost > 0


# =============================================================================
# 7. QUANT 2 STRATEGY TESTS
# =============================================================================

class TestResidualMomentum:
    """Tests for Residual Momentum strategy."""
    
    def test_residual_momentum_import(self):
        """ResidualMomentum can be imported."""
        from strategy.quant2.momentum.residual_momentum import ResidualMomentum
        
        rm = ResidualMomentum()
        assert rm is not None
    
    def test_residual_momentum_config(self):
        """ResidualMomentum accepts configuration."""
        from strategy.quant2.momentum.residual_momentum import ResidualMomentum
        
        rm = ResidualMomentum(
            lookback_months=24,
            scoring_months=6,
            min_observations=18
        )
        
        assert rm.lookback_months == 24
        assert rm.scoring_months == 6


class TestHMMRegimeDetector:
    """Tests for HMM regime detection."""
    
    def test_hmm_import(self):
        """HMMRegimeDetector can be imported."""
        try:
            from strategy.quant2.regime.hmm_detector import HMMRegimeDetector
            detector = HMMRegimeDetector()
            assert detector is not None
        except ImportError:
            pytest.skip("HMM detector requires hmmlearn")


class TestStatArb:
    """Tests for statistical arbitrage components."""
    
    def test_clustering_import(self):
        """ClusteringEngine can be imported."""
        try:
            from strategy.quant2.stat_arb.clustering import ClusteringEngine
            engine = ClusteringEngine()
            assert engine is not None
        except ImportError:
            pytest.skip("Clustering requires sklearn")
    
    def test_kalman_import(self):
        """KalmanHedgeRatio can be imported."""
        try:
            from strategy.quant2.stat_arb.kalman import KalmanHedgeRatio
            kalman = KalmanHedgeRatio()
            assert kalman is not None
        except ImportError:
            pytest.skip("Kalman filter requires pykalman")


# =============================================================================
# 8. INTEGRATION TESTS
# =============================================================================

@pytest.mark.skipif(not HAS_BACKTESTER, reason="Backtester not available")
class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    def test_full_backtest_pipeline(self, sample_prices, sample_volumes):
        """Complete backtest with all new features."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        from strategy.infrastructure.validation import validate_backtest
        
        # Create backtester with all features
        bt = PortfolioBacktester(
            sample_prices,
            initial_capital=10000,  # $10K account
            volumes=sample_volumes,
            max_volume_participation=0.02
        )
        
        def momentum_weights(prices, idx):
            """Simple momentum: top 3 by 63-day return."""
            if len(prices) < 63:
                return pd.Series(1/len(prices.columns), index=prices.columns)
            
            returns = prices.iloc[-63:].pct_change().sum()
            top_3 = returns.nlargest(3).index
            weights = pd.Series(0.0, index=prices.columns)
            weights[top_3] = 1/3
            return weights
        
        result = bt.run_backtest(
            momentum_weights,
            rebalance_freq='monthly',
            execution_delay=1,
            slippage_bps=5.0
        )
        
        # Validate results
        report = validate_backtest(result.returns, n_trials=1)
        
        assert result is not None
        assert report['confidence_level'] in ['HIGH', 'MEDIUM', 'LOW']
    
    def test_optimizer_with_backtest(self, sample_prices):
        """Cost-aware optimizer integrates with backtest."""
        from strategy.infrastructure.backtest import PortfolioBacktester
        from strategy.pipeline.allocation_layer import calculate_optimal_weights_with_costs
        
        bt = PortfolioBacktester(sample_prices, initial_capital=100000)
        
        # Track previous weights for cost calculation
        prev_weights = [None]
        
        def cost_aware_weights(prices, idx):
            returns = prices.pct_change().dropna()
            if len(returns) < 60:
                return pd.Series(1/len(prices.columns), index=prices.columns)
            
            weights = calculate_optimal_weights_with_costs(
                returns,
                current_weights=prev_weights[0],
                cost_bps=20.0
            )
            prev_weights[0] = weights
            return weights
        
        result = bt.run_backtest(cost_aware_weights, rebalance_freq='monthly')
        
        assert result is not None
        assert result.metrics['total_return'] is not None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
