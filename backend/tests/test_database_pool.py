"""Regression tests for the async database pool.

These guard the two bugs that previously stopped ``DatabasePool.initialize()``
from ever producing a usable session factory (which made the app silently fall
back to mock revenue data):

1. ``database_pool.py`` built its DSN from ``settings.supabase_db_*`` fields
   that did not exist on ``Settings``, raising ``AttributeError``.
2. ``poolclass=QueuePool`` is rejected by SQLAlchemy's asyncio engine; an
   async-adapted pool class is required.
3. ``get_session()`` was ``async def``, so it returned a coroutine and broke
   every ``async with db_pool.get_session()`` call site.

Both engine failures happen at engine *construction* time, so these tests
need no live database connection.
"""

import inspect

from sqlalchemy.pool import AsyncAdaptedQueuePool, QueuePool

from app.config import Settings, settings
from app.core.database_pool import DatabasePool

# Fields the DSN in DatabasePool.initialize() interpolates. If any of these
# disappears from Settings, the pool init will raise AttributeError again.
REQUIRED_DB_SETTINGS = (
    "supabase_db_user",
    "supabase_db_password",
    "supabase_db_host",
    "supabase_db_port",
    "supabase_db_name",
)


def test_settings_expose_database_connection_fields():
    """Bug 1: every field the DSN references must exist on Settings."""
    for field in REQUIRED_DB_SETTINGS:
        assert field in Settings.model_fields, f"Settings is missing '{field}'"
        # Accessing the attribute must not raise on the live instance either.
        getattr(settings, field)


async def test_pool_initializes_into_usable_session_factory():
    """Bugs 1 & 2: initialize() must succeed and leave a usable factory.

    initialize() swallows exceptions and leaves session_factory as None on
    failure, so a non-None factory is the signal that construction worked.
    """
    pool = DatabasePool()
    try:
        await pool.initialize()
        assert pool.engine is not None, "engine was not created (init failed)"
        assert pool.session_factory is not None, (
            "session_factory is None - DatabasePool.initialize() raised "
            "internally (check the DSN fields and poolclass)"
        )
    finally:
        await pool.close()


async def test_engine_uses_async_adapted_pool():
    """Bug 2: the engine must not use the sync QueuePool class."""
    pool = DatabasePool()
    try:
        await pool.initialize()
        pool_class = type(pool.engine.pool)
        assert issubclass(pool_class, AsyncAdaptedQueuePool)
        assert not (
            issubclass(pool_class, QueuePool)
            and not issubclass(pool_class, AsyncAdaptedQueuePool)
        ), "engine is using the sync QueuePool, which asyncio engines reject"
    finally:
        await pool.close()


async def test_engine_dsn_uses_asyncpg_driver():
    """The async engine must be built with the asyncpg driver."""
    pool = DatabasePool()
    try:
        await pool.initialize()
        assert pool.engine.url.drivername == "postgresql+asyncpg"
    finally:
        await pool.close()


async def test_get_session_returns_async_context_manager_not_coroutine():
    """Bug 3: get_session() must return a session usable directly as an
    async context manager, not a coroutine.

    Callers use ``async with db_pool.get_session() as session``. If
    get_session is made ``async def`` again it returns a coroutine, and that
    line fails with "'coroutine' object does not support the asynchronous
    context manager protocol" - exactly the production error this guards.
    """
    pool = DatabasePool()
    try:
        await pool.initialize()

        result = pool.get_session()
        assert not inspect.iscoroutine(result), (
            "get_session() returned a coroutine; it must return the "
            "AsyncSession directly (do not make it `async def`)"
        )
        assert hasattr(result, "__aenter__") and hasattr(result, "__aexit__"), (
            "get_session() result is not usable as an async context manager"
        )

        # Exercise the exact call-site pattern; reproduces the production
        # error if the contract regresses. (Entering the session is lazy and
        # does not require a live connection.)
        async with pool.get_session() as session:
            assert session is not None
    finally:
        await pool.close()
