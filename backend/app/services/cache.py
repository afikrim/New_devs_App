import json
import redis.asyncio as redis
from typing import Dict, Any
import os

from fastapi import HTTPException

from app.services.properties import get_property

# Initialize Redis client (typically configured centrally).
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

async def get_revenue_summary(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    """
    # Tenant isolation guard: verify the property belongs to this tenant
    # before doing any work. Without this, a tenant could request another
    # tenant's property id and read its revenue. Returns 404 (rather than
    # 403) so we do not reveal whether the property exists elsewhere.
    if await get_property(property_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Property not found")

    # Cache key is scoped to the tenant. A property id is only unique within a
    # tenant (composite PK), so a tenant-agnostic key would let one tenant's
    # cached revenue be served to another for a shared id (e.g. prop-001).
    cache_key = f"revenue:{tenant_id}:{property_id}"

    # Try to get from cache
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Revenue calculation is delegated to the reservation service.
    from app.services.reservations import calculate_total_revenue

    # Calculate revenue
    result = await calculate_total_revenue(property_id, tenant_id)

    # Cache the result for 5 minutes
    await redis_client.setex(cache_key, 300, json.dumps(result))

    return result
