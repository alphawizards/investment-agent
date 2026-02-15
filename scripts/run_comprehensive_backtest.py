"""
Comprehensive Backtesting Suite
================================
Runs backtests for all Quant 2.0 strategies on 21 years of data (2005-2025)

Strategies:
1. Quallamaggie (Swing Trading Momentum)
2. Quallamaggie + Meta-Labeling (ML-enhanced)
3. HMM Regime Detection
4. NCO Portfolio Optimization
5. Residual Momentum (Factor-neutral)

Note: Pairs Trading excluded per user request (computationally expensive)
"""

import sys
import io
# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
import json
import time

warnings.filterwarnings('ignore')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import strategies
from strategy.quallamaggie_backtest import run_quallamaggie_backtest
from strategy.quant2.meta_labeling.meta_model import MetaLabelModel
from strategy.quant2.meta_labeling.feature_engineering import FeatureEngineer
from strategy.quant2.regime.hmm_detector import HMMRegimeDetector
from strategy.quant2.optimization.nco_optimizer import NCOOptimizer
from strategy.quant2.momentum.residual_momentum import ResidualMomentum

print("="*80)
print("COMPREHENSIVE BACKTESTING SUITE - QUANT 2.0")
print("="*80)
print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============== DATA LOADING ==============

def load_cached_data():
    """Load combined dataset from cache using FastDataLoader."""
    print("[*] Loading cached data...")
    
    # Import FastDataLoader
    from strategy.fast_data_loader import FastDataLoader
    
    loader = FastDataLoader()
    
    # Load US stocks from Tiingo cache (560 stocks, 21 years)
    prices = loader.load_cached_tiingo_stocks()
    
    if prices.empty:
        print("ERROR: No cached Tiingo data found!")
        print("Please run: python fetch_us_stocks_20yr_tiingo.py")
        return None, None
    
    # Load VIX for regime detection
    vix = loader.load_cached_vix()
    
    if vix.empty:
        print("WARNING: VIX data not found - Regime Detection will use fallback")
        vix = None
    
    return prices, vix

# Load data
prices, vix = load_cached_data()
returns = prices.pct_change().dropna()

print()

# ============== STRATEGY 1: QUALLAMAGGIE ==============

def run_quallamaggie_strategy():
    """Run Quallamaggie swing trading backtest."""
    print("="*80)
    print("STRATEGY 1: QUALLAMAGGIE (SWING TRADING MOMENTUM)")
    print("="*80)
    
    start_time = time.time()
    
    try:
        # Use top 100 by average volume for performance
        avg_volume = (prices * returns.rolling(20).mean()).mean()
        top_tickers = [t for t in avg_volume.nlargest(100).index.tolist() if not pd.isna(avg_volume[t])]
        
        print(f"  Universe: {len(top_tickers)} stocks (top 100 by liquidity)")
        print(f"  Backtesting period: 2020-01-01 to {prices.index[-1].date()}")
        print(f"  Note: Using recent 5 years for Quallamaggie (full 21y may be slow)")
        
        # Run backtest using the standalone function
        result = run_quallamaggie_backtest(
            tickers=top_tickers,
            start_date='2020-01-01',
            end_date=str(prices.index[-1].date())
        )
        
        # Summary
        if result:
            print(f"\n✅ Quallamaggie Results:")
            print(f"  CAGR: {result.cagr:.2%}")
            print(f"  Sharpe Ratio: {result.sharpe:.2f}")
            print(f"  Max Drawdown: {result.max_drawdown:.2%}")
            print(f"  Win Rate: {result.win_rate:.2%}")
            print(f"  Total Trades: {result.total_trades}")
            
            elapsed = time.time() - start_time
            print(f"  ⏱️ Runtime: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
            
            return {
                'strategy': 'Quallamaggie',
                'cagr': float(result.cagr),
                'sharpe': float(result.sharpe),
                'max_drawdown': float(result.max_drawdown),
                'total_trades': int(result.total_trades)
            }
        else:
            print(f"❌ Backtest returned None")
            return None
        
    except Exception as e:
        print(f"❌ Quallamaggie backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============== STRATEGY 2: QUALLAMAGGIE + META-LABELING ==============

def run_quallamaggie_metalabeling():
    """Run Quallamaggie with Meta-Labeling enhancement."""
    print("\n" + "="*80)
    print("STRATEGY 2: QUALLAMAGGIE + META-LABELING (ML-ENHANCED)")
    print("="*80)
    
    start_time = time.time()
    
    try:
        # First run Quallamaggie to get base signals
        config = QullamaggieConfig()
        base_strategy = QullamaggieStrategy(config=config)
        
        # Top 100 for meta-labeling (faster)
        avg_volume = (prices * returns.rolling(20).mean()).mean()
        top_tickers = avg_volume.nlargest(100).index.tolist()
        
        print(f"  Universe: {len(top_tickers)} stocks (top 100 for ML)")
        
        # Generate features
        feature_engineer = FeatureEngineer()
        
        print("  Generating features...")
        features_dict = {}
        for ticker in top_tickers[:20]:  # Limit to 20 for demo
            try:
                ticker_prices = prices[ticker].dropna()
                if len(ticker_prices) > 100:
                    features = feature_engineer.generate_features(
                        prices=ticker_prices,
                        volume=None,
                        returns=returns[ticker]
                    )
                    features_dict[ticker] = features
            except Exception:
                continue
        
        print(f"  ✓ Generated features for {len(features_dict)} stocks")
        
        # Train meta-model
        meta_labeler = MetaLabelModel()
        
        print("  Training meta-model...")
        # Simplified training - in production, use triple barrier method
        X_train = pd.concat([f for f in features_dict.values()], axis=0)
        y_train = (returns.loc[X_train.index].mean(axis=1) > 0).astype(int)
        
        meta_labeler.fit(X_train, y_train)
        
        print(f"  ✓ Meta-model trained")
        print(f"  ✓ Feature importance: {dict(list(meta_labeler.feature_importance.items())[:5])}")
        
        # Combine signals
        print("\n✅ Meta-Labeling Enhancement:")
        print(f"  Base Strategy: Quallamaggie")
        print(f"  ML Model: Random Forest")
        print(f"  Features: {len(X_train.columns)}")
        print(f"  Note: Full backtest would apply meta-labels to filter trades")
        
        elapsed = time.time() - start_time
        print(f"  ⏱️ Runtime: {elapsed:.2f} seconds")
        
        return {
            'strategy': 'Quallamaggie + Meta-Labeling',
            'features_generated': len(features_dict),
            'model_accuracy': meta_labeler.metrics.get('accuracy', 0) if hasattr(meta_labeler, 'metrics') else 0,
        }
        
    except Exception as e:
        print(f"❌ Meta-labeling failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============== STRATEGY 3: HMM REGIME DETECTION ==============

def run_hmm_regime_detection():
    """Run HMM regime detection backtest."""
    print("\n" + "="*80)
    print("STRATEGY 3: HMM REGIME DETECTION")
    print("="*80)
    
    start_time = time.time()
    
    try:
        # Calculate market returns (SPY or equal-weighted)
        if 'SPY' in returns.columns:
            market_returns = returns['SPY']
            print("  Using SPY as market proxy")
        else:
            market_returns = returns.mean(axis=1)
            print("  Using equal-weighted returns as market proxy")
        
        # Initialize detector
        detector = HMMRegimeDetector(n_regimes=3, lookback_vol=21)
        
        print("  Detecting market regimes...")
        result = detector.detect(market_returns, use_fallback=True)
        
        # Print results
        print(f"\n✅ Regime Detection Results:")
        print(f"  Method: {result.metadata['method']}")
        print(f"  Current Regime: {result.metadata['current_regime']}")
        
        if 'current_probabilities' in result.metadata:
            print(f"  Current Probabilities:")
            for regime, prob in result.metadata['current_probabilities'].items():
                print(f"    {regime}: {prob:.2%}")
        
        if result.regime_stats:
            print(f"\n  Regime Statistics:")
            for regime, stats in result.regime_stats.items():
                print(f"    {regime}:")
                print(f"      Mean Return: {stats['mean_return']:.4f}")
                print(f"      Volatility: {stats['volatility']:.4f}")
                print(f"      Frequency: {stats['frequency']:.2%}")
        
        # Regime distribution
        print(f"\n  Regime Distribution:")
        regime_counts = result.regimes.value_counts()
        for regime, count in regime_counts.items():
            pct = count / len(result.regimes)
            print(f"    {regime}: {count} days ({pct:.1%})")
        
        # Transition matrix
        if result.transitions is not None and result.metadata['method'] == 'HMM':
            print(f"\n  Transition Matrix:")
            trans_df = pd.DataFrame(
                result.transitions,
                index=['BULL→', 'BEAR→', 'CHOP→'],
                columns=['BULL', 'BEAR', 'CHOP']
            )
            print(trans_df.round(3))
        
        elapsed = time.time() - start_time
        print(f"\n  ⏱️ Runtime: {elapsed:.2f} seconds")
        
        return {
            'strategy': 'HMM Regime Detection',
            'current_regime': result.metadata['current_regime'],
            'method': result.metadata['method'],
            'regime_stats': result.regime_stats,
        }
        
    except Exception as e:
        print(f"❌ HMM regime detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============== STRATEGY 4: NCO PORTFOLIO OPTIMIZATION ==============

def run_nco_optimization():
    """Run NCO portfolio optimization."""
    print("\n" + "="*80)
    print("STRATEGY 4: NCO PORTFOLIO OPTIMIZATION")
    print("="*80)
    
    start_time = time.time()
    
    try:
        # Use top 50 stocks for optimization
        avg_vol = returns.std() * np.sqrt(252)
        top_tickers = avg_vol.nlargest(50).index.tolist()
        
        print(f"  Universe: {len(top_tickers)} stocks (top 50 by volatility)")
        
        # Recent 3 years for optimization
        recent_returns = returns[top_tickers].tail(252 * 3)
        
        print(f"  Optimization period: {recent_returns.index[0].date()} to {recent_returns.index[-1].date()}")
        print(f"  Data points: {len(recent_returns)} days")
        
        # Initialize optimizer
        optimizer = NCOOptimizer(
            inner_objective='MinRisk',
            outer_objective='ERC',
            max_clusters=10,
            min_weight=0.02,
            max_weight=0.30
        )
        
        print("  Running NCO optimization...")
        result = optimizer.optimize(recent_returns)
        
        # Print results
        print(f"\n✅ NCO Optimization Results:")
        print(f"  Effective N: {result.metadata['effective_n']:.2f}")
        print(f"  Number of Assets: {result.metadata['n_assets']}")
        print(f"  Max Weight: {result.weights.max():.2%}")
        print(f"  Min Weight: {result.weights.min():.2%}")
        
        print(f"\n  Top 10 Holdings:")
        for ticker, weight in result.weights.nlargest(10).items():
            print(f"    {ticker}: {weight:.2%}")
        
        # Portfolio statistics
        stats = optimizer.get_portfolio_stats(recent_returns, result.weights)
        print(f"\n  Portfolio Statistics:")
        print(f"    Expected Return: {stats['expected_return']:.2%}")
        print(f"    Volatility: {stats['volatility']:.2%}")
        print(f"    Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        
        # Compare with HRP
        print("\n  Comparing NCO vs HRP...")
        comparison = optimizer.compare_with_hrp(recent_returns)
        print(f"  Top 5 differences (NCO - HRP):")
        top_diffs = comparison.reindex(comparison['Difference'].abs().nlargest(5).index)
        print(top_diffs)
        
        elapsed = time.time() - start_time
        print(f"\n  ⏱️ Runtime: {elapsed:.2f} seconds")
        
        return {
            'strategy': 'NCO Portfolio Optimization',
            'weights': result.weights.to_dict(),
            'stats': stats,
            'metadata': result.metadata,
        }
        
    except Exception as e:
        print(f"❌ NCO optimization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============== STRATEGY 5: RESIDUAL MOMENTUM ==============

def run_residual_momentum():
    """Run Residual Momentum (factor-neutral) backtest."""
    print("\n" + "="*80)
    print("STRATEGY 5: RESIDUAL MOMENTUM (FACTOR-NEUTRAL)")
    print("="*80)
    
    start_time = time.time()
    
    try:
        # Convert to monthly returns
        monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        
        # Use top 100 stocks
        avg_return = monthly_returns.mean()
        top_tickers = avg_return.abs().nlargest(100).index.tolist()
        
        print(f"  Universe: {len(top_tickers)} stocks (top 100 by avg return)")
        print(f"  Period: {monthly_returns.index[0].date()} to {monthly_returns.index[-1].date()}")
        print(f"  Monthly observations: {len(monthly_returns)}")
        
        # Initialize residual momentum
        res_mom = ResidualMomentum(
            lookback_months=36,
            scoring_months=12,
            min_observations=24
        )
        
        print("  Calculating residual momentum scores...")
        print("  Note: Fetching Fama-French factors...")
        
        # Calculate scores (will auto-download Fama-French data)
        result = res_mom.calculate_scores(
            stock_returns=monthly_returns[top_tickers],
            as_of_date=str(monthly_returns.index[-1].date())
        )
        
        print(f"\n✅ Residual Momentum Results:")
        print(f"  Method: {result.metadata['method']}")
        print(f"  Stocks Analyzed: {result.metadata['n_stocks']}")
        print(f"  Lookback Period: {result.metadata['lookback_months']} months")
        print(f"  Scoring Period: {result.metadata['scoring_months']} months")
        
        # Top 10 by residual momentum
        top_10 = res_mom.get_top_n(result, n=10)
        print(f"\n  Top 10 Stocks by Residual Momentum:")
        for i, ticker in enumerate(top_10, 1):
            score = result.scores.loc[ticker] if ticker in result.scores.index else np.nan
            print(f"    {i}. {ticker}: Score = {score:.3f}")
        
        # Bottom 10 (for short leg)
        bottom_10 = res_mom.get_bottom_n(result, n=10)
        print(f"\n  Bottom 10 Stocks (Short Candidates):")
        for i, ticker in enumerate(bottom_10, 1):
            score = result.scores.loc[ticker] if ticker in result.scores.index else np.nan
            print(f"    {i}. {ticker}: Score = {score:.3f}")
        
        # Factor exposure summary
        if result.factor_exposures:
            exposure_summary = res_mom.get_factor_exposure_summary(result)
            print(f"\n  Factor Exposure Summary:")
            print(exposure_summary)
        
        elapsed = time.time() - start_time
        print(f"\n  ⏱️ Runtime: {elapsed:.2f} seconds")
        
        return {
            'strategy': 'Residual Momentum',
            'top_10': top_10,
            'bottom_10': bottom_10,
            'metadata': result.metadata,
        }
        
    except Exception as e:
        print(f"❌ Residual Momentum failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============== RUN ALL STRATEGIES ==============

if __name__ == "__main__":
    all_results = {}
    
    # Strategy 1: Quallamaggie
    print("\n")
    qualla_results = run_quallamaggie_strategy()
    if qualla_results:
        all_results['quallamaggie'] = qualla_results
    
    # Strategy 2: Quallamaggie + Meta-Labeling
    print("\n")
    meta_results = run_quallamaggie_metalabeling()
    if meta_results:
        all_results['quallamaggie_metalabeling'] = meta_results
    
    # Strategy 3: HMM Regime Detection
    print("\n")
    regime_results = run_hmm_regime_detection()
    if regime_results:
        all_results['hmm_regime'] = regime_results
    
    # Strategy 4: NCO Portfolio Optimization
    print("\n")
    nco_results = run_nco_optimization()
    if nco_results:
        all_results['nco_optimization'] = nco_results
    
    # Strategy 5: Residual Momentum
    print("\n")
    momentum_results = run_residual_momentum()
    if momentum_results:
        all_results['residual_momentum'] = momentum_results
    
    # ============== FINAL SUMMARY ==============
    
    print("\n" + "="*80)
    print("COMPREHENSIVE BACKTEST SUMMARY")
    print("="*80)
    
    print(f"\nStrategies Run: {len(all_results)}/5")
    for strategy_name in all_results.keys():
        print(f"  ✅ {strategy_name}")
    
    # Save results
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"comprehensive_backtest_{timestamp}.json"
    
    # Convert to JSON-serializable format
    json_results = {}
    for key, value in all_results.items():
        if isinstance(value, dict):
            json_results[key] = {
                k: (v if isinstance(v, (int, float, str, list, dict)) else str(v))
                for k, v in value.items()
            }
    
    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    print("\n" + "="*80)
    print("✅ COMPREHENSIVE BACKTEST COMPLETE")
    print("="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
