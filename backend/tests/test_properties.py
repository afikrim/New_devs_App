"""Integration tests for the dashboard properties service.

These run against the seeded database (the docker-compose `db` service).
They skip cleanly if no database is reachable, so they do not break
environments without one.
"""

import pytest
from sqlalchemy import text

from app.core.database_pool import db_pool
from app.services.properties import get_property, list_properties


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


async def test_list_properties_is_tenant_scoped():
    """Each tenant sees only its own properties (no cross-tenant leakage)."""
    await _ensure_db_or_skip()

    tenant_a = await list_properties("tenant-a")
    tenant_b = await list_properties("tenant-b")

    assert {p["id"] for p in tenant_a} == {"prop-001", "prop-002", "prop-003"}
    assert {p["id"] for p in tenant_b} == {"prop-001", "prop-004", "prop-005"}


async def test_shared_property_id_resolves_per_tenant():
    """prop-001 exists for both tenants but must resolve to different rows.

    The properties PK is composite (id, tenant_id), so an id is only unique
    within a tenant. This guards against a query that forgets the tenant
    filter and returns the wrong tenant's property.
    """
    await _ensure_db_or_skip()

    a_001 = next(p for p in await list_properties("tenant-a") if p["id"] == "prop-001")
    b_001 = next(p for p in await list_properties("tenant-b") if p["id"] == "prop-001")

    assert a_001["name"] != b_001["name"]


async def test_unknown_tenant_returns_empty():
    await _ensure_db_or_skip()
    assert await list_properties("tenant-does-not-exist") == []


async def test_get_property_returns_row_for_owning_tenant():
    await _ensure_db_or_skip()
    prop = await get_property("prop-002", "tenant-a")  # prop-002 belongs to tenant-a
    assert prop is not None
    assert prop["id"] == "prop-002"


async def test_get_property_returns_none_for_foreign_tenant():
    """tenant-b does not own prop-002, so it must not resolve."""
    await _ensure_db_or_skip()
    assert await get_property("prop-002", "tenant-b") is None
