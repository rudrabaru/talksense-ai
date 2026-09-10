"""
Shared pytest configuration for the backend test suite.

Test-only infrastructure — imported by pytest, never by the application.
"""

import pytest

from db.database import engine


@pytest.fixture(autouse=True)
def _reset_async_engine_pool():
    """
    The app's AsyncEngine is a process-wide singleton. pytest-asyncio runs
    async tests on one session-scoped event loop, while sync TestClient tests
    run the FastAPI lifespan on their own private event loop. A pooled asyncpg
    connection created on one loop cannot be reused on another
    (``RuntimeError: got Future ... attached to a different loop``); the
    engine's ``pool_pre_ping`` surfaces this during lifespan startup
    (``recover_stale_sessions``).

    After every test, de-reference the pool without closing its connections
    (``Engine.dispose(close=False)`` simply swaps in a fresh empty pool) so
    the next test starts with a pool appropriate for its own event loop.
    This is SQLAlchemy's documented pattern for an engine that crosses a
    loop/fork boundary. It runs only in the test process and has no effect on
    production, where a single event loop owns the engine for the lifetime of
    the process.
    """
    yield
    engine.sync_engine.dispose(close=False)
