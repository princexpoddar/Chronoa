"""
CHRONOS Database Connection Manager.

Manages connections to the PostGIS/pgvector instance for production,
with a fallback to in-memory SQLite/SpatiaLite for testing.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Default to a local PostgreSQL instance. In a real deployment, this would
# be configured via environment variables.
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/chronos"

engine = None
AsyncSessionLocal = None

def init_db(url: str = DATABASE_URL):
    global engine, AsyncSessionLocal
    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

def get_session() -> AsyncSession:
    """Dependency for FastAPI endpoints."""
    if AsyncSessionLocal is None:
        init_db()
    return AsyncSessionLocal()
