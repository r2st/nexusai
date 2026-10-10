---
sidebar_position: 0
slug: /architecture
---

# Architecture

NexusAI is a container-first system built from:

- **Frontend**: Next.js
- **Backend**: FastAPI (async), with an ARQ worker for background jobs
- **Core data plane**: Postgres (pgvector), Redis, Meilisearch
- **Optional stacks**: DevLake, auth (Keycloak/OpenFGA/OpenBao), monitoring (Prometheus/Grafana/Loki), Ollama

Start here:

- [System Overview](/docs/architecture/overview)
- [Backend](/docs/architecture/backend)
- [Frontend](/docs/architecture/frontend)
- [Database](/docs/architecture/database)
- [Security](/docs/architecture/security)
