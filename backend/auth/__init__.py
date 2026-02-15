"""
Authentication Module
=====================
Centralized authentication dependencies for FastAPI routes.
"""

from .dependencies import (
    get_current_user,
    verify_api_key,
    create_access_token,
    get_optional_user,
)

__all__ = [
    "get_current_user",
    "verify_api_key",
    "create_access_token",
    "get_optional_user",
]
