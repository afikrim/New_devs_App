from typing import Any, Dict, List

from sqlalchemy import text

from app.core.database_pool import db_pool


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
