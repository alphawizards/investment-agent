"""
API Routers
===========
All API route handlers organized by domain.
"""

from .trades import router as trades_router
from .data import router as data_router
from .strategies import router as strategies_router
from .dashboard import router as dashboard_router
from .scanner import router as scanner_router
from .universes import router as universes_router
from .quant2 import router as quant2_router

__all__ = [
    "trades_router",
    "data_router",
    "strategies_router",
    "dashboard_router",
    "scanner_router",
    "universes_router",
    "quant2_router",
]
