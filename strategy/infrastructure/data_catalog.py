"""
Data Catalog Module
===================
Provides visibility into available backtesting data for each stock universe.

Features:
- Scan cached data and data sources for date range coverage
- Report earliest/latest available dates per ticker
- Calculate common backtesting windows
- Detect data gaps and quality issues
"""

import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
import pandas as pd
import numpy as np

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required if env vars are set directly

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    from tiingo import TiingoClient
    HAS_TIINGO = True
except ImportError:
    HAS_TIINGO = False

try:
    import norgatedata
    HAS_NORGATE = True
    # Default Norgate data path
    NORGATE_DATA_PATH = r"C:\ProgramData\Norgate Data"
except ImportError:
    HAS_NORGATE = False
    NORGATE_DATA_PATH = None


# ============== UNIVERSE DEFINITIONS ==============

UNIVERSES = {
    "sp500": {
        "name": "S&P 500",
        "market": "US",
        "data_source": "tiingo",
        "tickers": [
            # Technology
            'AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM', 'ADBE', 'ACN', 'CSCO', 'IBM',
            'INTC', 'AMD', 'TXN', 'QCOM', 'NOW', 'INTU', 'AMAT', 'ADI', 'LRCX', 'MU',
            # Financials
            'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'SPGI', 'AXP', 'BLK',
            # Health Care
            'UNH', 'LLY', 'JNJ', 'MRK', 'ABBV', 'TMO', 'ABT', 'DHR', 'PFE', 'AMGN',
            # Consumer
            'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'SBUX', 'TJX', 'CMG', 'BKNG',
            # Communication
            'GOOGL', 'GOOG', 'META', 'NFLX', 'DIS', 'CMCSA', 'T', 'VZ', 'CHTR', 'TMUS',
            # Staples
            'PG', 'COST', 'WMT', 'KO', 'PEP', 'PM', 'MDLZ', 'CL', 'MO', 'EL',
            # Industrials
            'GE', 'CAT', 'RTX', 'HON', 'UNP', 'BA', 'UPS', 'DE', 'LMT', 'ADP',
            # Energy
            'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY',
            # Materials
            'LIN', 'APD', 'SHW', 'FCX', 'NEM', 'NUE', 'ECL', 'VMC', 'MLM', 'DOW',
            # Utilities
            'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'PEG',
            # Real Estate
            'PLD', 'AMT', 'EQIX', 'CCI', 'PSA', 'O', 'WELL', 'SPG', 'DLR', 'AVB',
        ]
    },
    "nasdaq100": {
        "name": "NASDAQ 100",
        "market": "US",
        "data_source": "tiingo",
        "tickers": [
            'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'AVGO', 'GOOGL', 'GOOG', 'TSLA', 'COST',
            'NFLX', 'AMD', 'ADBE', 'QCOM', 'PEP', 'CSCO', 'LIN', 'TMUS', 'TXN', 'INTU',
            'AMGN', 'CMCSA', 'ISRG', 'HON', 'AMAT', 'BKNG', 'VRTX', 'ADP', 'REGN', 'GILD',
            'PANW', 'MU', 'ADI', 'SBUX', 'MDLZ', 'LRCX', 'MELI', 'KLAC', 'CHTR', 'SNPS',
            'CDNS', 'PYPL', 'CTAS', 'MAR', 'CRWD', 'ORLY', 'CEG', 'ABNB', 'WDAY', 'CSX',
            'NXPI', 'ROP', 'PCAR', 'MNST', 'MRVL', 'ADSK', 'AEP', 'MCHP', 'ODFL', 'FTNT',
            'DDOG', 'TEAM', 'ZS', 'MDB', 'NET', 'TTD', 'DASH', 'COIN', 'PLTR', 'ARM',
        ]
    },
    "asx200": {
        "name": "ASX 200",
        "market": "AU",
        "data_source": "norgate",  # or yfinance with .AX suffix
        "tickers": [
            # Banks & Financials
            'CBA.AX', 'NAB.AX', 'WBC.AX', 'ANZ.AX', 'MQG.AX', 'QBE.AX', 'SUN.AX', 'IAG.AX',
            # Mining & Resources
            'BHP.AX', 'RIO.AX', 'FMG.AX', 'NCM.AX', 'NST.AX', 'EVN.AX', 'S32.AX', 'MIN.AX',
            # Energy
            'WDS.AX', 'STO.AX', 'ORG.AX', 'APA.AX', 'AGL.AX',
            # Healthcare
            'CSL.AX', 'RMD.AX', 'COH.AX', 'SHL.AX', 'PME.AX', 'FPH.AX', 'RHC.AX',
            # Consumer & Retail
            'WES.AX', 'WOW.AX', 'COL.AX', 'JBH.AX', 'HVN.AX', 'SUL.AX',
            # Real Estate
            'GMG.AX', 'GPT.AX', 'MGR.AX', 'SCG.AX', 'VCX.AX',
            # Technology
            'XRO.AX', 'WTC.AX', 'REA.AX', 'SEK.AX', 'NXT.AX', 'TNE.AX',
            # Industrials
            'TCL.AX', 'BXB.AX', 'QAN.AX', 'QUB.AX',
            # Telecoms
            'TLS.AX', 'TPG.AX',
        ]
    },
    "momentum": {
        "name": "Momentum Leaders",
        "market": "US",
        "data_source": "tiingo",
        "tickers": [
            'NVDA', 'AMD', 'SMCI', 'PLTR', 'META', 'AVGO', 'ORCL', 'CRM', 'NOW', 'PANW',
            'CRWD', 'ZS', 'NET', 'DDOG', 'MDB', 'SNOW', 'COIN', 'MSTR', 'ARM', 'TSM',
        ]
    }
}


# ============== DATA CLASSES ==============

@dataclass
class TickerCoverage:
    """Coverage information for a single ticker."""
    ticker: str
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None
    total_days: int = 0
    trading_days: int = 0
    gaps: List[Tuple[date, date]] = field(default_factory=list)
    data_source: str = "unknown"
    is_available: bool = True
    error_message: Optional[str] = None
    
    @property
    def years_of_data(self) -> float:
        if self.earliest_date and self.latest_date:
            return (self.latest_date - self.earliest_date).days / 365.25
        return 0.0
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "earliest_date": self.earliest_date.isoformat() if self.earliest_date else None,
            "latest_date": self.latest_date.isoformat() if self.latest_date else None,
            "years_of_data": round(self.years_of_data, 2),
            "trading_days": self.trading_days,
            "gaps_count": len(self.gaps),
            "data_source": self.data_source,
            "is_available": self.is_available,
            "error": self.error_message
        }


@dataclass
class UniverseReport:
    """Coverage report for an entire universe."""
    universe_name: str
    universe_key: str
    market: str
    scan_time: datetime = field(default_factory=datetime.now)
    ticker_coverage: List[TickerCoverage] = field(default_factory=list)
    
    @property
    def total_tickers(self) -> int:
        return len(self.ticker_coverage)
    
    @property
    def available_tickers(self) -> int:
        return sum(1 for t in self.ticker_coverage if t.is_available)
    
    @property
    def common_start(self) -> Optional[date]:
        """Earliest common date where all available tickers have data."""
        available = [t for t in self.ticker_coverage if t.is_available and t.earliest_date]
        if not available:
            return None
        return max(t.earliest_date for t in available)
    
    @property
    def common_end(self) -> Optional[date]:
        """Latest common date where all available tickers have data."""
        available = [t for t in self.ticker_coverage if t.is_available and t.latest_date]
        if not available:
            return None
        return min(t.latest_date for t in available)
    
    @property
    def common_years(self) -> float:
        """Years of common data coverage."""
        if self.common_start and self.common_end:
            return (self.common_end - self.common_start).days / 365.25
        return 0.0
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame for display."""
        rows = [t.to_dict() for t in self.ticker_coverage]
        return pd.DataFrame(rows)
    
    def summary(self) -> Dict:
        """Return summary statistics."""
        return {
            "universe": self.universe_name,
            "market": self.market,
            "total_tickers": self.total_tickers,
            "available_tickers": self.available_tickers,
            "coverage_pct": round(100 * self.available_tickers / max(1, self.total_tickers), 1),
            "common_start": self.common_start.isoformat() if self.common_start else None,
            "common_end": self.common_end.isoformat() if self.common_end else None,
            "common_years": round(self.common_years, 2),
            "scan_time": self.scan_time.isoformat()
        }


@dataclass 
class BacktestWindow:
    """Recommended backtesting window for a universe."""
    universe: str
    start_date: date
    end_date: date
    available_tickers: int
    total_tickers: int
    
    @property
    def duration_years(self) -> float:
        return (self.end_date - self.start_date).days / 365.25
    
    def is_valid_for(self, min_years: float = 5) -> bool:
        return self.duration_years >= min_years


# ============== DATA CATALOG CLASS ==============

class DataCatalog:
    """
    Central catalog for all backtesting data availability.
    
    Provides:
    - Universe scanning for date range coverage
    - Data gap detection
    - Backtest window recommendations
    """
    
    def __init__(
        self,
        cache_dir: str = "./cache",
        tiingo_api_key: str = None,
        verbose: bool = True
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        
        # Tiingo client
        self.tiingo_api_key = tiingo_api_key or os.environ.get("TIINGO_API_KEY")
        self._tiingo_client = None
        
        # Catalog cache
        self._catalog_cache_file = self.cache_dir / "data_catalog.json"
        self._catalog: Dict[str, UniverseReport] = {}
    
    def _get_tiingo_client(self) -> Optional[TiingoClient]:
        """Get or create Tiingo client."""
        if self._tiingo_client is None and HAS_TIINGO and self.tiingo_api_key:
            self._tiingo_client = TiingoClient({"api_key": self.tiingo_api_key})
        return self._tiingo_client
    
    def _log(self, msg: str):
        if self.verbose:
            print(f"[DataCatalog] {msg}")
    
    def get_universe_tickers(self, universe: str) -> List[str]:
        """Get ticker list for a universe."""
        if universe not in UNIVERSES:
            raise ValueError(f"Unknown universe: {universe}. Available: {list(UNIVERSES.keys())}")
        return UNIVERSES[universe]["tickers"]
    
    def get_universe_info(self, universe: str) -> Dict:
        """Get metadata for a universe."""
        if universe not in UNIVERSES:
            raise ValueError(f"Unknown universe: {universe}")
        return UNIVERSES[universe]
    
    def _check_ticker_yfinance(self, ticker: str) -> TickerCoverage:
        """Check data availability for a ticker using yfinance."""
        coverage = TickerCoverage(ticker=ticker, data_source="yfinance")
        
        if not HAS_YFINANCE:
            coverage.is_available = False
            coverage.error_message = "yfinance not installed"
            return coverage
        
        try:
            # Fetch minimal data to get date range
            stock = yf.Ticker(ticker)
            hist = stock.history(period="max", interval="1d")
            
            if hist.empty:
                coverage.is_available = False
                coverage.error_message = "No data available"
                return coverage
            
            coverage.earliest_date = hist.index[0].date()
            coverage.latest_date = hist.index[-1].date()
            coverage.trading_days = len(hist)
            coverage.total_days = (coverage.latest_date - coverage.earliest_date).days
            coverage.is_available = True
            
            # Detect gaps (more than 5 business days)
            dates = pd.DatetimeIndex(hist.index)
            gaps = []
            for i in range(1, len(dates)):
                gap_days = (dates[i] - dates[i-1]).days
                if gap_days > 7:  # More than a week = potential gap
                    gaps.append((dates[i-1].date(), dates[i].date()))
            coverage.gaps = gaps[:10]  # Limit to 10 gaps
            
        except Exception as e:
            coverage.is_available = False
            coverage.error_message = str(e)
        
        return coverage
    
    def _check_ticker_tiingo(self, ticker: str) -> TickerCoverage:
        """Check data availability for a ticker using Tiingo."""
        coverage = TickerCoverage(ticker=ticker, data_source="tiingo")
        
        client = self._get_tiingo_client()
        if client is None:
            coverage.is_available = False
            coverage.error_message = "Tiingo not configured"
            return coverage
        
        try:
            # Get ticker metadata
            meta = client.get_ticker_metadata(ticker)
            
            if not meta or not meta.get('startDate'):
                coverage.is_available = False
                coverage.error_message = "No metadata available"
                return coverage
            
            coverage.earliest_date = datetime.strptime(meta['startDate'], '%Y-%m-%d').date()
            end_date_str = meta.get('endDate') or datetime.now().strftime('%Y-%m-%d')
            coverage.latest_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            coverage.is_available = True
            
            # Estimate trading days (roughly 252 per year)
            years = (coverage.latest_date - coverage.earliest_date).days / 365.25
            coverage.trading_days = int(years * 252)
            coverage.total_days = (coverage.latest_date - coverage.earliest_date).days
            
        except Exception as e:
            coverage.is_available = False
            coverage.error_message = str(e)
        
        return coverage
    
    def _check_ticker_norgate(self, ticker: str) -> TickerCoverage:
        """Check data availability for a ticker using Norgate Data."""
        # Convert .AX suffix to Norgate format (.AU)
        norgate_ticker = ticker.replace('.AX', '.AU')
        coverage = TickerCoverage(ticker=ticker, data_source="norgate")
        
        if not HAS_NORGATE:
            coverage.is_available = False
            coverage.error_message = "norgatedata not installed"
            return coverage
        
        try:
            # Get price history from Norgate
            # norgatedata uses 'stock_data' format
            prices = norgatedata.price_timeseries(
                norgate_ticker,
                stock_price_adjustment_setting=norgatedata.StockPriceAdjustmentType.TOTALRETURN,
                timeseriesformat='pandas-dataframe'
            )
            
            if prices is None or prices.empty:
                coverage.is_available = False
                coverage.error_message = "No data in Norgate database"
                return coverage
            
            coverage.earliest_date = prices.index[0].date() if hasattr(prices.index[0], 'date') else prices.index[0]
            coverage.latest_date = prices.index[-1].date() if hasattr(prices.index[-1], 'date') else prices.index[-1]
            coverage.trading_days = len(prices)
            coverage.total_days = (coverage.latest_date - coverage.earliest_date).days
            coverage.is_available = True
            
        except Exception as e:
            coverage.is_available = False
            coverage.error_message = str(e)
        
        return coverage
    
    def scan_ticker(self, ticker: str, data_source: str = "auto") -> TickerCoverage:
        """
        Scan a single ticker for data availability.
        
        Args:
            ticker: Ticker symbol
            data_source: 'tiingo', 'yfinance', 'norgate', or 'auto'
        """
        if data_source == "auto":
            # Prefer Norgate for ASX, Tiingo for US, yfinance as fallback
            if ticker.endswith('.AX'):
                if HAS_NORGATE:
                    data_source = "norgate"
                else:
                    data_source = "yfinance"
            elif self._get_tiingo_client():
                data_source = "tiingo"
            else:
                data_source = "yfinance"
        
        if data_source == "norgate":
            return self._check_ticker_norgate(ticker)
        elif data_source == "tiingo":
            return self._check_ticker_tiingo(ticker)
        else:
            return self._check_ticker_yfinance(ticker)
    
    def scan_universe(
        self,
        universe: str,
        max_tickers: int = None,
        use_cache: bool = True
    ) -> UniverseReport:
        """
        Scan all tickers in a universe for data availability.
        
        Args:
            universe: Universe key (sp500, nasdaq100, asx200, momentum)
            max_tickers: Limit number of tickers to scan (for testing)
            use_cache: Whether to use cached results
        
        Returns:
            UniverseReport with coverage for all tickers
        """
        info = self.get_universe_info(universe)
        tickers = info["tickers"]
        
        if max_tickers:
            tickers = tickers[:max_tickers]
        
        self._log(f"Scanning {len(tickers)} tickers in {info['name']}...")
        
        report = UniverseReport(
            universe_name=info["name"],
            universe_key=universe,
            market=info["market"]
        )
        
        data_source = info.get("data_source", "auto")
        
        for i, ticker in enumerate(tickers):
            if self.verbose and (i + 1) % 10 == 0:
                self._log(f"  Progress: {i+1}/{len(tickers)}")
            
            coverage = self.scan_ticker(ticker, data_source)
            report.ticker_coverage.append(coverage)
        
        self._log(f"Scan complete: {report.available_tickers}/{report.total_tickers} available")
        self._log(f"Common window: {report.common_start} to {report.common_end} ({report.common_years:.1f} years)")
        
        # Cache result
        self._catalog[universe] = report
        
        return report
    
    def get_backtest_window(
        self,
        universe: str,
        min_years: float = 5,
        end_date: date = None
    ) -> BacktestWindow:
        """
        Get recommended backtesting window for a universe.
        
        Args:
            universe: Universe key
            min_years: Minimum years of data required
            end_date: Optionally specify end date (defaults to latest common date)
        
        Returns:
            BacktestWindow with recommended dates
        """
        # Scan if not already cached
        if universe not in self._catalog:
            self.scan_universe(universe)
        
        report = self._catalog[universe]
        
        # Calculate window
        common_end = end_date or report.common_end or date.today()
        common_start = report.common_start or (common_end - timedelta(days=int(min_years * 365)))
        
        # Ensure minimum years
        if (common_end - common_start).days < min_years * 365:
            common_start = common_end - timedelta(days=int(min_years * 365))
        
        return BacktestWindow(
            universe=universe,
            start_date=common_start,
            end_date=common_end,
            available_tickers=report.available_tickers,
            total_tickers=report.total_tickers
        )
    
    def generate_coverage_report(self) -> pd.DataFrame:
        """
        Generate a summary report of all cached universe scans.
        
        Returns:
            DataFrame with universe coverage summary
        """
        rows = []
        for universe_key, report in self._catalog.items():
            summary = report.summary()
            rows.append(summary)
        
        if not rows:
            return pd.DataFrame()
        
        return pd.DataFrame(rows)
    
    def save_catalog(self, filepath: str = None):
        """Save catalog to JSON file."""
        filepath = filepath or self._catalog_cache_file
        
        data = {}
        for universe_key, report in self._catalog.items():
            data[universe_key] = {
                "summary": report.summary(),
                "tickers": [t.to_dict() for t in report.ticker_coverage]
            }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self._log(f"Catalog saved to {filepath}")
    
    def load_catalog(self, filepath: str = None) -> bool:
        """Load catalog from JSON file."""
        filepath = Path(filepath or self._catalog_cache_file)
        
        if not filepath.exists():
            self._log("No cached catalog found")
            return False
        
        try:
            with open(filepath) as f:
                data = json.load(f)
            
            self._log(f"Loaded catalog with {len(data)} universes")
            return True
        except Exception as e:
            self._log(f"Error loading catalog: {e}")
            return False


# ============== CLI INTERFACE ==============

def main():
    """Command-line interface for data catalog."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Catalog - Check backtesting data availability")
    parser.add_argument("--universe", "-u", default="sp500", 
                       choices=list(UNIVERSES.keys()),
                       help="Universe to scan")
    parser.add_argument("--max-tickers", "-n", type=int, default=None,
                       help="Limit number of tickers to scan")
    parser.add_argument("--output", "-o", default=None,
                       help="Output file for report")
    
    args = parser.parse_args()
    
    catalog = DataCatalog()
    report = catalog.scan_universe(args.universe, max_tickers=args.max_tickers)
    
    print("\n" + "="*60)
    print(f"COVERAGE SUMMARY: {report.universe_name}")
    print("="*60)
    
    df = report.to_dataframe()
    print(df[['ticker', 'earliest_date', 'latest_date', 'years_of_data', 'is_available']].to_string())
    
    print("\n" + "-"*60)
    print("SUMMARY:")
    for k, v in report.summary().items():
        print(f"  {k}: {v}")
    
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
