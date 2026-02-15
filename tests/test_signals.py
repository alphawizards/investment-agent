"""
Signal Generation Tests
=======================
Tests for signal layer and VectorBT utilities.
"""

import pytest
import pandas as pd
import numpy as np


class TestMomentumSignals:
    """Tests for momentum signal generation."""
    
    def test_signals_correct_shape(self, sample_prices):
        """Signals should match price data shape."""
        from strategy.pipeline.vectorbt_utils import generate_momentum_signals
        
        signals, strength = generate_momentum_signals(
            sample_prices, lookback=21, threshold=0.8
        )
        
        assert signals.shape == sample_prices.shape
        assert strength.shape == sample_prices.shape
    
    def test_signals_binary(self, sample_prices):
        """Signals should be 0 or 1."""
        from strategy.pipeline.vectorbt_utils import generate_momentum_signals
        
        signals, _ = generate_momentum_signals(
            sample_prices, lookback=21, threshold=0.8
        )
        
        unique_values = signals.values.flatten()
        unique_values = unique_values[~np.isnan(unique_values)]
        assert set(unique_values).issubset({0, 1})
    
    def test_strength_range(self, sample_prices):
        """Strength should be between 0 and 1."""
        from strategy.pipeline.vectorbt_utils import generate_momentum_signals
        
        _, strength = generate_momentum_signals(
            sample_prices, lookback=21, threshold=0.8
        )
        
        non_nan = strength.values[~np.isnan(strength.values)]
        assert non_nan.min() >= 0
        assert non_nan.max() <= 1
    
    def test_threshold_affects_signals(self, sample_prices):
        """Higher threshold should produce fewer signals."""
        from strategy.pipeline.vectorbt_utils import generate_momentum_signals
        
        signals_low, _ = generate_momentum_signals(
            sample_prices, lookback=21, threshold=0.5
        )
        signals_high, _ = generate_momentum_signals(
            sample_prices, lookback=21, threshold=0.9
        )
        
        # Higher threshold = fewer buy signals
        assert signals_high.sum().sum() <= signals_low.sum().sum()


class TestDualMomentumSignals:
    """Tests for dual momentum signal generation."""
    
    def test_dual_momentum_basic(self, sample_prices):
        """Dual momentum should produce valid signals."""
        from strategy.pipeline.vectorbt_utils import generate_dual_momentum_signals
        
        signals, strength = generate_dual_momentum_signals(
            sample_prices, 
            lookback=126,
            defensive_assets=['TLT']
        )
        
        assert signals.shape == sample_prices.shape
        assert not signals.isnull().all().all()


class TestMovingAverages:
    """Tests for moving average calculations."""
    
    def test_ma_windows(self, sample_prices):
        """Should calculate MAs for all specified windows."""
        from strategy.pipeline.vectorbt_utils import calculate_moving_averages
        
        windows = [10, 20, 50]
        result = calculate_moving_averages(sample_prices, windows=windows)
        
        assert len(result) == len(windows)
        for window in windows:
            assert window in result
            assert result[window].shape == sample_prices.shape
    
    def test_ema_differs_from_sma(self, sample_prices):
        """EMA should produce different results than SMA."""
        from strategy.pipeline.vectorbt_utils import calculate_moving_averages
        
        sma = calculate_moving_averages(sample_prices, windows=[20], use_ema=False)
        ema = calculate_moving_averages(sample_prices, windows=[20], use_ema=True)
        
        # They should not be exactly equal
        assert not np.allclose(sma[20].values, ema[20].values, equal_nan=True)
