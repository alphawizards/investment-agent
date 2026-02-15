"""
Quantitative Models Module
==========================
Contains execution cost models and validation utilities.

2025 Institutional Standards:
- Hybrid ASX/US transaction cost model
- Deflated Sharpe Ratio (DSR) validation
- Combinatorial Purged Cross-Validation (CPCV)
- DFAST 2025 Stress Testing
- Regime Detection
"""

from .execution import (
    calculate_transaction_cost,
    calculate_portfolio_rebalance_cost,
    almgren_chriss_cost
)
from .validation import (
    calculate_dsr,
    calculate_sharpe_ratio,
    validate_backtest_result,
    calculate_deflated_sharpe,
    CombinatorialPurgedKFold,
    run_cpcv_backtest
)
from .stress_testing import (
    DFASTScenario,
    StressScenario,
    DFAST_BASELINE,
    DFAST_ADVERSE,
    DFAST_SEVERELY_ADVERSE,
    get_scenario,
    run_stress_test,
    apply_stress_shock,
    print_stress_test_results
)
from .regime_detection import (
    VolatilityRegime,
    detect_volatility_regime,
    get_regime_vol_multiplier,
    calculate_regime_adjusted_costs,
    print_regime_summary
)

__all__ = [
    # Execution
    'calculate_transaction_cost',
    'calculate_portfolio_rebalance_cost',
    'almgren_chriss_cost',
    # Validation
    'calculate_dsr',
    'calculate_sharpe_ratio',
    'validate_backtest_result',
    'calculate_deflated_sharpe',
    # CPCV
    'CombinatorialPurgedKFold',
    'run_cpcv_backtest',
    # Stress Testing
    'DFASTScenario',
    'StressScenario',
    'DFAST_BASELINE',
    'DFAST_ADVERSE',
    'DFAST_SEVERELY_ADVERSE',
    'get_scenario',
    'run_stress_test',
    'apply_stress_shock',
    'print_stress_test_results',
    # Regime Detection
    'VolatilityRegime',
    'detect_volatility_regime',
    'get_regime_vol_multiplier',
    'calculate_regime_adjusted_costs',
    'print_regime_summary',
]

