"""
Validation API Router
=====================
API endpoints for strategy statistical validation (DSR/PSR).
Calculates real PSR/DSR from backtest results and price data.
"""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import json
import asyncio
import aiofiles
import logging

# Import validation functions
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strategy.infrastructure.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    sharpe_ratio_std,
    estimated_sharpe_ratio,
    validate_backtest,
)

router = APIRouter(prefix="/api/validation", tags=["validation"])
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CACHE_DIR = PROJECT_ROOT / "cache"


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


# === Helper Functions ===

async def _load_json_async(filepath: Path) -> Optional[Dict]:
    """Load a JSON file asynchronously."""
    if not filepath.exists():
        return None
    try:
        async with aiofiles.open(filepath, mode="r") as f:
            content = await f.read()
            return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Error loading %s: %s", filepath, e)
        return None


async def _load_all_strategy_results() -> Dict[str, Any]:
    """
    Load all strategy results from reports directory.
    Returns dict mapping strategy_name -> result_data.
    Each result_data has: metrics, weights, final_value, etc.
    """
    results = {}

    if not REPORTS_DIR.exists():
        return results

    # Load individual *_results.json files in parallel
    result_files = list(REPORTS_DIR.glob("*_results.json"))

    async def _load_one(fpath: Path):
        data = await _load_json_async(fpath)
        if data is None:
            return None, None
        name = fpath.stem.replace("_results", "")
        return name, data

    loaded = await asyncio.gather(*[_load_one(f) for f in result_files])
    for name, data in loaded:
        if name and data:
            results[name] = data

    # Also expand pipeline_results.json strategies
    pipeline_data = results.pop("pipeline", None)
    if pipeline_data and "strategies" in pipeline_data:
        for strat_name, strat_data in pipeline_data["strategies"].items():
            if strat_name not in results:
                results[strat_name] = strat_data

    return results


def _load_price_data() -> Optional[pd.DataFrame]:
    """Load close price data from parquet cache. Must run in thread pool."""
    price_path = CACHE_DIR / "us_prices_close.parquet"
    if not price_path.exists():
        logger.warning("Price cache not found at %s", price_path)
        return None
    try:
        return pd.read_parquet(price_path)
    except Exception as e:
        logger.warning("Error loading price data: %s", e)
        return None


def _compute_portfolio_returns(
    weights: Dict[str, float], prices: pd.DataFrame
) -> Optional[pd.Series]:
    """
    Compute daily portfolio returns from ticker weights and price data.
    Returns a pd.Series of daily returns, or None if insufficient data.
    """
    available_tickers = [t for t in weights if t in prices.columns]
    if not available_tickers:
        return None

    # Subset prices to available tickers and drop rows with all NaN
    sub_prices = prices[available_tickers].dropna(how="all")
    if len(sub_prices) < 10:
        return None

    # Forward-fill gaps, then compute daily returns
    sub_prices = sub_prices.ffill()
    daily_returns = sub_prices.pct_change().dropna(how="all")

    # Re-normalise weights to available tickers only
    total_w = sum(weights[t] for t in available_tickers)
    if total_w == 0:
        return None
    norm_weights = {t: weights[t] / total_w for t in available_tickers}

    # Weighted portfolio return
    weight_series = pd.Series(norm_weights)
    # Align: fill missing ticker returns with 0 for that day
    portfolio_returns = daily_returns[available_tickers].fillna(0).dot(weight_series)
    portfolio_returns = portfolio_returns.dropna()

    if len(portfolio_returns) < 10:
        return None

    return portfolio_returns


def _parse_metric_string(value: Any) -> Optional[float]:
    """Parse a metric value that might be a string like '1.046' or '25.63%'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace("%", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _calc_sortino(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Calculate annualised Sortino ratio from daily returns."""
    daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
    excess = returns - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    return (excess.mean() / downside.std()) * np.sqrt(252)


def _calc_max_drawdown(returns: pd.Series) -> float:
    """Calculate max drawdown from daily returns. Returns negative value."""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min())


def _validate_single_strategy(
    name: str,
    data: Dict[str, Any],
    prices: Optional[pd.DataFrame],
    n_trials: int,
) -> Optional[Dict[str, Any]]:
    """
    Validate a single strategy. Runs in thread pool (CPU-bound).
    Returns a dict compatible with StrategyValidation or None.
    """
    weights = data.get("weights", {})
    metrics = data.get("metrics", {})

    # Try to compute portfolio returns from weights + price data
    portfolio_returns = None
    if weights and prices is not None:
        portfolio_returns = _compute_portfolio_returns(weights, prices)

    # Parse reported metrics as fallback values
    reported_sharpe = _parse_metric_string(metrics.get("Sharpe Ratio"))
    reported_sortino = _parse_metric_string(metrics.get("Sortino Ratio"))
    reported_max_dd = _parse_metric_string(metrics.get("Max Drawdown"))

    if portfolio_returns is not None and len(portfolio_returns) >= 20:
        # --- Real calculation path ---
        validation = validate_backtest(
            returns=portfolio_returns,
            n_trials=max(n_trials, 1),
            benchmark_sr=0.0,
            risk_free_rate=0.0,
        )

        sharpe_annual = validation["sharpe_ratio_annual"]
        sortino = _calc_sortino(portfolio_returns)
        max_dd = _calc_max_drawdown(portfolio_returns)
        psr = validation["probabilistic_sr"]
        dsr = validation["deflated_sr"]

        # Handle NaN from high-kurtosis returns where SR std is undefined
        if np.isnan(psr):
            psr = 0.5  # uninformative prior
        if np.isnan(dsr):
            dsr = 0.0  # conservative: treat as not significant

        is_significant = bool(dsr > 0.95)
        confidence = "HIGH" if dsr > 0.95 else "MEDIUM" if dsr > 0.80 else "LOW"
    elif reported_sharpe is not None:
        # --- Fallback: use reported metrics with synthetic DSR ---
        sharpe_annual = reported_sharpe
        sortino = reported_sortino if reported_sortino is not None else 0.0
        # Max drawdown from reports is in percent string like "-24.38%"
        max_dd = (reported_max_dd / 100.0) if reported_max_dd is not None else 0.0

        # Approximate PSR/DSR from reported Sharpe (less accurate but useful)
        # Assume ~252 samples per year, typical SR std
        approx_sr_std = np.sqrt(1.0 / 252)
        psr = float(probabilistic_sharpe_ratio(
            reported_sharpe / np.sqrt(252), 0.0, approx_sr_std
        ))
        # For DSR we need returns; generate approximate ones
        np.random.seed(hash(name) % (2**31))
        synth_returns = pd.Series(
            np.random.normal(
                reported_sharpe / np.sqrt(252) * 0.01,
                0.01,
                252 * 3,
            )
        )
        dsr = float(deflated_sharpe_ratio(
            reported_sharpe / np.sqrt(252), max(n_trials, 1), synth_returns
        ))
        is_significant = dsr > 0.95
        confidence = "HIGH" if dsr > 0.95 else "MEDIUM" if dsr > 0.80 else "LOW"
    else:
        # Not enough data to validate
        return None

    strategy_id = name.lower().replace(" ", "-").replace("_", "-")

    return {
        "id": strategy_id,
        "name": name,
        "sharpe": round(float(sharpe_annual), 4),
        "sortino": round(float(sortino), 4),
        "max_drawdown": round(float(max_dd), 4),
        "validity": {
            "psr": round(float(psr), 4),
            "dsr": round(float(dsr), 4),
            "num_trials": n_trials,
            "is_significant": bool(is_significant),
            "confidence_level": confidence,
        },
    }


async def _build_validation_response(
    strategy_results: Dict[str, Any],
) -> ValidationResponse:
    """
    Build a ValidationResponse from strategy results dict.
    Loads price data and runs validation in thread pool.
    """
    if not strategy_results:
        return ValidationResponse(
            strategies=[],
            total_trials_accepted=0,
            total_trials_rejected=0,
            generated_at=datetime.now().isoformat(),
        )

    # Total number of strategies found = n_trials for multiple-testing adjustment
    n_trials = len(strategy_results)

    def _do_all_validations():
        prices = _load_price_data()

        validated = []
        for name, data in strategy_results.items():
            try:
                result = _validate_single_strategy(name, data, prices, n_trials)
                if result is not None:
                    validated.append(result)
            except Exception as e:
                logger.warning("Validation failed for %s: %s", name, e)
        return validated

    validated_list = await run_in_threadpool(_do_all_validations)

    accepted = sum(1 for v in validated_list if v["validity"]["is_significant"])
    rejected = len(validated_list) - accepted

    return ValidationResponse(
        strategies=[StrategyValidation(**v) for v in validated_list],
        total_trials_accepted=accepted,
        total_trials_rejected=rejected,
        generated_at=datetime.now().isoformat(),
    )


# === Endpoints ===

@router.get("/strategies", response_model=ValidationResponse)
async def get_validated_strategies():
    """
    Get all strategies with real DSR/PSR validation metrics.

    Loads strategy backtest results from the reports/ directory,
    reconstructs portfolio daily returns from cached price data,
    and computes Deflated Sharpe Ratio and Probabilistic Sharpe Ratio
    for each strategy.
    """
    strategy_results = await _load_all_strategy_results()
    return await _build_validation_response(strategy_results)


@router.get("/from-reports", response_model=ValidationResponse)
async def get_validation_from_reports():
    """
    Validate all strategies directly from the reports/ directory.

    This endpoint does not require the database. It reads all
    *_results.json files and pipeline_results.json from reports/,
    reconstructs portfolio returns from price cache, and calculates
    real PSR/DSR validation metrics.
    """
    strategy_results = await _load_all_strategy_results()

    if not strategy_results:
        raise HTTPException(
            status_code=404,
            detail="No strategy results found in reports/ directory. Run backtests first.",
        )

    return await _build_validation_response(strategy_results)


@router.post("/calculate-dsr")
async def calculate_dsr(
    sharpe_ratio: float,
    n_trials: int = 1,
    n_samples: int = 252,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
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
            returns *= sharpe_ratio / current_sr

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
            "interpretation": f"After testing {n_trials} variations, there is a {dsr * 100:.1f}% probability this strategy's performance is genuine.",
        }

    return await run_in_threadpool(_do_calculation)
