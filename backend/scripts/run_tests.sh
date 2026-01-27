#!/bin/bash
# Backend Test Runner Script
# Run comprehensive tests for the NexusAI backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  NexusAI Backend Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Default values
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_COVERAGE=false
VERBOSE=""
MARKERS=""
TEST_PATH="tests/"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_INTEGRATION=false
            TEST_PATH="tests/unit/"
            shift
            ;;
        --integration-only)
            RUN_UNIT=false
            TEST_PATH="tests/integration/"
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -vv)
            VERBOSE="-vv"
            shift
            ;;
        -k)
            MARKERS="-k $2"
            shift 2
            ;;
        -m)
            MARKERS="-m $2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --unit-only          Run only unit tests"
            echo "  --integration-only   Run only integration tests"
            echo "  --coverage           Generate coverage report"
            echo "  -v, --verbose        Verbose output"
            echo "  -vv                  More verbose output"
            echo "  -k EXPRESSION        Run tests matching expression"
            echo "  -m MARKER            Run tests with marker"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if in correct directory
if [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Must run from backend directory${NC}"
    exit 1
fi

# Activate virtual environment if exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -d ".venv" ] || [ -d "venv" ]; then
    echo -e "${YELLOW}Warning: virtual env found but activation script missing.${NC}"
    echo -e "${YELLOW}Proceeding with current Python environment.${NC}"
fi

# Set test environment variables
export ENVIRONMENT=test
export DEBUG=true
export SECRET_KEY="test-secret-key-for-testing-only-32chars!"
export DATABASE_URL="${TEST_DATABASE_URL:-postgresql+asyncpg://nexusai:nexusai@localhost:5432/nexusai_test}"
export REDIS_URL="${TEST_REDIS_URL:-redis://localhost:6379/1}"

echo -e "${YELLOW}Environment:${NC}"
echo "  DATABASE_URL: $DATABASE_URL"
echo "  REDIS_URL: $REDIS_URL"
echo ""

# Build pytest command
PYTEST_CMD="python -m pytest"

if [ "$RUN_COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=term-missing --cov-report=html:coverage_report"
fi

PYTEST_CMD="$PYTEST_CMD $VERBOSE $MARKERS $TEST_PATH"

# Add standard pytest options
PYTEST_CMD="$PYTEST_CMD --tb=short -x --strict-markers"

echo -e "${GREEN}Running tests...${NC}"
echo -e "${BLUE}Command: $PYTEST_CMD${NC}"
echo ""

# Run tests
$PYTEST_CMD

EXIT_CODE=$?

# Print summary
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  All tests passed! ✓${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  Some tests failed ✗${NC}"
    echo -e "${RED}========================================${NC}"
fi

if [ "$RUN_COVERAGE" = true ] && [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${BLUE}Coverage report generated at: coverage_report/index.html${NC}"
fi

exit $EXIT_CODE
