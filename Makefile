# NexusAI Makefile
# Run `make help` to see all available commands

.PHONY: help install dev start stop restart build logs clean test lint migrate \
        db-shell redis-cli backend-shell frontend-shell \
        prod prod-up prod-down prod-logs \
        docker-build docker-push \
        backup restore \
        docs api-docs oss-check

# Default target
.DEFAULT_GOAL := help

# Colors for help output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Project configuration
PROJECT_NAME := nexusai
SCRIPTS_DIR := scripts

# Docker Compose paths (organized structure)
COMPOSE_BASE := docker/compose/base/docker-compose.yml
COMPOSE_DEV := docker/compose/dev/docker-compose.override.yml
COMPOSE_DEV_FULL := docker/compose/dev/docker-compose.dev.yml
COMPOSE_PROD := docker/compose/prod/docker-compose.prod.yml
COMPOSE_AUTH := docker/compose/services/docker-compose.auth.yml
COMPOSE_MGMT := docker/compose/services/docker-compose.management.yml
COMPOSE_MONGO := docker/compose/services/docker-compose.mongodb.yml
COMPOSE_MON := docker/compose/services/docker-compose.monitoring.yml
COMPOSE_OLLAMA := docker/compose/services/docker-compose.ollama.yml

# Docker Compose commands
DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_DEV := $(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV)
DOCKER_COMPOSE_PROD := $(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_PROD)

# Container names (for docker exec)
BACKEND_CONTAINER := nexusai-backend
FRONTEND_CONTAINER := nexusai-frontend
POSTGRES_CONTAINER := nexusai-postgres

# Environment detection
ENV_FILE := .env
ENV_EXAMPLE := .env.example

#=============================================================================
# HELP
#=============================================================================

help: ## Show this help message
	@echo ""
	@echo "$(GREEN)NexusAI Development Commands$(RESET)"
	@echo "==============================="
	@echo ""
	@echo "$(YELLOW)Usage:$(RESET) make [target]"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} \
		/^[a-zA-Z_-]+:.*##/ { \
			printf "  $(BLUE)%-22s$(RESET) %s\n", $$1, $$2 \
		} \
		/^##@/ { \
			printf "\n$(YELLOW)%s$(RESET)\n", substr($$0, 5) \
		}' $(MAKEFILE_LIST)
	@echo ""

##@ Setup

install: env-check ## Initial project setup
	@echo "$(GREEN)Setting up NexusAI...$(RESET)"
	@$(MAKE) env-setup
	@$(MAKE) build
	@$(MAKE) start
	@$(MAKE) migrate
	@echo "$(GREEN)Setup complete!$(RESET)"
	@echo ""
	@echo "Services available at:"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"

env-setup: ## Create .env file from example if not exists
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(YELLOW)Creating .env from .env.example...$(RESET)"; \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "$(GREEN).env created. Please update with your API keys.$(RESET)"; \
	else \
		echo "$(BLUE).env already exists$(RESET)"; \
	fi

env-check: ## Verify required environment variables
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(RED)Error: .env file not found$(RESET)"; \
		echo "Run: make env-setup"; \
		exit 1; \
	fi

oss-check: ## Scan for secrets before open-sourcing
	@./$(SCRIPTS_DIR)/oss-check.sh

##@ Development

dev: env-check ## Start development environment using script
	@./$(SCRIPTS_DIR)/start-dev.sh

start: env-check ## Start all services in development mode
	@echo "$(GREEN)Starting development services...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) up -d --remove-orphans
	@$(MAKE) status

stop: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) down

restart: ## Restart all services
	@$(MAKE) stop
	@$(MAKE) start

restart-backend: ## Restart backend and worker containers
	@echo "$(YELLOW)Restarting backend services...$(RESET)"
	@docker restart nexusai-backend nexusai-worker
	@$(MAKE) status

restart-frontend: ## Restart frontend container
	@echo "$(YELLOW)Restarting frontend...$(RESET)"
	@docker restart nexusai-frontend
	@$(MAKE) status

restart-db: ## Restart database services (postgres, redis, meilisearch)
	@echo "$(YELLOW)Restarting database services...$(RESET)"
	@docker restart nexusai-postgres nexusai-redis nexusai-meilisearch
	@$(MAKE) status

rebuild-backend: ## Rebuild backend image and restart (use after changing requirements.txt)
	@echo "$(YELLOW)Rebuilding backend...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) build backend
	@$(DOCKER_COMPOSE_DEV) up -d --force-recreate backend worker
	@$(MAKE) status

rebuild-frontend: ## Rebuild frontend image and restart
	@echo "$(YELLOW)Rebuilding frontend...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) build frontend
	@$(DOCKER_COMPOSE_DEV) up -d --force-recreate frontend
	@$(MAKE) status

rebuild: ## Rebuild and restart all services
	@echo "$(YELLOW)Rebuilding services...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) up -d --build --force-recreate
	@$(MAKE) status

status: ## Show status of all services
	@echo ""
	@echo "$(GREEN)Service Status:$(RESET)"
	@$(DOCKER_COMPOSE_DEV) ps
	@echo ""
	@echo "$(GREEN)Endpoints:$(RESET)"
	@echo "  Frontend:    http://localhost:3000"
	@echo "  Backend:     http://localhost:8000"
	@echo "  API Docs:    http://localhost:8000/docs"
	@echo "  PostgreSQL:  localhost:5434"
	@echo "  Redis:       localhost:6379"
	@echo "  Meilisearch: http://localhost:7700"

##@ Logs & Debugging

logs: ## View logs from all services (follow mode)
	@$(DOCKER_COMPOSE_DEV) logs -f

logs-backend: ## View backend logs
	@$(DOCKER_COMPOSE_DEV) logs -f $(BACKEND_CONTAINER)

logs-frontend: ## View frontend logs
	@$(DOCKER_COMPOSE_DEV) logs -f $(FRONTEND_CONTAINER)

logs-worker: ## View worker logs
	@$(DOCKER_COMPOSE_DEV) logs -f worker

logs-db: ## View database logs
	@$(DOCKER_COMPOSE_DEV) logs -f postgres

logs-redis: ## View Redis logs
	@$(DOCKER_COMPOSE_DEV) logs -f redis

logs-traefik: ## View Traefik logs
	@$(DOCKER_COMPOSE_DEV) logs -f traefik

logs-meilisearch: ## View Meilisearch logs
	@$(DOCKER_COMPOSE_DEV) logs -f meilisearch

logs-tail: ## View last 100 lines of backend logs (no follow)
	@docker logs nexusai-backend --tail 100

##@ Shell Access

backend-shell: ## Open shell in backend container
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) bash

frontend-shell: ## Open shell in frontend container
	@$(DOCKER_COMPOSE_DEV) exec $(FRONTEND_CONTAINER) sh

db-shell: ## Open PostgreSQL shell
	@$(DOCKER_COMPOSE_DEV) exec postgres psql -U postgres -d nexusai

redis-cli: ## Open Redis CLI
	@$(DOCKER_COMPOSE_DEV) exec redis redis-cli

##@ Database

migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(RESET)"
	@docker exec nexusai-backend alembic upgrade head || $(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: MSG is required$(RESET)"; \
		echo "Usage: make migrate-create MSG=\"your migration message\""; \
		exit 1; \
	fi
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) alembic downgrade -1

migrate-history: ## Show migration history
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) alembic history

seed-users: ## Seed development users (admin, user, viewer)
	@echo "$(GREEN)Seeding development users...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) python -m scripts.seed_dev_users seed
	@echo ""
	@echo "$(GREEN)Default users created:$(RESET)"
	@echo "  admin@nexusai.dev    (password: admin123)  - Admin"
	@echo "  user@nexusai.dev     (password: user123)   - User"
	@echo "  viewer@nexusai.dev   (password: viewer123) - Viewer"

seed-users-reset: ## Reset and reseed development users
	@echo "$(YELLOW)Resetting development users...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) python -m scripts.seed_dev_users reset

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "$(RED)WARNING: This will destroy all data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(DOCKER_COMPOSE_DEV) down -v
	@$(MAKE) start
	@sleep 5
	@$(MAKE) migrate

##@ Testing

test: ## Run all tests
	@echo "$(GREEN)Running tests...$(RESET)"
	@$(MAKE) test-backend
	@$(MAKE) test-frontend

test-db-setup: ## Create test database if it doesn't exist
	@echo "$(BLUE)Ensuring test database exists...$(RESET)"
	@docker exec $(POSTGRES_CONTAINER) psql -U $${POSTGRES_USER:-postgres} -tc "SELECT 1 FROM pg_database WHERE datname = 'nexusai_test'" | grep -q 1 || \
		docker exec $(POSTGRES_CONTAINER) psql -U $${POSTGRES_USER:-postgres} -c "CREATE DATABASE nexusai_test;"
	@docker exec $(POSTGRES_CONTAINER) psql -U $${POSTGRES_USER:-postgres} -d nexusai_test -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" 2>/dev/null || true

test-backend: test-db-setup ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(RESET)"
	@docker exec $(BACKEND_CONTAINER) pytest tests/ -v

test-backend-cov: test-db-setup ## Run backend tests with coverage
	@docker exec $(BACKEND_CONTAINER) pytest tests/ -v --cov=app --cov-report=html

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(RESET)"
	@docker exec $(FRONTEND_CONTAINER) npm test -- --run

test-frontend-cov: ## Run frontend tests with coverage
	@docker exec $(FRONTEND_CONTAINER) npm run test:coverage

test-backend-unit: test-db-setup ## Run backend unit tests only
	@echo "$(BLUE)Running backend unit tests...$(RESET)"
	@docker exec $(BACKEND_CONTAINER) pytest tests/unit/ -v

test-backend-integration: test-db-setup ## Run backend integration tests only
	@echo "$(BLUE)Running backend integration tests...$(RESET)"
	@docker exec $(BACKEND_CONTAINER) pytest tests/integration/ -v

test-backend-quick: test-db-setup ## Run backend tests (no coverage, stop on first failure)
	@echo "$(BLUE)Running backend tests (quick)...$(RESET)"
	@docker exec $(BACKEND_CONTAINER) pytest tests/ -v -x --tb=short

test-backend-api: test-db-setup ## Run backend API tests (auth, chat, organizations)
	@echo "$(BLUE)Running backend API tests...$(RESET)"
	@docker exec $(BACKEND_CONTAINER) pytest tests/unit/test_auth.py tests/unit/test_chat.py tests/unit/test_organizations.py tests/unit/test_health.py -v

test-backend-specific: test-db-setup ## Run specific test file (usage: make test-backend-specific FILE=test_auth.py)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: FILE is required$(RESET)"; \
		echo "Usage: make test-backend-specific FILE=test_auth.py"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running tests from $(FILE)...$(RESET)"
	@docker exec $(BACKEND_CONTAINER) pytest tests/ -v -k "$(FILE)" || \
		docker exec $(BACKEND_CONTAINER) pytest tests/**/$(FILE) -v

##@ Code Quality

lint: ## Run all linters
	@$(MAKE) lint-backend
	@$(MAKE) lint-frontend

lint-backend: ## Lint backend code
	@echo "$(BLUE)Linting backend...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) ruff check app/
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) ruff format --check app/

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)Linting frontend...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) exec $(FRONTEND_CONTAINER) npm run lint

format: ## Format all code
	@$(MAKE) format-backend
	@$(MAKE) format-frontend

format-backend: ## Format backend code
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) ruff format app/
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) ruff check --fix app/

format-frontend: ## Format frontend code
	@$(DOCKER_COMPOSE_DEV) exec $(FRONTEND_CONTAINER) npm run lint -- --fix

typecheck: ## Run type checking
	@echo "$(BLUE)Type checking backend...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) exec $(BACKEND_CONTAINER) mypy app/
	@echo "$(BLUE)Type checking frontend...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) exec $(FRONTEND_CONTAINER) npm run type-check

##@ Production

prod: ## Start production environment
	@$(MAKE) prod-up

prod-up: env-check ## Start production services
	@echo "$(GREEN)Starting production services...$(RESET)"
	@$(DOCKER_COMPOSE_PROD) up -d
	@$(MAKE) prod-status

prod-down: ## Stop production services
	@$(DOCKER_COMPOSE_PROD) down

prod-logs: ## View production logs
	@$(DOCKER_COMPOSE_PROD) logs -f

prod-restart: ## Restart production services
	@$(DOCKER_COMPOSE_PROD) restart

prod-status: ## Show production service status
	@echo ""
	@echo "$(GREEN)Production Service Status:$(RESET)"
	@$(DOCKER_COMPOSE_PROD) ps

prod-scale: ## Scale backend (usage: make prod-scale N=3)
	@if [ -z "$(N)" ]; then \
		echo "$(RED)Error: N is required$(RESET)"; \
		echo "Usage: make prod-scale N=3"; \
		exit 1; \
	fi
	@$(DOCKER_COMPOSE_PROD) up -d --scale backend=$(N)

##@ Deployment

deploy: ## Deploy to production (usage: make deploy ENV=prod)
	@./$(SCRIPTS_DIR)/deploy.sh up -e $(ENV) -m

deploy-down: ## Stop production deployment
	@./$(SCRIPTS_DIR)/deploy.sh down -e $(ENV)

deploy-status: ## Show deployment status
	@./$(SCRIPTS_DIR)/deploy.sh status -e $(ENV)

##@ Optional Services

auth-up: ## Start authentication services (Keycloak, OpenFGA, OpenBAO)
	@echo "$(GREEN)Starting authentication services...$(RESET)"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_AUTH) up -d
	@echo "$(GREEN)Auth services started:$(RESET)"
	@echo "  Keycloak:  http://localhost:8081"
	@echo "  OpenFGA:   http://localhost:8082"
	@echo "  OpenBAO:   http://localhost:8200"

auth-down: ## Stop authentication services
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_AUTH) down

mongodb-up: ## Start MongoDB service
	@echo "$(GREEN)Starting MongoDB...$(RESET)"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_MONGO) up -d
	@echo "$(GREEN)MongoDB available at:$(RESET)"
	@echo "  MongoDB:       localhost:27017"
	@echo "  Mongo Express: http://localhost:8083"

mongodb-down: ## Stop MongoDB service
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_MONGO) down

monitoring-up: ## Start monitoring stack (Prometheus, Grafana)
	@echo "$(GREEN)Starting monitoring stack...$(RESET)"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_MON) up -d
	@echo "$(GREEN)Monitoring available at:$(RESET)"
	@echo "  Grafana:    http://localhost:3001"
	@echo "  Prometheus: http://localhost:9090"

monitoring-down: ## Stop monitoring stack
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_MON) down

management-up: ## Start management services (Portainer, pgAdmin)
	@echo "$(GREEN)Starting management services...$(RESET)"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_MGMT) up -d
	@echo "$(GREEN)Management available at:$(RESET)"
	@echo "  Portainer: http://localhost:9443"
	@echo "  pgAdmin:   http://localhost:5050"

management-down: ## Stop management services
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BASE) -f $(COMPOSE_MGMT) down

all-services: ## Start all optional services
	@$(MAKE) auth-up
	@$(MAKE) mongodb-up
	@$(MAKE) monitoring-up
	@$(MAKE) management-up
	@$(MAKE) devlake-up

all-services-down: ## Stop all optional services
	@$(MAKE) auth-down
	@$(MAKE) mongodb-down
	@$(MAKE) monitoring-down
	@$(MAKE) management-down
	@$(MAKE) devlake-down

##@ Local LLM (Ollama)

ollama-up: ## Start Ollama for local LLMs (Llama, Mistral, etc.)
	@echo "$(GREEN)Starting Ollama...$(RESET)"
	@docker network create nexusai-network 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(COMPOSE_OLLAMA) up -d
	@echo "$(GREEN)Ollama available at:$(RESET)"
	@echo "  Ollama API: http://localhost:11434"
	@echo "  Web UI:     http://localhost:3003"
	@echo ""
	@echo "$(YELLOW)Pull a model with:$(RESET)"
	@echo "  make ollama-pull MODEL=llama3"
	@echo "  make ollama-pull MODEL=mistral"
	@echo "  make ollama-pull MODEL=codellama"

ollama-down: ## Stop Ollama
	@$(DOCKER_COMPOSE) -f $(COMPOSE_OLLAMA) down

ollama-pull: ## Pull an Ollama model (usage: make ollama-pull MODEL=llama3)
	@if [ -z "$(MODEL)" ]; then \
		echo "$(RED)Error: MODEL is required$(RESET)"; \
		echo "Usage: make ollama-pull MODEL=llama3"; \
		echo ""; \
		echo "Popular models:"; \
		echo "  llama3      - Meta Llama 3 (8B)"; \
		echo "  llama3:70b  - Meta Llama 3 (70B)"; \
		echo "  mistral     - Mistral 7B"; \
		echo "  mixtral     - Mixtral 8x7B"; \
		echo "  codellama   - Code Llama"; \
		echo "  phi3        - Microsoft Phi-3"; \
		echo "  gemma       - Google Gemma"; \
		echo "  qwen2       - Alibaba Qwen 2"; \
		exit 1; \
	fi
	@echo "$(GREEN)Pulling $(MODEL)...$(RESET)"
	@docker exec nexusai-ollama ollama pull $(MODEL)

ollama-list: ## List installed Ollama models
	@docker exec nexusai-ollama ollama list

ollama-run: ## Run a model interactively (usage: make ollama-run MODEL=llama3)
	@if [ -z "$(MODEL)" ]; then \
		echo "$(RED)Error: MODEL is required$(RESET)"; \
		echo "Usage: make ollama-run MODEL=llama3"; \
		exit 1; \
	fi
	@docker exec -it nexusai-ollama ollama run $(MODEL)

ollama-logs: ## View Ollama logs
	@$(DOCKER_COMPOSE) -f $(COMPOSE_OLLAMA) logs -f ollama

ollama-status: ## Show Ollama status and models
	@echo "$(GREEN)Ollama Status:$(RESET)"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_OLLAMA) ps
	@echo ""
	@echo "$(GREEN)Installed Models:$(RESET)"
	@docker exec nexusai-ollama ollama list 2>/dev/null || echo "  Ollama not running"

##@ DevLake (Engineering Analytics)

COMPOSE_DEVLAKE=docker/compose/services/docker-compose.devlake.yml

devlake-up: ## Start DevLake for GitHub, Jira, Jenkins data collection
	@echo "$(GREEN)Starting DevLake...$(RESET)"
	@docker network create nexusai-internal 2>/dev/null || true
	@docker network create nexusai-public 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEVLAKE) up -d --remove-orphans
	@echo ""
	@echo "$(GREEN)DevLake services starting...$(RESET)"
	@echo "Please wait 30-60 seconds for services to become healthy."
	@echo ""
	@echo "$(GREEN)Access URLs:$(RESET)"
	@echo "  DevLake UI:  http://localhost:4000  (Configure connections here)"
	@echo "  DevLake API: http://localhost:8080"
	@echo "  Grafana:     http://localhost:3002  (Dashboards)"
	@echo ""
	@echo "$(YELLOW)Quick Start:$(RESET)"
	@echo "  1. Open http://localhost:4000"
	@echo "  2. Click 'Create Connection'"
	@echo "  3. Select 'GitHub' and enter your token"
	@echo "  4. Create a project and run a data collection"

devlake-down: ## Stop DevLake
	@echo "$(YELLOW)Stopping DevLake...$(RESET)"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEVLAKE) down

devlake-logs: ## View DevLake logs
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEVLAKE) logs -f devlake

devlake-status: ## Show DevLake status
	@echo "$(GREEN)DevLake Status:$(RESET)"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEVLAKE) ps
	@echo ""
	@curl -s http://localhost:8080/api/ping 2>/dev/null && echo "$(GREEN)DevLake API: Healthy$(RESET)" || echo "$(YELLOW)DevLake API: Not responding (may still be starting)$(RESET)"

devlake-reset: ## Reset DevLake (WARNING: destroys all collected data)
	@echo "$(RED)WARNING: This will destroy all DevLake data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEVLAKE) down -v
	@echo "$(GREEN)DevLake data cleared. Run 'make devlake-up' to start fresh.$(RESET)"

##@ Docker

build: ## Build all Docker images
	@echo "$(GREEN)Building Docker images...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) build

build-backend: ## Build backend image
	@$(DOCKER_COMPOSE_DEV) build $(BACKEND_CONTAINER)

build-frontend: ## Build frontend image
	@$(DOCKER_COMPOSE_DEV) build $(FRONTEND_CONTAINER)

build-no-cache: ## Build all images without cache
	@$(DOCKER_COMPOSE_DEV) build --no-cache

docker-push: ## Push images to registry (requires REGISTRY env var)
	@if [ -z "$(REGISTRY)" ]; then \
		echo "$(RED)Error: REGISTRY is required$(RESET)"; \
		echo "Usage: make docker-push REGISTRY=your-registry.com"; \
		exit 1; \
	fi
	@docker tag $(PROJECT_NAME)-backend $(REGISTRY)/$(PROJECT_NAME)-backend:latest
	@docker tag $(PROJECT_NAME)-frontend $(REGISTRY)/$(PROJECT_NAME)-frontend:latest
	@docker push $(REGISTRY)/$(PROJECT_NAME)-backend:latest
	@docker push $(REGISTRY)/$(PROJECT_NAME)-frontend:latest

##@ Backup & Restore

backup: ## Backup database
	@echo "$(GREEN)Creating database backup...$(RESET)"
	@mkdir -p backups
	@$(DOCKER_COMPOSE_DEV) exec postgres pg_dump -U postgres nexusai > backups/nexusai_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup created in backups/ directory$(RESET)"

restore: ## Restore database (usage: make restore FILE=backups/file.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: FILE is required$(RESET)"; \
		echo "Usage: make restore FILE=backups/nexusai_20240101_120000.sql"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restoring database from $(FILE)...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) exec -T postgres psql -U postgres -d nexusai < $(FILE)
	@echo "$(GREEN)Restore complete$(RESET)"

##@ Local Development (without Docker)

local-backend: ## Run backend locally (requires Python 3.12+)
	@echo "$(GREEN)Starting backend locally...$(RESET)"
	@cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

local-frontend: ## Run frontend locally (requires Node 20+)
	@echo "$(GREEN)Starting frontend locally...$(RESET)"
	@cd frontend && npm run dev

local-install-backend: ## Install backend dependencies locally
	@cd backend && pip install -r requirements.txt

local-install-frontend: ## Install frontend dependencies locally
	@cd frontend && npm install

local-install: ## Install all local dependencies
	@$(MAKE) local-install-backend
	@$(MAKE) local-install-frontend

##@ Cleanup

clean: ## Remove stopped containers and dangling images
	@echo "$(YELLOW)Cleaning up...$(RESET)"
	@docker system prune -f

clean-all: ## Remove all containers, images, and volumes (WARNING: destroys data)
	@echo "$(RED)WARNING: This will remove ALL Docker data including volumes!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(DOCKER_COMPOSE_DEV) down -v --rmi all
	@docker system prune -af --volumes

clean-volumes: ## Remove all volumes (WARNING: destroys data)
	@echo "$(RED)WARNING: This will destroy all data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(DOCKER_COMPOSE_DEV) down -v

clean-db-volume: ## Remove only PostgreSQL volume (WARNING: destroys database)
	@echo "$(RED)WARNING: This will destroy the database!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker volume rm nexusai-postgres-data 2>/dev/null || docker volume rm base_nexusai-postgres-data 2>/dev/null || echo "$(YELLOW)Volume not found or already removed$(RESET)"
	@echo "$(GREEN)Database volume removed. Run 'make dev' then 'make migrate' to recreate.$(RESET)"

clean-redis-volume: ## Remove only Redis volume
	@docker volume rm nexusai-redis-data 2>/dev/null || docker volume rm base_nexusai-redis-data 2>/dev/null || echo "$(YELLOW)Volume not found$(RESET)"

list-volumes: ## List all project volumes
	@echo "$(GREEN)Project Volumes:$(RESET)"
	@docker volume ls | grep -E "nexusai|base_" || echo "  No project volumes found"

clean-containers: ## Remove all nexusai containers (fixes "container name already in use" errors)
	@echo "$(YELLOW)Stopping and removing all nexusai containers...$(RESET)"
	@docker stop $$(docker ps -aq --filter "name=nexusai") 2>/dev/null || true
	@docker rm $$(docker ps -aq --filter "name=nexusai") 2>/dev/null || true
	@echo "$(GREEN)Containers removed. Run 'make dev' to start fresh.$(RESET)"

nuke: ## Nuclear option: stop everything, remove all containers and volumes
	@echo "$(RED)NUCLEAR OPTION: This will destroy EVERYTHING!$(RESET)"
	@read -p "Are you absolutely sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker stop $$(docker ps -q --filter "name=nexusai") 2>/dev/null || true
	@docker rm $$(docker ps -aq --filter "name=nexusai") 2>/dev/null || true
	@docker volume rm $$(docker volume ls -q | grep -E "nexusai|base_") 2>/dev/null || true
	@docker network rm nexusai-internal nexusai-public 2>/dev/null || true
	@echo "$(GREEN)Everything removed. Run 'make dev' to start fresh.$(RESET)"

clean-docker-dirs: ## Remove incorrectly created Docker directories
	@echo "$(YELLOW)Cleaning up Docker directories...$(RESET)"
	@$(DOCKER_COMPOSE_DEV) down 2>/dev/null || true
	@sudo rm -rf docker/compose/base/backend docker/compose/base/frontend docker/compose/base/deploy 2>/dev/null || \
		rm -rf docker/compose/base/backend docker/compose/base/frontend docker/compose/base/deploy 2>/dev/null || \
		echo "$(YELLOW)Some directories may require manual removal with sudo$(RESET)"
	@sudo rm -rf docker/compose/dev/backend docker/compose/dev/frontend 2>/dev/null || \
		rm -rf docker/compose/dev/backend docker/compose/dev/frontend 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete$(RESET)"

reset-dev: ## Full reset: stop containers, clean dirs, rebuild (WARNING: loses data)
	@echo "$(RED)WARNING: This will reset your development environment!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(MAKE) clean-docker-dirs
	@$(MAKE) clean-volumes
	@$(MAKE) dev

##@ Documentation

docs: ## Open documentation
	@echo "$(GREEN)Documentation:$(RESET)"
	@echo "  Development:   docs/DEVELOPMENT.md"
	@echo "  Setup Chatbot: docs/SETUP_CHATBOT.md"
	@echo "  Improvements:  docs/DEVLAKE_IMPROVEMENTS.md"
	@echo "  API Docs:      http://localhost:8000/docs (when running)"

docs-site-install: ## Install documentation site dependencies (Docusaurus)
	@cd docs && npm install

docs-site-dev: ## Run documentation site locally (Docusaurus)
	@cd docs && npm install && npm run start

docs-site-build: ## Build static HTML documentation (outputs docs/build/)
	@cd docs && npm install && npm run build

docs-site-serve: ## Serve the built static HTML docs (from docs/build/)
	@cd docs && npm install && npm run serve

api-docs: ## Open API documentation in browser
	@echo "$(GREEN)Opening API docs...$(RESET)"
	@open http://localhost:8000/docs 2>/dev/null || xdg-open http://localhost:8000/docs 2>/dev/null || echo "Open http://localhost:8000/docs in your browser"

##@ Kubernetes (requires kubectl & helm)

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(GREEN)Deploying to Kubernetes...$(RESET)"
	@helm upgrade --install $(PROJECT_NAME) ./helm/$(PROJECT_NAME) -f ./helm/$(PROJECT_NAME)/values.yaml

k8s-delete: ## Delete from Kubernetes
	@helm uninstall $(PROJECT_NAME)

k8s-status: ## Show Kubernetes deployment status
	@kubectl get pods -l app=$(PROJECT_NAME)
	@kubectl get svc -l app=$(PROJECT_NAME)

##@ Utilities

show-ports: ## Show all port mappings
	@echo "$(GREEN)Port Mappings:$(RESET)"
	@echo "  Frontend:    3000"
	@echo "  Backend:     8000"
	@echo "  PostgreSQL:  5434"
	@echo "  Redis:       6379"
	@echo "  Meilisearch: 7700"
	@echo "  Keycloak:    8081"
	@echo "  OpenFGA:     8082"
	@echo "  MongoDB:     27017"
	@echo "  Grafana:     3001"
	@echo "  Prometheus:  9090"
	@echo "  Portainer:   9443"
	@echo "  pgAdmin:     5050"

show-structure: ## Show docker-compose file structure
	@echo "$(GREEN)Docker Compose Structure:$(RESET)"
	@echo ""
	@echo "  docker/compose/"
	@echo "  ├── base/"
	@echo "  │   └── docker-compose.yml       (core services)"
	@echo "  ├── dev/"
	@echo "  │   ├── docker-compose.override.yml (dev overrides)"
	@echo "  │   └── docker-compose.dev.yml   (full dev config)"
	@echo "  ├── prod/"
	@echo "  │   └── docker-compose.prod.yml  (production config)"
	@echo "  └── services/"
	@echo "      ├── docker-compose.auth.yml       (Keycloak, OpenFGA, OpenBAO)"
	@echo "      ├── docker-compose.management.yml (Portainer, pgAdmin)"
	@echo "      ├── docker-compose.mongodb.yml    (MongoDB, Mongo Express)"
	@echo "      └── docker-compose.monitoring.yml (Prometheus, Grafana)"
