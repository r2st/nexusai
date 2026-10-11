#!/usr/bin/env bash
# =============================================================================
# NexusAI Deployment Script
# =============================================================================
# Automated deployment script for NexusAI platform
#
# Usage:
#   ./deploy.sh [command] [options]
#
# Commands:
#   up          Start all services (default)
#   down        Stop all services
#   restart     Restart all services
#   build       Build Docker images
#   logs        View logs
#   status      Check service status
#   migrate     Run database migrations
#   backup      Backup databases
#   restore     Restore from backup
#   k8s-deploy  Deploy to Kubernetes
#   k8s-delete  Delete from Kubernetes
#
# Options:
#   -e, --env        Environment (dev, staging, prod) [default: prod]
#   -m, --monitoring Include monitoring stack
#   -a, --auth       Include auth services
#   --management     Include management services
#   --mongodb        Include MongoDB service
#   --all            Include monitoring, auth, and management
#   -v, --verbose    Verbose output
#   -h, --help       Show this help message
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-nexusai}"
LOCK_FILE="/tmp/nexusai-deploy.lock"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="prod"
INCLUDE_MONITORING=false
INCLUDE_AUTH=false
INCLUDE_MANAGEMENT=false
INCLUDE_MONGODB=false
VERBOSE=false

# -----------------------------------------------------------------------------
# Cleanup and error handling
# -----------------------------------------------------------------------------
cleanup() {
    rm -f "$LOCK_FILE"
}

on_error() {
    local exit_code=$?
    log_error "Deployment failed with exit code $exit_code at line $1"
    cleanup
    exit "$exit_code"
}

trap 'on_error $LINENO' ERR
trap cleanup EXIT

acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
            log_error "Another deployment is running (PID: $lock_pid). Aborting."
            exit 1
        fi
        log_warn "Stale lock file found. Removing."
        rm -f "$LOCK_FILE"
    fi
    echo $$ > "$LOCK_FILE"
}

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

show_help() {
    head -n 30 "$0" | tail -n 28 | sed 's/^# //' | sed 's/^#//'
}

check_dependencies() {
    local deps=("docker")

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "$dep is required but not installed."
            exit 1
        fi
    done

    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        log_error "Docker Compose is required but not installed."
        exit 1
    fi
}

check_env_file() {
    local env_file="${PROJECT_ROOT}/.env"
    local example_file="${PROJECT_ROOT}/.env.example"

    if [[ ! -f "$env_file" ]]; then
        if [[ -f "$example_file" ]]; then
            log_warn ".env file not found. Creating from .env.example..."
            cp "$example_file" "$env_file"
            log_warn "Please update .env with your configuration before deploying."
            exit 1
        else
            log_error "Neither .env nor .env.example found!"
            exit 1
        fi
    fi

    # Validate required environment variables
    local required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY" "MEILISEARCH_API_KEY")

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$env_file" || grep -q "^${var}=$" "$env_file" || grep -q "^${var}=<" "$env_file"; then
            log_error "Required environment variable $var is not set in .env"
            exit 1
        fi
    done

    # Reject insecure default SECRET_KEY in non-dev environments
    if [[ "$ENVIRONMENT" != "dev" ]]; then
        local secret_key
        secret_key=$(grep -E '^SECRET_KEY=' "$env_file" | cut -d= -f2- || echo "")
        if [[ "$secret_key" == *"dev-secret-key"* ]] || [[ "$secret_key" == *"change-in-production"* ]]; then
            log_error "SECRET_KEY contains an insecure default value. Generate a proper secret: openssl rand -base64 32"
            exit 1
        fi
    fi
}

get_compose_files() {
    local compose_dir="${PROJECT_ROOT}/docker/compose"
    local files="-f ${compose_dir}/base/docker-compose.yml"

    if [[ "$ENVIRONMENT" == "dev" ]]; then
        files="$files -f ${compose_dir}/dev/docker-compose.dev.yml"
    elif [[ "$ENVIRONMENT" == "prod" ]]; then
        files="$files -f ${compose_dir}/prod/docker-compose.prod.yml"
    fi

    if [[ "$INCLUDE_AUTH" == true ]]; then
        files="$files -f ${compose_dir}/services/docker-compose.auth.yml"
    fi

    if [[ "$INCLUDE_MONITORING" == true ]]; then
        files="$files -f ${compose_dir}/services/docker-compose.monitoring.yml"
    fi

    if [[ "$INCLUDE_MANAGEMENT" == true ]]; then
        files="$files -f ${compose_dir}/services/docker-compose.management.yml"
    fi

    if [[ "$INCLUDE_MONGODB" == true ]]; then
        files="$files -f ${compose_dir}/services/docker-compose.mongodb.yml"
    fi

    echo "$files"
}

get_container_id() {
    local compose_files
    compose_files=$(get_compose_files)
    local service="$1"

    # shellcheck disable=SC2086
    $COMPOSE_CMD $compose_files -p "$COMPOSE_PROJECT_NAME" ps -q "$service" | head -n 1
}

# -----------------------------------------------------------------------------
# Command Functions
# -----------------------------------------------------------------------------
cmd_up() {
    acquire_lock
    log_info "Starting NexusAI services..."

    local compose_files
    compose_files=$(get_compose_files)

    # shellcheck disable=SC2086
    $COMPOSE_CMD $compose_files -p "$COMPOSE_PROJECT_NAME" up -d

    log_success "Services started successfully!"
    cmd_status
}

cmd_down() {
    log_info "Stopping NexusAI services..."

    local compose_files
    compose_files=$(get_compose_files)

    # shellcheck disable=SC2086
    $COMPOSE_CMD $compose_files -p "$COMPOSE_PROJECT_NAME" down

    log_success "Services stopped."
}

cmd_restart() {
    log_info "Restarting NexusAI services..."
    cmd_down
    cmd_up
}

cmd_build() {
    log_info "Building Docker images..."

    local compose_files
    compose_files=$(get_compose_files)

    # shellcheck disable=SC2086
    $COMPOSE_CMD $compose_files -p "$COMPOSE_PROJECT_NAME" build --no-cache

    log_success "Images built successfully!"
}

cmd_logs() {
    local compose_files
    compose_files=$(get_compose_files)

    local service="${1:-}"

    if [[ -n "$service" ]]; then
        # shellcheck disable=SC2086
        $COMPOSE_CMD $compose_files -p "$COMPOSE_PROJECT_NAME" logs -f "$service"
    else
        # shellcheck disable=SC2086
        $COMPOSE_CMD $compose_files -p "$COMPOSE_PROJECT_NAME" logs -f
    fi
}

cmd_status() {
    local compose_files
    compose_files=$(get_compose_files)

    echo ""
    echo "=== NexusAI Service Status ==="
    echo ""

    # shellcheck disable=SC2086
    $COMPOSE_CMD $compose_files -p "$COMPOSE_PROJECT_NAME" ps

    echo ""
    echo "=== Health Checks ==="
    echo ""

    # Check each service health
    local services=("backend" "frontend" "postgres" "redis" "meilisearch" "traefik")

    for service in "${services[@]}"; do
        local container_id
        container_id=$(get_container_id "$service")

        if [[ -n "$container_id" ]] && docker ps --format '{{.ID}}' | grep -q "^${container_id}$"; then
            local health
            health=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "no healthcheck")

            case "$health" in
                "healthy")
                    echo -e "  ${GREEN}✓${NC} $service: healthy"
                    ;;
                "unhealthy")
                    echo -e "  ${RED}✗${NC} $service: unhealthy"
                    ;;
                "starting")
                    echo -e "  ${YELLOW}○${NC} $service: starting"
                    ;;
                *)
                    echo -e "  ${BLUE}?${NC} $service: $health"
                    ;;
            esac
        else
            echo -e "  ${RED}✗${NC} $service: not running"
        fi
    done

    echo ""
}

cmd_migrate() {
    log_info "Running database migrations..."

    local compose_files
    compose_files=$(get_compose_files)

    # shellcheck disable=SC2086
    $COMPOSE_CMD $compose_files -p "$COMPOSE_PROJECT_NAME" exec backend alembic upgrade head

    log_success "Migrations completed!"
}

cmd_backup() {
    log_info "Creating database backup..."

    local backup_dir="${PROJECT_ROOT}/backups"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${backup_dir}/nexusai_backup_${timestamp}.sql.gz"

    mkdir -p "$backup_dir"

    local pg_user pg_db
    pg_user=$(grep -E '^POSTGRES_USER=' "${PROJECT_ROOT}/.env" | cut -d= -f2- | tr -d '"' || echo "nexusai")
    pg_db=$(grep -E '^POSTGRES_DB=' "${PROJECT_ROOT}/.env" | cut -d= -f2- | tr -d '"' || echo "nexusai")
    pg_user="${pg_user:-nexusai}"
    pg_db="${pg_db:-nexusai}"

    local container_id
    container_id=$(get_container_id "postgres")

    if [[ -z "$container_id" ]]; then
        log_error "Postgres container is not running."
        exit 1
    fi

    docker exec "$container_id" pg_dump \
        -U "$pg_user" \
        "$pg_db" | gzip > "$backup_file"

    log_success "Backup created: $backup_file"

    # Cleanup old backups (keep last 7)
    find "$backup_dir" -name "nexusai_backup_*.sql.gz" -mtime +7 -delete
    log_info "Cleaned up backups older than 7 days."
}

cmd_restore() {
    local backup_file="${1:-}"

    if [[ -z "$backup_file" ]]; then
        log_error "Please specify a backup file to restore."
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warn "This will replace all data in the database!"
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled."
        exit 0
    fi

    log_info "Restoring database from: $backup_file"

    local pg_user pg_db
    pg_user=$(grep -E '^POSTGRES_USER=' "${PROJECT_ROOT}/.env" | cut -d= -f2- | tr -d '"' || echo "nexusai")
    pg_db=$(grep -E '^POSTGRES_DB=' "${PROJECT_ROOT}/.env" | cut -d= -f2- | tr -d '"' || echo "nexusai")
    pg_user="${pg_user:-nexusai}"
    pg_db="${pg_db:-nexusai}"

    local container_id
    container_id=$(get_container_id "postgres")

    if [[ -z "$container_id" ]]; then
        log_error "Postgres container is not running."
        exit 1
    fi

    gunzip -c "$backup_file" | docker exec -i "$container_id" psql \
        -U "$pg_user" \
        "$pg_db"

    log_success "Database restored successfully!"
}

cmd_k8s_deploy() {
    log_info "Deploying to Kubernetes..."

    local k8s_dir="${PROJECT_ROOT}/deploy/k8s"

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required but not installed."
        exit 1
    fi

    # Apply namespace first
    kubectl apply -f "${k8s_dir}/namespace.yaml"

    # Apply ConfigMaps and Secrets
    kubectl apply -f "${k8s_dir}/configmap.yaml"

    log_warn "Please ensure secrets are properly configured before proceeding."
    log_warn "Update ${k8s_dir}/secrets.yaml with actual values or use external secrets."
    read -p "Continue with deployment? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled."
        exit 0
    fi

    # Apply all resources
    kubectl apply -f "${k8s_dir}/secrets.yaml"
    kubectl apply -f "${k8s_dir}/services.yaml"
    kubectl apply -f "${k8s_dir}/backend-deployment.yaml"
    kubectl apply -f "${k8s_dir}/frontend-deployment.yaml"
    kubectl apply -f "${k8s_dir}/worker-deployment.yaml"
    kubectl apply -f "${k8s_dir}/ingress.yaml"
    kubectl apply -f "${k8s_dir}/hpa.yaml"
    kubectl apply -f "${k8s_dir}/pdb.yaml"

    log_success "Kubernetes deployment completed!"
    log_info "Checking deployment status..."

    kubectl -n nexusai get pods
}

cmd_k8s_delete() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required but not installed."
        exit 1
    fi

    log_warn "This will delete all NexusAI resources from Kubernetes!"
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deletion cancelled."
        exit 0
    fi

    local k8s_dir="${PROJECT_ROOT}/deploy/k8s"

    kubectl delete -f "${k8s_dir}/" --ignore-not-found

    log_success "Kubernetes resources deleted."
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    # Parse arguments
    local command="${1:-up}"
    shift || true

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -m|--monitoring)
                INCLUDE_MONITORING=true
                shift
                ;;
            -a|--auth)
                INCLUDE_AUTH=true
                shift
                ;;
            --management)
                INCLUDE_MANAGEMENT=true
                shift
                ;;
            --mongodb)
                INCLUDE_MONGODB=true
                shift
                ;;
            --all)
                INCLUDE_MONITORING=true
                INCLUDE_AUTH=true
                INCLUDE_MANAGEMENT=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                set -x
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done

    # Validate environment
    case "$ENVIRONMENT" in
        dev|staging|prod)
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
            exit 1
            ;;
    esac

    # Change to project root
    cd "$PROJECT_ROOT"

    # Check dependencies
    check_dependencies

    # Check environment file (skip for some commands)
    case "$command" in
        help|-h|--help)
            ;;
        *)
            check_env_file
            ;;
    esac

    # Execute command
    case "$command" in
        up)
            cmd_up
            ;;
        down)
            cmd_down
            ;;
        restart)
            cmd_restart
            ;;
        build)
            cmd_build
            ;;
        logs)
            cmd_logs "$@"
            ;;
        status)
            cmd_status
            ;;
        migrate)
            cmd_migrate
            ;;
        backup)
            cmd_backup
            ;;
        restore)
            cmd_restore "$@"
            ;;
        k8s-deploy)
            cmd_k8s_deploy
            ;;
        k8s-delete)
            cmd_k8s_delete
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
