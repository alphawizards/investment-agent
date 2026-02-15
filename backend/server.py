"""
Server Entry Point
==================
Compatibility layer for supervisor which expects server:app.
Imports the main FastAPI application.
"""

import sys
from pathlib import Path

# Add parent path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

# Re-export for uvicorn
__all__ = ["app"]
