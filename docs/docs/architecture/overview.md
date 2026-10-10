---
sidebar_position: 1
---

# System Overview

## High-level diagram

```
Browser
  |
  v
Frontend (Next.js)  --->  Backend (FastAPI)  --->  Postgres (pgvector)
                              |   |               Redis (cache + queues)
                              |   +-------------> Meilisearch (search index)
                              |
                              +---> Worker (ARQ) -> background jobs

Optional stacks:
  - DevLake (MySQL + API + UI) -> Grafana dashboards
  - Keycloak (OIDC) + OpenFGA (authz) + OpenBao (secrets)
  - Monitoring (Prometheus/Grafana/Loki)
  - Ollama (local LLM)
```

## Runtime services (Docker Compose)

Base services are defined in `docker/compose/base/docker-compose.yml`:

- `traefik` (reverse proxy)
- `frontend` (Next.js)
- `backend` (FastAPI)
- `worker` (ARQ)
- `postgres` (pgvector)
- `redis`
- `meilisearch`

Additional stacks are in `docker/compose/services/`.

