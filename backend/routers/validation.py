"""
Validation API Router
=====================
API endpoints for strategy statistical validation (DSR/PSR).
Refactored to support full async operations.
"""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np
import pandas as pd

# Import validation functions
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strategy.infrastructure.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    sharpe_ratio_std,
    estimated_sharpe_ratio
)

router = APIRouter(prefix="/api/validation", tags=["validation"])


# === Response Models ===

class ValidityMetrics(BaseModel):
    psr: float
    dsr: float
    num_trials: int
    is_significant: bool
    confidence_level: str


class StrategyValidation(BaseModel):
    id: str
    name: str
    sharpe: float
    sortino: float
    max_drawdown: float
    validity: ValidityMetrics


class ValidationResponse(BaseModel):
    strategies: List[StrategyValidation]
    total_trials_rejected: int
    total_trials_accepted: int
    generated_at: str


# === Endpoints ===

@router.get("/strategies", response_model=ValidationResponse)
async def get_validated_strategies():
    """
    Get all strategies with DSR/PSR validation metrics.
    """
    # Mock data logic (kept synchronous but wrapped in endpoint)
    mock_strategies = [
        {
            "id": "momentum-alpha",
            "name": "Residual Momentum Alpha",
            "sharpe": 1.45,
            "sortino": 2.1,
            "max_drawdown": -0.14,
            "validity": {
                "psr": 0.97,
                "dsr": 1.24,
                "num_trials": 15,
                "is_significant": True,
                "confidence_level": "HIGH"
            }
        },
        {
            "id": "stat-arb-pairs",
            "name": "Statistical Arbitrage Pairs",
            "sharpe": 1.92,
            "sortino": 2.8,
            "max_drawdown": -0.08,
            "validity": {
                "psr": 0.99,
                "dsr": 1.65,
                "num_trials": 8,
                "is_significant": True,
                "confidence_level": "HIGH"
            }
        }
    ]
    
    significant = sum(1 for s in mock_strategies if s["validity"]["is_significant"])
    
    return ValidationResponse(
        strategies=[StrategyValidation(**s) for s in mock_strategies],
        total_trials_accepted=significant,
        total_trials_rejected=len(mock_strategies) - significant,
        generated_at=datetime.now().isoformat()
    )


@router.post("/calculate-dsr")
async def calculate_dsr(
    sharpe_ratio: float,
    n_trials: int = 1,
    n_samples: int = 252,
    skewness: float = 0.0,
    kurtosis: float = 3.0
) -> Dict[str, Any]:
    """
    Calculate Deflated Sharpe Ratio for a strategy.
    """
    def _do_calculation():
        # Generate synthetic returns matching the given Sharpe
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, n_samples))
        
        # Scale to match target Sharpe
        current_sr = estimated_sharpe_ratio(returns)
        if current_sr != 0:
            returns *= (sharpe_ratio / current_sr)
        
        # Calculate DSR
        sr_std = sharpe_ratio_std(returns)
        dsr = deflated_sharpe_ratio(sharpe_ratio, n_trials, returns)
        psr = probabilistic_sharpe_ratio(sharpe_ratio, 0.0, sr_std)
        
        confidence = "HIGH" if dsr > 0.95 else "MEDIUM" if dsr > 0.80 else "LOW"
        
        return {
            "sharpe_ratio": sharpe_ratio,
            "deflated_sharpe_ratio": round(dsr, 4),
            "probabilistic_sharpe_ratio": round(psr, 4),
            "n_trials": n_trials,
            "n_samples": n_samples,
            "is_significant": dsr > 0.95,
            "confidence_level": confidence,
            "interpretation": f"After testing {n_trials} variations, there is a {dsr*100:.1f}% probability this strategy's performance is genuine."
        }

    return await run_in_threadpool(_do_calculation)
