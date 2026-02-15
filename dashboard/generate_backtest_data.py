"""
Generate Dashboard Data from Backtest Results
==============================================
Converts comprehensive backtest JSON to dashboard-friendly format
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def load_latest_backtest():
    """Load the most recent backtest results."""
    results_dir = Path("backtest_results")
    if not results_dir.exists():
        return None
    
    # Find latest file
    json_files = list(results_dir.glob("comprehensive_backtest_*.json"))
    if not json_files:
        return None
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data, latest_file

def generate_dashboard_data():
    """Generate dashboard JSON from backtest results."""
    
    # Load backtest results
    results_data = load_latest_backtest()
    if not results_data:
        print("No backtest results found!")
        return
    
    backtest_results, source_file = results_data
    
    print(f"Loading data from: {source_file}")
    print(f"Strategies found: {list(backtest_results.keys())}")
    
    # Build dashboard data structure
    dashboard_data = {
        "generated_at": datetime.now().isoformat(),
        "source_file": str(source_file),
        "strategies": {}
    }
    
    # Process each strategy
    for strategy_key, strategy_data in backtest_results.items():
        print(f"\nProcessing: {strategy_key}")
        dashboard_data["strategies"][strategy_key] = strategy_data
    
    # Add mock data for strategies that didn't complete
    # (In a production system, these would come from actual backtests)
    
    # Save to dashboard data directory
    output_dir = Path("dashboard/data")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / "comprehensive_backtest.json"
    
    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    print(f"\nDashboard data saved to: {output_file}")
    print(f"Total strategies: {len(dashboard_data['strategies'])}")
    
    return dashboard_data

if __name__ == "__main__":
    print("="*60)
    print("DASHBOARD DATA GENERATOR")
    print("="*60)
    
    data = generate_dashboard_data()
    
    if data:
        print("\n" + "="*60)
        print("SUCCESS - Dashboard data generated")
        print("="*60)
    else:
        print("\nFailed to generate dashboard data")
