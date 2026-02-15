"""
Fetch Gold Price Data from Tiingo
==================================
Fetches GLD (Gold ETF) as a proxy for gold prices using Tiingo API
"""

from tiingo import TiingoClient
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*80)
print("🥇 FETCHING GOLD PRICE DATA FROM TIINGO")
print("="*80)

# Initialize Tiingo client
config = {
    'api_key': 'a49dba6e5f76ba7414cc23aba45fa93f435ad2d5'
}
client = TiingoClient(config)

# Fetch GLD (Gold ETF) as proxy for gold prices
ticker = 'GLD'
start_date = '2005-01-01'
end_date = datetime.now().strftime('%Y-%m-%d')

print(f"\n📊 Fetching {ticker} from Tiingo...")
print(f"   Date range: {start_date} to {end_date}")

try:
    historical_prices = client.get_dataframe(
        ticker,
        startDate=start_date,
        endDate=end_date,
        frequency='daily'
    )
    
    if not historical_prices.empty:
        print(f"\n✅ SUCCESS!")
        print(f"   Rows: {len(historical_prices)}")
        print(f"   Columns: {', '.join(historical_prices.columns)}")
        print(f"   Start: {historical_prices.index[0]}")
        print(f"   End: {historical_prices.index[-1]}")
        
        years = (historical_prices.index[-1] - historical_prices.index[0]).days / 365.25
        print(f"   Years: {years:.1f}")
        
        # Show sample data
        print(f"\n📈 Sample data (last 5 days):")
        print(historical_prices[['adjClose', 'adjVolume']].tail())
        
        # Save to cache
        cache_dir = Path('cache')
        cache_dir.mkdir(exist_ok=True)
        output_file = cache_dir / 'gold_tiingo_20yr.parquet'
        historical_prices.to_parquet(output_file)
        
        print(f"\n💾 Saved to: {output_file}")
        print(f"   Size: {output_file.stat().st_size / 1024:.2f} KB")
        
    else:
        print("\n❌ No data returned from Tiingo")
        
except Exception as e:
    print(f"\n❌ Error: {str(e)}")

print("\n" + "="*80)
print("✅ GOLD DATA FETCH COMPLETE")
print("="*80)
