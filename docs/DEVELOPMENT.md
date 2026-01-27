# NexusAI Development Guide

This guide covers how to run, develop, and deploy NexusAI.

## Quick Start

### Option 1: Using Make (Recommended)

```bash
# First time setup
make install

# Or if already set up
make dev
```

### Option 2: Using Shell Script

```bash
./scripts/start-dev.sh
```

### Option 3: Direct Docker Compose

```bash
cp .env.example .env
docker compose -f docker/compose/base/docker-compose.yml \
               -f docker/compose/dev/docker-compose.override.yml up -d
```

## Prerequisites

- **Docker** & **Docker Compose** (v2.0+)
- **Make** (optional but recommended)
- **8GB RAM** minimum (16GB recommended)
- **API Key** for at least one LLM provider (OpenAI, Anthropic, or Google)

## Project Structure

```
nexusai/
├── backend/                 # FastAPI backend
├── frontend/                # Next.js frontend
├── docker/
│   └── compose/
│       ├── base/           # Core docker-compose.yml
│       ├── dev/            # Development overrides
│       ├── prod/           # Production configuration
│       └── services/       # Optional service configs
│           ├── docker-compose.auth.yml       # Keycloak, OpenFGA, OpenBAO
│           ├── docker-compose.management.yml # Portainer, pgAdmin
│           ├── docker-compose.mongodb.yml    # MongoDB, Mongo Express
│           └── docker-compose.monitoring.yml # Prometheus, Grafana
├── scripts/
│   ├── start-dev.sh        # Development startup script
│   ├── deploy.sh           # Production deployment script
│   ├── init-openbao.sh     # OpenBAO initialization
│   └── init-openfga.sh     # OpenFGA initialization
├── docs/                    # Documentation
├── helm/                    # Kubernetes Helm charts
├── Makefile                 # Build automation
└── .env.example             # Environment template
```

## Available Commands

Run `make help` to see all available commands:

```
NexusAI Development Commands
===============================

Usage: make [target]

Setup
  install                Initial project setup
  env-setup              Create .env file from example if not exists
  env-check              Verify required environment variables

Development
  dev                    Start development environment using script
  start                  Start all services in development mode
  stop                   Stop all services
  restart                Restart all services
  rebuild                Rebuild and restart all services
  status                 Show status of all services

Logs & Debugging
  logs                   View logs from all services (follow mode)
  logs-backend           View backend logs
  logs-frontend          View frontend logs
  logs-worker            View worker logs
  logs-db                View database logs

Shell Access
  backend-shell          Open shell in backend container
  frontend-shell         Open shell in frontend container
  db-shell               Open PostgreSQL shell
  redis-cli              Open Redis CLI

Database
  migrate                Run database migrations
  migrate-create         Create new migration (usage: make migrate-create MSG="description")
  migrate-down           Rollback last migration
  migrate-history        Show migration history
  db-reset               Reset database (WARNING: destroys all data)

Testing
  test                   Run all tests
  test-backend           Run backend tests
  test-backend-cov       Run backend tests with coverage
  test-frontend          Run frontend tests
  test-frontend-cov      Run frontend tests with coverage

Code Quality
  lint                   Run all linters
  lint-backend           Lint backend code
  lint-frontend          Lint frontend code
  format                 Format all code
  format-backend         Format backend code
  format-frontend        Format frontend code
  typecheck              Run type checking

Production
  prod                   Start production environment
  prod-up                Start production services
  prod-down              Stop production services
  prod-logs              View production logs
  prod-restart           Restart production services
  prod-status            Show production service status
  prod-scale             Scale backend (usage: make prod-scale N=3)

Deployment
  deploy                 Deploy to production (usage: make deploy ENV=prod)
  deploy-down            Stop production deployment
  deploy-status          Show deployment status

Optional Services
  auth-up                Start authentication services (Keycloak, OpenFGA, OpenBAO)
  auth-down              Stop authentication services
  mongodb-up             Start MongoDB service
  mongodb-down           Stop MongoDB service
  monitoring-up          Start monitoring stack (Prometheus, Grafana)
  monitoring-down        Stop monitoring stack
  management-up          Start management services (Portainer, pgAdmin)
  management-down        Stop management services
  all-services           Start all optional services
  all-services-down      Stop all optional services

Local LLM (Ollama)
  ollama-up              Start Ollama for local LLMs (Llama, Mistral, etc.)
  ollama-down            Stop Ollama
  ollama-pull            Pull an Ollama model (usage: make ollama-pull MODEL=llama3)
  ollama-list            List installed Ollama models
  ollama-run             Run a model interactively (usage: make ollama-run MODEL=llama3)
  ollama-logs            View Ollama logs
  ollama-status          Show Ollama status and models

Docker
  build                  Build all Docker images
  build-backend          Build backend image
  build-frontend         Build frontend image
  build-no-cache         Build all images without cache
  docker-push            Push images to registry

Backup & Restore
  backup                 Backup database
  restore                Restore database (usage: make restore FILE=backups/file.sql)

Local Development (without Docker)
  local-backend          Run backend locally
  local-frontend         Run frontend locally
  local-install-backend  Install backend dependencies locally
  local-install-frontend Install frontend dependencies locally
  local-install          Install all local dependencies

Cleanup
  clean                  Remove stopped containers and dangling images
  clean-all              Remove all containers, images, and volumes
  clean-volumes          Remove all volumes (destroys data)
  clean-docker-dirs      Remove incorrectly created Docker directories
  reset-dev              Full reset: stop, clean dirs, rebuild (destroys data)

Kubernetes
  k8s-deploy             Deploy to Kubernetes
  k8s-delete             Delete from Kubernetes
  k8s-status             Show Kubernetes deployment status

Utilities
  show-ports             Show all port mappings
  show-structure         Show docker-compose file structure
```

## Service Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Next.js web application |
| Backend API | http://localhost:8000 | FastAPI REST API |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI documentation |
| PostgreSQL | localhost:5434 | Database |
| Redis | localhost:6379 | Cache & task queue |
| Meilisearch | http://localhost:7700 | Full-text search |

### Optional Service Endpoints

| Service | URL | Command |
|---------|-----|---------|
| Keycloak | http://localhost:8081 | `make auth-up` |
| OpenFGA | http://localhost:8082 | `make auth-up` |
| OpenBAO | http://localhost:8200 | `make auth-up` |
| MongoDB | localhost:27017 | `make mongodb-up` |
| Mongo Express | http://localhost:8083 | `make mongodb-up` |
| Grafana | http://localhost:3001 | `make monitoring-up` |
| Prometheus | http://localhost:9090 | `make monitoring-up` |
| Portainer | http://localhost:9443 | `make management-up` |
| pgAdmin | http://localhost:5050 | `make management-up` |
| Ollama API | http://localhost:11434 | `make ollama-up` |
| Ollama Web UI | http://localhost:3003 | `make ollama-up` |

## Environment Configuration

### Required Variables

```bash
# At least one AI provider is required
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
# or
GOOGLE_API_KEY=...
# or use local LLM (no API key needed)
# make ollama-up && make ollama-pull MODEL=llama3
```

### Optional Variables

```bash
# Database (defaults work for local dev)
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_NAME=nexusai
DATABASE_PORT=5434

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security (change in production!)
SECRET_KEY=your-secret-key
DEVLAKE_ENCRYPTION_SECRET=your-encryption-key
```

## Common Workflows

### Adding a New Feature

```bash
# 1. Start development environment
make dev

# 2. Make your changes...

# 3. Run linters
make lint

# 4. Run tests
make test

# 5. View logs if needed
make logs-backend
```

### Database Changes

```bash
# Create a new migration
make migrate-create MSG="Add user preferences table"

# Apply migrations
make migrate

# Rollback if needed
make migrate-down
```

### Debugging

```bash
# Open backend shell
make backend-shell

# Inside container:
python -c "from app.core.config import settings; print(settings)"

# Or connect to database
make db-shell
```

### Production Deployment

```bash
# Build and start production
make prod

# Scale backend to 3 instances
make prod-scale N=3

# View production logs
make prod-logs
```

### Using Optional Services

```bash
# Start authentication stack
make auth-up

# Start monitoring
make monitoring-up

# Start everything
make all-services

# Stop everything
make all-services-down
```

### Using Local LLMs (Ollama)

Run AI models locally without API keys:

```bash
# Start Ollama
make ollama-up

# Pull models
make ollama-pull MODEL=llama3      # Meta Llama 3 (8B)
make ollama-pull MODEL=mistral     # Mistral 7B
make ollama-pull MODEL=codellama   # Code Llama
make ollama-pull MODEL=mixtral     # Mixtral 8x7B

# List installed models
make ollama-list

# Run interactively
make ollama-run MODEL=llama3

# Access Web UI
# Open http://localhost:3003
```

Available models: llama3, llama3:70b, mistral, mixtral, codellama, phi3, gemma, qwen2, and more at [ollama.com/library](https://ollama.com/library)

**GPU Support:** Uncomment the GPU section in `docker/compose/services/docker-compose.ollama.yml` for NVIDIA GPU acceleration.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Traefik                              │
│                    (Reverse Proxy/LB)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Frontend  │   │   Backend   │   │   Worker    │
│  (Next.js)  │   │  (FastAPI)  │   │   (ARQ)     │
└─────────────┘   └──────┬──────┘   └──────┬──────┘
                         │                 │
         ┌───────────────┼─────────────────┤
         │               │                 │
         ▼               ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ PostgreSQL  │   │    Redis    │   │ Meilisearch │
│  (pgvector) │   │   (Cache)   │   │  (Search)   │
└─────────────┘   └─────────────┘   └─────────────┘
```

## Docker Compose Organization

The docker-compose files are organized by purpose:

```
docker/compose/
├── base/
│   └── docker-compose.yml          # Core services (backend, frontend, db, redis)
├── dev/
│   ├── docker-compose.override.yml # Development-specific overrides
│   └── docker-compose.dev.yml      # Full development configuration
├── prod/
│   └── docker-compose.prod.yml     # Production configuration
└── services/
    ├── docker-compose.auth.yml     # Keycloak, OpenFGA, OpenBAO
    ├── docker-compose.management.yml # Portainer, pgAdmin
    ├── docker-compose.mongodb.yml  # MongoDB, Mongo Express
    └── docker-compose.monitoring.yml # Prometheus, Grafana
```

### Combining Compose Files

The Makefile handles combining compose files automatically:

```bash
# Development (base + dev override)
make dev

# Production (base + prod)
make prod

# With monitoring (base + dev + monitoring)
make dev && make monitoring-up

# All services
make dev && make all-services
```

## Troubleshooting

### Port Already in Use

```bash
# Check which process is using the port
lsof -i :8000

# Kill the process or change the port in .env
BACKEND_PORT=9000 make dev
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
make logs-db

# Connect directly to verify
make db-shell
```

### Container Won't Start

```bash
# Rebuild from scratch
make clean
make build-no-cache
make start
```

### Permission Issues

```bash
# Reset volumes (WARNING: destroys data)
make clean-volumes
make start
```

### View Docker Compose Structure

```bash
make show-structure
```

### Docker Volume Path Issues

If containers fail with errors like "ModuleNotFoundError", "package.json not found", or "is a directory":

```bash
# Clean up incorrectly created Docker directories
make clean-docker-dirs

# Or for a full reset
make reset-dev
```

This happens when Docker creates empty directories instead of mounting the actual source. The cleanup command removes these directories so Docker can properly mount the source code.

### Frontend Shows "Page Not Found" or Proxy Errors

If the frontend container is running but shows connection errors to the backend:

```bash
# Check backend container status
make logs-backend

# Verify all containers are running
make status

# If backend isn't running, check for build errors
docker compose -f docker/compose/base/docker-compose.yml \
               -f docker/compose/dev/docker-compose.override.yml \
               logs backend
```

The frontend proxies `/api/*` requests to the backend. If the backend isn't healthy, the frontend will show proxy errors.

## Additional Resources

- [Setup Chatbot Documentation](./SETUP_CHATBOT.md)
- [DevLake Improvements](./DEVLAKE_IMPROVEMENTS.md)
- [API Documentation](http://localhost:8000/docs)
