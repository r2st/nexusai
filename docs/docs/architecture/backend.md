---
sidebar_position: 2
---

# Backend

## Tech stack

- Python 3.12
- FastAPI + async SQLAlchemy
- Postgres (`asyncpg`) + Alembic migrations
- Redis (cache, rate limiting, job queues)
- ARQ worker for background tasks

## Code layout

- App entry: `backend/app/main.py`
- API router registry: `backend/app/api/__init__.py` (mounted at `/api/v1`)
- Route modules: `backend/app/api/*.py`
- Business logic: `backend/app/services/`
- Data models: `backend/app/models/`
- Settings: `backend/app/core/config.py`

## Request lifecycle

1. Middleware adds security headers, request IDs, and (if enabled) tenant context.
2. Routers under `/api/v1` handle auth/chat/docs/analytics/etc.
3. Services perform work and persist via async SQLAlchemy.
4. Background workloads (imports, scheduled jobs, long-running analytics) run in the `worker` container.

