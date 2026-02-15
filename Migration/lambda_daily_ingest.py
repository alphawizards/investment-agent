"""
Daily Data Ingest Lambda Handler
=================================

AWS Lambda function to fetch daily OHLCV data from yfinance and store in Neon PostgreSQL.

Features:
- Fetches latest daily candle for each ticker in configured universe
- UPSERT logic (ON CONFLICT DO UPDATE) for idempotency
- Concurrent data fetching for performance
- Robust error handling with per-ticker failure logging
- CloudWatch metrics and structured logging
- Environment-based configuration

Environment Variables:
- NEON_DATABASE_URL: PostgreSQL connection string
- UNIVERSE_KEY: Stock universe to fetch (default: SPX500)
- MAX_CONCURRENT: Maximum concurrent yfinance requests (default: 10)
- LOG_LEVEL: Logging level (default: INFO)

Author: Manus AI
Date: 2026-01-11
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# Third-party imports
import yfinance as yf
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit

# Configure AWS Lambda Powertools
logger = Logger(service="daily-data-ingest")
tracer = Tracer(service="daily-data-ingest")
metrics = Metrics(namespace="PotentialParakeet", service="daily-data-ingest")

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """Lambda configuration from environment variables."""
    
    database_url: str
    universe_key: str = "SPX500"
    max_concurrent: int = 10
    log_level: str = "INFO"
    lookback_days: int = 5  # Fetch last N days to handle holidays/weekends
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL environment variable is required")
        
        return cls(
            database_url=database_url,
            universe_key=os.getenv("UNIVERSE_KEY", "SPX500"),
            max_concurrent=int(os.getenv("MAX_CONCURRENT", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            lookback_days=int(os.getenv("LOOKBACK_DAYS", "5"))
        )

# ============================================================================
# Stock Universe Definitions
# ============================================================================

def get_sp500_tickers() -> List[str]:
    """Get S&P 500 tickers (simplified for Lambda)."""
    # In production, fetch from external source or parameter store
    return [
        "AAPL", "MSFT", "AMZN", "GOOG", "GOOGL", "META", "TSLA", "NVDA", "BRK-B", "JPM",
        "V", "UNH", "HD", "MA", "PG", "XOM", "CVX", "JNJ", "LLY", "ABBV",
        "BAC", "PFE", "KO", "COST", "WMT", "MRK", "DIS", "CSCO", "PEP", "TMO",
        "ABT", "AVGO", "VZ", "ACN", "MCD", "ADBE", "CRM", "NKE", "CMCSA", "TXN",
        "DHR", "NEE", "WFC", "ORCL", "LIN", "BMY", "UPS", "PM", "QCOM", "RTX",
        "HON", "INTC", "INTU", "T", "LOW", "SPGI", "UNP", "CAT", "AMD", "SBUX",
        "GE", "AMGN", "BA", "IBM", "BLK", "AXP", "DE", "GILD", "MDT", "ISRG",
        "TJX", "BKNG", "MMM", "SYK", "ADP", "CI", "VRTX", "REGN", "ZTS", "CB",
        "NOW", "PLD", "SCHW", "MO", "ADI", "TMUS", "LRCX", "EOG", "DUK", "SO",
        "SLB", "MDLZ", "PNC", "USB", "BDX", "TGT", "CL", "EQIX", "ITW", "APD"
    ]

def get_nasdaq100_tickers() -> List[str]:
    """Get NASDAQ 100 tickers (simplified for Lambda)."""
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST",
        "PEP", "ADBE", "CSCO", "NFLX", "TMUS", "AMD", "CMCSA", "INTC", "INTU", "TXN",
        "QCOM", "HON", "AMGN", "AMAT", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADI",
        "PDD", "VRTX", "LRCX", "ADP", "REGN", "PANW", "KLAC", "MU", "SNPS", "CDNS",
        "ASML", "MELI", "PYPL", "MRVL", "CHTR", "MAR", "ORLY", "NXPI", "CSX", "ABNB"
    ]

def get_asx200_tickers() -> List[str]:
    """Get ASX 200 tickers (simplified for Lambda)."""
    return [
        "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX", "MQG.AX",
        "WOW.AX", "TLS.AX", "RIO.AX", "FMG.AX", "WDS.AX", "GMG.AX", "TCL.AX", "STO.AX",
        "QBE.AX", "SUN.AX", "IAG.AX", "AMC.AX", "COL.AX", "ORG.AX", "APA.AX", "REA.AX",
        "ALL.AX", "BXB.AX", "JHX.AX", "NCM.AX", "S32.AX", "ORI.AX", "ASX.AX", "XRO.AX"
    ]

UNIVERSE_REGISTRY = {
    "SPX500": get_sp500_tickers,
    "NASDAQ100": get_nasdaq100_tickers,
    "ASX200": get_asx200_tickers,
}

def get_universe_tickers(universe_key: str) -> List[str]:
    """Get tickers for specified universe."""
    if universe_key not in UNIVERSE_REGISTRY:
        raise ValueError(f"Unknown universe: {universe_key}. Available: {list(UNIVERSE_REGISTRY.keys())}")
    return UNIVERSE_REGISTRY[universe_key]()

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class MarketDataRow:
    """Represents a single row of market data."""
    ticker: str
    date: str  # YYYY-MM-DD format
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None
    source: str = "yfinance"
    data_quality: str = "good"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database insertion."""
        return asdict(self)

@dataclass
class FetchResult:
    """Result of fetching data for a single ticker."""
    ticker: str
    success: bool
    rows_fetched: int = 0
    error: Optional[str] = None
    data: Optional[List[MarketDataRow]] = None

# ============================================================================
# Data Fetching
# ============================================================================

class YFinanceDataFetcher:
    """Fetches OHLCV data from yfinance with error handling."""
    
    def __init__(self, config: Config):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
    
    async def fetch_ticker(self, ticker: str) -> FetchResult:
        """
        Fetch latest daily data for a single ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            FetchResult with success status and data or error
        """
        async with self.semaphore:  # Limit concurrent requests
            try:
                # Run yfinance in thread pool (it's synchronous)
                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(
                    None,
                    self._fetch_ticker_sync,
                    ticker
                )
                
                if df is None or df.empty:
                    return FetchResult(
                        ticker=ticker,
                        success=False,
                        error="No data returned from yfinance"
                    )
                
                # Convert DataFrame to MarketDataRow objects
                rows = self._dataframe_to_rows(ticker, df)
                
                logger.info(f"✅ {ticker}: Fetched {len(rows)} rows")
                return FetchResult(
                    ticker=ticker,
                    success=True,
                    rows_fetched=len(rows),
                    data=rows
                )
                
            except Exception as e:
                logger.warning(f"❌ {ticker}: {str(e)}")
                return FetchResult(
                    ticker=ticker,
                    success=False,
                    error=str(e)
                )
    
    def _fetch_ticker_sync(self, ticker: str) -> Optional[pd.DataFrame]:
        """Synchronous yfinance fetch (runs in thread pool)."""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.config.lookback_days)
            
            # Fetch data
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=False  # Keep both Close and Adj Close
            )
            
            if df.empty:
                return None
            
            # Reset index to make Date a column
            df = df.reset_index()
            
            return df
            
        except Exception as e:
            logger.warning(f"yfinance error for {ticker}: {e}")
            return None
    
    def _dataframe_to_rows(self, ticker: str, df: pd.DataFrame) -> List[MarketDataRow]:
        """Convert yfinance DataFrame to MarketDataRow objects."""
        rows = []
        
        for _, row in df.iterrows():
            try:
                # Extract date (handle different yfinance formats)
                if isinstance(row['Date'], pd.Timestamp):
                    date_str = row['Date'].strftime("%Y-%m-%d")
                else:
                    date_str = str(row['Date'])[:10]
                
                # Create MarketDataRow
                market_row = MarketDataRow(
                    ticker=ticker,
                    date=date_str,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume']),
                    adjusted_close=float(row.get('Adj Close', row['Close'])),
                    source="yfinance",
                    data_quality="good"
                )
                
                rows.append(market_row)
                
            except Exception as e:
                logger.warning(f"Failed to parse row for {ticker}: {e}")
                continue
        
        return rows
    
    async def fetch_all(self, tickers: List[str]) -> List[FetchResult]:
        """
        Fetch data for all tickers concurrently.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            List of FetchResult objects
        """
        logger.info(f"📥 Fetching data for {len(tickers)} tickers (max {self.config.max_concurrent} concurrent)")
        
        tasks = [self.fetch_ticker(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)
        
        return results

# ============================================================================
# Database Operations
# ============================================================================

class MarketDataRepository:
    """Handles database operations for market data."""
    
    def __init__(self, config: Config):
        self.config = config
        self.engine = create_async_engine(
            config.database_url,
            pool_size=1,  # Lambda: 1 connection per instance
            max_overflow=0,
            pool_pre_ping=True,
            echo=False
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def upsert_market_data(self, rows: List[MarketDataRow]) -> int:
        """
        Insert or update market data rows using UPSERT.
        
        Args:
            rows: List of MarketDataRow objects
            
        Returns:
            Number of rows affected
        """
        if not rows:
            return 0
        
        # Prepare UPSERT query (PostgreSQL-specific)
        upsert_query = text("""
            INSERT INTO market_data (
                ticker, date, open, high, low, close, volume, 
                adjusted_close, source, data_quality, created_at, updated_at
            ) VALUES (
                :ticker, :date, :open, :high, :low, :close, :volume,
                :adjusted_close, :source, :data_quality, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON CONFLICT (ticker, date) 
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                adjusted_close = EXCLUDED.adjusted_close,
                source = EXCLUDED.source,
                data_quality = EXCLUDED.data_quality,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        async with self.async_session() as session:
            try:
                # Execute batch insert
                result = await session.execute(
                    upsert_query,
                    [row.to_dict() for row in rows]
                )
                await session.commit()
                
                rows_affected = result.rowcount if result.rowcount else len(rows)
                logger.info(f"💾 Upserted {rows_affected} rows to database")
                
                return rows_affected
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error: {e}")
                raise
    
    async def get_latest_dates(self, tickers: List[str]) -> Dict[str, str]:
        """
        Get the latest date for each ticker in the database.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dict mapping ticker to latest date (YYYY-MM-DD)
        """
        if not tickers:
            return {}
        
        query = text("""
            SELECT ticker, MAX(date) as latest_date
            FROM market_data
            WHERE ticker = ANY(:tickers)
            GROUP BY ticker
        """)
        
        async with self.async_session() as session:
            result = await session.execute(query, {"tickers": tickers})
            rows = result.fetchall()
            
            return {row.ticker: row.latest_date.strftime("%Y-%m-%d") for row in rows}
    
    async def close(self):
        """Close database connection."""
        await self.engine.dispose()

# ============================================================================
# Lambda Handler
# ============================================================================

@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
async def handler_async(event: Dict, context) -> Dict:
    """
    Main Lambda handler (async version).
    
    Args:
        event: Lambda event (can contain universe_key override)
        context: Lambda context
        
    Returns:
        Response dict with status and metrics
    """
    start_time = datetime.now()
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Allow universe override from event
        if "universe_key" in event:
            config.universe_key = event["universe_key"]
        
        logger.info(f"🚀 Starting daily data ingest for universe: {config.universe_key}")
        
        # Get ticker universe
        tickers = get_universe_tickers(config.universe_key)
        logger.info(f"📊 Universe contains {len(tickers)} tickers")
        
        # Initialize fetcher and repository
        fetcher = YFinanceDataFetcher(config)
        repo = MarketDataRepository(config)
        
        # Fetch data for all tickers
        fetch_results = await fetcher.fetch_all(tickers)
        
        # Separate successful and failed fetches
        successful = [r for r in fetch_results if r.success]
        failed = [r for r in fetch_results if not r.success]
        
        logger.info(f"✅ Successful: {len(successful)}, ❌ Failed: {len(failed)}")
        
        # Log failed tickers
        if failed:
            failed_tickers = [r.ticker for r in failed]
            logger.warning(f"Failed tickers: {', '.join(failed_tickers[:20])}")
            if len(failed_tickers) > 20:
                logger.warning(f"... and {len(failed_tickers) - 20} more")
        
        # Collect all rows for database insertion
        all_rows = []
        for result in successful:
            if result.data:
                all_rows.extend(result.data)
        
        logger.info(f"📦 Total rows to upsert: {len(all_rows)}")
        
        # Upsert to database
        rows_affected = 0
        if all_rows:
            rows_affected = await repo.upsert_market_data(all_rows)
        
        # Close database connection
        await repo.close()
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Record CloudWatch metrics
        metrics.add_metric(name="TickersProcessed", unit=MetricUnit.Count, value=len(tickers))
        metrics.add_metric(name="TickersSuccessful", unit=MetricUnit.Count, value=len(successful))
        metrics.add_metric(name="TickersFailed", unit=MetricUnit.Count, value=len(failed))
        metrics.add_metric(name="RowsUpserted", unit=MetricUnit.Count, value=rows_affected)
        metrics.add_metric(name="ExecutionTime", unit=MetricUnit.Seconds, value=execution_time)
        
        # Build response
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Daily data ingest completed",
                "universe": config.universe_key,
                "tickers_processed": len(tickers),
                "tickers_successful": len(successful),
                "tickers_failed": len(failed),
                "rows_upserted": rows_affected,
                "execution_time_seconds": round(execution_time, 2),
                "failed_tickers": [r.ticker for r in failed[:50]]  # First 50 failures
            })
        }
        
        logger.info(f"✅ Ingest completed in {execution_time:.2f}s")
        return response
        
    except Exception as e:
        logger.exception(f"❌ Fatal error: {e}")
        
        metrics.add_metric(name="FatalErrors", unit=MetricUnit.Count, value=1)
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Daily data ingest failed",
                "error": str(e)
            })
        }

def handler(event: Dict, context) -> Dict:
    """
    Lambda handler entry point (sync wrapper for async handler).
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Response dict
    """
    # Run async handler in event loop
    return asyncio.run(handler_async(event, context))

# ============================================================================
# Local Testing
# ============================================================================

if __name__ == "__main__":
    """
    Local testing script.
    
    Usage:
        export NEON_DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
        python lambda_daily_ingest.py
    """
    # Mock Lambda event and context
    test_event = {
        "universe_key": "SPX500"  # Override universe if needed
    }
    
    class MockContext:
        function_name = "daily-data-ingest-test"
        memory_limit_in_mb = 512
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        aws_request_id = "test-request-id"
    
    # Run handler
    result = handler(test_event, MockContext())
    
    print("\n" + "="*80)
    print("LAMBDA EXECUTION RESULT")
    print("="*80)
    print(json.dumps(result, indent=2))
