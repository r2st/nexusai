---
sidebar_position: 4
---

# Database

## Primary database: Postgres + pgvector

NexusAI uses Postgres as the primary datastore and enables vector search via `pgvector`.

Typical stored data:

- Users, organizations/tenants, projects
- Conversations and chat messages
- Documents and extracted content/metadata
- Audit/event records and analytics rollups

Migrations are managed via Alembic.

## Supporting stores

- **Redis**: caching, rate limiting, and background job coordination
- **Meilisearch**: full-text search indexes

## DevLake database (optional)

DevLake runs its own MySQL database (`docker/compose/services/docker-compose.devlake.yml`) and feeds metrics dashboards via Grafana.

