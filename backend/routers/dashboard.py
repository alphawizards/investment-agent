"""
Dashboard Router
================
Endpoints for dashboard data aggregation.
Refactored to support full async operations (2025 standard).
"""

import sys
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import aiofiles
import asyncio

# Add parent path for strategy imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import authentication
try:
    from backend.auth import get_current_user
except ImportError:
    from auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def load_json_file_async(filepath: str) -> Optional[Dict]:
    """Safely load a JSON file asynchronously."""
    path = Path(filepath)
    if path.exists():
        try:
            async with aiofiles.open(path, mode='r') as f:
                content = await f.read()
                return json.loads(content)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {filepath}: {e}")
    return None


async def get_strategy_results_async() -> Dict[str, Any]:
    """Load all strategy results from reports directory asynchronously."""
    results = {}
    reports_dir = Path("reports")
    
    if reports_dir.exists():
        # reports_dir.glob is synchronous, but we can process files asynchronously
        files = list(reports_dir.glob("*_results.json"))
        
        async def load_file(results_file):
            try:
                async with aiofiles.open(results_file, mode='r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    strategy_name = results_file.stem.replace("_results", "")
                    return strategy_name, data
            except:
                return None, None

        # Load all files in parallel
        tasks = [load_file(f) for f in files]
        loaded_data = await asyncio.gather(*tasks)
        
        for name, data in loaded_data:
            if name:
                results[name] = data
    
    # Also try pipeline_results.json
    pipeline_results = await load_json_file_async("reports/pipeline_results.json")
    if pipeline_results and "strategies" in pipeline_results:
        for name, data in pipeline_results["strategies"].items():
            if name not in results:
                results[name] = data
    
    return results


@router.get("/data-status")
async def get_data_status() -> Dict[str, Any]:
    """
    Get data availability and freshness status for all universes.
    """
    try:
        from strategy.infrastructure.data_freshness import DataFreshness, get_data_status as _get_status
        # Assuming _get_status might be synchronous, but wrapping in a thread if needed
        # For now, if it's purely computation/metadata check, call directly
        return _get_status()
    except ImportError as e:
        # Fallback if modules not available
        return {
            "error": "Data freshness modules not available",
            "message": str(e),
            "generated_at": datetime.now().isoformat(),
            "overall_status": "unknown",
            "universes": [
                {"name": "sp500", "status": "unknown"},
                {"name": "nasdaq100", "status": "unknown"},
                {"name": "asx200", "status": "unknown"}
            ]
        }
    except Exception as e:
        return {
            "error": "Failed to get data status",
            "message": str(e),
            "generated_at": datetime.now().isoformat()
        }


@router.get("/")
async def get_dashboard_overview(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get main dashboard overview with all strategy metrics.
    """
    results = await get_strategy_results_async()
    
    # Calculate summary stats
    total_strategies = len(results)
    strategies_with_results = sum(1 for r in results.values() if r.get("metrics"))
    
    # Get best performer
    best_strategy = None
    best_return = float('-inf')
    
    strategy_summaries = []
    for name, data in results.items():
        metrics = data.get("metrics", {})
        
        # Parse CAGR (might be string like "15.2%")
        cagr_str = metrics.get("cagr", "0%")
        try:
            if isinstance(cagr_str, str):
                cagr = float(cagr_str.replace("%", "")) / 100
            else:
                cagr = float(cagr_str)
        except:
            cagr = 0
        
        if cagr > best_return:
            best_return = cagr
            best_strategy = name
        
        strategy_summaries.append({
            "name": name,
            "final_value": data.get("final_value", 0),
            "cagr": metrics.get("cagr", "N/A"),
            "sharpe": metrics.get("sharpe_ratio", "N/A"),
            "max_drawdown": metrics.get("max_drawdown", "N/A"),
            "status": "active" if metrics else "no_data"
        })
    
    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_strategies": total_strategies,
            "strategies_with_results": strategies_with_results,
            "best_performer": best_strategy,
            "best_cagr": f"{best_return*100:.1f}%" if best_strategy else "N/A"
        },
        "strategies": strategy_summaries,
        "last_update": datetime.now().isoformat()
    }


@router.get("/quant1")
async def get_quant1_dashboard() -> Dict[str, Any]:
    """
    Get Quant 1.0 dashboard data.
    """
    # Try to load from generated JSON first
    quant1_data = await load_json_file_async("dashboard/data/quant1_dashboard.json")
    
    if quant1_data:
        quant1_data["source"] = "cached"
        quant1_data["retrieved_at"] = datetime.now().isoformat()
        return quant1_data
    
    # Generate fresh data
    results = await get_strategy_results_async()
    
    quant1_strategies = ["Momentum", "Dual_Momentum", "HRP", "InverseVolatility"]
    
    data = {
        "generated_at": datetime.now().isoformat(),
        "source": "live",
        "strategies": {}
    }
    
    for strategy in quant1_strategies:
        if strategy in results:
            data["strategies"][strategy] = {
                "status": "active",
                "metrics": results[strategy].get("metrics", {}),
                "weights": results[strategy].get("weights", {}),
                "final_value": results[strategy].get("final_value", 0)
            }
        else:
            data["strategies"][strategy] = {
                "status": "no_data",
                "message": "Run backtest to generate data"
            }
    
    return data


@router.get("/quant2")
async def get_quant2_dashboard(universe: str = "SPX500") -> Dict[str, Any]:
    """
    Get Quant 2.0 dashboard data.
    """
    # Get universe info
    try:
        from strategy.stock_universe import get_universe_info, get_universe_tickers
        universe_info = get_universe_info(universe)
        universe_tickers = get_universe_tickers(universe)
    except (ImportError, ValueError) as e:
        # Fallback if universe module unavailable or invalid key
        universe_info = {"name": universe, "ticker_count": 0, "error": str(e)}
        universe_tickers = []
    
    # Try to load from generated JSON first
    quant2_data = await load_json_file_async("dashboard/data/quant2_dashboard.json")
    
    if quant2_data:
        quant2_data["source"] = "cached"
        quant2_data["retrieved_at"] = datetime.now().isoformat()
        quant2_data["universe"] = universe_info
        return quant2_data
    
    # Generate fresh data
    results = await get_strategy_results_async()
    
    quant2_strategies = [
        "Regime_Detection", "Stat_Arb", "Residual_Momentum", 
        "Meta_Labeling", "Short_Vol", "NCO"
    ]
    
    data = {
        "generated_at": datetime.now().isoformat(),
        "source": "live",
        "universe": universe_info,
        "universe_key": universe,
        "ticker_count": len(universe_tickers),
        "regime": {
            "current": "UNKNOWN",
            "probabilities": {"bull": 0.33, "bear": 0.33, "sideways": 0.34},
            "message": "Run Regime Detection strategy to update"
        },
        "strategies": {}
    }
    
    for strategy in quant2_strategies:
        if strategy in results:
            data["strategies"][strategy] = {
                "status": "active",
                "metrics": results[strategy].get("metrics", {}),
                "final_value": results[strategy].get("final_value", 0)
            }
        else:
            data["strategies"][strategy] = {
                "status": "no_data",
                "message": "Run backtest to generate data"
            }
    
    # Try to get regime from quant2_data directory
    regime_data = await load_json_file_async("dashboard/quant2_data/regime_overview.json")
    if regime_data:
        data["regime"] = regime_data
    
    return data


@router.get("/olmar")
async def get_olmar_dashboard() -> Dict[str, Any]:
    """
    Get OLMAR (Online Learning Mean Reversion) dashboard data.
    """
    # Try to load from generated JSON first
    olmar_data = await load_json_file_async("dashboard/olmar_data.json")
    
    if olmar_data:
        olmar_data["source"] = "cached"
        olmar_data["retrieved_at"] = datetime.now().isoformat()
        return olmar_data
    
    # Try alternative location
    olmar_data = await load_json_file_async("dashboard/data/olmar_dashboard.json")
    if olmar_data:
        olmar_data["source"] = "cached"
        olmar_data["retrieved_at"] = datetime.now().isoformat()
        return olmar_data
    
    # Generate minimal data structure
    results = await get_strategy_results_async()
    
    data = {
        "generated_at": datetime.now().isoformat(),
        "source": "live",
        "strategy": "OLMAR",
        "description": "Online Learning for Portfolio Selection with Mean Reversion",
        "parameters": {
            "window": 5,
            "epsilon": 10,
            "universe": "NASDAQ-100"
        }
    }
    
    if "OLMAR" in results:
        data["performance"] = results["OLMAR"].get("metrics", {})
        data["weights"] = results["OLMAR"].get("weights", {})
        data["final_value"] = results["OLMAR"].get("final_value", 0)
        data["status"] = "active"
    else:
        data["status"] = "no_data"
        data["message"] = "Run OLMAR backtest to generate data"
    
    return data


@router.get("/backtest")
async def get_backtest_dashboard() -> Dict[str, Any]:
    """
    Get comprehensive backtest dashboard data.
    """
    # Try to load from generated JSON first
    backtest_data = await load_json_file_async("dashboard/data/comprehensive_backtest.json")
    
    if backtest_data:
        backtest_data["source"] = "cached"
        backtest_data["retrieved_at"] = datetime.now().isoformat()
        return backtest_data
    
    # Generate from results
    results = await get_strategy_results_async()
    
    comparison_table = []
    
    for name, data in results.items():
        metrics = data.get("metrics", {})
        
        comparison_table.append({
            "strategy": name,
            "final_value": data.get("final_value", 0),
            "total_return": metrics.get("total_return", "N/A"),
            "cagr": metrics.get("cagr", "N/A"),
            "volatility": metrics.get("volatility", "N/A"),
            "sharpe_ratio": metrics.get("sharpe_ratio", "N/A"),
            "sortino_ratio": metrics.get("sortino_ratio", "N/A"),
            "max_drawdown": metrics.get("max_drawdown", "N/A"),
            "calmar_ratio": metrics.get("calmar_ratio", "N/A"),
            "win_rate": metrics.get("win_rate", "N/A")
        })
    
    return {
        "generated_at": datetime.now().isoformat(),
        "source": "live",
        "comparison_table": comparison_table,
        "total_strategies": len(comparison_table),
        "config": {
            "initial_capital": 100000,
            "base_currency": "AUD"
        }
    }


@router.get("/comparison")
async def get_strategy_comparison(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get side-by-side strategy comparison.
    """
    results = await get_strategy_results_async()
    
    if not results:
        return {
            "comparison": [],
            "message": "No backtest results available. Run strategies first.",
            "generated_at": datetime.now().isoformat()
        }
    
    # Build comparison matrix
    metrics_list = [
        "total_return", "cagr", "volatility", "sharpe_ratio",
        "sortino_ratio", "max_drawdown", "calmar_ratio", "win_rate"
    ]
    
    comparison = []
    for name, data in results.items():
        row = {"strategy": name, "final_value": data.get("final_value", 0)}
        metrics = data.get("metrics", {})
        
        for metric in metrics_list:
            row[metric] = metrics.get(metric, "N/A")
        
        comparison.append(row)
    
    # Sort by final value descending
    comparison.sort(key=lambda x: x.get("final_value", 0), reverse=True)
    
    return {
        "comparison": comparison,
        "metrics": metrics_list,
        "strategies_count": len(comparison),
        "generated_at": datetime.now().isoformat()
    }


@router.get("/allocation")
async def get_current_allocation() -> Dict[str, Any]:
    """
    Get recommended portfolio allocation based on latest strategy results.
    """
    results = await get_strategy_results_async()
    
    # Aggregate weights from all strategies
    all_weights = {}
    strategy_weights = {}
    
    for name, data in results.items():
        weights = data.get("weights", {})
        if weights:
            strategy_weights[name] = weights
            for ticker, weight in weights.items():
                if ticker not in all_weights:
                    all_weights[ticker] = []
                all_weights[ticker].append(weight)
    
    # Average weights across strategies
    combined_allocation = {}
    for ticker, weights in all_weights.items():
        combined_allocation[ticker] = sum(weights) / len(weights)
    
    # Normalize to sum to 1
    total = sum(combined_allocation.values())
    if total > 0:
        combined_allocation = {k: v/total for k, v in combined_allocation.items()}
    
    # Sort by weight descending
    combined_allocation = dict(
        sorted(combined_allocation.items(), key=lambda x: x[1], reverse=True)
    )
    
    return {
        "generated_at": datetime.now().isoformat(),
        "combined_allocation": combined_allocation,
        "by_strategy": strategy_weights,
        "total_positions": len(combined_allocation),
        "strategies_used": len(strategy_weights),
        "note": "Combined allocation is average of all strategy weights"
    }
