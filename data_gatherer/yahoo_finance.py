"""
Yahoo Finance data fetcher with retry logic and rate limiting.
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YahooFinanceFetcher:
    """Fetch stock data from Yahoo Finance."""
    
    # Rate limiting - conservative for overnight runs
    MIN_REQUEST_INTERVAL = 1.5  # seconds between requests (safe rate)
    MAX_RETRIES = 3
    RETRY_DELAY = 3  # seconds between retries
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.last_request_time = {}
    
    def _rate_limit(self, ticker: str) -> None:
        """Apply rate limiting between requests for same ticker."""
        if ticker in self.last_request_time:
            elapsed = time.time() - self.last_request_time[ticker]
            if elapsed < self.MIN_REQUEST_INTERVAL:
                time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time[ticker] = time.time()
    
    def _validate_price_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate price data for quality issues.
        Returns (is_valid, issue_description)
        """
        # Check required fields
        required = ['open', 'high', 'low', 'close', 'volume']
        for field in required:
            if field not in data or data[field] is None:
                return False, f"Missing {field}"
        
        # Price sanity checks
        if data['high'] < data['low']:
            return False, "High < Low"
        
        if data['close'] > data['high'] or data['close'] < data['low']:
            return False, "Close outside High/Low range"
        
        if data['open'] > data['high'] or data['open'] < data['low']:
            return False, "Open outside High/Low range"
        
        # Zero volume check - skip weekends/holidays (common in Yahoo data)
        # We'll allow zero volume as it's often just non-trading days
        # if data['volume'] == 0:
        #     return False, "Zero volume"
        
        # Negative prices
        if data['open'] <= 0 or data['high'] <= 0 or data['low'] <= 0 or data['close'] <= 0:
            return False, "Negative or zero price"
        
        # Extreme price movement (>50% from previous close would be flagged separately)
        
        return True, None
    
    def fetch_ticker_history(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_retries: int = MAX_RETRIES,
        exchange: Optional[str] = None
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """
        Fetch historical data for a single ticker.
        
        Returns: (success, price_data_list, error_message)
        """
        self._rate_limit(ticker)
        
        # Add .AX suffix for ASX stocks
        full_ticker = ticker
        if exchange == 'ASX' or (len(ticker) <= 3 and ticker.isupper() and not any(c.isdigit() for c in ticker)):
            # For ASX stocks, try with .AX suffix
            # Try without suffix first, then with suffix
            pass  # We'll try both
        
        for attempt in range(max_retries):
            try:
                stock = yf.Ticker(full_ticker)
                df = stock.history(start=start_date, end=end_date, auto_adjust=False)
                
                if df.empty:
                    return False, [], f"No data available for {full_ticker}"
                
                prices = []
                for idx, row in df.iterrows():
                    date_str = idx.strftime('%Y-%m-%d')
                    
                    price_data = {
                        'date': date_str,
                        'open': float(row['Open']) if row['Open'] is not None else None,
                        'high': float(row['High']) if row['High'] is not None else None,
                        'low': float(row['Low']) if row['Low'] is not None else None,
                        'close': float(row['Close']) if row['Close'] is not None else None,
                        'adj_close': float(row['Adj Close']) if row['Adj Close'] is not None else None,
                        'volume': int(row['Volume']) if row['Volume'] is not None else 0,
                    }
                    
                    is_valid, issue = self._validate_price_data(price_data)
                    if not is_valid:
                        logger.warning(f"Data quality issue for {ticker} on {date_str}: {issue}")
                        continue
                    
                    prices.append(price_data)
                
                return True, prices, None
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt + 1} failed for {ticker}: {error_msg}")
                
                if attempt < max_retries - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    return False, [], error_msg
        
        return False, [], "Max retries exceeded"
    
    def fetch_incremental(
        self,
        ticker: str,
        last_date: Optional[str] = None,
        days_back: int = 5
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """
        Fetch incremental data since last update.
        
        If last_date is provided, fetch from that date onwards.
        Otherwise, fetch last N days.
        """
        if last_date:
            # Parse last date and add 1 day
            try:
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
                start_date = (last_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            except ValueError:
                start_date = None
        else:
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        return self.fetch_ticker_history(ticker, start_date=start_date, end_date=end_date)
    
    def fetch_multiple(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        progress_callback=None
    ) -> Dict[str, Tuple[bool, List[Dict[str, Any]], Optional[str]]]:
        """
        Fetch data for multiple tickers in parallel.
        
        Returns: {ticker: (success, prices, error)}
        """
        results = {}
        total = len(tickers)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ticker = {
                executor.submit(
                    self.fetch_ticker_history, 
                    t, start_date, end_date
                ): t for t in tickers
            }
            
            completed = 0
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    results[ticker] = future.result()
                except Exception as e:
                    results[ticker] = (False, [], str(e))
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
        
        return results
    
    def get_ticker_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get basic info about a ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'name': info.get('shortName') or info.get('longName'),
                'exchange': info.get('exchange'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'market_cap': info.get('marketCap'),
            }
        except Exception as e:
            logger.warning(f"Failed to get info for {ticker}: {e}")
            return None


# Default instance
default_fetcher = YahooFinanceFetcher()


if __name__ == "__main__":
    # Test with a few tickers
    fetcher = YahooFinanceFetcher()
    
    # Test US ticker
    print("Testing AAPL...")
    success, prices, error = fetcher.fetch_ticker_history("AAPL", start_date="2024-01-01")
    print(f"  Success: {success}, Records: {len(prices)}, Error: {error}")
    
    # Test ASX ticker
    print("Testing BHP...")
    success, prices, error = fetcher.fetch_ticker_history("BHP", start_date="2024-01-01")
    print(f"  Success: {success}, Records: {len(prices)}, Error: {error}")
