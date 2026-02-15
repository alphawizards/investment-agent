"""
Backend Configuration
=====================
Centralized configuration using Pydantic Settings.
Supports all data sources and rate limiting.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pathlib import Path
from typing import List, Optional, Union

# Compute env file path before class definition
_ENV_FILE_PATH = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Use pydantic v2 model_config
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE_PATH),
        case_sensitive=True,
        extra="ignore"
    )
    
    # Application
    APP_NAME: str = "Quant Trading Dashboard API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"  # nosec B104
    PORT: int = 8000
    
    # Database (supports both SQLite for local dev and PostgreSQL for production)
    DATABASE_URL: str = "sqlite:///./data/trades.db"
    NEON_DATABASE_URL: str = ""  # PostgreSQL connection string (e.g., postgresql+asyncpg://user:pass@host/db?sslmode=require)
    USE_NEON: bool = False  # Set to True to use Neon PostgreSQL instead of SQLite

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_SECRETS_MANAGER_NAME: str = "potential-parakeet/prod"  # Secrets Manager secret name

    # S3 Configuration
    S3_BUCKET_NAME: str = "potential-parakeet-cache"
    S3_CACHE_PREFIX: str = "cache/"
    USE_S3_CACHE: bool = False  # Set to True to use S3 instead of local file system

    # Lambda Configuration
    IS_LAMBDA: bool = False  # Auto-detected in Lambda environment
    LAMBDA_TASK_ROOT: str = ""
    
    # CORS - stored as comma-separated string
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://localhost:8000"
    
    # Tiingo API (US Stocks, ETFs, Gold)
    TIINGO_API_KEY: str = ""
    TIINGO_IS_PREMIUM: bool = True
    TIINGO_RATE_LIMIT: int = 20000  # requests per hour
    
    # yFinance Settings (ASX, VIX, BTC)
    YFINANCE_CACHE_HOURS: int = 24
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200
    
    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_SCAN: str = "10/minute"
    RATE_LIMIT_DATA_REFRESH: str = "5/minute"
    
    # API Key for protected endpoints (optional)
    API_KEY: str = ""
    API_KEY_HASH: str = ""
    
    # JWT Configuration
    JWT_SECRET: str = "dev-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    
    @field_validator('JWT_SECRET', 'API_KEY')
    @classmethod
    def validate_production_secrets(cls, v, info):
        """Reject default development secrets in production."""
        # Only validate if DEBUG is False (production mode)
        # Note: This runs before full model construction, so we check env var directly
        import os
        debug = os.getenv('DEBUG', 'true').lower() in ('true', '1', 'yes')
        if not debug:
            if info.field_name == 'JWT_SECRET' and v == "dev-jwt-secret-change-in-production":
                raise ValueError("JWT_SECRET must be changed in production (DEBUG=false)")
            if info.field_name == 'API_KEY' and v == "dev-key-change-me":
                raise ValueError("API_KEY must be changed in production (DEBUG=false)")
        return v
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list."""
        if isinstance(self.CORS_ORIGINS, str):
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return self.CORS_ORIGINS

    @property
    def database_url_async(self) -> str:
        """
        Get the async database URL.
        Uses Neon PostgreSQL if USE_NEON is True, otherwise SQLite.
        """
        if self.USE_NEON and self.NEON_DATABASE_URL:
            # Ensure async driver is used
            if "postgresql://" in self.NEON_DATABASE_URL:
                return self.NEON_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
            return self.NEON_DATABASE_URL
        # SQLite async (using aiosqlite)
        return self.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

    @property
    def is_lambda_environment(self) -> bool:
        """Detect if running in AWS Lambda environment."""
        return os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None or self.IS_LAMBDA


# Global settings instance
settings = Settings()


# Ensure data directory exists
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Ensure cache directory exists
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Ensure reports directory exists
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
