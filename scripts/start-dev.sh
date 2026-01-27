#!/bin/bash
# =============================================================================
# NexusAI Development Environment Startup Script
# =============================================================================
# This script ensures proper configuration before starting Docker services.
# Usage: ./start-dev.sh [docker-compose-args]
# Example: ./start-dev.sh (default: up -d --force-recreate)
#          ./start-dev.sh up -d --build (rebuild images)
#          ./start-dev.sh down (stop services)
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the project root directory (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  NexusAI Development Environment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# =============================================================================
# Step 1: Ensure root .env file exists
# =============================================================================
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}[INFO]${NC} .env file not found. Creating from .env.example..."
        cp .env.example .env
        echo -e "${GREEN}[OK]${NC} Created .env file"
    else
        echo -e "${RED}[ERROR]${NC} Neither .env nor .env.example found!"
        exit 1
    fi
else
    echo -e "${GREEN}[OK]${NC} Root .env file exists"
fi

# =============================================================================
# Step 2: Ensure backend .env file exists
# =============================================================================
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        echo -e "${YELLOW}[INFO]${NC} backend/.env file not found. Creating from backend/.env.example..."
        cp backend/.env.example backend/.env
        echo -e "${GREEN}[OK]${NC} Created backend/.env file"
    else
        echo -e "${YELLOW}[WARN]${NC} backend/.env.example not found, skipping backend .env setup"
    fi
else
    echo -e "${GREEN}[OK]${NC} Backend .env file exists"
fi

# =============================================================================
# Step 3: Load and validate environment variables
# =============================================================================
echo ""
echo -e "${BLUE}[INFO]${NC} Loading environment variables..."

# Export variables from .env file
set -a
source .env
set +a

# Display key configuration
echo -e "${BLUE}[CONFIG]${NC} Database: ${DATABASE_USER}@${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_NAME}"
echo -e "${BLUE}[CONFIG]${NC} Redis: ${REDIS_HOST}:${REDIS_PORT}"

# =============================================================================
# Step 4: Check for port conflicts
# =============================================================================
echo ""
echo -e "${BLUE}[INFO]${NC} Checking for port conflicts..."

check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}[WARN]${NC} Port $port ($service) is already in use"
        return 1
    else
        echo -e "${GREEN}[OK]${NC} Port $port ($service) is available"
        return 0
    fi
}

# Check critical ports (non-blocking warnings)
check_port "${DATABASE_PORT}" "PostgreSQL" || true
check_port "${REDIS_PORT}" "Redis" || true
check_port "${MEILISEARCH_PORT:-7700}" "Meilisearch" || true
check_port "${BACKEND_PORT:-8000}" "Backend API" || true
check_port "${FRONTEND_PORT:-3000}" "Frontend" || true

# =============================================================================
# Step 5: Docker Compose command setup
# =============================================================================
# Use organized docker-compose files from docker/compose/ directory
COMPOSE_BASE="docker/compose/base/docker-compose.yml"
COMPOSE_DEV="docker/compose/dev/docker-compose.override.yml"
COMPOSE_DEVLAKE="docker/compose/services/docker-compose.devlake.yml"
COMPOSE_CMD="docker compose --env-file .env -f $COMPOSE_BASE -f $COMPOSE_DEV"
COMPOSE_DEVLAKE_CMD="docker compose --env-file .env -f $COMPOSE_DEVLAKE"

# =============================================================================
# Step 6: Stop existing containers first (ensures clean port mappings)
# =============================================================================
echo ""
echo -e "${BLUE}[INFO]${NC} Stopping existing containers..."
$COMPOSE_CMD down 2>/dev/null || true
$COMPOSE_DEVLAKE_CMD down 2>/dev/null || true

# =============================================================================
# Step 6a: Clean up orphaned networks (fixes label mismatch errors)
# =============================================================================
echo ""
echo -e "${BLUE}[INFO]${NC} Cleaning up Docker networks..."
# Remove networks that might have incorrect labels from manual creation
docker network rm nexusai-internal 2>/dev/null || true
docker network rm nexusai-public 2>/dev/null || true

# =============================================================================
# Step 7: Start Docker Compose
# =============================================================================
echo ""
echo -e "${BLUE}[INFO]${NC} Starting Docker Compose..."

# Default to 'up -d --force-recreate --remove-orphans' if no arguments provided
if [ $# -eq 0 ]; then
    COMPOSE_ARGS="up -d --force-recreate --remove-orphans"
else
    COMPOSE_ARGS="$@"
fi

echo -e "${BLUE}[CMD]${NC} $COMPOSE_CMD $COMPOSE_ARGS"
$COMPOSE_CMD $COMPOSE_ARGS

# =============================================================================
# Step 7a: Start DevLake services
# =============================================================================
if [[ "$COMPOSE_ARGS" == *"up"* ]]; then
    echo ""
    echo -e "${BLUE}[INFO]${NC} Starting DevLake services..."
    # Note: Do NOT use --remove-orphans here as it would remove main services
    # DevLake uses external networks created by the main compose stack
    $COMPOSE_DEVLAKE_CMD up -d
fi

# =============================================================================
# Step 8: Wait for services and show status
# =============================================================================
if [[ "$COMPOSE_ARGS" == *"up"* ]]; then
    echo ""
    echo -e "${BLUE}[INFO]${NC} Waiting for services to be healthy..."
    sleep 5

    # Show container status with env file
    echo ""
    $COMPOSE_CMD ps

    # Verify postgres port mapping
    echo ""
    POSTGRES_PORTS=$($COMPOSE_CMD ps postgres --format "{{.Ports}}" 2>/dev/null || echo "unknown")
    if [[ "$POSTGRES_PORTS" == *"${DATABASE_PORT}"* ]]; then
        echo -e "${GREEN}[OK]${NC} PostgreSQL port mapping verified: $POSTGRES_PORTS"
    else
        echo -e "${YELLOW}[WARN]${NC} PostgreSQL ports: $POSTGRES_PORTS (expected ${DATABASE_PORT}->5432)"
    fi

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Services Started Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "  Frontend:    ${BLUE}http://localhost:${FRONTEND_PORT:-3000}${NC}"
    echo -e "  Backend API: ${BLUE}http://localhost:${BACKEND_PORT:-8000}${NC}"
    echo -e "  API Docs:    ${BLUE}http://localhost:${BACKEND_PORT:-8000}/docs${NC}"
    echo -e "  PostgreSQL:  ${BLUE}localhost:${DATABASE_PORT}${NC}"
    echo -e "  Redis:       ${BLUE}localhost:${REDIS_PORT}${NC}"
    echo -e "  Meilisearch: ${BLUE}http://localhost:${MEILISEARCH_PORT:-7700}${NC}"
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  DevLake Services${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "  DevLake UI:  ${BLUE}http://localhost:4000${NC} (Configure connections)"
    echo -e "  DevLake API: ${BLUE}http://localhost:8080${NC}"
    echo -e "  Grafana:     ${BLUE}http://localhost:3002${NC} (DORA Dashboards)"
    echo ""
    echo -e "  ${YELLOW}Note:${NC} DevLake services may take 30-60 seconds to become healthy."
    echo -e "  ${YELLOW}Note:${NC} Use the chat to configure GitHub connections and get DORA metrics."
    echo ""
    echo -e "${YELLOW}[TIP]${NC} Run database migrations:"
    echo -e "  make migrate"
    echo ""
    echo -e "${YELLOW}[TIP]${NC} View logs:"
    echo -e "  make logs             # All services"
    echo -e "  make logs-backend     # Backend only"
    echo ""

    # Show development users if in development mode
    if [ "${ENVIRONMENT:-development}" = "development" ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  Development Test Users${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "  ${BLUE}Email${NC}                        ${BLUE}Password${NC}     ${BLUE}Role${NC}"
        echo -e "  ─────────────────────────────────────────────────────"
        echo -e "  admin@nexusai.dev            admin123     admin (superuser)"
        echo -e "  user@nexusai.dev             user123      user"
        echo -e "  viewer@nexusai.dev           viewer123    viewer"
        echo ""
        echo -e "  ${YELLOW}Note:${NC} Users are auto-created on first backend startup."
        echo -e "  ${YELLOW}Note:${NC} Run 'make migrate' first if this is a fresh database."
        echo ""
    fi
fi
