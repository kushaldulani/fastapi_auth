"""
Database connection using SQLAlchemy (async).

SIMPLEST possible setup:
1. Create async engine (connection to database)
2. Create session maker (factory for database sessions)
3. Provide a dependency for FastAPI routes

Key Concepts:
- Engine = Connection pool to database (create once, reuse)
- Session = Individual "conversation" with database (one per request)
- AsyncSession = Async version (non-blocking)
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use relative imports within the package (consistent with models/user.py)
from ..models.base import Base
from .config import settings


# ============================================================================
# 1. Create the async engine (connection pool)
# ============================================================================
# This connects to PostgreSQL using the URL from .env
# echo=True will print all SQL queries (helpful for learning!)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Print SQL queries in debug mode
    future=True,  # Use SQLAlchemy 2.0 style

    # Connection Pool Settings
    pool_size=5,           # Keep 5 connections open (default)
    max_overflow=10,       # Allow 10 extra connections temporarily (default)
    pool_pre_ping=True,    # Test connection before using (recommended for production)
    pool_recycle=3600,     # Recycle connections after 1 hour (prevents stale connections)
)


# ============================================================================
# 2. Create session maker (factory for sessions)
# ============================================================================
# Think of this as a "session factory"
# Each time you call it, you get a new database session
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (easier to use)
)


# ============================================================================
# 3. Base is imported from models.base
# ============================================================================
# Base is now defined in fastapi_auth.models.base
# All our models (User, Session, etc.) will inherit from it


# ============================================================================
# 4. Dependency for FastAPI (get a database session per request)
# ============================================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for each request.

    Usage in FastAPI:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()

    How it works:
    1. Creates a new session
    2. Yields it to the route (your code runs here)
    3. Closes the session automatically (cleanup)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session  # Give session to the route
        finally:
            await session.close()  # Always cleanup


# ============================================================================
# 5. Helper function to create all tables
# ============================================================================
async def create_tables():
    """
    Create all tables in the database.
    (Later we'll use Alembic migrations instead)
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """
    Drop all tables (useful for testing).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
