---
sidebar_position: 1
---

# Docker (Compose)

## Development

From the repo root:

```bash
cp .env.example .env
make dev
make migrate
```

Key endpoints:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

## Optional stacks

- DevLake: `make devlake-up`
- Ollama: `make ollama-up`

Compose files are organized under `docker/compose/` (see `make show-structure`).

