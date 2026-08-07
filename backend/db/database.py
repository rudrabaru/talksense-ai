"""
TalkSense AI v4 — Async Database Engine (Phase 3)

Provides:
    engine          — AsyncEngine bound to PostgreSQL via asyncpg
    AsyncSessionLocal — session factory (async_sessionmaker)
    get_db()        — FastAPI dependency that yields an AsyncSession per request


Design rules (from .agent/ARCHITECTURE.md + database_agent.md):
    - Driver: postgresql+asyncpg (DATABASE_URL sourced from core/config.py)
    - No sync fallback — this module is async-only
    - Pool is capped (pool_size=5, max_overflow=10) to avoid competing with the
      Whisper / Pyannote GPU pipeline for system resources
    - Sessions are scoped per-request via FastAPI Depends(get_db)
    - Table creation uses Alembic (alembic upgrade head).
      correct way to call a sync DDL method inside an async context
    - Do NOT import this module at module level inside audio handlers or the
      WebSocket session manager — use asyncio.create_task for all DB writes
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings

logger = logging.getLogger(__name__)

# ── Settings ──────────────────────────────────────────────────────────────────

_settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    _settings.database_url,
    # ── Pool configuration ────────────────────────────────────────────────────
    # pool_size: persistent connections kept alive between requests.
    # max_overflow: additional connections allowed when pool is exhausted.
    # Kept small — the real-time audio pipeline owns the CPU/GPU budget.
    pool_size=5,
    max_overflow=10,
    # pool_pre_ping: issues a lightweight SELECT 1 before lending a connection
    # from the pool, ensuring stale connections are dropped cleanly.
    pool_pre_ping=True,
    # echo=False in production; flip to True temporarily to debug SQL queries.
    echo=False,
)

# ── Session factory ───────────────────────────────────────────────────────────

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # expire_on_commit=False: keeps ORM objects usable after commit inside the
    # same async context (essential for returning data after writes in CRUD).
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ── Table initialisation ──────────────────────────────────────────────────────


# ── FastAPI dependency ────────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that opens an AsyncSession for the duration of a single
    HTTP request and guarantees it is closed (returned to the pool) afterwards.

    Usage in a route:

        from db.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession
        from fastapi import Depends

        @app.get("/example")
        async def example_route(db: AsyncSession = Depends(get_db)):
            ...

    The session is NOT used by the WebSocket audio pipeline or the 5-second
    background flusher — those create their own short-lived sessions directly
    via AsyncSessionLocal() to avoid sharing state across async contexts.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
