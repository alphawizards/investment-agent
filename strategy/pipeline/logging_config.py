"""
Logging Configuration
=====================
Structured logging with structlog for observability.

Usage:
    from strategy.pipeline.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("event_name", key="value")
"""

import logging
import sys
from typing import Any

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


def configure_logging(
    level: str = "INFO",
    json_format: bool = False
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON output (for production)
    """
    if HAS_STRUCTLOG:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
        ]
        
        if json_format:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, level.upper()),
        stream=sys.stdout,
    )


def get_logger(name: str) -> Any:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance (structlog if available, else stdlib)
    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)


# Auto-configure on import
configure_logging()
