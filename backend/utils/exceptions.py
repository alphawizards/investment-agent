"""
Custom Exception Classes
========================
Domain-specific exceptions for better error handling and debugging.
"""


class QuantBaseError(Exception):
    """Base exception for all quant-related errors."""
    pass


class StrategyExecutionError(QuantBaseError):
    """Raised when a strategy fails to execute."""
    
    def __init__(self, strategy_name: str, message: str):
        self.strategy_name = strategy_name
        super().__init__(f"Strategy '{strategy_name}' failed: {message}")


class DataLoadError(QuantBaseError):
    """Raised when market data cannot be loaded."""
    
    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"Data load failed from {source}: {message}")


class ValidationError(QuantBaseError):
    """Raised when input validation fails."""
    pass


class ExternalAPIError(QuantBaseError):
    """Raised when external API (Tiingo/yFinance/S3) fails."""
    
    def __init__(self, service: str, message: str):
        self.service = service
        super().__init__(f"{service} API error: {message}")


class BacktestError(QuantBaseError):
    """Raised when backtest computation fails."""
    pass


class DatabaseError(QuantBaseError):
    """Raised when database operations fail."""
    pass
