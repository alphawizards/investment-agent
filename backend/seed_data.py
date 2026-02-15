"""
Seed Data Script
================
Populate database with sample trade data for dashboard testing.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import random

from backend.database.connection import SessionLocal, init_db
from backend.database.models import Trade, TradeStatus, TradeDirection


def generate_sample_trades(num_trades: int = 100) -> list:
    """Generate sample trade data."""
    
    tickers = [
        ('SPY', 'S&P 500 ETF', 'US_EQUITY'),
        ('QQQ', 'Nasdaq 100 ETF', 'US_TECH'),
        ('TLT', 'US Long Treasuries', 'US_BONDS'),
        ('GLD', 'Gold ETF', 'COMMODITIES'),
        ('IVV.AX', 'iShares S&P 500', 'AU_EQUITY'),
        ('VGS.AX', 'Vanguard Int Shares', 'AU_EQUITY'),
        ('VAS.AX', 'Vanguard AU Shares', 'AU_EQUITY'),
        ('VAF.AX', 'Vanguard AU Bonds', 'AU_BONDS'),
    ]
    
    strategies = ['dual_momentum', 'momentum', 'hrp']
    
    trades = []
    base_date = datetime.now() - timedelta(days=365)
    
    for i in range(num_trades):
        ticker_info = random.choice(tickers)
        ticker, name, asset_class = ticker_info
        
        # Generate entry date
        entry_date = base_date + timedelta(days=random.randint(0, 350))
        
        # Random prices
        if 'BOND' in asset_class:
            base_price = random.uniform(80, 120)
        elif 'GOLD' in ticker or 'COMMODITIES' in asset_class:
            base_price = random.uniform(150, 250)
        else:
            base_price = random.uniform(300, 500)
        
        entry_price = round(base_price * random.uniform(0.95, 1.05), 2)
        
        # Determine if trade is closed
        is_closed = random.random() > 0.15  # 85% closed
        
        # Exit price with some randomness
        if is_closed:
            # Slight positive bias (60% winning)
            if random.random() > 0.4:
                exit_multiplier = random.uniform(1.01, 1.15)
            else:
                exit_multiplier = random.uniform(0.85, 0.99)
            exit_price = round(entry_price * exit_multiplier, 2)
            exit_date = entry_date + timedelta(days=random.randint(5, 60))
            status = TradeStatus.CLOSED
        else:
            exit_price = None
            exit_date = None
            status = TradeStatus.OPEN
        
        quantity = random.randint(5, 50)
        direction = TradeDirection.BUY  # Mostly long positions
        
        # Calculate P&L
        pnl = None
        pnl_percent = None
        if is_closed and exit_price:
            pnl = round((exit_price - entry_price) * quantity - 3.0, 2)  # $3 commission
            pnl_percent = round(((exit_price - entry_price) / entry_price) * 100, 2)
        
        trade = Trade(
            trade_id=f"TRD-{entry_date.strftime('%Y%m%d')}-{i+1:04d}",
            ticker=ticker,
            asset_name=name,
            asset_class=asset_class,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            commission=3.0,
            currency='AUD',
            entry_date=entry_date,
            exit_date=exit_date,
            pnl=pnl,
            pnl_percent=pnl_percent,
            strategy_name=random.choice(strategies),
            signal_score=round(random.uniform(0.5, 1.0), 3),
            status=status,
            notes=f"Auto-generated trade #{i+1}"
        )
        
        trades.append(trade)
    
    return trades


def seed_database():
    """Seed the database with sample trades."""
    print("🌱 Seeding database with sample trades...")
    
    # Initialize database
    init_db()
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing = db.query(Trade).count()
        if existing > 0:
            print(f"⚠️  Database already has {existing} trades. Skipping seed.")
            return
        
        # Generate and insert trades
        trades = generate_sample_trades(100)
        db.add_all(trades)
        db.commit()
        
        print(f"✅ Successfully seeded {len(trades)} trades")
        
        # Print summary
        open_count = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).count()
        closed_count = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED).count()
        
        print(f"   - Open trades: {open_count}")
        print(f"   - Closed trades: {closed_count}")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
