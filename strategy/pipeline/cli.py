"""
CLI for running the trading pipeline.

Usage:
    python -m strategy.pipeline.cli scan
    python -m strategy.pipeline.cli scan --strategy Dual_Momentum
    python -m strategy.pipeline.cli compare
    python -m strategy.pipeline.cli report --strategy HRP
"""

import argparse
import sys
from datetime import datetime

from .pipeline import TradingPipeline, PipelineConfig, run_daily_scan
from .signal_layer import SignalManager
from .strategies import (
    create_quallamaggie_1m,
    create_quallamaggie_3m,
    create_quallamaggie_6m
)


def main():
    parser = argparse.ArgumentParser(
        description="Trading Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Run strategy scan')
    scan_parser.add_argument(
        '--strategy', '-s',
        type=str,
        default=None,
        help='Specific strategy to run (default: all)'
    )
    scan_parser.add_argument(
        '--start-date',
        type=str,
        default='2020-01-01',
        help='Start date (YYYY-MM-DD)'
    )
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare all strategies')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate HTML report')
    report_parser.add_argument(
        '--strategy', '-s',
        type=str,
        required=True,
        help='Strategy name'
    )
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available strategies')
    
    args = parser.parse_args()
    
    if args.command == 'scan':
        run_scan(args)
    elif args.command == 'compare':
        run_compare()
    elif args.command == 'report':
        run_report(args)
    elif args.command == 'list':
        run_list()
    else:
        parser.print_help()


def run_scan(args):
    """Run strategy scan."""
    print("\n" + "=" * 60)
    print("🚀 TRADING PIPELINE SCAN")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # Create pipeline with Quallamaggie strategies
    config = PipelineConfig(start_date=args.start_date)
    pipeline = TradingPipeline(config)
    
    # Register Quallamaggie strategies
    pipeline.signal_manager.register_strategy(create_quallamaggie_1m())
    pipeline.signal_manager.register_strategy(create_quallamaggie_3m())
    pipeline.signal_manager.register_strategy(create_quallamaggie_6m())
    
    if args.strategy:
        # Run single strategy
        result = pipeline.run(args.strategy)
    else:
        # Run all strategies
        results = pipeline.run_all_strategies()
        
        # Print comparison
        print("\n" + "=" * 60)
        print("📊 STRATEGY COMPARISON")
        print("=" * 60)
        comparison = pipeline.compare_strategies()
        print(comparison.to_string(index=False))
    
    # Save results
    pipeline.save_results()


def run_compare():
    """Compare all strategies from saved results."""
    import json
    from pathlib import Path
    
    results_file = Path("reports/pipeline_results.json")
    
    if not results_file.exists():
        print("No saved results found. Run 'scan' first.")
        sys.exit(1)
    
    with open(results_file) as f:
        results = json.load(f)
    
    print("\n" + "=" * 60)
    print("📊 STRATEGY COMPARISON")
    print(f"Last updated: {results.get('generated_at', 'Unknown')}")
    print("=" * 60)
    
    for name, data in results.get('strategies', {}).items():
        print(f"\n{name}:")
        for metric, value in data.get('metrics', {}).items():
            print(f"  {metric}: {value}")


def run_report(args):
    """Generate HTML report for a strategy."""
    config = PipelineConfig()
    pipeline = TradingPipeline(config)
    
    # Need to run the strategy first
    print(f"Running {args.strategy}...")
    pipeline.run(args.strategy)
    
    # Generate report
    output = pipeline.generate_html_report(args.strategy)
    print(f"\n📊 Report generated: {output}")


def run_list():
    """List available strategies."""
    pipeline = TradingPipeline()
    
    # Register Quallamaggie strategies
    pipeline.signal_manager.register_strategy(create_quallamaggie_1m())
    pipeline.signal_manager.register_strategy(create_quallamaggie_3m())
    pipeline.signal_manager.register_strategy(create_quallamaggie_6m())
    
    print("\n📋 Available Strategies:")
    print("-" * 30)
    
    for name in pipeline.signal_manager.list_strategies():
        strategy = pipeline.signal_manager.get_strategy(name)
        desc = strategy.description if strategy else ""
        print(f"  • {name}")
        if desc:
            print(f"    {desc}")


if __name__ == "__main__":
    main()
