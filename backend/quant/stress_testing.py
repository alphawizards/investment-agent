"""
Stress Testing Module
=====================
DFAST 2025 and custom stress scenario implementation.

2025 Institutional Standard:
- DFAST (Dodd-Frank Act Stress Test) scenarios
- Regime-dependent volatility multipliers
- Synthetic shock generation

Reference:
    Federal Reserve DFAST 2024/2025 Supervisory Scenarios
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class StressScenario(str, Enum):
    """Standard stress scenario types."""
    BASELINE = "baseline"
    ADVERSE = "adverse"
    SEVERELY_ADVERSE = "severely_adverse"
    CUSTOM = "custom"


@dataclass
class DFASTScenario:
    """
    DFAST 2025 Stress Scenario Definition.
    
    Based on Federal Reserve supervisory scenarios for stress testing.
    
    Attributes:
        name: Scenario identifier
        equity_shock: Equity market drawdown (e.g., -0.50 = -50%)
        vix_peak: Peak VIX level during stress
        vol_multiplier: Volatility multiplier for cost models
        duration_days: Duration of stress period
        recovery_days: Recovery period length
    """
    name: str
    equity_shock: float
    vix_peak: float
    vol_multiplier: float
    duration_days: int = 90
    recovery_days: int = 180
    description: str = ""
    
    def __post_init__(self):
        if self.equity_shock > 0:
            raise ValueError("equity_shock should be negative (e.g., -0.50 for -50%)")


# Pre-defined DFAST 2025 Scenarios
DFAST_BASELINE = DFASTScenario(
    name="DFAST_2025_Baseline",
    equity_shock=-0.10,
    vix_peak=25,
    vol_multiplier=1.0,
    duration_days=60,
    recovery_days=120,
    description="Baseline scenario - mild market correction"
)

DFAST_ADVERSE = DFASTScenario(
    name="DFAST_2025_Adverse",
    equity_shock=-0.30,
    vix_peak=45,
    vol_multiplier=2.0,
    duration_days=90,
    recovery_days=180,
    description="Adverse scenario - significant market decline with elevated volatility"
)

DFAST_SEVERELY_ADVERSE = DFASTScenario(
    name="DFAST_2025_Severely_Adverse",
    equity_shock=-0.50,
    vix_peak=65,
    vol_multiplier=3.0,
    duration_days=120,
    recovery_days=270,
    description="Severely adverse scenario - market crash comparable to 2008 GFC"
)

# Custom scenarios for specific events
COVID_CRASH = DFASTScenario(
    name="COVID_March_2020",
    equity_shock=-0.34,
    vix_peak=82.69,
    vol_multiplier=4.0,
    duration_days=23,
    recovery_days=150,
    description="COVID-19 market crash (Feb-Mar 2020)"
)

GFC_2008 = DFASTScenario(
    name="GFC_2008",
    equity_shock=-0.57,
    vix_peak=80.86,
    vol_multiplier=4.0,
    duration_days=365,
    recovery_days=730,
    description="Global Financial Crisis 2008"
)


# Registry of all scenarios
SCENARIO_REGISTRY: Dict[str, DFASTScenario] = {
    "baseline": DFAST_BASELINE,
    "adverse": DFAST_ADVERSE,
    "severely_adverse": DFAST_SEVERELY_ADVERSE,
    "covid_2020": COVID_CRASH,
    "gfc_2008": GFC_2008,
}


def get_scenario(name: str) -> DFASTScenario:
    """Get a registered scenario by name."""
    if name not in SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario: {name}. Available: {list(SCENARIO_REGISTRY.keys())}")
    return SCENARIO_REGISTRY[name]


def apply_stress_shock(
    prices: pd.DataFrame,
    scenario: DFASTScenario,
    shock_start_idx: Optional[int] = None
) -> pd.DataFrame:
    """
    Apply a stress shock to price data.
    
    Creates a synthetic stressed price path by:
    1. Applying gradual drawdown over duration_days
    2. Increasing volatility during stress period
    3. Gradual recovery over recovery_days
    
    Args:
        prices: Original price DataFrame
        scenario: Stress scenario to apply
        shock_start_idx: Index to start shock (default: middle of data)
        
    Returns:
        pd.DataFrame: Stressed price data
    """
    stressed_prices = prices.copy()
    n_samples = len(prices)
    
    # Default: start shock at middle of data
    if shock_start_idx is None:
        shock_start_idx = n_samples // 3
    
    shock_end_idx = min(shock_start_idx + scenario.duration_days, n_samples)
    recovery_end_idx = min(shock_end_idx + scenario.recovery_days, n_samples)
    
    # Create shock multiplier path
    shock_multiplier = np.ones(n_samples)
    
    # Drawdown phase (linear decline)
    if shock_end_idx > shock_start_idx:
        drawdown_steps = shock_end_idx - shock_start_idx
        drawdown_path = np.linspace(1.0, 1.0 + scenario.equity_shock, drawdown_steps)
        shock_multiplier[shock_start_idx:shock_end_idx] = drawdown_path
    
    # Recovery phase (linear recovery to original level)
    if recovery_end_idx > shock_end_idx:
        recovery_steps = recovery_end_idx - shock_end_idx
        recovery_path = np.linspace(1.0 + scenario.equity_shock, 1.0, recovery_steps)
        shock_multiplier[shock_end_idx:recovery_end_idx] = recovery_path
    
    # Apply shock to all columns
    for col in stressed_prices.columns:
        base_price = prices[col].iloc[shock_start_idx]
        # Apply multiplicative shock
        stressed_prices.loc[stressed_prices.index[shock_start_idx:], col] *= \
            shock_multiplier[shock_start_idx:n_samples][:len(stressed_prices) - shock_start_idx]
    
    return stressed_prices


def apply_volatility_regime(
    returns: pd.DataFrame,
    scenario: DFASTScenario,
    stress_start_idx: Optional[int] = None,
    stress_duration: Optional[int] = None
) -> pd.DataFrame:
    """
    Apply increased volatility during stress regime.
    
    Args:
        returns: Original returns DataFrame
        scenario: Stress scenario (uses vol_multiplier)
        stress_start_idx: Start of stress period
        stress_duration: Duration of elevated volatility
        
    Returns:
        pd.DataFrame: Returns with elevated volatility during stress
    """
    stressed_returns = returns.copy()
    n_samples = len(returns)
    
    if stress_start_idx is None:
        stress_start_idx = n_samples // 3
    if stress_duration is None:
        stress_duration = scenario.duration_days
    
    stress_end_idx = min(stress_start_idx + stress_duration, n_samples)
    
    # Scale returns during stress period
    stressed_returns.iloc[stress_start_idx:stress_end_idx] *= scenario.vol_multiplier
    
    return stressed_returns


def run_stress_test(
    prices: pd.DataFrame,
    strategy_func: callable,
    strategy_params: dict,
    scenarios: List[str] = None,
    transaction_cost_bps: float = 15.0
) -> Dict[str, dict]:
    """
    Run backtest under multiple stress scenarios.
    
    Args:
        prices: Price DataFrame
        strategy_func: Strategy function (prices, **params) -> weights
        strategy_params: Strategy parameters
        scenarios: List of scenario names to test (default: all standard)
        transaction_cost_bps: Base transaction cost
        
    Returns:
        Dict mapping scenario names to results
    """
    if scenarios is None:
        scenarios = ["baseline", "adverse", "severely_adverse"]
    
    results = {}
    
    # Run baseline (no stress)
    try:
        weights = strategy_func(prices, **strategy_params)
        price_returns = prices.pct_change()
        portfolio_returns = (weights.shift(1) * price_returns).sum(axis=1).dropna()
        
        # Calculate costs with base volatility
        weight_changes = weights.diff().abs().sum(axis=1)
        daily_turnover = weight_changes / 2
        daily_cost = daily_turnover * (transaction_cost_bps / 10000)
        portfolio_returns = portfolio_returns - daily_cost.reindex(portfolio_returns.index, fill_value=0)
        
        results["no_stress"] = {
            "sharpe": _calc_sharpe(portfolio_returns),
            "total_return": (1 + portfolio_returns).prod() - 1,
            "max_drawdown": _calc_max_drawdown(portfolio_returns),
            "scenario": None
        }
    except Exception as e:
        results["no_stress"] = {"error": str(e)}
    
    # Run each stress scenario
    for scenario_name in scenarios:
        scenario = get_scenario(scenario_name)
        
        try:
            # Apply stress shock to prices
            stressed_prices = apply_stress_shock(prices, scenario)
            
            # Run strategy on stressed data
            weights = strategy_func(stressed_prices, **strategy_params)
            
            # Calculate returns
            price_returns = stressed_prices.pct_change()
            portfolio_returns = (weights.shift(1) * price_returns).sum(axis=1).dropna()
            
            # Apply elevated costs during stress (using vol_multiplier)
            weight_changes = weights.diff().abs().sum(axis=1)
            daily_turnover = weight_changes / 2
            # Higher costs during stress due to wider spreads
            adjusted_cost_bps = transaction_cost_bps * scenario.vol_multiplier
            daily_cost = daily_turnover * (adjusted_cost_bps / 10000)
            portfolio_returns = portfolio_returns - daily_cost.reindex(portfolio_returns.index, fill_value=0)
            
            results[scenario_name] = {
                "sharpe": _calc_sharpe(portfolio_returns),
                "total_return": float((1 + portfolio_returns).prod() - 1),
                "max_drawdown": _calc_max_drawdown(portfolio_returns),
                "scenario": scenario.name,
                "equity_shock": scenario.equity_shock,
                "vol_multiplier": scenario.vol_multiplier
            }
            
        except Exception as e:
            results[scenario_name] = {"error": str(e), "scenario": scenario_name}
    
    return results


def _calc_sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    """Calculate Sharpe ratio."""
    if len(returns) < 20:
        return 0.0
    excess = returns.mean() * 252 - rf
    vol = returns.std() * np.sqrt(252)
    return float(excess / vol) if vol > 1e-6 else 0.0


def _calc_max_drawdown(returns: pd.Series) -> float:
    """Calculate maximum drawdown."""
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    return float(drawdown.min())


def print_stress_test_results(results: Dict[str, dict]):
    """Print stress test results in a formatted table."""
    print("\n" + "=" * 70)
    print("STRESS TEST RESULTS")
    print("=" * 70)
    
    print(f"\n{'Scenario':<25}{'Sharpe':<12}{'Return':<12}{'Max DD':<12}{'Vol Mult':<10}")
    print("-" * 70)
    
    for scenario_name, metrics in results.items():
        if "error" in metrics:
            print(f"{scenario_name:<25}{'ERROR':<12}{metrics.get('error', '')}")
            continue
        
        sharpe = metrics.get('sharpe', 0)
        ret = metrics.get('total_return', 0) * 100
        dd = metrics.get('max_drawdown', 0) * 100
        vol_mult = metrics.get('vol_multiplier', 1.0)
        
        print(f"{scenario_name:<25}{sharpe:<12.4f}{ret:<12.1f}%{dd:<11.1f}%{vol_mult:<10.1f}")
    
    print("-" * 70)
