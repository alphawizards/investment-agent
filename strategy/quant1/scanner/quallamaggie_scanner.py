"""
Quallamaggie Stock Scanner
==========================
Scans a large universe of stocks using yfinance and applies
Quallamaggie filter criteria to find momentum breakout candidates.

Outputs results as JSON for the dashboard frontend.
"""

import pandas as pd
import numpy as np
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("Error: yfinance required. Install with: pip install yfinance")

try:
    from scipy.stats import linregress
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ============== STOCK UNIVERSE ==============

# S&P 500 stocks (representative sample - full list would be 500+)
SP500_TICKERS = [
    # Technology
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'META', 'AVGO', 'ORCL', 'CSCO', 'CRM',
    'ADBE', 'ACN', 'IBM', 'INTC', 'AMD', 'TXN', 'QCOM', 'NOW', 'INTU', 'AMAT',
    'MU', 'LRCX', 'ADI', 'KLAC', 'SNPS', 'CDNS', 'PANW', 'CRWD', 'FTNT', 'ZS',
    # Communication Services
    'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR', 'EA', 'TTWO', 'WBD',
    # Consumer Discretionary
    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'BKNG', 'MAR',
    'GM', 'F', 'ORLY', 'AZO', 'CMG', 'DHI', 'LEN', 'ROST', 'YUM', 'DG',
    # Consumer Staples
    'PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'CL', 'MDLZ', 'KHC',
    'STZ', 'GIS', 'K', 'HSY', 'KMB', 'TAP', 'TSN', 'CAG', 'SJM', 'CPB',
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY',
    'AMGN', 'GILD', 'CVS', 'CI', 'ELV', 'ISRG', 'VRTX', 'REGN', 'MDT', 'SYK',
    'BSX', 'BDX', 'ZBH', 'HCA', 'IQV', 'DXCM', 'MRNA', 'BIIB', 'ILMN', 'IDXX',
    # Financials
    'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'AXP', 'SPGI', 'BLK',
    'C', 'SCHW', 'PNC', 'USB', 'TFC', 'COF', 'CME', 'ICE', 'CB', 'AON',
    # Industrials
    'CAT', 'DE', 'UNP', 'HON', 'UPS', 'RTX', 'BA', 'LMT', 'GE', 'MMM',
    'ETN', 'ITW', 'PH', 'EMR', 'FDX', 'WM', 'CSX', 'NSC', 'JCI', 'ROK',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'PXD',
    'HES', 'DVN', 'HAL', 'BKR', 'FANG', 'WMB', 'KMI', 'OKE', 'TRGP', 'LNG',
    # Materials
    'LIN', 'APD', 'SHW', 'FCX', 'NEM', 'NUE', 'ECL', 'VMC', 'MLM', 'DOW',
    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'PEG',
    # Real Estate
    'PLD', 'AMT', 'EQIX', 'CCI', 'PSA', 'O', 'WELL', 'SPG', 'DLR', 'AVB',
]

# NASDAQ 100 additions (not in S&P 500)
NASDAQ_ADDITIONS = [
    'SMCI', 'ARM', 'MELI', 'WDAY', 'TEAM', 'DDOG', 'ZM', 'OKTA', 'MDB', 'NET',
    'SNOW', 'DASH', 'COIN', 'MSTR', 'PLTR', 'ABNB', 'RBLX', 'ROKU', 'LCID', 'RIVN',
    'PYPL', 'SQ', 'SHOP', 'UBER', 'LYFT', 'PINS', 'SNAP', 'TWLO', 'DBX', 'ZI',
    'DOCU', 'HUBS', 'PAYC', 'TTD', 'SMAR', 'VEEV', 'SPLK', 'ANSS', 'PTC', 'MANH',
]

# Popular momentum/growth stocks
MOMENTUM_ADDITIONS = [
    'IONQ', 'RGTI', 'QBTS', 'SOUN', 'AI', 'PATH', 'U', 'APP', 'CELH', 'DUOL',
    'AFRM', 'SOFI', 'HOOD', 'UPST', 'BILL', 'TOST', 'CAVA', 'BROS', 'DKNG', 'PENN',
]

# Full universe
FULL_UNIVERSE = list(set(SP500_TICKERS + NASDAQ_ADDITIONS + MOMENTUM_ADDITIONS))


# ============== SCANNER CLASS ==============

class QuallamaggieScanner:
    """
    Scans stocks for Quallamaggie momentum breakout setups.
    
    Filter Criteria:
    1. Liquidity: Price > $5, 20D Avg Dollar Volume > $20M
    2. Momentum: 3M Return >= 30%, 1M Return >= 10%, RS > SPY
    3. Trend: Perfect SMA alignment, above SMA200, positive SMA50 slope
    4. Consolidation: Price >= 85% of 126D high, ATR contraction
    """
    
    def __init__(
        self,
        min_price: float = 5.0,
        min_dollar_volume: float = 20_000_000,
        momentum_3m_threshold: float = 0.30,
        momentum_1m_threshold: float = 0.10,
        htf_threshold: float = 0.85,
        lookback_days: int = 200
    ):
        self.min_price = min_price
        self.min_dollar_volume = min_dollar_volume
        self.momentum_3m_threshold = momentum_3m_threshold
        self.momentum_1m_threshold = momentum_1m_threshold
        self.htf_threshold = htf_threshold
        self.lookback_days = lookback_days
        
        self.results = []
        self.scan_stats = {}
    
    def fetch_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for all tickers."""
        if not HAS_YFINANCE:
            raise ImportError("yfinance required")
        
        print(f"Fetching data for {len(tickers)} tickers...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days + 50)
        
        data = {}
        
        # Batch download for efficiency
        try:
            df = yf.download(
                tickers,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                progress=True,
                auto_adjust=False,
                threads=True
            )
            
            if df.empty:
                print("Warning: No data returned from batch download")
                return data
            
            # Parse multi-index columns
            for ticker in tickers:
                try:
                    if isinstance(df.columns, pd.MultiIndex):
                        ticker_df = df.xs(ticker, level=1, axis=1).copy()
                    else:
                        ticker_df = df.copy()
                    
                    if len(ticker_df) > 100:  # Minimum data requirement
                        data[ticker] = ticker_df
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"Batch download failed: {e}")
            print("Falling back to individual downloads...")
            
            for ticker in tickers:
                try:
                    t = yf.Ticker(ticker)
                    hist = t.history(start=start_date, end=end_date)
                    if len(hist) > 100:
                        data[ticker] = hist
                except:
                    continue
        
        print(f"Successfully fetched data for {len(data)} tickers")
        return data
    
    def fetch_spy_data(self) -> pd.Series:
        """Fetch SPY data for relative strength calculation."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 50)
            spy = yf.download('SPY', start=start_date, end=end_date, progress=False)
            
            if isinstance(spy.columns, pd.MultiIndex):
                return spy['Adj Close'].squeeze()
            return spy['Adj Close'].squeeze() if 'Adj Close' in spy.columns else spy['Close'].squeeze()
        except:
            return None
    
    def scan(self, tickers: List[str] = None) -> List[Dict]:
        """
        Run the full Quallamaggie scan.
        
        Returns:
            List of dicts with scan results for stocks passing all filters
        """
        tickers = tickers or FULL_UNIVERSE
        
        print("=" * 60)
        print("QUALLAMAGGIE MOMENTUM SCANNER")
        print("=" * 60)
        print(f"Universe: {len(tickers)} stocks")
        print(f"Filters: Price>${self.min_price}, $Vol>{self.min_dollar_volume/1e6}M, "
              f"3M>{self.momentum_3m_threshold*100}%, 1M>{self.momentum_1m_threshold*100}%")
        print("=" * 60)
        
        # Fetch all data
        data = self.fetch_data(tickers)
        spy_data = self.fetch_spy_data()
        
        # Calculate SPY 3M return for relative strength
        spy_3m_ret = None
        if spy_data is not None and len(spy_data) > 63:
            spy_3m_ret = (spy_data.iloc[-1] / spy_data.iloc[-64]) - 1
            print(f"SPY 3M Return: {spy_3m_ret*100:.1f}%")
        
        self.results = []
        stats = {
            'total_scanned': len(data),
            'passed_liquidity': 0,
            'passed_momentum': 0,
            'passed_trend': 0,
            'passed_consolidation': 0,
            'final_candidates': 0
        }
        
        for ticker, df in data.items():
            try:
                result = self._analyze_stock(ticker, df, spy_3m_ret)
                
                if result is None:
                    continue
                
                # Track filter progression
                if result.get('passed_liquidity'):
                    stats['passed_liquidity'] += 1
                if result.get('passed_momentum'):
                    stats['passed_momentum'] += 1
                if result.get('passed_trend'):
                    stats['passed_trend'] += 1
                if result.get('passed_consolidation'):
                    stats['passed_consolidation'] += 1
                
                # Only include stocks passing ALL filters
                if result.get('passed_all'):
                    stats['final_candidates'] += 1
                    self.results.append(result)
                    
            except Exception as e:
                continue
        
        # Sort by 3M momentum (descending)
        self.results.sort(key=lambda x: x.get('ret_3m', 0), reverse=True)
        
        self.scan_stats = stats
        
        # Print summary
        print("\n" + "=" * 60)
        print("SCAN SUMMARY")
        print("=" * 60)
        print(f"Total Scanned: {stats['total_scanned']}")
        print(f"Passed Liquidity: {stats['passed_liquidity']}")
        print(f"Passed Momentum: {stats['passed_momentum']}")
        print(f"Passed Trend: {stats['passed_trend']}")
        print(f"Passed Consolidation: {stats['passed_consolidation']}")
        print(f"FINAL CANDIDATES: {stats['final_candidates']}")
        print("=" * 60)
        
        return self.results
    
    def _analyze_stock(self, ticker: str, df: pd.DataFrame, spy_3m_ret: float = None) -> Optional[Dict]:
        """Analyze a single stock against all filter criteria."""
        
        # Get price columns
        close = df['Adj Close'] if 'Adj Close' in df.columns else df['Close']
        raw_close = df['Close'] if 'Close' in df.columns else close
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        if len(close) < 130:  # Need enough data for all indicators
            return None
        
        # Current values
        current_price = float(raw_close.iloc[-1])
        current_adj_close = float(close.iloc[-1])
        
        result = {
            'ticker': ticker,
            'price': current_price,
            'passed_liquidity': False,
            'passed_momentum': False,
            'passed_trend': False,
            'passed_consolidation': False,
            'passed_all': False
        }
        
        # ========== LIQUIDITY FILTERS ==========
        # Price > $5
        if current_price <= self.min_price:
            return result
        
        # 20-day avg dollar volume > $20M
        dollar_volume = (raw_close * volume).rolling(20).mean()
        avg_dollar_vol = float(dollar_volume.iloc[-1])
        
        if avg_dollar_vol < self.min_dollar_volume:
            return result
        
        result['passed_liquidity'] = True
        result['dollar_volume'] = avg_dollar_vol
        
        # ========== MOMENTUM FILTERS ==========
        # 3-month return >= 30%
        if len(close) < 64:
            return result
        ret_3m = (close.iloc[-1] / close.iloc[-64]) - 1
        
        if ret_3m < self.momentum_3m_threshold:
            return result
        
        # 1-month return >= 10%
        if len(close) < 22:
            return result
        ret_1m = (close.iloc[-1] / close.iloc[-22]) - 1
        
        if ret_1m < self.momentum_1m_threshold:
            return result
        
        # Relative Strength vs SPY
        rs_vs_spy = ret_3m - (spy_3m_ret if spy_3m_ret else 0.08)
        if spy_3m_ret is not None and ret_3m <= spy_3m_ret:
            return result
        
        result['passed_momentum'] = True
        result['ret_3m'] = float(ret_3m)
        result['ret_1m'] = float(ret_1m)
        result['rs_vs_spy'] = float(rs_vs_spy)
        
        # ========== TREND FILTERS ==========
        # Calculate SMAs
        sma_10 = close.rolling(10).mean()
        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        sma_200 = close.rolling(200).mean()
        
        # Perfect alignment: Close > SMA10 > SMA20 > SMA50
        perfect_align = (
            current_adj_close > sma_10.iloc[-1] > sma_20.iloc[-1] > sma_50.iloc[-1]
        )
        
        if not perfect_align:
            return result
        
        # Above 200 SMA
        if current_adj_close <= sma_200.iloc[-1]:
            return result
        
        # Positive SMA50 slope
        if HAS_SCIPY and len(sma_50) >= 10:
            sma50_recent = sma_50.iloc[-10:].dropna()
            if len(sma50_recent) >= 10:
                slope, _, _, _, _ = linregress(range(len(sma50_recent)), sma50_recent.values)
                if slope <= 0:
                    return result
        
        result['passed_trend'] = True
        result['sma_alignment'] = True
        
        # ========== CONSOLIDATION FILTERS ==========
        # High Tight Flag: Price >= 85% of 126-day high
        high_126d = high.rolling(126).max().iloc[-1]
        pct_from_high = current_adj_close / high_126d
        
        if pct_from_high < self.htf_threshold:
            return result
        
        # ATR contraction: Current ATR(14) < 20-day avg ATR
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr_14 = tr.rolling(14).mean()
        atr_avg = atr_14.rolling(20).mean()
        
        atr_contracting = atr_14.iloc[-1] < atr_avg.iloc[-1]
        
        if not atr_contracting:
            return result
        
        result['passed_consolidation'] = True
        result['pct_from_high'] = float(pct_from_high)
        result['atr_contraction'] = True
        
        # ========== PASSED ALL FILTERS ==========
        result['passed_all'] = True
        result['signal'] = 'STRONG' if ret_3m >= 0.40 and pct_from_high >= 0.90 else 'WATCH'
        
        return result
    
    def to_json(self, filepath: str = None) -> str:
        """Export results to JSON."""
        output = {
            'scan_time': datetime.now().isoformat(),
            'stats': self.scan_stats,
            'candidates': self.results
        }
        
        json_str = json.dumps(output, indent=2)
        
        if filepath:
            Path(filepath).write_text(json_str)
            print(f"Results saved to {filepath}")
        
        return json_str
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to DataFrame."""
        if not self.results:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        
        # Format columns
        if 'ret_3m' in df.columns:
            df['ret_3m_pct'] = (df['ret_3m'] * 100).round(1).astype(str) + '%'
        if 'ret_1m' in df.columns:
            df['ret_1m_pct'] = (df['ret_1m'] * 100).round(1).astype(str) + '%'
        if 'pct_from_high' in df.columns:
            df['pct_from_high_fmt'] = (df['pct_from_high'] * 100).round(1).astype(str) + '%'
        
        return df


def run_scanner(output_path: str = None) -> List[Dict]:
    """Run the full Quallamaggie scan and optionally save results."""
    scanner = QuallamaggieScanner()
    results = scanner.scan(FULL_UNIVERSE)
    
    # Print top candidates
    if results:
        print("\n" + "=" * 60)
        print("TOP CANDIDATES")
        print("=" * 60)
        for i, r in enumerate(results[:15], 1):
            print(f"{i:2}. {r['ticker']:6} | Price: ${r['price']:8.2f} | "
                  f"3M: {r['ret_3m']*100:5.1f}% | 1M: {r['ret_1m']*100:5.1f}% | "
                  f"Signal: {r['signal']}")
    
    # Save results
    if output_path is None:
        output_path = 'dashboard/scan_results.json'
    
    scanner.to_json(output_path)
    
    return results


if __name__ == "__main__":
    results = run_scanner()
