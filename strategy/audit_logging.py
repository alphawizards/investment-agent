"""
Audit Logging Module for Investment-Ready Trading Platform.

Provides comprehensive audit trail for all trading activities,
data changes, and system events for regulatory compliance.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import uuid


class AuditEventType(str, Enum):
    """Types of audit events for categorization."""
    TRADE_SIGNAL = "trade_signal"
    TRADE_EXECUTED = "trade_executed"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    REBALANCE_STARTED = "rebalance_started"
    REBALANCE_COMPLETED = "rebalance_completed"
    DATA_FETCHED = "data_fetched"
    DATA_VALIDATED = "data_validated"
    DATA_CACHED = "data_cached"
    BACKTEST_STARTED = "backtest_started"
    BACKTEST_COMPLETED = "backtest_completed"
    CONFIG_CHANGED = "config_changed"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    API_ACCESS = "api_access"
    ERROR = "error"
    SYSTEM_EVENT = "system_event"


class AuditLogger:
    """
    Centralized audit logging for regulatory compliance.
    
    Features:
    - Immutable append-only log files
    - Structured JSON format for easy parsing
    - Event correlation via request IDs
    - Configurable retention policies
    """
    
    def __init__(
        self,
        log_dir: str = "./audit_logs",
        retention_days: int = 2555,  # ~7 years for regulatory compliance
        enable_console: bool = False,
    ):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for audit log files
            retention_days: Days to retain logs (default: 7 years)
            enable_console: Also log to console for debugging
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        
        # Configure file handler for daily rotation
        self._logger = logging.getLogger("audit")
        self._logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self._logger.handlers:
            self._setup_handlers(enable_console)
    
    def _setup_handlers(self, enable_console: bool):
        """Setup log handlers."""
        # File handler - one file per day
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{today}.jsonl"
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(file_handler)
        
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            self._logger.addHandler(console_handler)
    
    def log(
        self,
        event_type: AuditEventType,
        details: dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ticker: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> str:
        """
        Log an audit event.
        
        Args:
            event_type: Type of audit event
            details: Event-specific details
            user_id: User who triggered the event
            request_id: Correlation ID for request tracking
            ticker: Related ticker symbol
            strategy: Related strategy name
            
        Returns:
            Unique event ID
        """
        event_id = str(uuid.uuid4())
        
        event = {
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type.value,
            "user_id": user_id,
            "request_id": request_id,
            "ticker": ticker,
            "strategy": strategy,
            "details": details,
        }
        
        # Write as single-line JSON for easy parsing
        self._logger.info(json.dumps(event, default=str))
        
        return event_id
    
    def log_trade_signal(
        self,
        ticker: str,
        strategy: str,
        signal_type: str,
        signal_value: float,
        metadata: Optional[dict] = None,
    ) -> str:
        """Log a trade signal generation."""
        return self.log(
            AuditEventType.TRADE_SIGNAL,
            {
                "signal_type": signal_type,
                "signal_value": signal_value,
                "metadata": metadata or {},
            },
            ticker=ticker,
            strategy=strategy,
        )
    
    def log_trade_execution(
        self,
        ticker: str,
        action: str,  # BUY, SELL, HOLD
        quantity: float,
        price: float,
        total_value: float,
        commission: float = 0.0,
        slippage: float = 0.0,
        order_id: Optional[str] = None,
    ) -> str:
        """Log a trade execution."""
        return self.log(
            AuditEventType.TRADE_EXECUTED,
            {
                "action": action,
                "quantity": quantity,
                "price": price,
                "total_value": total_value,
                "commission": commission,
                "slippage": slippage,
                "order_id": order_id,
            },
            ticker=ticker,
        )
    
    def log_backtest(
        self,
        strategy: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        final_value: float,
        total_return_pct: float,
        sharpe_ratio: float,
        max_drawdown_pct: float,
        num_trades: int,
        parameters: Optional[dict] = None,
    ) -> str:
        """Log a backtest completion."""
        return self.log(
            AuditEventType.BACKTEST_COMPLETED,
            {
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
                "final_value": final_value,
                "total_return_pct": total_return_pct,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown_pct": max_drawdown_pct,
                "num_trades": num_trades,
                "parameters": parameters or {},
            },
            strategy=strategy,
        )
    
    def log_data_fetch(
        self,
        source: str,
        tickers: list[str],
        start_date: str,
        end_date: str,
        rows_fetched: int,
        cache_hit: bool = False,
    ) -> str:
        """Log a data fetch operation."""
        return self.log(
            AuditEventType.DATA_FETCHED,
            {
                "source": source,
                "tickers": tickers,
                "start_date": start_date,
                "end_date": end_date,
                "rows_fetched": rows_fetched,
                "cache_hit": cache_hit,
            },
        )
    
    def log_api_access(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> str:
        """Log an API access event."""
        return self.log(
            AuditEventType.API_ACCESS,
            {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "ip_address": ip_address,
                "duration_ms": duration_ms,
            },
            user_id=user_id,
        )
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> str:
        """Log an error event."""
        return self.log(
            AuditEventType.ERROR,
            {
                "error_type": error_type,
                "error_message": error_message,
                "stack_trace": stack_trace,
                "context": context or {},
            },
        )
    
    def query_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        ticker: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 1000,
    ) -> list[dict]:
        """
        Query audit logs with filters.
        
        Returns:
            List of matching audit events
        """
        results = []
        
        # Determine which log files to search
        log_files = sorted(self.log_dir.glob("audit_*.jsonl"))
        if start_date:
            log_files = [f for f in log_files if f.stem >= f"audit_{start_date}"]
        if end_date:
            log_files = [f for f in log_files if f.stem <= f"audit_{end_date}"]
        
        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if len(results) >= limit:
                        break
                    
                    try:
                        event = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    
                    # Apply filters
                    if event_type and event.get("event_type") != event_type.value:
                        continue
                    if ticker and event.get("ticker") != ticker:
                        continue
                    if strategy and event.get("strategy") != strategy:
                        continue
                    
                    results.append(event)
        
        return results
    
    def generate_compliance_report(
        self,
        start_date: str,
        end_date: str,
    ) -> dict:
        """
        Generate a compliance report for a date range.
        
        Returns:
            Summary report suitable for regulatory review
        """
        events = self.query_logs(start_date=start_date, end_date=end_date, limit=100000)
        
        report = {
            "report_generated_at": datetime.utcnow().isoformat() + "Z",
            "period_start": start_date,
            "period_end": end_date,
            "total_events": len(events),
            "event_summary": {},
            "trades": [],
            "errors": [],
            "backtests": [],
        }
        
        # Summarize events by type
        for event in events:
            event_type = event.get("event_type", "unknown")
            report["event_summary"][event_type] = report["event_summary"].get(event_type, 0) + 1
            
            # Extract key events
            if event_type == AuditEventType.TRADE_EXECUTED.value:
                report["trades"].append({
                    "timestamp": event.get("timestamp"),
                    "ticker": event.get("ticker"),
                    "details": event.get("details"),
                })
            elif event_type == AuditEventType.ERROR.value:
                report["errors"].append({
                    "timestamp": event.get("timestamp"),
                    "details": event.get("details"),
                })
            elif event_type == AuditEventType.BACKTEST_COMPLETED.value:
                report["backtests"].append({
                    "timestamp": event.get("timestamp"),
                    "strategy": event.get("strategy"),
                    "details": event.get("details"),
                })
        
        return report


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
