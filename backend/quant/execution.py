"""
Execution Cost Models
=====================
Hybrid transaction cost estimation for Australian and US equities.

2025 Standard Implementation:
- ASX (.AX): Fixed $3.00 AUD broker fee (Stake.com)
- US Equities: Almgren-Chriss Market Impact + Commission
"""

import numpy as np


def calculate_transaction_cost(
    ticker: str,
    shares: float, 
    price: float, 
    daily_vol: float = 0.02, 
    daily_volume: float = 1_000_000, 
    regime_vol_multiplier: float = 1.0,
    us_commission_per_share: float = 0.005
) -> float:
    """
    Hybrid Transaction Cost Model (2025 Standard).
    
    Automatically routes between cost models based on ticker suffix:
    1. ASX (.AX): Fixed broker fee ($3.00 AUD)
    2. US/Global: Almgren-Chriss Market Impact + Commission
    
    Args:
        ticker: Asset ticker symbol (e.g., 'AAPL', 'BHP.AX')
        shares: Number of shares to trade
        price: Current price per share
        daily_vol: Daily volatility as decimal (default: 0.02 = 2%)
        daily_volume: Average daily trading volume in shares
        regime_vol_multiplier: Stress testing multiplier (default: 1.0)
        us_commission_per_share: US commission per share (default: $0.005)
        
    Returns:
        float: Total execution cost in local currency
    """
    
    # --- LOGIC BRANCH 1: ASX Fixed Fee ---
    if ticker.endswith('.AX'):
        return 3.00  # $3.00 AUD flat fee

    # --- LOGIC BRANCH 2: US Equities (Almgren-Chriss) ---
    if daily_volume == 0: 
        # Penalty for illiquid stocks (1% of trade value)
        return abs(shares) * price * 0.01

    # Almgren-Chriss Constants (calibrated for US equities)
    ETA = 0.142   # Temporary Impact coefficient
    BETA = 0.6    # Square Root Law exponent
    
    # Participation Rate (what % of daily volume is our trade)
    pct_adv = abs(shares) / daily_volume
    
    # Regime Adjustment for stress testing
    sigma = daily_vol * regime_vol_multiplier
    
    # Impact Cost ($ per share)
    # Market impact follows square root law: impact ∝ σ × (Q/V)^β
    impact_per_share = sigma * price * ETA * (pct_adv ** BETA)
    
    # Total costs
    total_impact = impact_per_share * abs(shares)
    explicit_commission = abs(shares) * us_commission_per_share
    
    return total_impact + explicit_commission


def calculate_portfolio_rebalance_cost(
    old_weights: dict,
    new_weights: dict,
    portfolio_value: float,
    prices: dict,
    daily_volumes: dict = None,
    daily_vols: dict = None
) -> float:
    """
    Calculate total cost of rebalancing a portfolio.
    
    Args:
        old_weights: Dict of {ticker: weight} for current portfolio
        new_weights: Dict of {ticker: weight} for target portfolio
        portfolio_value: Total portfolio value
        prices: Dict of {ticker: price}
        daily_volumes: Dict of {ticker: volume} (optional)
        daily_vols: Dict of {ticker: volatility} (optional)
        
    Returns:
        float: Total rebalancing cost
    """
    if daily_volumes is None:
        daily_volumes = {}
    if daily_vols is None:
        daily_vols = {}
    
    total_cost = 0.0
    all_tickers = set(old_weights.keys()) | set(new_weights.keys())
    
    for ticker in all_tickers:
        old_w = old_weights.get(ticker, 0.0)
        new_w = new_weights.get(ticker, 0.0)
        weight_change = abs(new_w - old_w)
        
        if weight_change < 1e-6:
            continue
            
        trade_value = weight_change * portfolio_value
        price = prices.get(ticker, 100.0)
        shares = trade_value / price
        
        cost = calculate_transaction_cost(
            ticker=ticker,
            shares=shares,
            price=price,
            daily_vol=daily_vols.get(ticker, 0.02),
            daily_volume=daily_volumes.get(ticker, 1_000_000)
        )
        
        total_cost += cost
    
    return total_cost


# Backward compatibility alias
def almgren_chriss_cost(
    shares: float, 
    price: float, 
    daily_vol: float, 
    daily_volume: float, 
    regime_vol_multiplier: float = 1.0
) -> float:
    """
    Legacy function - use calculate_transaction_cost instead.
    
    Kept for backward compatibility with existing code.
    """
    return calculate_transaction_cost(
        ticker="US_EQUITY",  # Assumes US equity
        shares=shares,
        price=price,
        daily_vol=daily_vol,
        daily_volume=daily_volume,
        regime_vol_multiplier=regime_vol_multiplier
    )
