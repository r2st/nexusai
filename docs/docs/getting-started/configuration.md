---
sidebar_position: 3
---

# Configuration

NexusAI is configured primarily via `.env` (see `.env.example` at the repo root).

## Core settings

Common settings used by Docker Compose and the backend:

```bash
# App
ENVIRONMENT=development
SECRET_KEY=change-me
DOMAIN=localhost

# Backend API base path
API_PREFIX=/api/v1

# Database / cache
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=nexusai
REDIS_PASSWORD=

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## AI provider selection

NexusAI supports multiple providers. Configure at least one:

```bash
DEFAULT_AI_PROVIDER=google   # google | groq | ollama | openai | anthropic | ...
DEFAULT_AI_MODEL=gemini-1.5-flash

GOOGLE_API_KEY=...
GROQ_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

If you want a fully local setup, use Ollama:

```bash
DEFAULT_AI_PROVIDER=ollama
DEFAULT_AI_MODEL=llama3.2
```

## Optional services

NexusAI can be extended with additional stacks (all are Docker Compose files under `docker/compose/services/`):

- **DevLake + Grafana (DORA & engineering metrics)**: `make devlake-up`
- **Auth stack (Keycloak + OpenFGA + OpenBao)**: see `docker/compose/services/docker-compose.auth.yml`
- **Monitoring (Prometheus/Grafana/Loki)**: see `docker/compose/services/docker-compose.monitoring.yml`
- **Local LLM (Ollama + WebUI)**: `make ollama-up`

## Feature flags (backend)

Some capabilities are guarded by feature flags (see `backend/app/core/config.py`):

- Knowledge graph / Neo4j integration
- DevOps agents and analytics workflows
- OpenAPI actions
- Code interpreter tools

Use the `/features` endpoint to confirm what is enabled at runtime.

