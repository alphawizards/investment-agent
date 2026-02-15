"""
Error Handler Utilities
=======================
Reusable decorators and utilities for consistent error handling across routers.
"""

from functools import wraps
from typing import Dict, Tuple, Type, Callable, Any
import logging

from fastapi import HTTPException

from .exceptions import (
    QuantBaseError,
    StrategyExecutionError,
    DataLoadError,
    ValidationError,
    ExternalAPIError,
    BacktestError,
    DatabaseError,
)

logger = logging.getLogger(__name__)


# Default error mappings for common exception types
DEFAULT_ERROR_MAP: Dict[Type[Exception], Tuple[int, str]] = {
    StrategyExecutionError: (500, "Strategy execution failed"),
    DataLoadError: (503, "Data source unavailable"),
    ValidationError: (422, "Validation failed"),
    ExternalAPIError: (503, "External service unavailable"),
    BacktestError: (500, "Backtest computation failed"),
    DatabaseError: (500, "Database operation failed"),
    ImportError: (500, "Required module not available"),
    ValueError: (400, "Invalid parameter value"),
    KeyError: (400, "Missing required field"),
    ZeroDivisionError: (500, "Computation error"),
    FileNotFoundError: (404, "Resource not found"),
}


def handle_errors(
    error_map: Dict[Type[Exception], Tuple[int, str]] = None,
    log_errors: bool = True,
    include_defaults: bool = True
):
    """
    Decorator to handle endpoint errors consistently.
    
    Args:
        error_map: Custom mapping of exception types to (status_code, message).
        log_errors: Whether to log caught exceptions.
        include_defaults: Whether to include DEFAULT_ERROR_MAP.
    
    Usage:
        @router.get("/strategies")
        @handle_errors({RuntimeError: (500, "Strategy engine unavailable")})
        async def list_strategies():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            return await _execute_with_handling(func, args, kwargs, error_map, log_errors, include_defaults, is_async=True)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            return _execute_with_handling_sync(func, args, kwargs, error_map, log_errors, include_defaults)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


async def _execute_with_handling(
    func: Callable,
    args: tuple,
    kwargs: dict,
    error_map: Dict[Type[Exception], Tuple[int, str]],
    log_errors: bool,
    include_defaults: bool,
    is_async: bool
) -> Any:
    """Execute function with error handling (async version)."""
    combined_map = _build_error_map(error_map, include_defaults)
    
    try:
        return await func(*args, **kwargs)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except tuple(combined_map.keys()) as e:
        _handle_known_error(e, func.__name__, combined_map, log_errors)
    except Exception as e:
        _handle_unknown_error(e, func.__name__, log_errors)


def _execute_with_handling_sync(
    func: Callable,
    args: tuple,
    kwargs: dict,
    error_map: Dict[Type[Exception], Tuple[int, str]],
    log_errors: bool,
    include_defaults: bool
) -> Any:
    """Execute function with error handling (sync version)."""
    combined_map = _build_error_map(error_map, include_defaults)
    
    try:
        return func(*args, **kwargs)
    except HTTPException:
        raise
    except tuple(combined_map.keys()) as e:
        _handle_known_error(e, func.__name__, combined_map, log_errors)
    except Exception as e:
        _handle_unknown_error(e, func.__name__, log_errors)


def _build_error_map(
    custom_map: Dict[Type[Exception], Tuple[int, str]],
    include_defaults: bool
) -> Dict[Type[Exception], Tuple[int, str]]:
    """Build combined error map from defaults and custom mappings."""
    if include_defaults:
        combined = DEFAULT_ERROR_MAP.copy()
        if custom_map:
            combined.update(custom_map)
        return combined
    return custom_map or {}


def _handle_known_error(
    exc: Exception,
    func_name: str,
    error_map: Dict[Type[Exception], Tuple[int, str]],
    log_errors: bool
) -> None:
    """Handle a known/mapped exception type."""
    exc_type = type(exc)
    
    # Find matching error type (exact match or parent class)
    status_code, message = 500, "Internal server error"
    for mapped_type, (code, msg) in error_map.items():
        if isinstance(exc, mapped_type):
            status_code, message = code, msg
            break
    
    if log_errors:
        logger.error(f"{func_name}: {exc_type.__name__} - {exc}")
    
    raise HTTPException(status_code=status_code, detail=message)


def _handle_unknown_error(exc: Exception, func_name: str, log_errors: bool) -> None:
    """Handle an unknown exception type."""
    if log_errors:
        logger.exception(f"{func_name}: Unhandled exception")
    
    # Don't expose internal details
    raise HTTPException(
        status_code=500,
        detail="An unexpected error occurred"
    )


def safe_execute(
    operation: Callable,
    error_message: str = "Operation failed",
    default: Any = None
) -> Any:
    """
    Execute an operation safely, returning a default on failure.
    
    Useful for non-critical operations where failure should not
    crash the entire request.
    
    Usage:
        data = safe_execute(
            lambda: load_optional_data(),
            error_message="Optional data unavailable",
            default={}
        )
    """
    try:
        return operation()
    except Exception as e:
        logger.warning(f"{error_message}: {e}")
        return default
