"""
Trading Pipeline Orchestrator
==============================
Main pipeline that coordinates all 4 layers.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

from .data_layer import DataManager, DataConfig, get_data_manager
from .signal_layer import SignalManager, BaseStrategy, SignalResult
from .allocation_layer import AllocationManager, AllocationConfig, AllocationResult
from .reporting_layer import ReportingManager, PerformanceMetrics, StrategyReport

# Delay import to avoid circular dependency
HAS_META = False
try:
    # Check if module exists without importing it at top level
    import strategy.quant2.meta_labeling.orchestrator
    HAS_META = True
except ImportError:
    pass


@dataclass
class PipelineConfig:
    """Configuration for the trading pipeline."""
    
    # Data
    tickers: List[str] = None
    start_date: str = "2020-01-01"
    end_date: str = None
    
    # Portfolio
    initial_capital: float = 100_000.0
    rebalance_frequency: str = "monthly"  # daily, weekly, monthly
    
    # Risk
    max_position_pct: float = 0.25
    max_drawdown_exit: float = 0.20
    
    # Output
    output_dir: str = "reports"

    # Meta-Labeling
    use_meta_labeling: bool = False
    meta_model_path: str = "models/meta_model.pkl"
    
    def __post_init__(self):
        if self.end_date is None:
            self.end_date = datetime.now().strftime("%Y-%m-%d")


@dataclass
class PipelineResult:
    """Complete result from pipeline execution."""
    
    strategy_name: str
    config: PipelineConfig
    
    # Results from each layer
    signals: SignalResult
    allocation: AllocationResult
    report: StrategyReport
    
    # Portfolio simulation
    equity_curve: pd.Series
    portfolio_returns: pd.Series
    final_value: float
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_seconds: float = 0


class TradingPipeline:
    """
    Main trading pipeline orchestrator.
    
    Coordinates:
    1. Data Layer - Fetches market data
    2. Signal Layer - Generates trading signals
    3. Allocation Layer - Optimizes portfolio weights
    4. Reporting Layer - Generates performance reports
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        
        # Initialize layers
        self.data_manager = DataManager()
        self.signal_manager = SignalManager()
        self.allocation_manager = AllocationManager()
        self.reporting_manager = ReportingManager()
        
        # Initialize Meta-Strategy Orchestrator
        self.meta_orchestrator = None
        if self.config.use_meta_labeling and HAS_META:
            try:
                from strategy.quant2.meta_labeling.orchestrator import MetaStrategyOrchestrator, MetaStrategyConfig
                self.meta_orchestrator = MetaStrategyOrchestrator(
                    MetaStrategyConfig(model_path=self.config.meta_model_path)
                )
            except ImportError as e:
                print(f"Warning: Failed to import MetaStrategyOrchestrator: {e}")

        # Cache
        self._prices: Optional[pd.DataFrame] = None
        self._results: Dict[str, PipelineResult] = {}
    
    def run(
        self,
        strategy_name: str = "Dual_Momentum",
        optimization_method: str = "HRP"
    ) -> PipelineResult:
        """
        Run the complete pipeline for a strategy.
        
        Args:
            strategy_name: Name of the registered strategy
            optimization_method: HRP, MVO, InverseVol, or EqualWeight
            
        Returns:
            PipelineResult with complete analysis
        """
        start_time = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"🚀 TRADING PIPELINE: {strategy_name}")
        print(f"{'='*60}")
        
        # 1. DATA LAYER
        print("\n📊 Layer 1: Fetching Data...")
        prices = self.data_manager.fetch_prices(
            tickers=self.config.tickers,
            start_date=self.config.start_date,
            end_date=self.config.end_date
        )
        self._prices = prices
        
        if prices.empty:
            raise ValueError("Failed to fetch price data")
        
        returns = prices.pct_change().dropna()
        
        # 2. SIGNAL LAYER
        print(f"\n📈 Layer 2: Generating Signals ({strategy_name})...")
        signal_result = self.signal_manager.generate_signals(
            strategy_name, prices
        )
        
        # 2b. META-LABELING FILTER (Optional)
        if self.config.use_meta_labeling and self.meta_orchestrator:
            print(f"\n🧠 Layer 2b: Applying Meta-Labeling Filter...")
            # Note: We need VIX and Volume for full features.
            # Currently Pipeline mostly handles Close prices.
            # This is a limitation we accept for now or need to fetch Volume/VIX.

            # Fetch Volume if not available (Basic attempt)
            # Fetch VIX (Basic attempt)
            # For now, we pass None and let Orchestrator handle missing data gracefully or skip features

            # If training is needed, we could run it here, but typically training is separate.
            # Here we assume inference mode.

            signal_result = self.meta_orchestrator.apply_filtering(
                signal_result, prices
            )

        # 3. ALLOCATION LAYER
        print(f"\n⚖️ Layer 3: Optimizing Allocation ({optimization_method})...")
        if optimization_method == "HRP":
            allocation_result = self.allocation_manager.optimize_hrp(
                returns, signal_result.signals
            )
        elif optimization_method == "MVO":
            allocation_result = self.allocation_manager.optimize_mvo(
                returns, signal_result.signals
            )
        else:
            allocation_result = self.allocation_manager.optimize_inverse_volatility(returns)
        
        # 4. SIMULATE PORTFOLIO
        print("\n💰 Simulating Portfolio...")
        portfolio_returns, equity_curve = self._simulate_portfolio(
            returns, signal_result.signals, allocation_result.weights
        )
        
        if equity_curve.empty:
            final_value = self.config.initial_capital
        else:
            final_value = self.config.initial_capital * equity_curve.iloc[-1]
        
        # 5. REPORTING LAYER
        print("\n📋 Layer 4: Generating Reports...")
        report = self.reporting_manager.generate_report(
            portfolio_returns, strategy_name
        )
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Create result
        result = PipelineResult(
            strategy_name=strategy_name,
            config=self.config,
            signals=signal_result,
            allocation=allocation_result,
            report=report,
            equity_curve=equity_curve,
            portfolio_returns=portfolio_returns,
            final_value=final_value,
            execution_time_seconds=execution_time
        )
        
        self._results[strategy_name] = result
        
        # Print summary
        self._print_summary(result)
        
        return result
    
    def run_all_strategies(self) -> Dict[str, PipelineResult]:
        """Run pipeline for all registered strategies."""
        results = {}
        
        for strategy_name in self.signal_manager.list_strategies():
            try:
                result = self.run(strategy_name)
                results[strategy_name] = result
            except Exception as e:
                print(f"⚠️ Error running {strategy_name}: {e}")
        
        return results
    
    def compare_strategies(self) -> pd.DataFrame:
        """Compare all executed strategies."""
        if not self._results:
            print("No results to compare. Run strategies first.")
            return pd.DataFrame()
        
        strategy_returns = {
            name: result.portfolio_returns
            for name, result in self._results.items()
        }
        
        return self.reporting_manager.compare_strategies(strategy_returns)
    
    def _simulate_portfolio(
        self,
        returns: pd.DataFrame,
        signals: pd.DataFrame,
        weights: pd.Series
    ) -> tuple:
        """
        Simulate portfolio performance.
        
        Returns:
            (portfolio_returns, equity_curve)
        """
        # Align data
        common_assets = weights.index.intersection(returns.columns)
        weights = weights[common_assets]
        returns = returns[common_assets]
        
        if len(common_assets) == 0:
            # If no assets selected, return flat equity curve
            zero_returns = pd.Series(0.0, index=returns.index)
            flat_equity = pd.Series(1.0, index=returns.index)
            return zero_returns, flat_equity
        
        # Portfolio returns (simple weighted average)
        portfolio_returns = (returns * weights).sum(axis=1)
        
        # Equity curve
        equity_curve = (1 + portfolio_returns).cumprod()
        
        return portfolio_returns, equity_curve
    
    def _print_summary(self, result: PipelineResult):
        """Print pipeline execution summary."""
        metrics = result.report.metrics
        
        print(f"\n{'='*60}")
        print(f"📊 RESULTS: {result.strategy_name}")
        print(f"{'='*60}")
        print(f"Final Value:    ${result.final_value:,.2f}")
        print(f"Total Return:   {metrics.total_return:.2%}")
        print(f"CAGR:           {metrics.cagr:.2%}")
        print(f"Volatility:     {metrics.volatility:.2%}")
        print(f"Sharpe Ratio:   {metrics.sharpe_ratio:.3f}")
        print(f"Sortino Ratio:  {metrics.sortino_ratio:.3f}")
        print(f"Max Drawdown:   {metrics.max_drawdown:.2%}")
        print(f"Calmar Ratio:   {metrics.calmar_ratio:.3f}")
        print(f"\nExecution Time: {result.execution_time_seconds:.2f}s")
        print(f"{'='*60}")
    
    def generate_html_report(
        self,
        strategy_name: str = None,
        benchmark_ticker: str = "SPY"
    ) -> str:
        """Generate HTML report for a strategy."""
        if strategy_name and strategy_name in self._results:
            result = self._results[strategy_name]
            returns = result.portfolio_returns
        else:
            # Get the latest result
            if not self._results:
                print("No results available")
                return ""
            result = list(self._results.values())[-1]
            returns = result.portfolio_returns
            strategy_name = result.strategy_name
        
        # Get benchmark returns
        benchmark_returns = None
        if self._prices is not None and benchmark_ticker in self._prices.columns:
            benchmark_returns = self._prices[benchmark_ticker].pct_change().dropna()
        
        output_path = f"{self.config.output_dir}/{strategy_name}_report.html"
        return self.reporting_manager.generate_html_report(
            returns,
            benchmark_returns=benchmark_returns,
            output_path=output_path,
            title=f"{strategy_name} Strategy Report"
        )
    
    def export_results_json(self) -> Dict[str, Any]:
        """Export all results to JSON format."""
        export = {
            'generated_at': datetime.now().isoformat(),
            'config': {
                'start_date': self.config.start_date,
                'end_date': self.config.end_date,
                'initial_capital': self.config.initial_capital
            },
            'strategies': {}
        }
        
        for name, result in self._results.items():
            export['strategies'][name] = {
                'final_value': result.final_value,
                'metrics': result.report.metrics.to_dict(),
                'weights': result.allocation.weights.to_dict(),
                'execution_time': result.execution_time_seconds
            }
        
        return export
    
    def save_results(self, output_path: str = None):
        """Save results to JSON file."""
        output_path = output_path or f"{self.config.output_dir}/pipeline_results.json"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = self.export_results_json()
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"💾 Results saved to: {output_path}")


def run_daily_scan() -> Dict[str, Any]:
    """
    Run daily scanning for all strategies.
    
    Returns dict with scan results for dashboard.
    """
    print("\n" + "=" * 70)
    print("📊 DAILY STRATEGY SCAN")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Initialize pipeline
    pipeline = TradingPipeline()
    
    # Run all strategies
    results = pipeline.run_all_strategies()
    
    # Compare
    comparison = pipeline.compare_strategies()
    print("\n📈 STRATEGY COMPARISON:")
    print(comparison.to_string(index=False))
    
    # Generate reports
    for strategy_name in results.keys():
        pipeline.generate_html_report(strategy_name)
    
    # Save results
    pipeline.save_results()
    
    return pipeline.export_results_json()


if __name__ == "__main__":
    run_daily_scan()
