# NexusAI Backend

FastAPI backend for NexusAI — AI-powered engineering metrics and chat platform with multi-tenant support.

## Features

- **FastAPI** with async endpoints, OpenAPI docs, and structured logging
- **SQLAlchemy** async ORM with PostgreSQL, pgvector, and row-level security
- **Redis** for caching, rate limiting, and pub/sub
- **Multi-LLM Gateway** — 12+ providers (OpenAI, Anthropic, Google, Ollama, etc.) with circuit breaker and fallback routing
- **RAG Pipeline** — document upload, chunking, embedding, and vector search
- **MCP Server** — Model Context Protocol with built-in DevLake, Jira, CI, and repository tools
- **AI Agents** — LangGraph-based orchestration with tool use and human-in-the-loop
- **Multi-tenancy** — organization-scoped data isolation via PostgreSQL RLS
- **Guardrails** — PII detection, prompt injection filtering, content safety, secret redaction
- **Observability** — Langfuse tracing, OpenTelemetry, Prometheus metrics
- **Compliance** — GDPR DSR handling, SOC 2 controls, HIPAA audit trails

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ with pgvector extension
- Redis 7+

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev,test]"

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration (at minimum: DATABASE_*, REDIS_*, SECRET_KEY)

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # REST API endpoints (40+ route modules)
│   │   ├── auth.py           # Registration, login, token refresh
│   │   ├── chat.py           # Conversations and AI chat
│   │   ├── agents.py         # Agent CRUD and execution
│   │   ├── organizations.py  # Multi-tenant org management
│   │   ├── compliance.py     # GDPR, SOC 2 endpoints
│   │   ├── deps.py           # Shared dependencies (auth, tenant, rate limit)
│   │   └── ...
│   ├── core/             # Framework configuration
│   │   ├── config.py         # Pydantic Settings (all env vars)
│   │   ├── database.py       # Async engine, session factories, read replicas
│   │   ├── security.py       # JWT tokens, password hashing
│   │   ├── middleware.py      # Request ID, rate limit, tenant, security headers
│   │   └── multitenancy.py   # RLS tenant context management
│   ├── models/           # SQLAlchemy ORM models
│   ├── services/         # Business logic layer
│   │   ├── llm_gateway/      # Multi-provider LLM routing
│   │   ├── agents/           # AI agent orchestration
│   │   ├── rag/              # Document retrieval pipeline
│   │   ├── mcp/              # MCP protocol server
│   │   ├── guardrails/       # Input/output safety
│   │   ├── compliance/       # GDPR, SOC 2, HIPAA
│   │   └── ...
│   └── main.py           # FastAPI app factory and lifespan
├── alembic/              # Database migration scripts
├── tests/
│   ├── unit/             # Unit tests (~90 files)
│   ├── integration/      # Integration tests
│   └── fixtures/         # Seed data for tests
└── pyproject.toml        # Dependencies and tool config
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

All endpoints include `summary` and `description` fields for clear documentation.

## Key Environment Variables

See [`.env.example`](.env.example) for the full list with comments.

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` or `DATABASE_HOST/USER/PASSWORD/NAME` | PostgreSQL connection | Yes |
| `REDIS_URL` or `REDIS_HOST` | Redis connection | Yes |
| `SECRET_KEY` (or `JWT_SECRET`) | JWT signing key | Yes |
| `DEFAULT_AI_PROVIDER` | LLM provider (`google`, `openai`, `anthropic`, `ollama`) | No (default: `google`) |
| `GOOGLE_API_KEY` / `OPENAI_API_KEY` / etc. | API key for chosen provider | Yes (for non-Ollama) |
| `MULTI_TENANT_ENABLED` | Enable organization-scoped data isolation | No (default: `true`) |
| `AGENTS_ENABLED` | Enable AI agent features | No (default: `true`) |
| `GUARDRAILS_ENABLED` | Enable input/output safety checks | No (default: `true`) |
| `ENVIRONMENT` | `development`, `staging`, or `production` | No (default: `development`) |

## License

MIT. See the repository root `LICENSE`.
