"""
Database Connection Management
==============================
SQLAlchemy async session management with connection pooling.
Supports both SQLite (local dev) and PostgreSQL (production/Neon).

Migration Notes:
- Uses async engine and session for all database operations
- pool_size=1, max_overflow=0 for Lambda compatibility
- Falls back to higher pool size for local development
"""

import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Import settings dynamically
try:
    from config import settings
except ImportError:
    from backend.config import settings

# Base class for models
Base = declarative_base()

# ============================================================================
# Async Database Engine (Primary - for Lambda and Production)
# ============================================================================

def get_async_engine_config():
    """
    Get async engine configuration based on environment.

    Lambda: NullPool (no connection pooling - prevents connection leaks)
    Local Dev: pool_size=5, max_overflow=10 (higher concurrency)
    """
    is_lambda = settings.is_lambda_environment
    is_postgres = settings.USE_NEON and settings.NEON_DATABASE_URL

    base_config = {
        "echo": settings.DEBUG and not is_lambda,  # Disable echo in Lambda for performance
        "pool_pre_ping": True,  # Verify connections before use
    }

    if is_lambda:
        # Lambda configuration: NO pooling (NullPool)
        # Each invocation gets a fresh connection that closes immediately after use
        # This prevents connection exhaustion when many Lambda instances spin up
        base_config["poolclass"] = NullPool
    else:
        # Local development: standard pooling
        if is_postgres:
            base_config.update({
                "pool_size": 5,
                "max_overflow": 10,
                "pool_recycle": 3600,
            })
        else:
            # SQLite doesn't support connection pooling well
            base_config["poolclass"] = NullPool

    return base_config


# Create async engine
async_engine = create_async_engine(
    settings.database_url_async,
    **get_async_engine_config()
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading issues
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency injection for database sessions.

    Usage in FastAPI:
        @router.get("/trades")
        async def get_trades(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Trade))
            return result.scalars().all()

    Yields:
        Async database session that auto-closes after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_async_db() -> None:
    """
    Initialize database tables asynchronously.

    Usage:
        await init_async_db()
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ============================================================================
# Sync Database Engine (Legacy - for backward compatibility)
# ============================================================================

# Create sync engine for legacy code (will be phased out)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator:
    """
    LEGACY: Sync dependency injection for database sessions.

    ⚠️ This will be deprecated in favor of get_async_db().
    Only use this for code that hasn't been migrated to async yet.

    Yields:
        Database session that auto-closes after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    LEGACY: Initialize database tables synchronously.

    ⚠️ This will be deprecated in favor of init_async_db().
    """
    Base.metadata.create_all(bind=engine)
