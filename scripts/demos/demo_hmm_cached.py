"""
Demo: HMM Regime Detection with Cached VIX Data
================================================
Demonstrates using FastDataLoader to access cached VIX data
for instant regime detection without live API calls.
"""

from strategy.fast_data_loader import FastDataLoader
from strategy.quant2.regime.hmm_detector import HMMRegimeDetector
import pandas as pd

def demo_hmm_with_cached_vix():
    """Run HMM regime detection using cached VIX data."""
    
    print("="*60)
    print("HMM REGIME DETECTION - CACHED DATA DEMO")
    print("="*60)
    
    # Load cached VIX data (instant, 21 years)
    loader = FastDataLoader()
    vix = loader.load_cached_vix()
    
    if vix.empty:
        print("ERROR: No VIX cache found. Run test_stack_readiness.py first.")
        return
    
    # Calculate VIX returns for HMM
    vix_returns = vix.pct_change().dropna()
    
    print(f"\n📊 VIX Data Loaded:")
    print(f"   Period: {vix.index.min().date()} to {vix.index.max().date()}")
    print(f"   Days: {len(vix)}")
    print(f"   Current VIX: {vix.iloc[-1]:.2f}")
    
    # Run HMM detection
    print(f"\n🔍 Running HMM Detection...")
    detector = HMMRegimeDetector(n_regimes=3, lookback_vol=21)
    result = detector.detect(vix_returns, use_fallback=True)
    
    # Display results
    print(f"\n✅ Detection Results:")
    print(f"   Method: {result.metadata['method']}")
    print(f"   Current Regime: {result.metadata['current_regime']}")
    
    if 'current_probabilities' in result.metadata:
        print(f"\n   Regime Probabilities:")
        for regime, prob in result.metadata['current_probabilities'].items():
            print(f"     {regime}: {prob:.2%}")
    
    if result.regime_stats:
        print(f"\n   Regime Statistics:")
        for regime, stats in result.regime_stats.items():
            print(f"     {regime}:")
            print(f"       Mean Return: {stats['mean_return']:+.4f}")
            print(f"       Volatility: {stats['volatility']:.4f}")
            print(f"       Frequency: {stats['frequency']:.1%}")
    
    # Recent regime history
    print(f"\n📈 Recent Regime History (Last 10 days):")
    recent_regimes = result.regimes.tail(10)
    for date, regime in recent_regimes.items():
        vix_level = vix.loc[date]
        print(f"   {date.date()}: {regime.name:6} (VIX: {vix_level:5.2f})")
    
    print("\n" + "="*60)
    print("✅ Demo Complete")
    print("="*60)
    
    return result


if __name__ == "__main__":
    demo_hmm_with_cached_vix()
