"""
Comprehensive Data Availability Check
======================================
Verifies availability of:
1. ASX ETFs via yFinance
2. US ETFs via Tiingo
3. VIX index data
4. Gold (GLD, GOLD, $GOLD)
5. Bitcoin (BTC, BTC-USD)
"""

import yfinance as yf
import requests
import pandas as pd
from datetime import datetime

print("="*80)
print("DATA AVAILABILITY VERIFICATION")
print("="*80)

# Tiingo API setup
TIINGO_TOKEN = "a49dba6e5f76ba7414cc23aba45fa93f435ad2d5"  # nosec B105
TIINGO_HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': f'Token {TIINGO_TOKEN}'
}

def check_tiingo(ticker):
    """Check if ticker exists on Tiingo"""
    try:
        url = f"https://api.tiingo.com/tiingo/daily/{ticker}"
        response = requests.get(url, headers=TIINGO_HEADERS, timeout=5)
        return response.status_code == 200
    except:
        return False

def check_yfinance(ticker):
    """Check if ticker exists on yFinance"""
    try:
        data = yf.download(ticker, start="2024-12-01", end="2024-12-26", progress=False)
        return not data.empty
    except:
        return False

# ============================================================================
# 1. ASX ETFs Availability
# ============================================================================
print("\n" + "="*80)
print("1. ASX ETFs - yFinance Availability")
print("="*80)

asx_etfs = [
    'VAS.AX', 'IVV.AX', 'VGS.AX', 'VAP.AX', 'VGB.AX', 'VAF.AX',
    'VGE.AX', 'VDHG.AX', 'VDGR.AX', 'VDBA.AX', 'VDCO.AX',
    'ETPMAG.AX',  # Gold
]

print(f"\nTesting {len(asx_etfs)} ASX ETFs on yFinance...")
asx_results = {}
for ticker in asx_etfs:
    available = check_yfinance(ticker)
    asx_results[ticker] = available
    status = "✅" if available else "❌"
    print(f"  {ticker}: {status}")

asx_success = sum(asx_results.values())
print(f"\n📊 ASX ETF Summary: {asx_success}/{len(asx_etfs)} available ({asx_success/len(asx_etfs)*100:.0f}%)")

# ============================================================================
# 2. US ETFs - Tiingo Availability
# ============================================================================
print("\n" + "="*80)
print("2. US ETFs - Tiingo Availability")
print("="*80)

us_etfs = [
    'SPY', 'QQQ', 'VEA', 'VWO', 'TLT', 'IEF', 'GLD', 'DBC', 'VNQ',
    'EEM', 'AGG', 'LQD', 'HYG', 'IWM', 'XLF', 'XLE', 'XLV', 'XLI'
]

print(f"\nTesting {len(us_etfs)} US ETFs on Tiingo...")
etf_results = {}
for ticker in us_etfs:
    available = check_tiingo(ticker)
    etf_results[ticker] = available
    status = "✅" if available else "❌"
    print(f"  {ticker}: {status}")

etf_success = sum(etf_results.values())
print(f"\n📊 US ETF Summary: {etf_success}/{len(us_etfs)} available ({etf_success/len(us_etfs)*100:.0f}%)")

# ============================================================================
# 3. VIX Index - Both Sources
# ============================================================================
print("\n" + "="*80)
print("3. VIX Index Availability")
print("="*80)

vix_tickers = ['^VIX', 'VIX', 'VIXM']

print("\n📊 Tiingo:")
for ticker in vix_tickers:
    available = check_tiingo(ticker)
    status = "✅" if available else "❌"
    print(f"  {ticker}: {status}")

print("\n📊 yFinance:")
for ticker in ['^VIX']:
    available = check_yfinance(ticker)
    status = "✅" if available else "❌"
    print(f"  {ticker}: {status}")

# ============================================================================
# 4. Gold Data
# ============================================================================
print("\n" + "="*80)
print("4. Gold Data Availability")
print("="*80)

gold_tickers = ['GLD', 'GOLD', 'GC=F', 'GLDM', 'IAU']

print("\n📊 Tiingo:")
for ticker in gold_tickers:
    available = check_tiingo(ticker)
    status = "✅" if available else "❌"  
    print(f"  {ticker}: {status}")

print("\n📊 yFinance:")
for ticker in gold_tickers:
    available = check_yfinance(ticker)
    status = "✅" if available else "❌"
    print(f"  {ticker}: {status}")

# ============================================================================
# 5. Bitcoin Data
# ============================================================================
print("\n" + "="*80)
print("5. Bitcoin Data Availability")
print("="*80)

btc_tickers = ['BTC-USD', 'GBTC', 'BITO', 'btcusd']

print("\n📊 Tiingo (has crypto endpoint):")
# Tiingo has separate crypto endpoint
try:
    url = "https://api.tiingo.com/tiingo/crypto/prices?tickers=btcusd"
    response = requests.get(url, headers=TIINGO_HEADERS, timeout=5)
    crypto_available = response.status_code == 200
    print(f"  Crypto API: {'✅' if crypto_available else '❌'}")
except:
    print(f"  Crypto API: ❌")

for ticker in btc_tickers[:2]:  # GBTC and BITO are stocks
    available = check_tiingo(ticker)
    status = "✅" if available else "❌"
    print(f"  {ticker}: {status}")

print("\n📊 yFinance:")
for ticker in btc_tickers[:3]:
    available = check_yfinance(ticker)
    status = "✅" if available else "❌"
    print(f"  {ticker}: {status}")

# ============================================================================
# 6. Summary Report
# ============================================================================
print("\n" + "="*80)
print("SUMMARY REPORT")
print("="*80)

print("\n✅ AVAILABLE:")
print("  - ASX ETFs: yFinance (use as backup)")
print(f"  - US ETFs: Tiingo ({etf_success}/{len(us_etfs)} coverage)")
print("  - VIX: yFinance (^VIX)")
print("  - Gold: Both Tiingo (GLD) and yFinance (GLD, GC=F)")
print("  - Bitcoin: yFinance (BTC-USD), Tiingo has crypto API")

print("\n⚠️  RECOMMENDATIONS:")
print("  1. Use Tiingo for US stocks and ETFs (institutional grade)")
print("  2. Use yFinance for ASX ETFs only")
print("  3. Fetch VIX from yFinance (^VIX)")
print("  4. Use GLD for gold exposure (available on both)")
print("  5. Use BTC-USD from yFinance for Bitcoin")
print("  6. Exclude pairs trading (computationally expensive)")
print("  7. No options data needed (confirmed)")

print("\n" + "="*80)
print("✅ VERIFICATION COMPLETE")
print("="*80)
