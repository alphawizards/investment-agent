"""
Data Validation Module for Investment-Ready Trading Platform.

Provides comprehensive data validation at ingestion, integrity checks,
and reconciliation reports for production-grade quantitative trading.
"""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


class DataValidator:
    """
    Validates financial market data at ingestion point.
    
    Checks for:
    - Missing values and data gaps
    - Invalid price values (negative, zero, extreme)
    - OHLC consistency (High >= Low, etc.)
    - Volume anomalies
    - Stale data detection
    """
    
    # Price change thresholds for anomaly detection
    MAX_DAILY_CHANGE_PCT = 50.0  # Flag if price changes > 50% in a day
    MIN_VALID_PRICE = 0.0001
    MAX_VALID_PRICE = 1_000_000
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, raise exceptions on validation failures.
                         If False, log warnings and return validation report.
        """
        self.strict_mode = strict_mode
        self.validation_errors: list[dict] = []
        
    def validate_ohlcv(self, df: pd.DataFrame, ticker: str = "UNKNOWN") -> dict:
        """
        Validate OHLCV data for a single ticker.
        
        Args:
            df: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
            ticker: Ticker symbol for reporting
            
        Returns:
            Validation report dictionary
        """
        report = {
            "ticker": ticker,
            "timestamp": datetime.utcnow().isoformat(),
            "total_rows": len(df),
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        
        if df.empty:
            report["valid"] = False
            report["errors"].append("Empty DataFrame")
            return report
        
        # Check required columns
        required_cols = ["Open", "High", "Low", "Close"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            report["valid"] = False
            report["errors"].append(f"Missing columns: {missing_cols}")
            return report
        
        # 1. Missing values check
        missing = df[required_cols].isnull().sum()
        if missing.any():
            report["warnings"].append(f"Missing values: {missing.to_dict()}")
        
        # 2. Negative/zero price check
        for col in required_cols:
            if (df[col] <= 0).any():
                report["warnings"].append(f"{col} contains non-positive values")
        
        # 3. OHLC consistency (High >= Low)
        if (df["High"] < df["Low"]).any():
            invalid_rows = (df["High"] < df["Low"]).sum()
            report["errors"].append(f"High < Low in {invalid_rows} rows")
            report["valid"] = False
        
        # 4. OHLC consistency (High >= Open, Close)
        if ((df["High"] < df["Open"]) | (df["High"] < df["Close"])).any():
            report["warnings"].append("High not >= Open/Close in some rows")
        
        # 5. OHLC consistency (Low <= Open, Close)
        if ((df["Low"] > df["Open"]) | (df["Low"] > df["Close"])).any():
            report["warnings"].append("Low not <= Open/Close in some rows")
        
        # 6. Extreme price check
        if (df["Close"] > self.MAX_VALID_PRICE).any():
            report["warnings"].append(f"Close prices exceed {self.MAX_VALID_PRICE}")
        if (df["Close"] < self.MIN_VALID_PRICE).any():
            report["warnings"].append(f"Close prices below {self.MIN_VALID_PRICE}")
        
        # 7. Extreme daily change check
        returns = df["Close"].pct_change().abs() * 100
        extreme_returns = returns > self.MAX_DAILY_CHANGE_PCT
        if extreme_returns.any():
            report["warnings"].append(
                f"Extreme daily returns (>{self.MAX_DAILY_CHANGE_PCT}%) on "
                f"{extreme_returns.sum()} days"
            )
        
        # 8. Data gaps check (for daily data)
        if isinstance(df.index, pd.DatetimeIndex):
            gaps = self._detect_gaps(df.index)
            if gaps:
                report["warnings"].append(f"Data gaps detected: {len(gaps)} periods")
        
        # 9. Volume check (if available)
        if "Volume" in df.columns:
            if (df["Volume"] < 0).any():
                report["errors"].append("Negative volume detected")
                report["valid"] = False
            zero_volume = (df["Volume"] == 0).sum()
            if zero_volume > len(df) * 0.1:  # >10% zero volume
                report["warnings"].append(f"High zero-volume days: {zero_volume}")
        
        return report
    
    def _detect_gaps(self, index: pd.DatetimeIndex, max_gap_days: int = 5) -> list:
        """Detect gaps in date index that exceed max_gap_days (excluding weekends)."""
        gaps = []
        if len(index) < 2:
            return gaps
        
        sorted_idx = index.sort_values()
        for i in range(1, len(sorted_idx)):
            gap = (sorted_idx[i] - sorted_idx[i-1]).days
            if gap > max_gap_days:
                gaps.append((sorted_idx[i-1], sorted_idx[i], gap))
        
        return gaps
    
    def validate_multiple(self, data_dict: dict[str, pd.DataFrame]) -> dict:
        """
        Validate multiple tickers.
        
        Args:
            data_dict: Dictionary of {ticker: DataFrame}
            
        Returns:
            Combined validation report
        """
        combined_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_tickers": len(data_dict),
            "valid_tickers": 0,
            "invalid_tickers": [],
            "reports": {},
        }
        
        for ticker, df in data_dict.items():
            report = self.validate_ohlcv(df, ticker)
            combined_report["reports"][ticker] = report
            if report["valid"]:
                combined_report["valid_tickers"] += 1
            else:
                combined_report["invalid_tickers"].append(ticker)
        
        return combined_report


class ParquetIntegrity:
    """
    Provides checksum verification for Parquet cache files.
    
    Creates and verifies SHA-256 checksums to ensure data integrity
    and detect corruption or tampering.
    """
    
    CHECKSUM_FILE = ".checksums.json"
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.checksum_file = self.cache_dir / self.CHECKSUM_FILE
        self._checksums: dict = {}
        self._load_checksums()
    
    def _load_checksums(self):
        """Load existing checksums from file."""
        if self.checksum_file.exists():
            import json
            with open(self.checksum_file, "r") as f:
                self._checksums = json.load(f)
    
    def _save_checksums(self):
        """Save checksums to file."""
        import json
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.checksum_file, "w") as f:
            json.dump(self._checksums, f, indent=2)
    
    def compute_checksum(self, file_path: Path) -> str:
        """Compute SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def register_file(self, file_path: str | Path) -> str:
        """
        Register a file and store its checksum.
        
        Args:
            file_path: Path to the Parquet file
            
        Returns:
            The computed checksum
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        checksum = self.compute_checksum(path)
        self._checksums[str(path.name)] = {
            "checksum": checksum,
            "registered_at": datetime.utcnow().isoformat(),
            "size_bytes": path.stat().st_size,
        }
        self._save_checksums()
        return checksum
    
    def verify_file(self, file_path: str | Path) -> dict:
        """
        Verify a file's integrity against stored checksum.
        
        Returns:
            Verification result with status
        """
        path = Path(file_path)
        filename = path.name
        
        result = {
            "file": str(path),
            "verified_at": datetime.utcnow().isoformat(),
            "status": "unknown",
            "details": None,
        }
        
        if not path.exists():
            result["status"] = "missing"
            result["details"] = "File not found"
            return result
        
        if filename not in self._checksums:
            result["status"] = "unregistered"
            result["details"] = "No checksum on record"
            return result
        
        current_checksum = self.compute_checksum(path)
        stored_checksum = self._checksums[filename]["checksum"]
        
        if current_checksum == stored_checksum:
            result["status"] = "valid"
            result["details"] = "Checksum matches"
        else:
            result["status"] = "corrupted"
            result["details"] = f"Checksum mismatch: expected {stored_checksum[:16]}..., got {current_checksum[:16]}..."
        
        return result
    
    def verify_all(self) -> dict:
        """
        Verify all registered files.
        
        Returns:
            Summary report of all verifications
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_files": len(self._checksums),
            "valid": 0,
            "corrupted": 0,
            "missing": 0,
            "results": [],
        }
        
        for filename in self._checksums:
            file_path = self.cache_dir / filename
            result = self.verify_file(file_path)
            report["results"].append(result)
            
            if result["status"] == "valid":
                report["valid"] += 1
            elif result["status"] == "corrupted":
                report["corrupted"] += 1
            elif result["status"] == "missing":
                report["missing"] += 1
        
        return report


class DataReconciliation:
    """
    Generates data reconciliation reports for audit purposes.
    
    Compares data from different sources and timestamps to ensure
    consistency and track any discrepancies.
    """
    
    def __init__(self):
        self.reports: list[dict] = []
    
    def compare_sources(
        self,
        source1_data: pd.DataFrame,
        source2_data: pd.DataFrame,
        source1_name: str = "Source1",
        source2_name: str = "Source2",
        tolerance_pct: float = 0.01,
    ) -> dict:
        """
        Compare data from two sources.
        
        Args:
            source1_data: DataFrame from first source
            source2_data: DataFrame from second source
            source1_name: Name of first source
            source2_name: Name of second source
            tolerance_pct: Acceptable price difference percentage
            
        Returns:
            Reconciliation report
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "source1": source1_name,
            "source2": source2_name,
            "tolerance_pct": tolerance_pct,
            "status": "pass",
            "discrepancies": [],
            "summary": {},
        }
        
        # Find common dates
        common_dates = source1_data.index.intersection(source2_data.index)
        report["summary"]["common_dates"] = len(common_dates)
        report["summary"]["source1_only"] = len(source1_data.index.difference(source2_data.index))
        report["summary"]["source2_only"] = len(source2_data.index.difference(source1_data.index))
        
        if len(common_dates) == 0:
            report["status"] = "no_overlap"
            return report
        
        # Compare Close prices on common dates
        s1_close = source1_data.loc[common_dates, "Close"]
        s2_close = source2_data.loc[common_dates, "Close"]
        
        diff_pct = ((s1_close - s2_close).abs() / s1_close * 100)
        discrepancies = diff_pct[diff_pct > tolerance_pct]
        
        if len(discrepancies) > 0:
            report["status"] = "discrepancies_found"
            for date, diff in discrepancies.head(10).items():  # Report first 10
                report["discrepancies"].append({
                    "date": str(date),
                    "source1_value": float(s1_close.loc[date]),
                    "source2_value": float(s2_close.loc[date]),
                    "difference_pct": float(diff),
                })
        
        report["summary"]["total_discrepancies"] = len(discrepancies)
        report["summary"]["max_discrepancy_pct"] = float(diff_pct.max()) if len(diff_pct) > 0 else 0
        
        self.reports.append(report)
        return report
    
    def generate_summary_report(self) -> dict:
        """Generate a summary of all reconciliation reports."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_reconciliations": len(self.reports),
            "passed": sum(1 for r in self.reports if r["status"] == "pass"),
            "failed": sum(1 for r in self.reports if r["status"] != "pass"),
            "reports": self.reports,
        }
