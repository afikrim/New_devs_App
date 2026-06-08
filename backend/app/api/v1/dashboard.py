from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.cache import get_revenue_summary
from app.services.properties import list_properties
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()


@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:

    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"

    properties = await list_properties(tenant_id)

    return {"properties": properties}

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"
    
    revenue_data = await get_revenue_summary(property_id, tenant_id)

    # Return the revenue as a decimal string, not a float. total is produced
    # from a Decimal upstream; converting to float here can introduce
    # binary-floating-point drift (e.g. 333.334 -> 333.33399999...).
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": str(revenue_data['total']),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
