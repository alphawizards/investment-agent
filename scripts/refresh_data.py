"""
Unified Data Refresh Script
============================
Master script to update all dashboard data.

Usage:
    python refresh_data.py --all           # Full refresh
    python refresh_data.py --quant1        # Quant 1.0 strategies only
    python refresh_data.py --quant2        # Quant 2.0 strategies only
    python refresh_data.py --scanner       # Quallamaggie scanner only
    python refresh_data.py --prices-only   # Just update price data
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import warnings

warnings.filterwarnings('ignore')

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Output directory for dashboard JSON files
DATA_DIR = PROJECT_ROOT / "dashboard" / "data"
DATA_DIR.mkdir(exist_ok=True)

# Timestamps file
TIMESTAMPS_FILE = DATA_DIR / "timestamps.json"


def log(msg: str, level: str = "INFO"):
    """Print log message with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def load_timestamps() -> Dict:
    """Load existing timestamps."""
    if TIMESTAMPS_FILE.exists():
        with open(TIMESTAMPS_FILE, 'r') as f:
            return json.load(f)
    return {
        "last_updated": None,
        "prices": None,
        "quant1": {},
        "quant2": {},
        "scanner": None
    }


def save_timestamps(ts: Dict):
    """Save timestamps to file."""
    with open(TIMESTAMPS_FILE, 'w') as f:
        json.dump(ts, f, indent=2)
    log(f"Timestamps saved to {TIMESTAMPS_FILE}")


def save_json(filename: str, data: Dict):
    """Save data to JSON file."""
    filepath = DATA_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    log(f"Saved: {filepath}")


# =============================================================================
# PRICE DATA REFRESH
# =============================================================================

def refresh_prices(lookback_days: int = 252, full_refresh: bool = False) -> Optional[Dict]:
    """
    Fetch latest prices for the full universe using FastDataLoader.
    
    Returns:
        Dict with price data or None on failure
    """
    log("Starting price data refresh (Fast Mode)...")
    if full_refresh:
        log("⚠️ Full Refresh detected: Ignoring cache...")
    
    try:
        from strategy.fast_data_loader import FastDataLoader
        from datetime import timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        loader = FastDataLoader(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        # Use fast parallel fetch with caching
        prices_df, returns_df = loader.fetch_universe(full_refresh=full_refresh)
        
        log(f"Loaded {len(prices_df.columns)} assets, {len(prices_df)} days")
        
        # Save summary to JSON
        price_summary = {
            "generated_at": datetime.now().isoformat(),
            "n_assets": len(prices_df.columns),
            "n_days": len(prices_df),
            "date_range": {
                "start": str(prices_df.index[0].date()),
                "end": str(prices_df.index[-1].date())
            },
            "latest_prices": {
                col: float(prices_df[col].iloc[-1].item()) if hasattr(prices_df[col].iloc[-1], 'item') else float(prices_df[col].iloc[-1])
                for col in list(prices_df.columns)[:20]
            }
        }
        
        save_json("price_summary.json", price_summary)
        
        return {
            "prices": prices_df,
            "returns": returns_df,
            "summary": price_summary
        }
        
    except Exception as e:
        log(f"Error fetching prices: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# QUANT 1.0 STRATEGIES
# =============================================================================

def refresh_quant1(price_data: Optional[Dict] = None) -> bool:
    """
    Refresh Quant 1.0 strategies (Momentum, Dual Momentum, HRP).
    
    Args:
        price_data: Pre-loaded price data (if None, loads fresh)
        
    Returns:
        True if successful
    """
    log("Refreshing Quant 1.0 strategies...")
    
    try:
        # Load prices if not provided
        if price_data is None:
            price_data = refresh_prices(lookback_days=365)
            if price_data is None:
                return False
        
        returns = price_data.get("returns")
        if returns is None or returns.empty:
            log("No returns data available", "ERROR")
            return False
        
        # Calculate momentum scores
        log("Calculating momentum scores...")
        momentum_12m = returns.rolling(252).sum().iloc[-1].dropna()
        momentum_6m = returns.rolling(126).sum().iloc[-1].dropna()
        momentum_1m = returns.rolling(21).sum().iloc[-1].dropna()
        
        # Dual momentum ranking
        log("Calculating dual momentum rankings...")
        dual_mom = (momentum_12m.rank(pct=True) + momentum_6m.rank(pct=True)) / 2
        
        # Top picks
        top_momentum = momentum_12m.nlargest(20)
        top_dual = dual_mom.nlargest(20)
        
        # Build output
        quant1_data = {
            "generated_at": datetime.now().isoformat(),
            "momentum": {
                "top_20": [
                    {"ticker": t, "score": round(float(s), 4), "rank": i+1}
                    for i, (t, s) in enumerate(top_momentum.items())
                ],
                "avg_12m_return": float(momentum_12m.mean()),
                "best_performer": top_momentum.idxmax(),
                "best_return": float(top_momentum.max())
            },
            "dual_momentum": {
                "top_20": [
                    {"ticker": t, "score": round(float(s), 4), "rank": i+1}
                    for i, (t, s) in enumerate(top_dual.items())
                ],
                "risk_on": float(dual_mom.mean()) > 0.5
            },
            "hrp": {
                "status": "calculated",
                "n_assets": len(returns.columns),
                "description": "See HRP module for full weights"
            },
            "last_updated": datetime.now().isoformat()
        }
        
        save_json("quant1_dashboard.json", quant1_data)
        
        return True
        
    except Exception as e:
        log(f"Error in Quant 1.0 refresh: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# QUANT 2.0 STRATEGIES
# =============================================================================

def refresh_quant2(price_data: Optional[Dict] = None) -> bool:
    """
    Refresh Quant 2.0 strategies.
    
    Includes:
    - HMM Regime Detection
    - Statistical Arbitrage
    - Meta-Labeling
    - VRP Signal
    - NCO Optimizer
    - Residual Momentum (monthly only - uses cached if within 30 days)
    
    Args:
        price_data: Pre-loaded price data
        
    Returns:
        True if successful
    """
    log("Refreshing Quant 2.0 strategies...")
    
    try:
        # Load prices if not provided
        if price_data is None:
            price_data = refresh_prices(lookback_days=500)
            if price_data is None:
                return False
        
        returns = price_data.get("returns")
        prices = price_data.get("prices")
        
        if returns is None or returns.empty:
            log("No returns data available", "ERROR")
            return False
        
        quant2_data = {
            "generated_at": datetime.now().isoformat(),
            "strategies": {}
        }
        
        # ----- 1. Regime Detection -----
        log("Running HMM Regime Detection...")
        try:
            # Use SPY returns for regime detection
            if "SPY" in returns.columns:
                spy_returns = returns["SPY"].dropna()
            else:
                # Fallback to first column
                spy_returns = returns.iloc[:, 0].dropna()
            
            # Try HMM
            from strategy.quant2.regime.hmm_detector import HMMRegimeDetector
            detector = HMMRegimeDetector(n_regimes=3)
            result = detector.detect(spy_returns)
            
            quant2_data["strategies"]["regime"] = {
                "current": result.metadata.get("current_regime", "UNKNOWN"),
                "probabilities": result.metadata.get("current_probabilities", {}),
                "method": result.metadata.get("method", "FALLBACK"),
                "n_observations": len(spy_returns)
            }
            log(f"  Regime: {result.metadata.get('current_regime', 'UNKNOWN')}")
        except Exception as e:
            log(f"  Regime detection failed: {e}", "WARN")
            quant2_data["strategies"]["regime"] = {"error": str(e)}
        
        # ----- 2. Statistical Arbitrage -----
        log("Running Statistical Arbitrage scan...")
        try:
            # Get top 50 most liquid stocks for pairs
            top_tickers = list(returns.mean().nlargest(50).index)
            sub_returns = returns[top_tickers].dropna()
            sub_prices = prices[top_tickers].dropna()
            
            from strategy.quant2.stat_arb.pairs_strategy import PairsStrategy
            strategy = PairsStrategy(eps=0.7, min_samples=2)
            result = strategy.scan_for_pairs(sub_returns, sub_prices)
            
            quant2_data["strategies"]["stat_arb"] = {
                "n_clusters": result.metadata.get("n_clusters", 0),
                "n_pairs": result.metadata.get("n_valid_pairs", 0),
                "active_signals": len(result.active_pairs),
                "top_pairs": [
                    {
                        "pair": f"{p['ticker_y']} / {p['ticker_x']}",
                        "zscore": round(p.get('zscore', 0), 2),
                        "signal": p.get('signal', 'NONE')
                    }
                    for p in result.active_pairs[:5]
                ]
            }
            log(f"  Found {len(result.active_pairs)} active pair signals")
        except Exception as e:
            log(f"  Stat Arb failed: {e}", "WARN")
            quant2_data["strategies"]["stat_arb"] = {"error": str(e)}
        
        # ----- 3. VRP Signal -----
        log("Running VRP Signal generation...")
        try:
            import yfinance as yf
            vix = yf.download("^VIX", period="1y", progress=False)["Close"]
            
            if not vix.empty:
                from strategy.quant2.volatility.vrp_signal import VRPSignal
                vrp = VRPSignal()
                result = vrp.generate_signals(vix)
                
                quant2_data["strategies"]["vrp"] = {
                    "current_vix": round(float(vix.iloc[-1]), 2),
                    "signal": result.current_signal,
                    "term_structure": result.term_structure,
                    "vix_percentile": round(result.vix_percentile, 1)
                }
                log(f"  VRP Signal: {result.current_signal} (VIX: {vix.iloc[-1]:.1f})")
            else:
                quant2_data["strategies"]["vrp"] = {"error": "VIX data unavailable"}
        except Exception as e:
            log(f"  VRP Signal failed: {e}", "WARN")
            quant2_data["strategies"]["vrp"] = {"error": str(e)}
        
        # ----- 4. Meta-Labeling (placeholder) -----
        quant2_data["strategies"]["meta_labeling"] = {
            "status": "ready",
            "model_trained": False,
            "description": "Run scanner first to generate signals for filtering"
        }
        
        # ----- 5. Residual Momentum (monthly only) -----
        log("Checking Residual Momentum (monthly strategy)...")
        timestamps = load_timestamps()
        last_resmom = timestamps.get("quant2", {}).get("residual_momentum")
        
        should_run_resmom = True
        if last_resmom:
            last_update = datetime.fromisoformat(last_resmom)
            days_since = (datetime.now() - last_update).days
            if days_since < 28:
                log(f"  Residual Momentum: Using cached results ({days_since} days old)")
                should_run_resmom = False
        
        if should_run_resmom:
            log("  Running Residual Momentum calculation...")
            try:
                # Convert to monthly returns
                monthly_returns = returns.resample('M').sum()
                
                from strategy.quant2.momentum.residual_momentum import ResidualMomentum
                rm = ResidualMomentum(lookback_months=36, scoring_months=12)
                result = rm.calculate_scores(monthly_returns)
                
                top_stocks = rm.get_top_n(result, n=10)
                bottom_stocks = rm.get_bottom_n(result, n=5)
                
                quant2_data["strategies"]["residual_momentum"] = {
                    "rebalance_freq": "monthly",
                    "top_10": top_stocks,
                    "avoid": bottom_stocks,
                    "n_scored": result.metadata.get("n_stocks_scored", 0),
                    "last_calculated": datetime.now().isoformat()
                }
                log(f"  Scored {result.metadata.get('n_stocks_scored', 0)} stocks")
                
                # Update timestamp
                if "quant2" not in timestamps:
                    timestamps["quant2"] = {}
                timestamps["quant2"]["residual_momentum"] = datetime.now().isoformat()
                save_timestamps(timestamps)
                
            except Exception as e:
                log(f"  Residual Momentum failed: {e}", "WARN")
                quant2_data["strategies"]["residual_momentum"] = {"error": str(e)}
        else:
            quant2_data["strategies"]["residual_momentum"] = {
                "status": "cached",
                "last_updated": last_resmom
            }
        
        # ----- 6. NCO Optimizer (placeholder) -----
        quant2_data["strategies"]["nco"] = {
            "status": "ready",
            "description": "NCO runs after all signals generated"
        }
        
        # Save combined data
        save_json("quant2_dashboard.json", quant2_data)
        
        return True
        
    except Exception as e:
        log(f"Error in Quant 2.0 refresh: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# QUALLAMAGGIE SCANNER
# =============================================================================

def refresh_scanner(price_data: Optional[Dict] = None) -> bool:
    """
    Run Quallamaggie breakout scanner.
    
    Args:
        price_data: Pre-loaded price data
        
    Returns:
        True if successful
    """
    log("Running Quallamaggie Scanner...")
    
    try:
        # Load prices if not provided
        if price_data is None:
            price_data = refresh_prices(lookback_days=90)
            if price_data is None:
                return False
        
        prices = price_data.get("prices")
        returns = price_data.get("returns")
        
        if prices is None or prices.empty:
            log("No price data available", "ERROR")
            return False
        
        # Calculate scanner criteria
        log("Calculating breakout candidates...")
        
        candidates = []
        for ticker in prices.columns:
            try:
                price = prices[ticker].dropna()
                if len(price) < 50:
                    continue
                
                # Calculate indicators
                ma50 = price.rolling(50).mean()
                ma20 = price.rolling(20).mean()
                high_52w = price.rolling(252).max()
                atr = (price.rolling(14).max() - price.rolling(14).min()).iloc[-1]
                
                current_price = price.iloc[-1]
                current_ma50 = ma50.iloc[-1]
                current_ma20 = ma20.iloc[-1]
                current_52w = high_52w.iloc[-1]
                
                # Quallamaggie criteria:
                # 1. Price above 50-day MA
                # 2. Price above 20-day MA
                # 3. Within 10% of 52-week high
                above_ma50 = current_price > current_ma50
                above_ma20 = current_price > current_ma20
                near_high = (current_52w - current_price) / current_52w < 0.10
                
                # Relative strength (simple version)
                ret_21d = float(returns[ticker].tail(21).sum()) if ticker in returns.columns else 0
                
                if above_ma50 and above_ma20 and near_high:
                    candidates.append({
                        "ticker": ticker,
                        "price": round(float(current_price), 2),
                        "dist_from_high": round(float((current_52w - current_price) / current_52w * 100), 2),
                        "above_ma50": True,
                        "above_ma20": True,
                        "return_21d": round(ret_21d * 100, 2),
                        "atr": round(float(atr), 2)
                    })
            except Exception:
                continue
        
        # Sort by 21-day return
        candidates.sort(key=lambda x: x["return_21d"], reverse=True)
        
        scanner_data = {
            "generated_at": datetime.now().isoformat(),
            "n_universe": len(prices.columns),
            "n_candidates": len(candidates),
            "top_breakouts": candidates[:30],  # Top 30
            "criteria": {
                "above_ma50": True,
                "above_ma20": True,
                "near_52w_high": "within 10%"
            }
        }
        
        save_json("scanner_results.json", scanner_data)
        log(f"Found {len(candidates)} breakout candidates")
        
        return True
        
    except Exception as e:
        log(f"Error in scanner: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# MAIN CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Unified Data Refresh Script for Quant Dashboards"
    )
    
    parser.add_argument("--all", action="store_true", help="Full refresh (prices + all strategies)")
    parser.add_argument("--quant1", action="store_true", help="Quant 1.0 strategies only")
    parser.add_argument("--quant2", action="store_true", help="Quant 2.0 strategies only")
    parser.add_argument("--scanner", action="store_true", help="Quallamaggie scanner only")
    parser.add_argument("--prices-only", action="store_true", help="Just update price data")
    parser.add_argument("--full-refresh", action="store_true", help="Force full download (ignore cache)")
    
    args = parser.parse_args()
    
    # Default to --all if no arguments
    if not any([args.all, args.quant1, args.quant2, args.scanner, args.prices_only]):
        args.all = True
    
    print("=" * 60)
    print("Unified Data Refresh Script")
    print("=" * 60)
    
    start_time = datetime.now()
    timestamps = load_timestamps()
    price_data = None
    
    # Fetch prices once (shared across strategies)
    if args.all or args.prices_only or args.quant1 or args.quant2 or args.scanner:
        price_data = refresh_prices(full_refresh=args.full_refresh)
        if price_data:
            timestamps["prices"] = datetime.now().isoformat()
    
    if args.prices_only:
        save_timestamps(timestamps)
        log("Prices refresh complete!")
        return
    
    # Run selected strategies
    if args.all or args.quant1:
        if refresh_quant1(price_data):
            timestamps.setdefault("quant1", {})
            timestamps["quant1"]["momentum"] = datetime.now().isoformat()
            timestamps["quant1"]["dual_momentum"] = datetime.now().isoformat()
            timestamps["quant1"]["hrp"] = datetime.now().isoformat()
    
    if args.all or args.quant2:
        if refresh_quant2(price_data):
            ts_now = datetime.now().isoformat()
            timestamps.setdefault("quant2", {})
            timestamps["quant2"]["regime"] = ts_now
            timestamps["quant2"]["stat_arb"] = ts_now
            timestamps["quant2"]["meta_labeling"] = ts_now
            timestamps["quant2"]["vrp"] = ts_now
            timestamps["quant2"]["nco"] = ts_now
            # Note: residual_momentum timestamp updated separately (monthly only)
    
    if args.all or args.scanner:
        if refresh_scanner(price_data):
            timestamps["scanner"] = datetime.now().isoformat()
    
    # Save timestamps
    timestamps["last_updated"] = datetime.now().isoformat()
    save_timestamps(timestamps)
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    print("=" * 60)
    log(f"Refresh complete in {elapsed:.1f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    main()
