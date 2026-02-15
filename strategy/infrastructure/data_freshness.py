"""
Data Freshness Module
=====================
Tracks the freshness/staleness of cached market data.

Features:
- Check last update timestamps for cached data
- Compare against latest market close dates
- Alert when data is stale and needs refresh
- Support for US and AU market calendars
"""

import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import pandas as pd


# ============== MARKET CALENDARS ==============

# Simplified market calendars (major holidays only)
US_HOLIDAYS_2024_2025 = {
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 15),  # MLK Day
    date(2024, 2, 19),  # Presidents Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 5, 27),  # Memorial Day
    date(2024, 6, 19),  # Juneteenth
    date(2024, 7, 4),   # Independence Day
    date(2024, 9, 2),   # Labor Day
    date(2024, 11, 28), # Thanksgiving
    date(2024, 12, 25), # Christmas
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
}

AU_HOLIDAYS_2024_2025 = {
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 26),  # Australia Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 4, 1),   # Easter Monday
    date(2024, 4, 25),  # ANZAC Day
    date(2024, 6, 10),  # Queen's Birthday (varies by state)
    date(2024, 12, 25), # Christmas
    date(2024, 12, 26), # Boxing Day
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 27),  # Australia Day (observed)
    date(2025, 4, 18),  # Good Friday
    date(2025, 4, 21),  # Easter Monday
    date(2025, 4, 25),  # ANZAC Day
    date(2025, 6, 9),   # Queen's Birthday
    date(2025, 12, 25), # Christmas
    date(2025, 12, 26), # Boxing Day
}


# ============== DATA CLASSES ==============

@dataclass
class FreshnessInfo:
    """Freshness information for a data source or universe."""
    name: str
    last_cache_update: Optional[datetime] = None
    latest_data_date: Optional[date] = None
    expected_latest_date: Optional[date] = None
    staleness_days: int = 0
    is_stale: bool = False
    needs_refresh: bool = False
    message: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "last_cache_update": self.last_cache_update.isoformat() if self.last_cache_update else None,
            "latest_data_date": self.latest_data_date.isoformat() if self.latest_data_date else None,
            "expected_latest_date": self.expected_latest_date.isoformat() if self.expected_latest_date else None,
            "staleness_days": self.staleness_days,
            "is_stale": self.is_stale,
            "needs_refresh": self.needs_refresh,
            "message": self.message
        }


@dataclass
class FreshnessReport:
    """Comprehensive freshness report for all tracked data."""
    check_time: datetime = field(default_factory=datetime.now)
    universes: List[FreshnessInfo] = field(default_factory=list)
    overall_status: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "check_time": self.check_time.isoformat(),
            "overall_status": self.overall_status,
            "universes": [u.to_dict() for u in self.universes],
            "needs_refresh_count": sum(1 for u in self.universes if u.needs_refresh)
        }


# ============== DATA FRESHNESS CLASS ==============

class DataFreshness:
    """
    Checks and tracks data freshness/staleness.
    
    Provides:
    - Last trading date calculation for US/AU markets
    - Cache freshness checking
    - Staleness alerts
    """
    
    def __init__(
        self,
        cache_dir: str = "./cache",
        max_staleness_days: int = 1,
        verbose: bool = True
    ):
        self.cache_dir = Path(cache_dir)
        self.max_staleness_days = max_staleness_days
        self.verbose = verbose
        
        # Metadata file for tracking updates
        self._metadata_file = self.cache_dir / "data_freshness_meta.json"
        self._metadata: Dict = self._load_metadata()
    
    def _log(self, msg: str):
        if self.verbose:
            print(f"[DataFreshness] {msg}")
    
    def _load_metadata(self) -> Dict:
        """Load cached metadata."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file) as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_metadata(self):
        """Save metadata to file."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self._metadata_file, 'w') as f:
            json.dump(self._metadata, f, indent=2, default=str)
    
    def is_trading_day(self, d: date, market: str = "US") -> bool:
        """Check if a date is a trading day for the given market."""
        # Weekend check
        if d.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Holiday check
        holidays = US_HOLIDAYS_2024_2025 if market == "US" else AU_HOLIDAYS_2024_2025
        if d in holidays:
            return False
        
        return True
    
    def get_last_trading_date(self, market: str = "US", as_of: date = None) -> date:
        """
        Get the last completed trading date for a market.
        
        Args:
            market: 'US' or 'AU'
            as_of: Calculate as of this date (defaults to today)
        
        Returns:
            Last trading date where data should be available
        """
        as_of = as_of or date.today()
        current = as_of
        now = datetime.now()
        
        # US market closes at 4pm ET (roughly 9pm GMT+10)
        # AU market closes at 4pm AEDT (roughly 6am GMT)
        
        # If it's before market close, we need yesterday's data
        if market == "US":
            # US market hours: 9:30am - 4:00pm ET
            # That's roughly 12:30am - 7:00am AEDT next day
            market_close_hour = 7  # 7am AEDT = 4pm ET
            if now.hour < market_close_hour:
                current = current - timedelta(days=1)
        elif market == "AU":
            # AU market hours: 10:00am - 4:00pm AEDT
            market_close_hour = 16
            if now.hour < market_close_hour:
                current = current - timedelta(days=1)
        
        # Walk back to find last trading day
        while not self.is_trading_day(current, market):
            current = current - timedelta(days=1)
        
        return current
    
    def record_update(self, universe: str, latest_date: date):
        """
        Record that data was updated/refreshed.
        
        Args:
            universe: Universe key (sp500, nasdaq100, asx200)
            latest_date: Latest data date in the cache
        """
        self._metadata[universe] = {
            "last_update": datetime.now().isoformat(),
            "latest_data_date": latest_date.isoformat()
        }
        self._save_metadata()
        self._log(f"Recorded update for {universe}: data up to {latest_date}")
    
    def check_universe_freshness(
        self,
        universe: str,
        market: str = "US"
    ) -> FreshnessInfo:
        """
        Check freshness for a specific universe.
        
        Args:
            universe: Universe key
            market: 'US' or 'AU'
        
        Returns:
            FreshnessInfo with staleness details
        """
        info = FreshnessInfo(name=universe)
        
        # Get expected latest date
        info.expected_latest_date = self.get_last_trading_date(market)
        
        # Check metadata
        if universe in self._metadata:
            meta = self._metadata[universe]
            info.last_cache_update = datetime.fromisoformat(meta['last_update'])
            info.latest_data_date = date.fromisoformat(meta['latest_data_date'])
            
            # Calculate staleness
            info.staleness_days = (info.expected_latest_date - info.latest_data_date).days
            info.is_stale = info.staleness_days > self.max_staleness_days
            info.needs_refresh = info.is_stale
            
            if info.is_stale:
                info.message = f"Data is {info.staleness_days} days behind market"
            else:
                info.message = "Data is current"
        else:
            # No metadata - check if cache files exist
            info.needs_refresh = True
            info.is_stale = True
            info.message = "No data cached - needs initial fetch"
        
        return info
    
    def check_all_universes(self) -> FreshnessReport:
        """
        Check freshness for all tracked universes.
        
        Returns:
            FreshnessReport with all universe statuses
        """
        report = FreshnessReport()
        
        # Define universes and their markets
        universes = {
            "sp500": "US",
            "nasdaq100": "US",
            "asx200": "AU",
            "momentum": "US"
        }
        
        for universe, market in universes.items():
            info = self.check_universe_freshness(universe, market)
            report.universes.append(info)
        
        # Determine overall status
        stale_count = sum(1 for u in report.universes if u.is_stale)
        if stale_count == 0:
            report.overall_status = "all_current"
        elif stale_count == len(report.universes):
            report.overall_status = "all_stale"
        else:
            report.overall_status = "partially_stale"
        
        return report
    
    def is_data_stale(
        self,
        universe: str,
        max_staleness_days: int = None
    ) -> bool:
        """
        Quick check if data for a universe is stale.
        
        Args:
            universe: Universe key
            max_staleness_days: Override default max staleness
        
        Returns:
            True if data needs refreshing
        """
        market = "AU" if universe == "asx200" else "US"
        info = self.check_universe_freshness(universe, market)
        
        if max_staleness_days is not None:
            return info.staleness_days > max_staleness_days
        
        return info.is_stale
    
    def get_refresh_command(self, universe: str) -> str:
        """
        Get command to refresh data for a universe.
        
        Returns:
            Shell command to run for data refresh
        """
        return f"python -c \"from strategy.fast_data_loader import FastDataLoader; " \
               f"loader = FastDataLoader(); " \
               f"loader.fetch_prices_fast({repr(self._get_tickers(universe))})\""
    
    def _get_tickers(self, universe: str) -> List[str]:
        """Get tickers for a universe (imports from data_catalog)."""
        try:
            from strategy.infrastructure.data_catalog import UNIVERSES
            return UNIVERSES.get(universe, {}).get("tickers", [])
        except ImportError:
            return []


# ============== UTILITY FUNCTIONS ==============

def get_data_status() -> Dict:
    """
    Get comprehensive data status for API/dashboard.
    
    Returns dict suitable for JSON response.
    """
    freshness = DataFreshness(verbose=False)
    report = freshness.check_all_universes()
    
    # Try to get catalog data too
    try:
        from strategy.infrastructure.data_catalog import DataCatalog
        catalog = DataCatalog(verbose=False)
        # Load cached catalog if available
        catalog.load_catalog()
        coverage = catalog.generate_coverage_report()
        coverage_dict = coverage.to_dict('records') if not coverage.empty else []
    except:
        coverage_dict = []
    
    return {
        "check_time": datetime.now().isoformat(),
        "overall_status": report.overall_status,
        "freshness": report.to_dict(),
        "coverage": coverage_dict,
        "markets": {
            "US": {
                "last_trading_date": freshness.get_last_trading_date("US").isoformat(),
                "is_open": False  # Simplified
            },
            "AU": {
                "last_trading_date": freshness.get_last_trading_date("AU").isoformat(),
                "is_open": False
            }
        }
    }


# ============== CLI INTERFACE ==============

def main():
    """Command-line interface for data freshness checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Freshness - Check data staleness")
    parser.add_argument("--universe", "-u", default=None,
                       help="Specific universe to check")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Check all universes")
    
    args = parser.parse_args()
    
    freshness = DataFreshness()
    
    if args.universe:
        market = "AU" if args.universe == "asx200" else "US"
        info = freshness.check_universe_freshness(args.universe, market)
        print(f"\n{args.universe.upper()} Freshness:")
        for k, v in info.to_dict().items():
            print(f"  {k}: {v}")
    else:
        report = freshness.check_all_universes()
        
        print("\n" + "="*60)
        print("DATA FRESHNESS REPORT")
        print("="*60)
        print(f"Check Time: {report.check_time}")
        print(f"Overall Status: {report.overall_status}")
        print("-"*60)
        
        for u in report.universes:
            status = "🔴 STALE" if u.is_stale else "🟢 CURRENT"
            print(f"\n{u.name}:")
            print(f"  Status: {status}")
            print(f"  Latest Data: {u.latest_data_date}")
            print(f"  Expected: {u.expected_latest_date}")
            print(f"  Staleness: {u.staleness_days} days")
            print(f"  Message: {u.message}")


if __name__ == "__main__":
    main()
