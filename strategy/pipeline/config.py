"""
Pipeline Configuration
======================
Centralized configuration using pydantic-settings.

Environment variables override defaults.
Copy .env.example to .env and customize.
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # ============== SECURITY ==============
    # SHA256 hash of API key (recommended for production)
    API_KEY_HASH: str = ""
    # Plain API key (dev fallback only)
    API_KEY: str = "dev-key-change-me"
    # Comma-separated CORS origins
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080"
    
    # ============== TRADING ==============
    RISK_FREE_RATE: float = 0.04
    TRADING_DAYS_PER_YEAR: int = 252
    INITIAL_CAPITAL: float = 100_000.0
    
    # ============== CACHE ==============
    CACHE_EXPIRY_HOURS: int = 24
    CACHE_DIR: str = ".cache/data"
    
    # ============== FEATURE FLAGS ==============
    USE_VECTORBT: bool = True
    VECTORBT_TIMEOUT: int = 30
    
    # ============== API ==============
    RATE_LIMIT_SCAN: str = "5/minute"
    RATE_LIMIT_DEFAULT: str = "60/minute"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience singleton
settings = get_settings()
