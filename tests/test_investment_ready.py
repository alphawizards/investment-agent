"""
Tests for Investment-Ready Data Validation and Audit Logging Modules.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from strategy.data_validation import DataValidator, ParquetIntegrity, DataReconciliation
from strategy.audit_logging import AuditLogger, AuditEventType, get_audit_logger


class TestDataValidator:
    """Tests for OHLCV data validation."""
    
    @pytest.fixture
    def validator(self):
        return DataValidator(strict_mode=False)
    
    @pytest.fixture
    def valid_ohlcv(self):
        """Create valid OHLCV data."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        return pd.DataFrame({
            "Open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            "High": [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            "Low": [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
            "Close": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            "Volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
        }, index=dates)
    
    def test_valid_data_passes(self, validator, valid_ohlcv):
        """Valid OHLCV data should pass validation."""
        report = validator.validate_ohlcv(valid_ohlcv, "TEST")
        assert report["valid"] is True
        assert len(report["errors"]) == 0
    
    def test_empty_dataframe(self, validator):
        """Empty DataFrame should fail."""
        report = validator.validate_ohlcv(pd.DataFrame(), "EMPTY")
        assert report["valid"] is False
        assert "Empty DataFrame" in report["errors"]
    
    def test_missing_columns(self, validator):
        """Missing required columns should fail."""
        df = pd.DataFrame({"Open": [100], "Close": [102]})
        report = validator.validate_ohlcv(df, "PARTIAL")
        assert report["valid"] is False
        assert any("Missing columns" in e for e in report["errors"])
    
    def test_high_less_than_low(self, validator, valid_ohlcv):
        """High < Low should be an error."""
        invalid = valid_ohlcv.copy()
        invalid.loc[invalid.index[0], "High"] = 90  # Less than Low of 95
        report = validator.validate_ohlcv(invalid, "BAD_OHLC")
        assert report["valid"] is False
        assert any("High < Low" in e for e in report["errors"])
    
    def test_negative_volume(self, validator, valid_ohlcv):
        """Negative volume should be an error."""
        invalid = valid_ohlcv.copy()
        invalid.loc[invalid.index[0], "Volume"] = -100
        report = validator.validate_ohlcv(invalid, "NEG_VOL")
        assert report["valid"] is False
        assert any("Negative volume" in e for e in report["errors"])
    
    def test_extreme_returns_warning(self, validator, valid_ohlcv):
        """Extreme daily returns should trigger a warning."""
        extreme = valid_ohlcv.copy()
        extreme.loc[extreme.index[1], "Close"] = 200  # 100% return
        report = validator.validate_ohlcv(extreme, "EXTREME")
        assert report["valid"] is True  # Still valid, just a warning
        assert any("Extreme daily returns" in w for w in report["warnings"])


class TestParquetIntegrity:
    """Tests for Parquet checksum verification."""
    
    @pytest.fixture
    def temp_cache(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def sample_parquet(self, temp_cache):
        """Create a sample Parquet file."""
        df = pd.DataFrame({
            "A": [1, 2, 3],
            "B": ["x", "y", "z"]
        })
        path = Path(temp_cache) / "test_data.parquet"
        df.to_parquet(path)
        return path
    
    def test_register_and_verify(self, temp_cache, sample_parquet):
        """Register a file and verify it."""
        integrity = ParquetIntegrity(cache_dir=temp_cache)
        checksum = integrity.register_file(sample_parquet)
        
        assert len(checksum) == 64  # SHA-256 is 64 hex chars
        
        result = integrity.verify_file(sample_parquet)
        assert result["status"] == "valid"
    
    def test_detect_corruption(self, temp_cache, sample_parquet):
        """Detect a corrupted file."""
        integrity = ParquetIntegrity(cache_dir=temp_cache)
        integrity.register_file(sample_parquet)
        
        # Corrupt the file
        with open(sample_parquet, "ab") as f:
            f.write(b"corrupted data")
        
        result = integrity.verify_file(sample_parquet)
        assert result["status"] == "corrupted"
    
    def test_missing_file(self, temp_cache):
        """Handle missing file gracefully."""
        integrity = ParquetIntegrity(cache_dir=temp_cache)
        result = integrity.verify_file("nonexistent.parquet")
        assert result["status"] == "missing"


class TestDataReconciliation:
    """Tests for data source reconciliation."""
    
    @pytest.fixture
    def source1(self):
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        return pd.DataFrame({
            "Open": [100, 101, 102, 103, 104],
            "High": [105, 106, 107, 108, 109],
            "Low": [95, 96, 97, 98, 99],
            "Close": [102, 103, 104, 105, 106],
        }, index=dates)
    
    @pytest.fixture
    def source2_matching(self, source1):
        """Source that matches source1."""
        return source1.copy()
    
    @pytest.fixture
    def source2_different(self, source1):
        """Source with discrepancies."""
        df = source1.copy()
        df.loc[df.index[0], "Close"] = 200  # Big difference
        return df
    
    def test_matching_sources(self, source1, source2_matching):
        """Matching sources should pass."""
        recon = DataReconciliation()
        report = recon.compare_sources(source1, source2_matching, "yfinance", "tiingo")
        assert report["status"] == "pass"
        assert report["summary"]["total_discrepancies"] == 0
    
    def test_discrepancy_detection(self, source1, source2_different):
        """Detect discrepancies between sources."""
        recon = DataReconciliation()
        report = recon.compare_sources(source1, source2_different, "yfinance", "tiingo")
        assert report["status"] == "discrepancies_found"
        assert report["summary"]["total_discrepancies"] > 0


class TestAuditLogger:
    """Tests for audit logging."""
    
    @pytest.fixture
    def temp_audit_dir(self):
        """Create temporary audit log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def logger(self, temp_audit_dir):
        return AuditLogger(log_dir=temp_audit_dir, enable_console=False)
    
    def test_log_creates_event_id(self, logger):
        """Logging should return a unique event ID."""
        event_id = logger.log(
            AuditEventType.SYSTEM_EVENT,
            {"test": "data"},
        )
        assert event_id is not None
        assert len(event_id) == 36  # UUID format
    
    def test_log_trade_execution(self, logger):
        """Log a trade execution."""
        event_id = logger.log_trade_execution(
            ticker="AAPL",
            action="BUY",
            quantity=100,
            price=150.50,
            total_value=15050.00,
            commission=5.00,
        )
        assert event_id is not None
    
    def test_log_backtest(self, logger):
        """Log a backtest completion."""
        event_id = logger.log_backtest(
            strategy="DualMomentum",
            start_date="2020-01-01",
            end_date="2023-12-31",
            initial_capital=100000,
            final_value=150000,
            total_return_pct=50.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=15.0,
            num_trades=120,
        )
        assert event_id is not None
    
    def test_query_logs(self, logger):
        """Query logged events."""
        # Log some events
        logger.log_trade_execution("AAPL", "BUY", 100, 150, 15000)
        logger.log_trade_execution("GOOGL", "SELL", 50, 2500, 125000)
        
        # Query them back
        events = logger.query_logs(event_type=AuditEventType.TRADE_EXECUTED)
        assert len(events) == 2
    
    def test_compliance_report(self, logger):
        """Generate compliance report."""
        logger.log_trade_execution("AAPL", "BUY", 100, 150, 15000)
        logger.log_error("TestError", "Test error message")
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        report = logger.generate_compliance_report(today, today)
        
        assert report["total_events"] == 2
        assert len(report["trades"]) == 1
        assert len(report["errors"]) == 1
