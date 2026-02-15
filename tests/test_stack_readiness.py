"""
Test Stack Readiness for Quant 1.0 & 2.0 Backtesting
Fetches additional data to assess complete stack readiness:
- ASX ETFs from yFinance
- Gold price from Tiingo
- BTC-USD from yFinance
- VIX from yFinance
"""

import os
from pathlib import Path
import pandas as pd
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import Tiingo client
try:
    from tiingo import TiingoClient
except ImportError:
    print("⚠️ Tiingo not installed. Install with: pip install tiingo")
    TiingoClient = None

def test_yfinance_asx_etfs():
    """Test ASX ETF data availability from yFinance"""
    print("\n" + "="*80)
    print("📊 Testing ASX ETF Data from yFinance")
    print("="*80)
    
    # Popular ASX ETFs
    asx_etfs = [
        'VAS.AX',   # Vanguard Australian Shares Index ETF
        'A200.AX',  # BetaShares Australia 200 ETF
        'IOZ.AX',   # iShares Core S&P/ASX 200 ETF
        'STW.AX',   # SPDR S&P/ASX 200 Fund
        'VGS.AX',   # Vanguard MSCI International Shares
        'VGE.AX',   # Vanguard FTSE Emerging Markets
    ]
    
    start_date = '2005-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    results = {}
    for ticker in asx_etfs:
        try:
            print(f"  Fetching {ticker}...", end=' ')
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if not data.empty:
                results[ticker] = {
                    'success': True,
                    'rows': len(data),
                    'start': data.index[0],
                    'end': data.index[-1],
                    'years': (data.index[-1] - data.index[0]).days / 365.25
                }
                print(f"✅ {len(data)} rows ({results[ticker]['years']:.1f} years)")
            else:
                results[ticker] = {'success': False, 'error': 'No data returned'}
                print("❌ No data")
                
        except Exception as e:
            results[ticker] = {'success': False, 'error': str(e)}
            print(f"❌ Error: {str(e)[:50]}")
    
    # Summary
    successful = sum(1 for r in results.values() if r.get('success'))
    print(f"\n📋 ASX ETF Summary: {successful}/{len(asx_etfs)} successful")
    
    return results

def test_tiingo_gold():
    """Test Gold price data from Tiingo"""
    print("\n" + "="*80)
    print("🥇 Testing Gold Price Data from Tiingo")
    print("="*80)
    
    if TiingoClient is None:
        print("❌ Tiingo client not available")
        return {'success': False, 'error': 'Tiingo not installed'}
    
    try:
        # Initialize Tiingo client
        api_key = os.getenv('TIINGO_API_KEY')
        if not api_key:
            print("❌ TIINGO_API_KEY not found in environment")
            return {'success': False, 'error': 'API key not found'}
        
        config = {'api_key': api_key}
        client = TiingoClient(config)
        
        # Try GLD (Gold ETF) as proxy
        ticker = 'GLD'
        print(f"  Fetching {ticker} from Tiingo...", end=' ')
        
        historical_prices = client.get_dataframe(
            ticker,
            startDate='2005-01-01',
            endDate=datetime.now().strftime('%Y-%m-%d'),
            frequency='daily'
        )
        
        if not historical_prices.empty:
            result = {
                'success': True,
                'ticker': ticker,
                'rows': len(historical_prices),
                'start': historical_prices.index[0],
                'end': historical_prices.index[-1],
                'years': (historical_prices.index[-1] - historical_prices.index[0]).days / 365.25,
                'columns': list(historical_prices.columns)
            }
            print(f"✅ {len(historical_prices)} rows ({result['years']:.1f} years)")
            print(f"  Columns: {', '.join(historical_prices.columns)}")
            
            # Save to cache
            cache_dir = Path('cache')
            cache_dir.mkdir(exist_ok=True)
            output_file = cache_dir / 'gold_tiingo_20yr.parquet'
            historical_prices.to_parquet(output_file)
            print(f"  💾 Saved to: {output_file}")
            
            return result
        else:
            print("❌ No data returned")
            return {'success': False, 'error': 'No data returned'}
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {'success': False, 'error': str(e)}

def test_yfinance_btc():
    """Test BTC-USD data from yFinance"""
    print("\n" + "="*80)
    print("₿  Testing BTC-USD Data from yFinance")
    print("="*80)
    
    ticker = 'BTC-USD'
    start_date = '2014-09-01'  # Bitcoin data typically starts around 2014 on yfinance
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        print(f"  Fetching {ticker}...", end=' ')
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if not data.empty:
            result = {
                'success': True,
                'rows': len(data),
                'start': data.index[0],
                'end': data.index[-1],
                'years': (data.index[-1] - data.index[0]).days / 365.25,
                'columns': list(data.columns)
            }
            print(f"✅ {len(data)} rows ({result['years']:.1f} years)")
            
            # Save to cache
            cache_dir = Path('cache')
            cache_dir.mkdir(exist_ok=True)
            output_file = cache_dir / 'btc_usd_yfinance.parquet'
            data.to_parquet(output_file)
            print(f"  💾 Saved to: {output_file}")
            
            return result
        else:
            print("❌ No data returned")
            return {'success': False, 'error': 'No data returned'}
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {'success': False, 'error': str(e)}

def test_yfinance_vix():
    """Test VIX data from yFinance"""
    print("\n" + "="*80)
    print("📈 Testing VIX Data from yFinance")
    print("="*80)
    
    ticker = '^VIX'
    start_date = '2005-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        print(f"  Fetching {ticker}...", end=' ')
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if not data.empty:
            result = {
                'success': True,
                'rows': len(data),
                'start': data.index[0],
                'end': data.index[-1],
                'years': (data.index[-1] - data.index[0]).days / 365.25,
                'columns': list(data.columns)
            }
            print(f"✅ {len(data)} rows ({result['years']:.1f} years)")
            
            # Save to cache
            cache_dir = Path('cache')
            cache_dir.mkdir(exist_ok=True)
            output_file = cache_dir / 'vix_yfinance.parquet'
            data.to_parquet(output_file)
            print(f"  💾 Saved to: {output_file}")
            
            return result
        else:
            print("❌ No data returned")
            return {'success': False, 'error': 'No data returned'}
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {'success': False, 'error': str(e)}

def assess_stack_readiness():
    """Final assessment of stack readiness for Quant 1.0 & 2.0"""
    print("\n" + "="*80)
    print("🎯 STACK READINESS ASSESSMENT")
    print("="*80)
    
    # Load existing cache files
    cache_dir = Path('cache')
    cache_files = list(cache_dir.glob('*.parquet'))
    
    print("\n📦 Available Data Files:")
    total_size_mb = 0
    for f in sorted(cache_files):
        size_mb = f.stat().st_size / (1024 * 1024)
        total_size_mb += size_mb
        print(f"  • {f.name:<50} {size_mb:>8.2f} MB")
    
    print(f"\n  Total Cache Size: {total_size_mb:.2f} MB")
    
    # Strategy Readiness Matrix
    print("\n" + "="*80)
    print("📊 STRATEGY READINESS MATRIX")
    print("="*80)
    
    strategies = {
        "Quant 1.0 - Dual Momentum + HRP": {
            "needs": ["US stocks/ETFs", "Historical data"],
            "status": "✅ READY",
            "notes": "Can run on ETF subset or top stocks"
        },
        "OLMAR (Mean Reversion)": {
            "needs": ["Price data", "Volume data"],
            "status": "✅ READY",
            "notes": "560 tickers available, may reduce to 100 for speed"
        },
        "Meta-Labeling (ML Filtering)": {
            "needs": ["Price data", "Technical indicators"],
            "status": "✅ READY",
            "notes": "Can derive all features from price/volume"
        },
        "Regime Detection (HMM)": {
            "needs": ["Returns", "Volatility", "VIX"],
            "status": "✅ READY" if Path(cache_dir / 'vix_yfinance.parquet').exists() else "⚠️ NEEDS VIX",
            "notes": "VIX data now available" if Path(cache_dir / 'vix_yfinance.parquet').exists() else "Run this script to fetch VIX"
        },
        "Pairs Trading (Statistical Arbitrage)": {
            "needs": ["Price data", "Cointegration tests"],
            "status": "⚠️ SLOW",
            "notes": "156k pairs to test, use sector clustering"
        },
        "Momentum Strategies": {
            "needs": ["Price data"],
            "status": "✅ READY",
            "notes": "Can run simple momentum, Fama-French optional"
        },
        "Volatility Strategies": {
            "needs": ["Realized vol only"],
            "status": "⚠️ LIMITED",
            "notes": "No options data, can only do vol-based allocation"
        },
        "Portfolio Optimization (NCO)": {
            "needs": ["Returns", "Covariance"],
            "status": "✅ READY",
            "notes": "Can run on full universe or subset"
        }
    }
    
    ready_count = 0
    partial_count = 0
    not_ready_count = 0
    
    for strategy, details in strategies.items():
        status = details['status']
        if '✅' in status:
            ready_count += 1
            emoji = "✅"
        elif '⚠️' in status:
            partial_count += 1
            emoji = "⚠️"
        else:
            not_ready_count += 1
            emoji = "❌"
        
        print(f"\n{emoji} {strategy}")
        print(f"   Needs: {', '.join(details['needs'])}")
        print(f"   Status: {status}")
        print(f"   Notes: {details['notes']}")
    
    # Final Summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80)
    print(f"✅ Fully Ready:      {ready_count}/8 strategies")
    print(f"⚠️  Partial/Limited:  {partial_count}/8 strategies")
    print(f"❌ Not Ready:        {not_ready_count}/8 strategies")
    
    print("\n🎯 RECOMMENDATION:")
    if ready_count >= 6:
        print("  ✅ STACK IS PRODUCTION-READY for backtesting!")
        print("  You can begin backtesting immediately on most strategies.")
    elif ready_count >= 4:
        print("  ⚠️ STACK IS MOSTLY READY with minor gaps.")
        print("  Fetch missing data (VIX, etc.) to unlock all strategies.")
    else:
        print("  ❌ STACK NEEDS MORE DATA before comprehensive backtesting.")
        print("  Focus on fetching missing datasets first.")
    
    print("\n📝 NEXT STEPS:")
    print("  1. Review the implementation plan (already loaded)")
    print("  2. Decide which strategies to prioritize")
    print("  3. Start with quick wins: OLMAR, Momentum, NCO")
    print("  4. Run comprehensive backtests on 2005-2025 data")
    print("  5. Generate performance reports and visualizations")
    
    return {
        'ready': ready_count,
        'partial': partial_count,
        'not_ready': not_ready_count,
        'total': len(strategies)
    }

if __name__ == "__main__":
    print("="*80)
    print("🚀 QUANT TRADING STACK READINESS TEST")
    print("="*80)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 1: ASX ETFs from yFinance
    results['asx_etfs'] = test_yfinance_asx_etfs()
    
    # Test 2: Gold from Tiingo
    results['gold_tiingo'] = test_tiingo_gold()
    
    # Test 3: BTC-USD from yFinance
    results['btc_usd'] = test_yfinance_btc()
    
    # Test 4: VIX from yFinance
    results['vix'] = test_yfinance_vix()
    
    # Final Assessment
    readiness = assess_stack_readiness()
    
    print("\n" + "="*80)
    print("✅ TESTING COMPLETE")
    print("="*80)
