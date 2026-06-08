from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.core.database_pool import db_pool


async def get_property(property_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Return a single property scoped to a tenant, or None if it does not
    belong to that tenant.

    Because the properties primary key is composite (id, tenant_id), the same
    property id can exist under different tenants. Filtering on both ensures a
    tenant can only ever resolve its own row.
    """
    if db_pool.session_factory is None:
        await db_pool.initialize()
    if db_pool.session_factory is None:
        raise RuntimeError("Database pool not available")

    query = text(
        """
        SELECT id, name, timezone
        FROM properties
        WHERE id = :property_id AND tenant_id = :tenant_id
        """
    )

    async with db_pool.get_session() as session:
        result = await session.execute(
            query, {"property_id": property_id, "tenant_id": tenant_id}
        )
        row = result.fetchone()

    if row is None:
        return None
    return {"id": row.id, "name": row.name, "timezone": row.timezone}


async def list_properties(tenant_id: str) -> List[Dict[str, Any]]:
    """Return all properties for a tenant, ordered by creation time.

    Tenant scoping is enforced in the query: a property id is only unique
    within a tenant (the table's primary key is composite on id + tenant_id),
    so callers must never receive another tenant's rows.
    """
    # Reuse the shared pool; initialize lazily if startup has not yet.
    if db_pool.session_factory is None:
        await db_pool.initialize()
    if db_pool.session_factory is None:
        raise RuntimeError("Database pool not available")

    query = text(
        """
        SELECT id, name, timezone
        FROM properties
        WHERE tenant_id = :tenant_id
        ORDER BY created_at, id
        """
    )

    async with db_pool.get_session() as session:
        result = await session.execute(query, {"tenant_id": tenant_id})
        rows = result.fetchall()

    return [
        {"id": row.id, "name": row.name, "timezone": row.timezone}
        for row in rows
    ]
