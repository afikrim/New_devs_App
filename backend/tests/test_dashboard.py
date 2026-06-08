"""Tests for the dashboard summary endpoint's revenue handling.

Guards the regression where the endpoint coerced the revenue total (a
decimal string from a Decimal) into a float, which can introduce binary
floating-point drift. The endpoint must return total_revenue as a string.
"""

from types import SimpleNamespace

import app.api.v1.dashboard as dashboard


async def test_summary_returns_total_revenue_as_string(monkeypatch):
    async def fake_summary(property_id, tenant_id):
        return {
            "property_id": property_id,
            "total": "333.334",  # 3-decimal value from numeric(10,3)
            "currency": "USD",
            "count": 3,
        }

    monkeypatch.setattr(dashboard, "get_revenue_summary", fake_summary)

    user = SimpleNamespace(tenant_id="tenant-a")
    resp = await dashboard.get_dashboard_summary(property_id="prop-001", current_user=user)

    # The key guard: a float here means someone reintroduced float(...).
    assert isinstance(resp["total_revenue"], str)
    assert resp["total_revenue"] == "333.334"


async def test_summary_preserves_decimal_string_exactly(monkeypatch):
    """A trailing-zero decimal must pass through unchanged (no 1000.0)."""
    async def fake_summary(property_id, tenant_id):
        return {
            "property_id": property_id,
            "total": "2250.000",
            "currency": "USD",
            "count": 4,
        }

    monkeypatch.setattr(dashboard, "get_revenue_summary", fake_summary)

    user = SimpleNamespace(tenant_id="tenant-a")
    resp = await dashboard.get_dashboard_summary(property_id="prop-001", current_user=user)

    assert resp["total_revenue"] == "2250.000"
