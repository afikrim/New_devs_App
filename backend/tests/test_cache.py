"""Tests for the tenant-isolation guard in get_revenue_summary.

The guard rejects a request before any revenue work when the property does
not belong to the requesting tenant. It runs before Redis is touched, so
these tests need only the database.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.core.database_pool import db_pool
from app.services.cache import get_revenue_summary


async def _ensure_db_or_skip():
    if db_pool.session_factory is None:
        await db_pool.initialize()
    if db_pool.session_factory is None:
        pytest.skip("database pool unavailable")
    try:
        async with db_pool.get_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"database not reachable: {exc}")


async def test_rejects_property_from_another_tenant():
    """prop-002 belongs to tenant-a; tenant-b must get a 404, not data."""
    await _ensure_db_or_skip()
    with pytest.raises(HTTPException) as exc_info:
        await get_revenue_summary("prop-002", "tenant-b")
    assert exc_info.value.status_code == 404


async def test_rejects_nonexistent_property():
    await _ensure_db_or_skip()
    with pytest.raises(HTTPException) as exc_info:
        await get_revenue_summary("prop-does-not-exist", "tenant-a")
    assert exc_info.value.status_code == 404
