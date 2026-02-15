"""
Backtesting Module
==================
High-performance backtesting using vectorbt.

Features:
- Portfolio simulation with transaction costs
- Multiple rebalancing frequencies
- Performance metrics (Sharpe, Sortino, Max DD, Calmar)
- Comparison with benchmarks
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import warnings

# vectorbt for high-performance backtesting
import vectorbt as vbt

from strategy.infrastructure.config import CONFIG, BACKTEST_CONFIG, is_us_ticker

# Import UniverseProvider for Point-in-Time universe selection (survivorship bias-free)
try:
    from strategy.data.universe import UniverseProvider
    UNIVERSE_PROVIDER_AVAILABLE = True
except ImportError:
    UNIVERSE_PROVIDER_AVAILABLE = False

warnings.filterwarnings('ignore')


@dataclass
class BacktestResult:
    """Container for backtest results."""
    portfolio_value: pd.Series
    returns: pd.Series
    weights_history: pd.DataFrame
    trades: pd.DataFrame
    metrics: Dict
    benchmark_value: Optional[pd.Series] = None


class PortfolioBacktester:
    """
    Backtest portfolio strategies with realistic costs.
    
    Uses vectorbt for efficient vectorized operations.
    """
    
    def __init__(self,
                 prices: pd.DataFrame,
                 initial_capital: float = None,
                 volumes: pd.DataFrame = None,
                 max_volume_participation: float = 0.02):
        """
        Initialize backtester.
        
        Args:
            prices: DataFrame of prices (AUD-normalized)
            initial_capital: Starting capital in AUD
            volumes: DataFrame of daily volumes (optional, for liquidity constraints)
            max_volume_participation: Max fraction of daily volume (default: 2%)
        """
        self.prices = prices
        self.initial_capital = initial_capital or BACKTEST_CONFIG.INITIAL_CAPITAL_AUD
        self.returns = prices.pct_change().fillna(0)
        self.volumes = volumes
        self.max_volume_participation = max_volume_participation
        
    def run_backtest(self,
                     weights_func: Callable[[pd.DataFrame, int], pd.Series],
                     rebalance_freq: str = 'monthly',
                     include_costs: bool = True,
                     execution_delay: int = 1,
                     slippage_bps: float = 0.5,
                     market_impact_bps: float = 0.25,
                     use_dynamic_universe: bool = False,
                     index_name: str = 'SP500') -> BacktestResult:
        """
        Run backtest with dynamic weight allocation.
        
        UPDATED 2025-12: Fixed look-ahead bias by adding execution delay.
        Signals are now calculated at T-1 Close but applied to returns starting
        at T+execution_delay, simulating realistic order execution.
        
        Args:
            weights_func: Function that takes (prices_up_to_date, index) and returns weights
            rebalance_freq: 'daily', 'weekly', 'monthly', 'quarterly'
            include_costs: Whether to include transaction costs
            execution_delay: Days to delay execution (default=1, T+1 execution)
                            Set to 0 for legacy behavior (look-ahead bias)
            slippage_bps: Bid-ask half-spread in basis points (default: 0.5 = 0.005%)
            market_impact_bps: Price impact in basis points (default: 0.25 = 0.0025%)
            use_dynamic_universe: If True, filter stocks to only those in the index
                                  at each rebalance date (survivorship bias-free)
            index_name: Index to use for dynamic universe (default: 'SP500')
            
        Returns:
            BacktestResult object
            
        Note:
            With execution_delay=1 (default), if signal is generated on Monday close,
            the trade executes at Tuesday close. This is conservative but realistic.
        """
        # Get rebalance dates
        rebalance_dates = self._get_rebalance_dates(rebalance_freq)
        
        # Initialize tracking
        portfolio_values = [self.initial_capital]
        weights_history = []
        trades_list = []
        current_weights = pd.Series(0, index=self.prices.columns)
        current_value = self.initial_capital
        
        # Track pending weight changes for execution delay
        pending_weights = {}  # date -> target_weights
        
        # Initialize Universe Provider for Point-in-Time selection
        universe_provider = None
        if use_dynamic_universe and UNIVERSE_PROVIDER_AVAILABLE:
            universe_provider = UniverseProvider()
        
        dates = self.prices.index
        
        for i in range(1, len(dates)):
            date = dates[i]
            prev_date = dates[i-1]
            
            # Check if we have pending weights to apply (execution delay)
            if date in pending_weights:
                target_weights = pending_weights.pop(date)
                
                # Calculate trading costs if applicable
                if include_costs:
                    cost = self._calculate_rebalance_cost(
                        current_weights, 
                        target_weights, 
                        current_value,
                        slippage_bps=slippage_bps,
                        market_impact_bps=market_impact_bps
                    )
                    current_value -= cost
                    
                    # Record trades
                    trade_record = {
                        'date': date,
                        'cost': cost,
                        'turnover': abs(target_weights - current_weights).sum(),
                        'slippage_bps': slippage_bps,
                        'market_impact_bps': market_impact_bps
                    }
                    trades_list.append(trade_record)
                
                current_weights = target_weights
            
            # Check if rebalance signal day
            if date in rebalance_dates:
                # --- Dynamic Universe Selection (Survivorship Bias-Free) ---
                if universe_provider is not None:
                    # Get tickers that were in the index on this date
                    valid_tickers = universe_provider.get_assets_at_date(date, index_name=index_name)
                    
                    # Intersect with data we actually have prices for
                    available_universe = [t for t in valid_tickers if t in self.prices.columns]
                    
                    if not available_universe:
                        # Fallback if universe is empty (before data starts)
                        available_universe = self.prices.columns.tolist()
                else:
                    # Legacy: Use all columns
                    available_universe = self.prices.columns.tolist()
                
                # Get prices filtered to available universe
                lookback_prices = self.prices.loc[:prev_date, available_universe]
                target_weights = weights_func(lookback_prices, i)
                
                # Ensure weights use full index for portfolio tracking
                full_weights = pd.Series(0.0, index=self.prices.columns)
                for ticker in target_weights.index:
                    if ticker in full_weights.index:
                        full_weights[ticker] = target_weights[ticker]
                target_weights = full_weights
                
                # --- LIQUIDITY GUARDRAIL: Cap positions at 2% of daily volume ---
                if self.volumes is not None and date in self.volumes.index:
                    daily_vol = self.volumes.loc[date]
                    max_shares_map = (daily_vol * self.max_volume_participation).to_dict()
                    
                    adjusted_weights = target_weights.copy()
                    liquidity_capped = False
                    
                    for asset in target_weights.index:
                        weight = target_weights[asset]
                        if weight == 0 or asset not in self.prices.columns:
                            continue
                        
                        price = self.prices.loc[date, asset]
                        if price <= 0:
                            continue
                            
                        target_shares = (weight * current_value) / price
                        max_shares = max_shares_map.get(asset, float('inf'))
                        
                        if target_shares > max_shares and max_shares > 0:
                            # Cap at max allowed shares
                            allowed_weight = (max_shares * price) / current_value
                            adjusted_weights[asset] = allowed_weight
                            liquidity_capped = True
                    
                    if liquidity_capped:
                        # Note: We reduce exposure rather than renormalize
                        # This creates a "cash buffer" for illiquid positions
                        target_weights = adjusted_weights
                
                # Schedule execution for T+execution_delay
                if execution_delay > 0 and i + execution_delay < len(dates):
                    exec_date = dates[i + execution_delay]
                    pending_weights[exec_date] = target_weights
                else:
                    # Legacy behavior (execution_delay=0) or end of data
                    # Apply immediately (with look-ahead bias warning)
                    if include_costs:
                        cost = self._calculate_rebalance_cost(
                            current_weights, 
                            target_weights, 
                            current_value,
                            slippage_bps=slippage_bps,
                            market_impact_bps=market_impact_bps
                        )
                        current_value -= cost
                        trades_list.append({
                            'date': date,
                            'cost': cost,
                            'turnover': abs(target_weights - current_weights).sum(),
                            'slippage_bps': slippage_bps,
                            'market_impact_bps': market_impact_bps
                        })
                    current_weights = target_weights
            
            # Calculate portfolio return
            daily_returns = self.returns.loc[date]
            portfolio_return = (current_weights * daily_returns).sum()
            current_value *= (1 + portfolio_return)
            
            portfolio_values.append(current_value)
            weights_history.append({
                'date': date,
                **current_weights.to_dict()
            })
        
        # Compile results
        portfolio_value = pd.Series(portfolio_values, index=[dates[0]] + list(dates[1:]))
        portfolio_returns = portfolio_value.pct_change().dropna()
        
        weights_df = pd.DataFrame(weights_history)
        if not weights_df.empty:
            weights_df.set_index('date', inplace=True)
        
        trades_df = pd.DataFrame(trades_list)
        
        metrics = self._calculate_metrics(portfolio_returns, portfolio_value)
        
        # Add execution parameters to metrics for transparency
        metrics['execution_delay'] = execution_delay
        metrics['slippage_bps'] = slippage_bps
        metrics['market_impact_bps'] = market_impact_bps
        
        return BacktestResult(
            portfolio_value=portfolio_value,
            returns=portfolio_returns,
            weights_history=weights_df,
            trades=trades_df,
            metrics=metrics
        )
    
    def run_static_backtest(self,
                            weights: pd.Series,
                            rebalance_freq: str = 'monthly',
                            include_costs: bool = True,
                            execution_delay: int = 1,
                            slippage_bps: float = 0.5,
                            market_impact_bps: float = 0.25) -> BacktestResult:
        """
        Run backtest with static target weights.
        
        Simpler than dynamic backtest - just maintain constant weights.
        
        Args:
            weights: Target portfolio weights
            rebalance_freq: Rebalancing frequency
            include_costs: Include transaction costs
            execution_delay: Days to delay execution (default=1)
            slippage_bps: Bid-ask half-spread in basis points (default=0.5)
            market_impact_bps: Market impact in basis points (default=0.25)
            
        Returns:
            BacktestResult object
        """
        def static_weights_func(prices, idx):
            # Filter to only include assets that exist in prices
            available = [c for c in weights.index if c in prices.columns]
            w = weights[available]
            return w / w.sum()  # Renormalize
        
        return self.run_backtest(
            static_weights_func, 
            rebalance_freq, 
            include_costs,
            execution_delay=execution_delay,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps
        )
    
    def run_momentum_backtest(self,
                              lookback: int = 252,
                              top_n: int = 3,
                              rebalance_freq: str = 'monthly',
                              execution_delay: int = 1,
                              slippage_bps: float = 0.5,
                              market_impact_bps: float = 0.25) -> BacktestResult:
        """
        Run momentum strategy backtest.
        
        Selects top N assets by lookback return, equal weight.
        
        Args:
            lookback: Lookback period in days
            top_n: Number of top assets to hold
            rebalance_freq: Rebalancing frequency
            execution_delay: Days to delay execution (default=1)
            slippage_bps: Bid-ask half-spread in basis points (default=0.5)
            market_impact_bps: Market impact in basis points (default=0.25)
            
        Returns:
            BacktestResult object
        """
        def momentum_weights_func(prices, idx):
            if len(prices) < lookback:
                # Not enough data, equal weight
                n = len(prices.columns)
                return pd.Series(1/n, index=prices.columns)
            
            # Calculate lookback returns
            returns = prices.iloc[-1] / prices.iloc[-lookback] - 1
            
            # Select top N
            top_assets = returns.nlargest(top_n).index
            
            # Equal weight among top assets
            weights = pd.Series(0, index=prices.columns)
            weights[top_assets] = 1.0 / top_n
            
            return weights
        
        return self.run_backtest(
            momentum_weights_func, 
            rebalance_freq, 
            include_costs=True,
            execution_delay=execution_delay,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps
        )
    
    def run_dual_momentum_backtest(self,
                                    lookback: int = 252,
                                    defensive_asset: str = 'TLT',
                                    rebalance_freq: str = 'monthly',
                                    execution_delay: int = 1,
                                    slippage_bps: float = 0.5,
                                    market_impact_bps: float = 0.25) -> BacktestResult:
        """
        Run Antonacci Dual Momentum strategy.
        
        Logic:
        1. If best risky asset has positive return -> hold it
        2. If best risky asset has negative return -> hold defensive asset
        
        Args:
            lookback: Lookback period
            defensive_asset: Safe haven asset ticker
            rebalance_freq: Rebalancing frequency
            execution_delay: Days to delay execution (default=1)
            slippage_bps: Bid-ask half-spread in basis points (default=0.5)
            market_impact_bps: Market impact in basis points (default=0.25)
            
        Returns:
            BacktestResult object
        """
        risky_assets = [c for c in self.prices.columns if c != defensive_asset]
        
        def dual_momentum_weights_func(prices, idx):
            if len(prices) < lookback:
                # Not enough data
                return pd.Series(1/len(prices.columns), index=prices.columns)
            
            # Calculate lookback returns
            returns = prices.iloc[-1] / prices.iloc[-lookback] - 1
            
            # Find best risky asset
            risky_returns = returns[risky_assets]
            best_risky = risky_returns.idxmax()
            best_risky_return = risky_returns[best_risky]
            
            weights = pd.Series(0, index=prices.columns)
            
            # Absolute momentum check
            if best_risky_return > 0:
                weights[best_risky] = 1.0
            else:
                # Go to defensive
                if defensive_asset in prices.columns:
                    weights[defensive_asset] = 1.0
                else:
                    # Fallback to cash (0% return)
                    weights[risky_assets[0]] = 0  # Hold nothing
            
            return weights
        
        return self.run_backtest(
            dual_momentum_weights_func, 
            rebalance_freq, 
            include_costs=True,
            execution_delay=execution_delay,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps
        )
    
    def _get_rebalance_dates(self, freq: str) -> pd.DatetimeIndex:
        """Get dates when rebalancing occurs."""
        dates = self.prices.index
        
        if freq == 'daily':
            return dates
        elif freq == 'weekly':
            # Every Monday
            return dates[dates.weekday == 0]
        elif freq == 'monthly':
            # First trading day of each month
            return dates[dates.to_series().dt.is_month_start | 
                        (dates.to_series().shift(1).dt.month != dates.to_series().dt.month)]
        elif freq == 'quarterly':
            # First trading day of each quarter
            return dates[dates.to_series().dt.is_quarter_start |
                        (dates.to_series().shift(1).dt.quarter != dates.to_series().dt.quarter)]
        else:
            raise ValueError(f"Unknown frequency: {freq}")
    
    def _calculate_rebalance_cost(self,
                                   current_weights: pd.Series,
                                   target_weights: pd.Series,
                                   portfolio_value: float,
                                   slippage_bps: float = 0.5,
                                   market_impact_bps: float = 0.25) -> float:
        """
        Calculate trading cost including brokerage, slippage, and market impact.
        
        UPDATED 2025-12: Added slippage and market impact modeling.
        
        Cost Components:
        1. Flat brokerage: $3 AUD per trade (Stake.com structure)
        2. Slippage: Half the bid-ask spread (default 0.5 bps = 0.005%)
        3. Market impact: Price impact proportional to trade size (default 0.25 bps)
        
        Args:
            current_weights: Current portfolio weights
            target_weights: Target portfolio weights
            portfolio_value: Current portfolio value in AUD
            slippage_bps: Bid-ask half-spread in basis points (0.5 = 0.005%)
            market_impact_bps: Base market impact in basis points (0.25 = 0.0025%)
            
        Returns:
            Total estimated transaction cost in AUD
            
        Note:
            For small-caps or less liquid names, consider higher values:
            - slippage_bps: 2-5 for small-caps, 0.25-0.5 for mega-caps
            - market_impact_bps: 1-3 for volatile stocks, 0.1-0.5 for ETFs
        """
        total_cost = 0.0
        trade_fee_aud = 3.0  # $3 AUD per trade
        
        for ticker in target_weights.index:
            current = current_weights.get(ticker, 0)
            target = target_weights[ticker]
            delta = abs(target - current)
            
            if delta > 0.005:  # Skip tiny trades (< 0.5% weight change)
                trade_value = delta * portfolio_value
                
                # 1. Flat brokerage fee
                total_cost += trade_fee_aud
                
                # 2. Slippage cost (half-spread, proportional to trade value)
                slippage_cost = trade_value * (slippage_bps / 10000)
                total_cost += slippage_cost
                
                # 3. Market impact (square-root model for larger trades)
                # Impact increases with sqrt of relative trade size
                # Reference size: 5% of portfolio (delta=0.05)
                if delta > 0.01:  # Only apply impact for meaningful trades
                    impact_multiplier = np.sqrt(delta / 0.05)
                    impact_cost = trade_value * (market_impact_bps / 10000) * impact_multiplier
                    total_cost += impact_cost
        
        return total_cost
    
    def _calculate_metrics(self,
                           returns: pd.Series,
                           portfolio_value: pd.Series) -> Dict:
        """Calculate performance metrics."""
        # Annualization factor
        trading_days = 252
        
        # Basic metrics
        total_return = (portfolio_value.iloc[-1] / portfolio_value.iloc[0]) - 1
        years = len(returns) / trading_days
        cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Risk metrics
        volatility = returns.std() * np.sqrt(trading_days)
        
        # Sharpe ratio
        excess_return = returns.mean() * trading_days - CONFIG.RISK_FREE_RATE
        sharpe = excess_return / volatility if volatility > 0 else 0
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(trading_days) if len(downside_returns) > 0 else volatility
        sortino = excess_return / downside_std if downside_std > 0 else 0
        
        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Calmar ratio
        calmar = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Win rate
        win_rate = (returns > 0).mean()
        
        return {
            'total_return': total_return,
            'cagr': cagr,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar,
            'win_rate': win_rate,
            'best_day': returns.max(),
            'worst_day': returns.min(),
            'trading_days': len(returns)
        }


class VectorBTBacktester:
    """
    High-performance backtesting using vectorbt directly.
    
    More efficient for large-scale backtests and parameter optimization.
    """
    
    def __init__(self, prices: pd.DataFrame):
        """
        Initialize vectorbt backtester.
        
        Args:
            prices: DataFrame of prices (AUD-normalized)
        """
        self.prices = prices
        
    def run_momentum_scan(self,
                          lookback_range: List[int] = [63, 126, 189, 252],
                          top_n_range: List[int] = [2, 3, 4, 5]) -> pd.DataFrame:
        """
        Scan momentum parameters to find optimal settings.
        
        Args:
            lookback_range: List of lookback periods to test
            top_n_range: List of top N values to test
            
        Returns:
            DataFrame of results for each parameter combination
        """
        results = []
        
        for lookback in lookback_range:
            for top_n in top_n_range:
                # Calculate momentum signal
                returns_lookback = self.prices.pct_change(lookback)
                
                # Rank assets
                ranks = returns_lookback.rank(axis=1, pct=True)
                
                # Create signal: 1 for top N percentile
                threshold = 1 - (top_n / len(self.prices.columns))
                signal = (ranks >= threshold).astype(float)
                
                # Equal weight among selected
                weights = signal.div(signal.sum(axis=1), axis=0).fillna(0)
                
                # Calculate portfolio returns
                daily_returns = self.prices.pct_change()
                port_returns = (weights.shift(1) * daily_returns).sum(axis=1)
                
                # Calculate metrics
                sharpe = port_returns.mean() / port_returns.std() * np.sqrt(252)
                cum_return = (1 + port_returns).prod() - 1
                max_dd = ((1 + port_returns).cumprod() / (1 + port_returns).cumprod().cummax() - 1).min()
                
                results.append({
                    'lookback': lookback,
                    'top_n': top_n,
                    'sharpe': sharpe,
                    'total_return': cum_return,
                    'max_drawdown': max_dd,
                    'avg_turnover': weights.diff().abs().sum(axis=1).mean()
                })
        
        return pd.DataFrame(results).sort_values('sharpe', ascending=False)
    
    def run_vbt_backtest(self, weights: pd.DataFrame) -> vbt.Portfolio:
        """
        Run backtest using vectorbt Portfolio.
        
        Args:
            weights: DataFrame of target weights over time
            
        Returns:
            vbt.Portfolio object with results
        """
        # Create portfolio from target weights
        portfolio = vbt.Portfolio.from_orders(
            close=self.prices,
            size=weights,
            size_type='targetpercent',
            freq='D',
            init_cash=BACKTEST_CONFIG.INITIAL_CAPITAL_AUD
        )
        
        return portfolio


def demo():
    """Demonstrate backtesting functionality."""
    print("=" * 60)
    print("Backtesting Demo")
    print("=" * 60)
    
    # Create sample price data
    np.random.seed(42)
    n_days = 252 * 5  # 5 years
    
    tickers = ['SPY', 'QQQ', 'TLT', 'GLD', 'VGS.AX', 'VAS.AX']
    dates = pd.date_range('2019-01-01', periods=n_days, freq='B')
    
    # Simulated prices with realistic drift
    prices_data = {}
    drifts = [0.10, 0.12, 0.03, 0.05, 0.08, 0.07]  # Annual drifts
    vols = [0.16, 0.20, 0.12, 0.15, 0.14, 0.13]  # Annual vols
    
    for ticker, drift, vol in zip(tickers, drifts, vols):
        daily_drift = drift / 252
        daily_vol = vol / np.sqrt(252)
        returns = np.random.normal(daily_drift, daily_vol, n_days)
        prices_data[ticker] = 100 * np.exp(np.cumsum(returns))
    
    prices = pd.DataFrame(prices_data, index=dates)
    
    # Initialize backtester
    bt = PortfolioBacktester(prices, initial_capital=100000)
    
    print("\n" + "=" * 60)
    print("1. Equal Weight Buy & Hold")
    print("=" * 60)
    
    equal_weights = pd.Series(1/len(tickers), index=tickers)
    result = bt.run_static_backtest(equal_weights, rebalance_freq='monthly')
    
    print(f"Final Value: ${result.portfolio_value.iloc[-1]:,.2f}")
    print(f"Total Return: {result.metrics['total_return']*100:.2f}%")
    print(f"CAGR: {result.metrics['cagr']*100:.2f}%")
    print(f"Volatility: {result.metrics['volatility']*100:.2f}%")
    print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.3f}")
    print(f"Max Drawdown: {result.metrics['max_drawdown']*100:.2f}%")
    
    print("\n" + "=" * 60)
    print("2. Momentum Strategy (Top 3)")
    print("=" * 60)
    
    mom_result = bt.run_momentum_backtest(lookback=252, top_n=3)
    
    print(f"Final Value: ${mom_result.portfolio_value.iloc[-1]:,.2f}")
    print(f"Total Return: {mom_result.metrics['total_return']*100:.2f}%")
    print(f"CAGR: {mom_result.metrics['cagr']*100:.2f}%")
    print(f"Volatility: {mom_result.metrics['volatility']*100:.2f}%")
    print(f"Sharpe Ratio: {mom_result.metrics['sharpe_ratio']:.3f}")
    print(f"Max Drawdown: {mom_result.metrics['max_drawdown']*100:.2f}%")
    print(f"Total Trading Costs: ${mom_result.trades['cost'].sum():,.2f}")
    
    print("\n" + "=" * 60)
    print("3. Dual Momentum Strategy")
    print("=" * 60)
    
    dual_result = bt.run_dual_momentum_backtest(lookback=252, defensive_asset='TLT')
    
    print(f"Final Value: ${dual_result.portfolio_value.iloc[-1]:,.2f}")
    print(f"Total Return: {dual_result.metrics['total_return']*100:.2f}%")
    print(f"CAGR: {dual_result.metrics['cagr']*100:.2f}%")
    print(f"Volatility: {dual_result.metrics['volatility']*100:.2f}%")
    print(f"Sharpe Ratio: {dual_result.metrics['sharpe_ratio']:.3f}")
    print(f"Max Drawdown: {dual_result.metrics['max_drawdown']*100:.2f}%")
    
    print("\n" + "=" * 60)
    print("4. Momentum Parameter Scan")
    print("=" * 60)
    
    vbt_bt = VectorBTBacktester(prices)
    scan_results = vbt_bt.run_momentum_scan()
    
    print("\nTop 5 Parameter Combinations:")
    print(scan_results.head().to_string())


if __name__ == "__main__":
    demo()
