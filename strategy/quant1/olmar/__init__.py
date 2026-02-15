"""
OLMAR (On-Line Moving Average Reversion) Strategy Package
==========================================================
Implements cost-aware OLMAR strategy for online portfolio selection.

This is an ADDITIONAL strategy - does not modify existing strategies.

Algorithms:
- OLMAR: Mean reversion using moving average price prediction

Reference:
- B. Li and S.C.H. Hoi, "On-Line Portfolio Selection with Moving Average Reversion"
- Marigold/universal-portfolios (MIT License)
"""

from strategy.quant1.olmar.kernels import (
    calculate_price_relatives,
    predict_ma_reversion,
    predict_ema_reversion,
    project_simplex,
    olmar_update,
    olmar_weights,
    olmar_weights_ema,
    validate_weights,
    calculate_dsr
)

from strategy.quant1.olmar.constraints import (
    calculate_turnover,
    apply_turnover_cap,
    apply_cost_penalty,
    smooth_weights_over_time,
    warn_if_zero_costs,
    calculate_cost_drag,
    get_turnover_stats
)

from strategy.quant1.olmar.olmar_strategy import (
    OLMARConfig,
    OLMARSignalResult,
    OLMARStrategy,
    create_olmar_weekly,
    create_olmar_monthly,
    create_olmar_daily
)

__all__ = [
    # Kernels
    'calculate_price_relatives',
    'predict_ma_reversion',
    'predict_ema_reversion',
    'project_simplex',
    'olmar_update',
    'olmar_weights',
    'olmar_weights_ema',
    'validate_weights',
    'calculate_dsr',
    # Constraints
    'calculate_turnover',
    'apply_turnover_cap',
    'apply_cost_penalty',
    'smooth_weights_over_time',
    'warn_if_zero_costs',
    'calculate_cost_drag',
    'get_turnover_stats',
    # Strategy
    'OLMARConfig',
    'OLMARSignalResult',
    'OLMARStrategy',
    'create_olmar_weekly',
    'create_olmar_monthly',
    'create_olmar_daily'
]
