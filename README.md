# Property Revenue Dashboard

A multi-tenant property revenue dashboard (FastAPI backend, React/Vite
frontend, PostgreSQL, Redis). This repository is a debugging exercise; see
[ASSIGNMENT.md](ASSIGNMENT.md) for the original brief.

## Investigation write-up

For the full account of the bugs that were reported, how they were diagnosed,
the root causes, and how each fix was verified, see **[NOTES.md](NOTES.md)**.

## Quick start

```bash
docker compose up --build

# Frontend:    http://localhost:3000
# Backend API: http://localhost:8000/docs
```

## Tests

```bash
# Backend (pytest)
cd backend && pytest

# Frontend (vitest)
cd frontend && npm test
```

## Layout

- `backend/` - FastAPI app, services, and tests.
- `frontend/` - React/Vite dashboard.
- `database/` - schema and seed data.
- [NOTES.md](NOTES.md) - investigation and fixes.
- [ASSIGNMENT.md](ASSIGNMENT.md) - the original task.
