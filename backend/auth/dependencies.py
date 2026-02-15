"""
Authentication Dependencies
===========================
JWT and API Key authentication for FastAPI routes.

Usage:
    from backend.auth.dependencies import get_current_user, verify_api_key
    
    @router.get("/protected")
    async def protected_route(user = Depends(get_current_user)):
        return {"user": user}
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
import jwt

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import settings
except ImportError:
    from backend.config import settings


# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Verify API key from X-API-Key header.
    
    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    if not settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server"
        )
    
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    return api_key


async def get_current_user(
    token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> dict:
    """
    Verify JWT token and extract user info.
    
    Raises:
        HTTPException: 401 if token is missing or invalid
    
    Returns:
        dict: Decoded JWT payload containing user info
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        payload = jwt.decode(
            token.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload to encode in the token
        expires_delta: Token expiry duration (default: from settings)
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


# Alias for backwards compatibility with existing test fixtures
async def get_optional_user(
    token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[dict]:
    """
    Optional JWT verification - returns None if no token provided.
    Use for endpoints that work differently for authenticated vs anonymous users.
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token)
    except HTTPException:
        return None
