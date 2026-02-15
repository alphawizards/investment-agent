"""
Trading Pipeline Runner
========================
Standalone script to run the trading pipeline.

Usage:
    python run_pipeline.py scan
    python run_pipeline.py scan --strategy Dual_Momentum
    python run_pipeline.py list

⚠️ DEPRECATED: This file will be removed in the next release.
   Use 'python -m strategy.pipeline.cli scan' instead.
"""

import warnings
warnings.warn(
    "\n\n"
    "⚠️  DEPRECATION WARNING ⚠️\n"
    "run_pipeline.py is deprecated and will be removed in the next release.\n"
    "Please use 'python -m strategy.pipeline.cli scan' instead.\n",
    DeprecationWarning,
    stacklevel=2
)

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import argparse
import warnings

warnings.filterwarnings('ignore')

# Import yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("Warning: yfinance not installed")


# ============== CONFIGURATION ==============

@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    
    # Data
    start_date: str = "2020-01-01"
    end_date: str = None
    initial_capital: float = 100_000.0
    
    # Universe
    tickers: List[str] = field(default_factory=lambda: [
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI',
        'XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLI', 'XLB',
        'ARKK', 'SOXX', 'SMH', 'XBI', 'TAN',
        'EFA', 'EEM', 'VEA', 'VWO',
        'TLT', 'IEF', 'BND', 'HYG', 'LQD',
        'GLD', 'SLV', 'USO', 'DBC'
    ])
    
    # Output
    output_dir: str = "reports"
    
    def __post_init__(self):
        if self.end_date is None:
            self.end_date = datetime.now().strftime("%Y-%m-%d")


# ============== DATA LAYER ==============

def fetch_prices(tickers: List[str], start: str, end: str) -> pd.DataFrame:
    """Fetch price data from yfinance."""
    print(f"📊 Fetching data for {len(tickers)} tickers...")
    
    try:
        data = yf.download(
            tickers,
            start=start,
            end=end,
            progress=False,
            threads=False,
            auto_adjust=True
        )
        
        if isinstance(data.columns, pd.MultiIndex):
            prices = data['Close']
        else:
            prices = data[['Close']] if 'Close' in data.columns else data
        
        # Filter valid data
        valid_cols = prices.columns[prices.notna().sum() / len(prices) >= 0.7]
        prices = prices[valid_cols].dropna(how='all')
        
        print(f"   ✓ Loaded {len(prices.columns)} tickers")
        return prices
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return pd.DataFrame()


# ============== SIGNAL LAYER ==============

def momentum_signals(prices: pd.DataFrame, lookback: int, top_n: int = 5) -> pd.DataFrame:
    """Generate momentum signals - top N stocks by return."""
    returns = prices.pct_change(lookback)
    signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
    
    for date in prices.index[lookback:]:
        row = returns.loc[date].dropna()
        if len(row) > 0:
            top = row.nlargest(min(top_n, len(row))).index
            for ticker in top:
                signals.loc[date, ticker] = 1
    
    return signals


def dual_momentum_signals(
    prices: pd.DataFrame, 
    lookback: int = 252, 
    defensive: List[str] = None
) -> pd.DataFrame:
    """Generate Dual Momentum signals."""
    defensive = defensive or ['TLT', 'IEF', 'BND']
    returns = prices.pct_change(lookback)
    signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
    
    risky = [c for c in prices.columns if c not in defensive]
    
    for date in prices.index[lookback:]:
        row = returns.loc[date].dropna()
        risky_ret = row.reindex([r for r in risky if r in row.index])
        
        if len(risky_ret) > 0:
            best = risky_ret.idxmax()
            if risky_ret[best] > 0.04:  # Above risk-free rate
                signals.loc[date, best] = 1
            else:
                def_ret = row.reindex([d for d in defensive if d in row.index])
                if len(def_ret) > 0:
                    signals.loc[date, def_ret.idxmax()] = 1
    
    return signals


def hrp_signals(prices: pd.DataFrame) -> pd.DataFrame:
    """HRP signals - all assets always on (allocation handles weights)."""
    return pd.DataFrame(1, index=prices.index, columns=prices.columns)


# ============== ALLOCATION LAYER ==============

def inverse_volatility_weights(returns: pd.DataFrame) -> pd.Series:
    """Calculate inverse volatility weights."""
    vol = returns.std() * np.sqrt(252)
    inv_vol = 1 / vol.replace(0, np.nan)
    weights = inv_vol / inv_vol.sum()
    return weights.fillna(0)


def equal_weights(assets: List[str]) -> pd.Series:
    """Equal weight allocation."""
    n = len(assets)
    return pd.Series(1/n, index=assets) if n > 0 else pd.Series()


# ============== REPORTING LAYER ==============

@dataclass
class Metrics:
    """Performance metrics."""
    total_return: float = 0.0
    cagr: float = 0.0
    volatility: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    calmar: float = 0.0
    win_rate: float = 0.0


def calculate_metrics(returns: pd.Series, rf: float = 0.04) -> Metrics:
    """Calculate performance metrics."""
    if returns.empty:
        return Metrics()
    
    returns = returns.dropna()
    equity = (1 + returns).cumprod()
    
    years = len(returns) / 252
    total_ret = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1/years) - 1 if years > 0 else 0
    vol = returns.std() * np.sqrt(252)
    
    # Drawdown
    rolling_max = equity.expanding().max()
    drawdown = (equity - rolling_max) / rolling_max
    max_dd = drawdown.min()
    
    # Risk-adjusted
    excess = returns.mean() * 252 - rf
    sharpe = excess / vol if vol > 0 else 0
    
    down_vol = returns[returns < 0].std() * np.sqrt(252) if (returns < 0).any() else 0
    sortino = excess / down_vol if down_vol > 0 else 0
    
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0
    
    win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
    
    return Metrics(
        total_return=total_ret,
        cagr=cagr,
        volatility=vol,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=max_dd,
        calmar=calmar,
        win_rate=win_rate
    )


# ============== PIPELINE ==============

class TradingPipeline:
    """Main trading pipeline."""
    
    STRATEGIES = {
        'Momentum_1M': lambda p: momentum_signals(p, 21, 5),
        'Momentum_3M': lambda p: momentum_signals(p, 63, 5),
        'Momentum_6M': lambda p: momentum_signals(p, 126, 5),
        'Dual_Momentum': lambda p: dual_momentum_signals(p, 252),
        'HRP': lambda p: hrp_signals(p)
    }
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.prices: Optional[pd.DataFrame] = None
        self.results: Dict[str, Dict] = {}
    
    def run(self, strategy_name: str = None) -> Dict[str, Any]:
        """Run pipeline for a strategy (or all)."""
        
        # Fetch data
        if self.prices is None:
            self.prices = fetch_prices(
                self.config.tickers,
                self.config.start_date,
                self.config.end_date
            )
        
        if self.prices.empty:
            print("❌ No data available")
            return {}
        
        returns = self.prices.pct_change().dropna()
        
        # Run strategies
        strategies = {strategy_name: self.STRATEGIES[strategy_name]} if strategy_name else self.STRATEGIES
        
        for name, signal_fn in strategies.items():
            print(f"\n📈 Running: {name}")
            
            # Generate signals
            signals = signal_fn(self.prices)
            
            # Calculate portfolio returns using signals
            # At each rebalance point, invest in signaled assets with equal weight
            port_returns_list = []
            
            for date in returns.index:
                if date not in signals.index:
                    port_returns_list.append(0)
                    continue
                
                # Get active signals for this date
                active = signals.loc[date]
                active_assets = active[active == 1].index.tolist()
                
                if len(active_assets) == 0:
                    port_returns_list.append(0)
                    continue
                
                # Equal weight among active assets
                day_returns = returns.loc[date].reindex(active_assets).dropna()
                if len(day_returns) > 0:
                    avg_return = day_returns.mean()
                    port_returns_list.append(avg_return)
                else:
                    port_returns_list.append(0)
            
            port_returns = pd.Series(port_returns_list, index=returns.index)
            equity = (1 + port_returns).cumprod()
            final_value = self.config.initial_capital * equity.iloc[-1]
            
            # Metrics
            metrics = calculate_metrics(port_returns)
            
            # Get final weights (latest signal)
            latest = signals.iloc[-1]
            active = latest[latest == 1].index.tolist()
            weights = equal_weights(active)
            
            self.results[name] = {
                'final_value': final_value,
                'metrics': metrics,
                'weights': weights.to_dict()
            }
            
            print(f"   Active positions: {len(active)}")
            print(f"   Final Value: ${final_value:,.0f}")
            print(f"   CAGR: {metrics.cagr:.2%}")
            print(f"   Sharpe: {metrics.sharpe:.3f}")
            print(f"   Max DD: {metrics.max_drawdown:.2%}")
        
        return self.results
    
    def compare(self) -> pd.DataFrame:
        """Compare all strategies."""
        if not self.results:
            print("Run strategies first")
            return pd.DataFrame()
        
        rows = []
        for name, data in self.results.items():
            m = data['metrics']
            rows.append({
                'Strategy': name,
                'Final Value': f"${data['final_value']:,.0f}",
                'CAGR': f"{m.cagr:.2%}",
                'Sharpe': f"{m.sharpe:.3f}",
                'Sortino': f"{m.sortino:.3f}",
                'Max DD': f"{m.max_drawdown:.2%}",
                'Calmar': f"{m.calmar:.3f}",
                'Win Rate': f"{m.win_rate:.1%}"
            })
        
        return pd.DataFrame(rows).sort_values('Sharpe', ascending=False, key=lambda x: x.str.extract(r'(-?\d+\.?\d*)')[0].astype(float))
    
    def save_results(self, path: str = None):
        """Save results to JSON."""
        path = path or f"{self.config.output_dir}/pipeline_results.json"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        export = {
            'generated_at': datetime.now().isoformat(),
            'config': {
                'start_date': self.config.start_date,
                'end_date': self.config.end_date,
                'initial_capital': self.config.initial_capital
            },
            'strategies': {}
        }
        
        for name, data in self.results.items():
            m = data['metrics']
            export['strategies'][name] = {
                'final_value': data['final_value'],
                'metrics': {
                    'CAGR': f"{m.cagr:.2%}",
                    'Sharpe Ratio': f"{m.sharpe:.3f}",
                    'Sortino Ratio': f"{m.sortino:.3f}",
                    'Volatility': f"{m.volatility:.2%}",
                    'Max Drawdown': f"{m.max_drawdown:.2%}",
                    'Calmar Ratio': f"{m.calmar:.3f}",
                    'Win Rate': f"{m.win_rate:.1%}"
                }
            }
        
        with open(path, 'w') as f:
            json.dump(export, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {path}")


# ============== CLI ==============

def main():
    parser = argparse.ArgumentParser(description="Trading Pipeline")
    parser.add_argument('command', choices=['scan', 'list', 'compare'])
    parser.add_argument('--strategy', '-s', default=None)
    parser.add_argument('--start-date', default='2020-01-01')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        print("\n📋 Available Strategies:")
        for name in TradingPipeline.STRATEGIES.keys():
            print(f"   • {name}")
        return
    
    config = PipelineConfig(start_date=args.start_date)
    pipeline = TradingPipeline(config)
    
    if args.command == 'scan':
        print("\n" + "=" * 60)
        print("🚀 TRADING PIPELINE SCAN")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)
        
        pipeline.run(args.strategy)
        pipeline.save_results()
        
        print("\n" + "=" * 60)
        print("📊 COMPARISON")
        print("=" * 60)
        print(pipeline.compare().to_string(index=False))
    
    elif args.command == 'compare':
        # Load from file
        results_file = Path("reports/pipeline_results.json")
        if results_file.exists():
            with open(results_file) as f:
                data = json.load(f)
            print(f"\nLast scan: {data.get('generated_at')}")
            for name, strat in data.get('strategies', {}).items():
                print(f"\n{name}:")
                for k, v in strat.get('metrics', {}).items():
                    print(f"   {k}: {v}")
        else:
            print("No saved results. Run 'scan' first.")


if __name__ == "__main__":
    main()
