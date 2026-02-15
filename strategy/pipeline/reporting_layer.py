"""
Reporting Layer
===============
Performance reporting using QuantStats and custom metrics.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import warnings

warnings.filterwarnings('ignore')

# Try to import quantstats
try:
    import quantstats as qs
    HAS_QUANTSTATS = True
except ImportError:
    HAS_QUANTSTATS = False
    print("Warning: quantstats not installed. Using basic reporting.")


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    
    # Returns
    total_return: float = 0.0
    cagr: float = 0.0
    
    # Risk
    volatility: float = 0.0
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    
    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trading
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Rolling
    rolling_sharpe_30d: float = 0.0
    rolling_sharpe_90d: float = 0.0
    rolling_vol_30d: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'Total Return': f"{self.total_return:.2%}",
            'CAGR': f"{self.cagr:.2%}",
            'Volatility': f"{self.volatility:.2%}",
            'Max Drawdown': f"{self.max_drawdown:.2%}",
            'Sharpe Ratio': f"{self.sharpe_ratio:.3f}",
            'Sortino Ratio': f"{self.sortino_ratio:.3f}",
            'Calmar Ratio': f"{self.calmar_ratio:.3f}",
            'Win Rate': f"{self.win_rate:.1%}",
            'Rolling Sharpe (30D)': f"{self.rolling_sharpe_30d:.3f}",
            'Rolling Sharpe (90D)': f"{self.rolling_sharpe_90d:.3f}",
            'Rolling Vol (30D)': f"{self.rolling_vol_30d:.2%}"
        }


@dataclass
class StrategyReport:
    """Complete report for a strategy."""
    strategy_name: str
    metrics: PerformanceMetrics
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    rolling_metrics: pd.DataFrame
    trade_stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ReportingManager:
    """
    Performance reporting and analysis.
    
    Provides:
    - Standard performance metrics
    - Rolling statistics
    - HTML report generation
    - Strategy comparison
    """
    
    def __init__(self, risk_free_rate: float = 0.04):
        self.risk_free_rate = risk_free_rate
        self._reports: Dict[str, StrategyReport] = {}
    
    def calculate_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series = None
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            returns: Strategy returns (daily)
            benchmark_returns: Optional benchmark returns
            
        Returns:
            PerformanceMetrics object
        """
        metrics = PerformanceMetrics()
        
        if returns.empty:
            return metrics
        
        returns = returns.dropna()
        
        # Total return
        equity = (1 + returns).cumprod()
        metrics.total_return = equity.iloc[-1] - 1
        
        # CAGR
        years = len(returns) / 252
        if years > 0:
            metrics.cagr = (equity.iloc[-1]) ** (1 / years) - 1
        
        # Volatility (annualized)
        metrics.volatility = returns.std() * np.sqrt(252)
        
        # Drawdown
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max
        metrics.max_drawdown = drawdown.min()
        metrics.avg_drawdown = drawdown[drawdown < 0].mean() if (drawdown < 0).any() else 0
        
        # Sharpe Ratio
        excess_return = returns.mean() * 252 - self.risk_free_rate
        if metrics.volatility > 0:
            metrics.sharpe_ratio = excess_return / metrics.volatility
        
        # Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        if downside_vol > 0:
            metrics.sortino_ratio = excess_return / downside_vol
        
        # Calmar Ratio
        if metrics.max_drawdown != 0:
            metrics.calmar_ratio = metrics.cagr / abs(metrics.max_drawdown)
        
        # Win Rate
        winning_days = (returns > 0).sum()
        total_days = len(returns)
        if total_days > 0:
            metrics.win_rate = winning_days / total_days
        
        # Average Win/Loss
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        metrics.avg_win = wins.mean() if len(wins) > 0 else 0
        metrics.avg_loss = losses.mean() if len(losses) > 0 else 0
        
        # Profit Factor
        total_wins = wins.sum() if len(wins) > 0 else 0
        total_losses = abs(losses.sum()) if len(losses) > 0 else 0
        if total_losses > 0:
            metrics.profit_factor = total_wins / total_losses
        
        # Rolling metrics
        if len(returns) >= 30:
            rolling_ret_30 = returns.rolling(30).mean() * 252
            rolling_vol_30 = returns.rolling(30).std() * np.sqrt(252)
            rolling_sharpe_30 = (rolling_ret_30 - self.risk_free_rate) / rolling_vol_30
            metrics.rolling_sharpe_30d = rolling_sharpe_30.iloc[-1] if not pd.isna(rolling_sharpe_30.iloc[-1]) else 0
            metrics.rolling_vol_30d = rolling_vol_30.iloc[-1] if not pd.isna(rolling_vol_30.iloc[-1]) else 0
        
        if len(returns) >= 90:
            rolling_ret_90 = returns.rolling(90).mean() * 252
            rolling_vol_90 = returns.rolling(90).std() * np.sqrt(252)
            rolling_sharpe_90 = (rolling_ret_90 - self.risk_free_rate) / rolling_vol_90
            metrics.rolling_sharpe_90d = rolling_sharpe_90.iloc[-1] if not pd.isna(rolling_sharpe_90.iloc[-1]) else 0
        
        return metrics
    
    def calculate_rolling_metrics(
        self,
        returns: pd.Series,
        windows: List[int] = None
    ) -> pd.DataFrame:
        """
        Calculate rolling performance metrics.
        
        Args:
            returns: Daily returns
            windows: Rolling window sizes (default: 21, 63, 126, 252 days)
            
        Returns:
            DataFrame with rolling metrics
        """
        windows = windows or [21, 63, 126, 252]
        
        rolling_data = {}
        
        for window in windows:
            prefix = f"{window}D"
            
            # Rolling return
            rolling_ret = returns.rolling(window).apply(
                lambda x: (1 + x).prod() - 1, raw=False
            )
            rolling_data[f'{prefix}_Return'] = rolling_ret
            
            # Rolling volatility
            rolling_vol = returns.rolling(window).std() * np.sqrt(252)
            rolling_data[f'{prefix}_Vol'] = rolling_vol
            
            # Rolling Sharpe
            ann_ret = returns.rolling(window).mean() * 252
            rolling_sharpe = (ann_ret - self.risk_free_rate) / rolling_vol
            rolling_data[f'{prefix}_Sharpe'] = rolling_sharpe
        
        return pd.DataFrame(rolling_data)
    
    def generate_report(
        self,
        returns: pd.Series,
        strategy_name: str,
        prices: pd.Series = None
    ) -> StrategyReport:
        """
        Generate complete strategy report.
        
        Args:
            returns: Daily returns
            strategy_name: Name of the strategy
            prices: Optional price series for equity curve
            
        Returns:
            StrategyReport object
        """
        # Calculate metrics
        metrics = self.calculate_metrics(returns)
        
        # Equity curve
        equity_curve = (1 + returns).cumprod()
        
        # Drawdown curve
        rolling_max = equity_curve.expanding().max()
        drawdown_curve = (equity_curve - rolling_max) / rolling_max
        
        # Rolling metrics
        rolling_metrics = self.calculate_rolling_metrics(returns)
        
        report = StrategyReport(
            strategy_name=strategy_name,
            metrics=metrics,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            rolling_metrics=rolling_metrics
        )
        
        self._reports[strategy_name] = report
        return report
    
    def generate_html_report(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series = None,
        output_path: str = None,
        title: str = "Strategy Report"
    ) -> str:
        """
        Generate HTML report using QuantStats.
        
        Args:
            returns: Daily returns
            benchmark_returns: Benchmark returns (default: SPY)
            output_path: Path to save HTML file
            title: Report title
            
        Returns:
            Path to generated HTML file
        """
        if not HAS_QUANTSTATS:
            print("QuantStats not available for HTML report")
            return self._generate_basic_html(returns, output_path, title)
        
        output_path = output_path or f"reports/{title.replace(' ', '_')}.html"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if benchmark_returns is not None:
                qs.reports.html(
                    returns,
                    benchmark=benchmark_returns,
                    output=output_path,
                    title=title
                )
            else:
                qs.reports.html(
                    returns,
                    output=output_path,
                    title=title
                )
            
            print(f"📊 HTML report saved to: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error generating HTML report: {e}")
            return self._generate_basic_html(returns, output_path, title)
    
    def _generate_basic_html(
        self,
        returns: pd.Series,
        output_path: str,
        title: str
    ) -> str:
        """Generate basic HTML report without QuantStats."""
        metrics = self.calculate_metrics(returns)
        equity = (1 + returns).cumprod()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #1a1a2e; color: #eee; }}
                h1 {{ color: #00d4ff; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #333; padding: 12px; text-align: left; }}
                th {{ background: #16213e; color: #00d4ff; }}
                tr:nth-child(even) {{ background: #0f0f23; }}
                .metric-positive {{ color: #00ff88; }}
                .metric-negative {{ color: #ff4444; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            
            <h2>Performance Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
        """
        
        for key, value in metrics.to_dict().items():
            css_class = ""
            if "%" in str(value):
                num = float(value.strip('%')) / 100
                css_class = "metric-positive" if num > 0 else "metric-negative"
            html += f'<tr><td>{key}</td><td class="{css_class}">{value}</td></tr>'
        
        html += """
            </table>
        </body>
        </html>
        """
        
        output_path = output_path or f"reports/{title.replace(' ', '_')}.html"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        print(f"📊 Basic HTML report saved to: {output_path}")
        return output_path
    
    def compare_strategies(
        self,
        strategy_returns: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """
        Compare multiple strategies.
        
        Args:
            strategy_returns: Dict of strategy_name -> returns
            
        Returns:
            DataFrame with comparison metrics
        """
        comparison = []
        
        for name, returns in strategy_returns.items():
            metrics = self.calculate_metrics(returns)
            
            comparison.append({
                'Strategy': name,
                'Total Return': f"{metrics.total_return:.2%}",
                'CAGR': f"{metrics.cagr:.2%}",
                'Volatility': f"{metrics.volatility:.2%}",
                'Sharpe': f"{metrics.sharpe_ratio:.3f}",
                'Sortino': f"{metrics.sortino_ratio:.3f}",
                'Max DD': f"{metrics.max_drawdown:.2%}",
                'Calmar': f"{metrics.calmar_ratio:.3f}",
                'Win Rate': f"{metrics.win_rate:.1%}"
            })
        
        df = pd.DataFrame(comparison)
        
        # Sort by Sharpe ratio
        df['Sharpe_sort'] = df['Sharpe'].astype(float)
        df = df.sort_values('Sharpe_sort', ascending=False).drop('Sharpe_sort', axis=1)
        
        return df
    
    def export_to_json(
        self,
        strategy_name: str = None
    ) -> Dict[str, Any]:
        """Export reports to JSON format for API/dashboard."""
        if strategy_name and strategy_name in self._reports:
            report = self._reports[strategy_name]
            return {
                'strategy_name': report.strategy_name,
                'metrics': report.metrics.to_dict(),
                'equity_curve': report.equity_curve.to_dict(),
                'timestamp': report.timestamp.isoformat()
            }
        
        # Export all
        return {
            name: {
                'strategy_name': report.strategy_name,
                'metrics': report.metrics.to_dict(),
                'timestamp': report.timestamp.isoformat()
            }
            for name, report in self._reports.items()
        }
