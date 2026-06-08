# Investigation Notes

How we approached the Property Revenue Dashboard bugs, what the root causes
turned out to be, and how each fix was verified. See [ASSIGNMENT.md](ASSIGNMENT.md)
for the original brief.

## The three reported symptoms

1. **Client A (Sunset Properties): "revenue numbers don't match our records."** An accuracy problem.
2. **Client B (Ocean Rentals): "sometimes a refresh shows numbers that belong to another company."** A tenant-isolation / privacy problem.
3. **Finance: "totals are slightly off by a few cents."** A precision problem.

Our working assumption was that these were three different faults, not one.
That turned out to be correct, and a couple of latent bugs surfaced along the
way once the first fix unblocked the code path.

## How we worked

- Confirmed the environment first: `docker compose ps`, then inspected the
  database directly with `psql` to learn the real shape of the data
  (tenants, properties, reservations) and the figures the dashboard *should*
  be showing.
- Noticed early that the `properties` primary key is composite
  `(id, tenant_id)`, so a property id like `prop-001` exists under **both**
  tenants as different properties. That single fact explained most of the
  tenant-isolation risk and shaped every fix afterwards.
- Fixed one root cause at a time, verified each against the live container,
  and added a regression test before moving on, so a fix could not silently
  regress later.

## Bug 1 - Accuracy: the dashboard was serving mock data

**Symptom:** Client A's numbers did not match their records.

**Root cause:** The async database pool never initialized, so every revenue
query fell back to a hardcoded mock dictionary in
`reservations.calculate_total_revenue`. Two separate defects in
`core/database_pool.py` caused this:

1. The connection URL was built from `settings.supabase_db_*` fields that did
   not exist on `Settings`, raising `AttributeError` on startup.
2. `poolclass=QueuePool` is rejected by SQLAlchemy's async engine; it needs an
   async-adapted pool.

Both were swallowed by a broad `try/except` that logged a warning and carried
on with `session_factory = None`, so the app degraded silently to mock data
instead of failing.

**Fix:**
- Added the `SUPABASE_DB_*` settings fields (defaults matching
  docker-compose, overridable via env) and the matching compose env vars.
- Switched to `AsyncAdaptedQueuePool`.
- Added a startup validation that fails fast on missing required DB config,
  so the app refuses to boot misconfigured rather than quietly serving mock
  numbers.

**Verified:** pool initializes; a tenant-scoped query returns the real seeded
figures (e.g. tenant-a `prop-001` = `2250.000`, not the mock `1000.00`).

## Bug 2 - A coroutine bug the first fix exposed

Once the pool actually initialized, the code reached a line it had never
reached before and failed with
`'coroutine' object does not support the asynchronous context manager protocol`.

**Root cause:** `DatabasePool.get_session` was declared `async def` but did no
awaiting, so `db_pool.get_session()` returned a coroutine while every call site
used `async with db_pool.get_session()`. We kept the fix in the core method
(made it a plain method returning the session) because both call sites - and
one of them lives in the core module itself - already assumed that contract.

**Verified:** added a regression test that reproduces the exact production
error if the method is ever made `async def` again (confirmed it fails on the
reverted code, then passes on the fix).

## Bug 3 - Precision: floats were mangling decimals

**Symptom:** finance saw totals off by a few cents.

**Root cause:** the dashboard summary endpoint converted the revenue total (a
`Decimal` rendered as a string upstream) into a `float`. Binary floating point
cannot represent many decimal values exactly, so values like `333.334` drift.
The frontend then did more float math (`Math.round(x * 100) / 100`) on top.

**Fix:** keep revenue as a decimal **string** end to end. The backend returns
the string as-is; the frontend types it as `string` and formats it with a new
float-free `formatMoney` helper (string-based rounding and grouping). Removed
the old "Precision Mismatch Detected" warning, which only existed to surface
the float artifact we eliminated.

**Verified:** the endpoint returns `total_revenue` as a string; `formatMoney`
is unit-tested across rounding, integer carry (`9.999` -> `10.00`), grouping,
and negatives.

## Bug 4 - Privacy: cross-tenant revenue leakage

**Symptom:** Client B occasionally saw another company's numbers.

**Root cause:** two tenant-isolation gaps, both made dangerous by the shared
`prop-001` id:

1. The revenue cache key was `revenue:{property_id}` - not scoped by tenant.
   Whichever tenant queried a shared id first populated the cache, and the
   other tenant was served that cached value.
2. Nothing verified that the requested property actually belonged to the
   requesting tenant before computing/returning revenue.

**Fix (in `services/cache.py:get_revenue_summary`):**
- Check ownership first: look the property up scoped to the tenant
  (`properties.get_property`) and return 404 if it is not theirs, before any
  cache or revenue work.
- Scope the cache key by tenant: `revenue:{tenant_id}:{property_id}`.

**Verified:** over HTTP, tenant-b requesting tenant-a's `prop-002` gets `404`,
while its own `prop-004` returns `200` with the correct revenue. Covered by
tests for the guard and the ownership lookup.

## Supporting cleanup

While fixing the above we also replaced the dashboard's **hardcoded,
tenant-blind property dropdown** (it listed both tenants' ids and only one
tenant's names) with a real, tenant-scoped `GET /dashboard/properties`
endpoint wired into the frontend.

## Symptom-to-fix map

| Reported symptom | Root cause | Fix |
| --- | --- | --- |
| Client A: numbers don't match | Pool never initialized -> mock data | Pool init (settings fields + async pool) |
| Finance: off by a few cents | Decimal -> float conversion | Decimal string end to end + `formatMoney` |
| Client B: sees another company's data | Tenant-agnostic cache key + no ownership check | Tenant-scoped key + ownership guard |

## Testing

- Backend (`backend/tests`, pytest): pool init, config validation,
  `get_session` contract, properties tenant-scoping, the cross-tenant guard,
  and the decimal-string endpoint response.
- Frontend (`frontend`, vitest): `formatMoney` decimal formatting.
- Run: `cd backend && pytest` and `cd frontend && npm test`.

## Change history

Each fix landed on its own branch and merged into `main` with a merge commit:

- `fix/database-pool-init` - pool initialization, `get_session`, startup config validation.
- `feat/dashboard-properties-endpoint` - tenant-scoped properties endpoint + frontend wiring.
- `fix/revenue-decimal-precision` - decimal-string revenue + vitest.
- `feat/tenant-property-guard` - cross-tenant ownership guard + tenant-scoped cache key.
