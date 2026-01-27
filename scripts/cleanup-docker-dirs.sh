#!/bin/bash
# =============================================================================
# Cleanup script for incorrectly created Docker directories
# =============================================================================
# Run this script to remove directories that were created by Docker
# when volume mounts used incorrect relative paths.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Docker Directory Cleanup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Stop all running containers first
echo -e "${YELLOW}[INFO]${NC} Stopping all containers..."
docker compose -f docker/compose/base/docker-compose.yml -f docker/compose/dev/docker-compose.override.yml down -v 2>/dev/null || true

# Directories that may have been incorrectly created
DIRS_TO_REMOVE=(
    "docker/compose/base/backend"
    "docker/compose/base/frontend"
    "docker/compose/base/deploy"
    "docker/compose/dev/backend"
    "docker/compose/dev/frontend"
)

echo ""
echo -e "${YELLOW}[INFO]${NC} Removing incorrectly created directories..."

for dir in "${DIRS_TO_REMOVE[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${YELLOW}[REMOVE]${NC} $dir"
        sudo rm -rf "$dir" 2>/dev/null || rm -rf "$dir" 2>/dev/null || {
            echo -e "${RED}[WARN]${NC} Could not remove $dir - may need sudo"
        }
    else
        echo -e "${GREEN}[OK]${NC} $dir does not exist"
    fi
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Cleanup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}[TIP]${NC} You can now start the development environment:"
echo -e "  make dev"
echo ""
