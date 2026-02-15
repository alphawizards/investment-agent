#!/usr/bin/env python3
"""
Quantitative Global Investing Strategy
=======================================
Main execution script for Australian retail investors.

This system implements:
1. Dual Momentum signal generation
2. HRP portfolio optimization
3. Cost-aware execution (Stake.com fees)
4. AUD currency normalization

Author: Quantitative Strategy Team
License: MIT
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import argparse
import sys
from pathlib import Path

# Add parent directory to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategy.config import CONFIG, BACKTEST_CONFIG, get_us_tickers, get_asx_tickers
from strategy.data_loader import DataLoader

# Optional imports - require pandas_ta which needs Python >= 3.12
try:
    from strategy.quant1.momentum.signals import MomentumSignals, CompositeSignal
    HAS_SIGNALS = True
except ImportError:
    MomentumSignals = None
    CompositeSignal = None
    HAS_SIGNALS = False

from strategy.quant1.optimization.optimizer import PortfolioOptimizer, CostAwareOptimizer
from strategy.backtest import PortfolioBacktester, VectorBTBacktester

warnings.filterwarnings('ignore')


class QuantStrategy:
    """
    Main strategy class orchestrating all components.
    
    Workflow:
    1. Load and normalize data (AUD)
    2. Generate momentum signals
    3. Optimize portfolio (HRP)
    4. Apply cost-benefit gate
    5. Generate trade recommendations
    """
    
    def __init__(self,
                 tickers: list = None,
                 start_date: str = None,
                 end_date: str = None,
                 portfolio_value: float = 100000):
        """
        Initialize strategy.
        
        Args:
            tickers: List of tickers to trade (default: from config)
            start_date: Backtest start date
            end_date: Backtest end date
            portfolio_value: Portfolio value in AUD
        """
        # Default to mixed US/ASX portfolio
        if tickers is None:
            tickers = [
                # US ETFs (via Stake)
                'SPY', 'QQQ', 'TLT', 'GLD',
                # ASX ETFs (no FX friction)
                'IVV.AX', 'VGS.AX', 'VAS.AX', 'VAF.AX'
            ]
        
        self.tickers = tickers
        self.start_date = start_date or CONFIG.START_DATE
        self.end_date = end_date or CONFIG.END_DATE
        self.portfolio_value = portfolio_value
        
        # Components
        self.data_loader = DataLoader(self.start_date, self.end_date)
        self.momentum = MomentumSignals()
        self.composite = CompositeSignal()
        
        # Data storage
        self.prices = None
        self.returns = None
        self.signals = None
        self.weights = None
        
    def load_data(self) -> tuple:
        """
        Load and prepare data.
        
        Returns:
            Tuple of (prices, returns) DataFrames
        """
        print("\n" + "=" * 60)
        print("STEP 1: Loading Data")
        print("=" * 60)
        
        self.prices, self.returns = self.data_loader.load_selective_dataset(
            self.tickers
        )
        
        print(f"\nData Summary:")
        print(f"  Period: {self.prices.index[0].strftime('%Y-%m-%d')} to {self.prices.index[-1].strftime('%Y-%m-%d')}")
        print(f"  Trading days: {len(self.prices)}")
        print(f"  Assets: {len(self.prices.columns)}")
        
        return self.prices, self.returns
    
    def generate_signals(self) -> pd.DataFrame:
        """
        Generate trading signals.
        
        Returns:
            DataFrame of signals
        """
        print("\n" + "=" * 60)
        print("STEP 2: Generating Signals")
        print("=" * 60)
        
        if self.prices is None:
            self.load_data()
        
        # Dual momentum signals
        dual_mom = self.momentum.dual_momentum(self.prices)
        mom_score = self.momentum.momentum_score(self.prices)
        
        # Get latest signals
        latest_dual = dual_mom.iloc[-1]
        latest_score = mom_score.iloc[-1]
        
        print("\nDual Momentum Signals (latest):")
        for ticker in self.tickers:
            if ticker in latest_dual.index:
                signal = "✓ BUY" if latest_dual[ticker] == 1 else "✗ AVOID"
                score = latest_score.get(ticker, 0)
                print(f"  {ticker}: {signal} (score: {score:.3f})")
        
        self.signals = dual_mom
        return dual_mom
    
    def optimize_portfolio(self, method: str = 'hrp') -> pd.Series:
        """
        Optimize portfolio weights.
        
        Args:
            method: 'hrp', 'mvo', or 'risk_parity'
            
        Returns:
            Series of optimal weights
        """
        print("\n" + "=" * 60)
        print(f"STEP 3: Portfolio Optimization ({method.upper()})")
        print("=" * 60)
        
        if self.returns is None:
            self.load_data()
        
        # Filter to assets with positive signals (if available)
        if self.signals is not None:
            latest_signals = self.signals.iloc[-1]
            active_assets = latest_signals[latest_signals == 1].index.tolist()
            
            if len(active_assets) < 2:
                print("Warning: Less than 2 assets passed signal filter. Using all assets.")
                active_assets = self.returns.columns.tolist()
        else:
            active_assets = self.returns.columns.tolist()
        
        # Filter returns to active assets
        active_returns = self.returns[active_assets]
        
        # Initialize optimizer
        optimizer = PortfolioOptimizer(active_returns)
        
        # Optimize based on method
        if method == 'hrp':
            weights = optimizer.optimize_hrp()
        elif method == 'mvo':
            weights = optimizer.optimize_mvo(objective='Sharpe')
        elif method == 'risk_parity':
            weights = optimizer.optimize_risk_parity()
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Extend to full universe (zero weight for inactive)
        full_weights = pd.Series(0, index=self.tickers)
        for asset in weights.index:
            if asset in full_weights.index:
                full_weights[asset] = weights[asset]
        
        # Get portfolio stats
        stats = optimizer.get_portfolio_stats(weights)
        
        print("\nOptimal Weights:")
        for ticker, weight in full_weights.items():
            if weight > 0.01:
                print(f"  {ticker}: {weight*100:.1f}%")
        
        print(f"\nPortfolio Statistics:")
        print(f"  Expected Return: {stats['expected_return']*100:.2f}%")
        print(f"  Volatility: {stats['volatility']*100:.2f}%")
        print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.3f}")
        
        self.weights = full_weights
        return full_weights
    
    def analyze_costs(self, 
                      current_weights: pd.Series = None,
                      expected_alpha: float = 0.02) -> dict:
        """
        Analyze trading costs and determine if trades should execute.
        
        Args:
            current_weights: Current portfolio weights
            expected_alpha: Expected annual alpha from strategy
            
        Returns:
            Cost analysis dict
        """
        print("\n" + "=" * 60)
        print("STEP 4: Cost-Benefit Analysis")
        print("=" * 60)
        
        if self.weights is None:
            self.optimize_portfolio()
        
        if current_weights is None:
            # Assume starting from cash
            current_weights = pd.Series(0, index=self.tickers)
        
        # Initialize cost-aware optimizer
        cost_opt = CostAwareOptimizer(
            self.returns,
            current_weights=current_weights,
            portfolio_value_aud=self.portfolio_value
        )
        
        # Analyze costs
        should_trade, analysis = cost_opt.cost_benefit_gate(
            target_weights=self.weights,
            expected_alpha=expected_alpha
        )
        
        print(f"\nCost Analysis ($3 AUD per trade):")
        print(f"  Expected Alpha: {analysis['expected_alpha']*100:.2f}%")
        print(f"  Brokerage: ${analysis['brokerage_aud']:.2f}")
        print(f"  Total Cost: ${analysis['total_cost_aud']:.2f}")
        print(f"  Trade Count: {analysis['trade_count']}")
        print(f"  Cost Drag: {analysis['cost_drag']*100:.3f}%")
        print(f"  Net Benefit: {analysis['net_benefit']*100:.3f}%")
        print(f"  Turnover: {analysis['turnover']*100:.1f}%")
        
        print(f"\n{'✓ EXECUTE TRADES' if should_trade else '✗ HOLD CURRENT POSITIONS'}")
        
        return analysis
    
    def run_backtest(self, 
                     strategy: str = 'dual_momentum',
                     rebalance_freq: str = 'monthly') -> dict:
        """
        Run full strategy backtest.
        
        Args:
            strategy: 'dual_momentum', 'momentum', or 'equal_weight'
            rebalance_freq: Rebalancing frequency
            
        Returns:
            Backtest results dict
        """
        print("\n" + "=" * 60)
        print(f"STEP 5: Backtesting ({strategy})")
        print("=" * 60)
        
        if self.prices is None:
            self.load_data()
        
        bt = PortfolioBacktester(self.prices, self.portfolio_value)
        
        if strategy == 'dual_momentum':
            # Find a defensive asset
            defensive = 'TLT' if 'TLT' in self.prices.columns else 'VAF.AX'
            result = bt.run_dual_momentum_backtest(
                lookback=252,
                defensive_asset=defensive,
                rebalance_freq=rebalance_freq
            )
        elif strategy == 'momentum':
            result = bt.run_momentum_backtest(
                lookback=252,
                top_n=3,
                rebalance_freq=rebalance_freq
            )
        elif strategy == 'equal_weight':
            equal_weights = pd.Series(1/len(self.tickers), index=self.tickers)
            result = bt.run_static_backtest(
                equal_weights,
                rebalance_freq=rebalance_freq
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        print(f"\nBacktest Results ({len(result.returns)} days):")
        print(f"  Initial Capital: ${self.portfolio_value:,.2f}")
        print(f"  Final Value: ${result.portfolio_value.iloc[-1]:,.2f}")
        print(f"  Total Return: {result.metrics['total_return']*100:.2f}%")
        print(f"  CAGR: {result.metrics['cagr']*100:.2f}%")
        print(f"  Volatility: {result.metrics['volatility']*100:.2f}%")
        print(f"  Sharpe Ratio: {result.metrics['sharpe_ratio']:.3f}")
        print(f"  Sortino Ratio: {result.metrics['sortino_ratio']:.3f}")
        print(f"  Max Drawdown: {result.metrics['max_drawdown']*100:.2f}%")
        print(f"  Calmar Ratio: {result.metrics['calmar_ratio']:.3f}")
        print(f"  Win Rate: {result.metrics['win_rate']*100:.1f}%")
        
        if not result.trades.empty:
            print(f"\nTrading Summary:")
            print(f"  Total Trades: {len(result.trades)}")
            print(f"  Total Costs: ${result.trades['cost'].sum():,.2f}")
            print(f"  Avg Turnover: {result.trades['turnover'].mean()*100:.1f}%")
        
        return result.metrics
    
    def generate_recommendations(self) -> dict:
        """
        Generate final trade recommendations.
        
        Returns:
            Dict with recommendations
        """
        print("\n" + "=" * 60)
        print("FINAL RECOMMENDATIONS")
        print("=" * 60)
        
        if self.weights is None:
            self.optimize_portfolio()
        
        recommendations = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'portfolio_value': self.portfolio_value,
            'allocations': {},
            'us_etf_allocation': 0,
            'asx_etf_allocation': 0
        }
        
        us_tickers = get_us_tickers()
        
        print("\nRecommended Portfolio Allocation:")
        print("-" * 40)
        
        for ticker, weight in self.weights.items():
            if weight > 0.01:
                allocation_aud = weight * self.portfolio_value
                is_us = ticker in us_tickers
                
                recommendations['allocations'][ticker] = {
                    'weight': weight,
                    'allocation_aud': allocation_aud,
                    'platform': 'Stake.com' if is_us else 'ASX Broker'
                }
                
                if is_us:
                    recommendations['us_etf_allocation'] += weight
                else:
                    recommendations['asx_etf_allocation'] += weight
                
                platform = "Stake.com" if is_us else "ASX"
                print(f"  {ticker}: {weight*100:.1f}% (${allocation_aud:,.0f}) via {platform}")
        
        print("-" * 40)
        print(f"\nTotal US ETF allocation: {recommendations['us_etf_allocation']*100:.1f}%")
        print(f"Total ASX ETF allocation: {recommendations['asx_etf_allocation']*100:.1f}%")
        
        # Calculate expected brokerage costs ($3 per trade)
        num_positions = sum(1 for w in self.weights if w > 0.01)
        brokerage_cost = num_positions * 3.0  # $3 AUD per trade
        
        print(f"\nExpected Brokerage Cost: ${brokerage_cost:.2f} ({num_positions} trades × $3)")
        print(f"Cost as % of Portfolio: {(brokerage_cost / self.portfolio_value) * 100:.3f}%")
        
        print("\n💡 RECOMMENDATION:")
        print(f"  → Low transaction costs with $3/trade structure")
        
        return recommendations
    
    def run_full_pipeline(self):
        """Run complete strategy pipeline."""
        print("\n" + "=" * 60)
        print("QUANTITATIVE GLOBAL INVESTING STRATEGY")
        print("For Australian Retail Investors")
        print("=" * 60)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"Portfolio Value: ${self.portfolio_value:,.2f} AUD")
        
        # Step 1: Load data
        self.load_data()
        
        # Step 2: Generate signals
        self.generate_signals()
        
        # Step 3: Optimize portfolio
        self.optimize_portfolio(method='hrp')
        
        # Step 4: Analyze costs
        self.analyze_costs(expected_alpha=0.02)
        
        # Step 5: Run backtest
        self.run_backtest(strategy='dual_momentum')
        
        # Step 6: Generate recommendations
        recommendations = self.generate_recommendations()
        
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        
        return recommendations


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Quantitative Global Investing Strategy'
    )
    parser.add_argument(
        '--portfolio-value',
        type=float,
        default=100000,
        help='Portfolio value in AUD (default: 100000)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default='2015-01-01',
        help='Backtest start date (default: 2015-01-01)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='Backtest end date (default: today)'
    )
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['dual_momentum', 'momentum', 'equal_weight'],
        default='dual_momentum',
        help='Strategy to backtest (default: dual_momentum)'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demo with sample data'
    )
    
    args = parser.parse_args()
    
    if args.demo:
        print("Running demo with sample data...")
        # Demo with subset of data
        strategy = QuantStrategy(
            tickers=['SPY', 'QQQ', 'TLT', 'GLD'],
            start_date='2020-01-01',
            portfolio_value=args.portfolio_value
        )
    else:
        strategy = QuantStrategy(
            start_date=args.start_date,
            end_date=args.end_date,
            portfolio_value=args.portfolio_value
        )
    
    strategy.run_full_pipeline()


if __name__ == "__main__":
    main()
