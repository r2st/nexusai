#!/usr/bin/env bash
###############################################################################
# NexusAI Load Test Runner
# ========================
# Orchestrates load tests with multiple profiles and generates reports.
#
# Usage:
#   ./run_tests.sh                        # Run smoke test (default)
#   ./run_tests.sh --profile load         # Run load test (1K users)
#   ./run_tests.sh --profile spike        # Run spike test (10K users)
#   ./run_tests.sh --profile breakpoint   # Find breaking point (15K users)
#   ./run_tests.sh --tool locust          # Use Locust only
#   ./run_tests.sh --tool k6              # Use k6 only
#   ./run_tests.sh --tool both            # Run both (default)
###############################################################################

set -euo pipefail

# ─── Colors & Formatting ───────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Configuration ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="${PROJECT_DIR}/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Defaults
PROFILE="smoke"
TOOL="both"
TARGET_URL="${TARGET_URL:-http://localhost:8000}"
SKIP_INFRA=false
GENERATE_REPORT=true

# ─── Argument Parsing ──────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile|-p)   PROFILE="$2"; shift 2 ;;
    --tool|-t)      TOOL="$2"; shift 2 ;;
    --target|-u)    TARGET_URL="$2"; shift 2 ;;
    --skip-infra)   SKIP_INFRA=true; shift ;;
    --no-report)    GENERATE_REPORT=false; shift ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --profile, -p   Test profile: smoke|load|stress|spike|endurance|breakpoint (default: smoke)"
      echo "  --tool, -t      Test tool: locust|k6|both (default: both)"
      echo "  --target, -u    Target URL (default: http://localhost:8000)"
      echo "  --skip-infra    Skip infrastructure setup"
      echo "  --no-report     Skip report generation"
      echo "  --help, -h      Show this help"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Profile-specific settings
declare -A PROFILE_USERS
PROFILE_USERS=(
  [smoke]=10
  [load]=1000
  [stress]=5000
  [spike]=10000
  [endurance]=2000
  [breakpoint]=15000
)

declare -A PROFILE_DURATION
PROFILE_DURATION=(
  [smoke]=60
  [load]=300
  [stress]=600
  [spike]=300
  [endurance]=1800
  [breakpoint]=900
)

declare -A PROFILE_SPAWN_RATE
PROFILE_SPAWN_RATE=(
  [smoke]=2
  [load]=50
  [stress]=100
  [spike]=500
  [endurance]=50
  [breakpoint]=200
)

USERS="${PROFILE_USERS[$PROFILE]:-10}"
DURATION="${PROFILE_DURATION[$PROFILE]:-60}"
SPAWN_RATE="${PROFILE_SPAWN_RATE[$PROFILE]:-2}"

# ─── Utility Functions ─────────────────────────────────────────────────────────

log_header() {
  echo -e "\n${BLUE}${BOLD}══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}${BOLD}  $1${NC}"
  echo -e "${BLUE}${BOLD}══════════════════════════════════════════════════════════════${NC}\n"
}

log_info()    { echo -e "${CYAN}ℹ  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn()    { echo -e "${YELLOW}⚠  $1${NC}"; }
log_error()   { echo -e "${RED}❌ $1${NC}"; }

check_dependency() {
  if ! command -v "$1" &>/dev/null; then
    log_warn "$1 not found. $2"
    return 1
  fi
  return 0
}

wait_for_service() {
  local url="$1"
  local name="$2"
  local max_attempts="${3:-30}"
  local attempt=0

  log_info "Waiting for ${name} at ${url}..."
  while [ $attempt -lt $max_attempts ]; do
    if curl -sf "$url" > /dev/null 2>&1; then
      log_success "${name} is ready"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  log_error "${name} did not become ready in time"
  return 1
}

# ─── Pre-flight Checks ─────────────────────────────────────────────────────────

log_header "NexusAI Load Test Runner"

echo -e "  ${BOLD}Profile:${NC}     ${YELLOW}${PROFILE}${NC}"
echo -e "  ${BOLD}Users:${NC}       ${USERS}"
echo -e "  ${BOLD}Duration:${NC}    ${DURATION}s"
echo -e "  ${BOLD}Spawn Rate:${NC}  ${SPAWN_RATE}/s"
echo -e "  ${BOLD}Target:${NC}      ${TARGET_URL}"
echo -e "  ${BOLD}Tool:${NC}        ${TOOL}"
echo ""

# Create results directory
mkdir -p "${RESULTS_DIR}/${TIMESTAMP}"

# Check target availability
if ! wait_for_service "${TARGET_URL}/health" "NexusAI API" 5; then
  log_warn "Target not reachable. Starting infrastructure..."

  if [ "$SKIP_INFRA" = false ]; then
    cd "$PROJECT_DIR"
    docker compose up -d postgres redis app
    wait_for_service "${TARGET_URL}/health" "NexusAI API" 60
  else
    log_error "Target not reachable and --skip-infra is set. Aborting."
    exit 1
  fi
fi

# ─── Run Locust Tests ──────────────────────────────────────────────────────────

run_locust() {
  if ! check_dependency "locust" "Install: pip install locust"; then
    log_warn "Skipping Locust tests"
    return 1
  fi

  log_header "Running Locust Load Test [${PROFILE}]"

  local results_prefix="${RESULTS_DIR}/${TIMESTAMP}/locust"

  locust \
    -f "${PROJECT_DIR}/locust/locustfile.py" \
    --headless \
    --host="${TARGET_URL}" \
    -u "${USERS}" \
    -r "${SPAWN_RATE}" \
    -t "${DURATION}s" \
    --csv="${results_prefix}" \
    --html="${results_prefix}_report.html" \
    --logfile="${results_prefix}.log" \
    --loglevel=INFO \
    --print-stats \
    --only-summary 2>&1 | tee "${results_prefix}_output.txt"

  local exit_code=$?

  if [ $exit_code -eq 0 ]; then
    log_success "Locust test completed successfully"
  else
    log_error "Locust test failed with exit code ${exit_code}"
  fi

  return $exit_code
}

# ─── Run k6 Tests ──────────────────────────────────────────────────────────────

run_k6() {
  if ! check_dependency "k6" "Install: https://k6.io/docs/getting-started/installation/"; then
    log_warn "Skipping k6 tests"
    return 1
  fi

  log_header "Running k6 Performance Test [${PROFILE}]"

  local results_file="${RESULTS_DIR}/${TIMESTAMP}/k6_results.json"
  local summary_file="${RESULTS_DIR}/${TIMESTAMP}/k6_summary.json"

  K6_BROWSER_ENABLED=false k6 run \
    --env "TARGET_URL=${TARGET_URL}" \
    --env "PROFILE=${PROFILE}" \
    --out "json=${results_file}" \
    --summary-trend-stats="avg,min,med,max,p(50),p(90),p(95),p(99),count" \
    "${PROJECT_DIR}/k6/load_test.js" 2>&1 | tee "${RESULTS_DIR}/${TIMESTAMP}/k6_output.txt"

  local exit_code=$?

  # Move generated summary if it exists
  if [ -f "${PROJECT_DIR}/k6/results/k6_summary.json" ]; then
    mv "${PROJECT_DIR}/k6/results/k6_summary.json" "$summary_file" 2>/dev/null || true
  fi

  if [ $exit_code -eq 0 ]; then
    log_success "k6 test completed successfully"
  else
    log_error "k6 test failed with exit code ${exit_code}"
  fi

  return $exit_code
}

# ─── Run WebSocket Tests ───────────────────────────────────────────────────────

run_k6_websocket() {
  if ! check_dependency "k6" ""; then
    return 1
  fi

  log_header "Running k6 WebSocket Test [${PROFILE}]"

  k6 run \
    --env "TARGET_URL=${TARGET_URL}" \
    --env "PROFILE=${PROFILE}" \
    "${PROJECT_DIR}/k6/websocket_test.js" 2>&1 | tee "${RESULTS_DIR}/${TIMESTAMP}/k6_ws_output.txt"
}

# ─── Execute Tests ─────────────────────────────────────────────────────────────

LOCUST_RESULT=0
K6_RESULT=0

case "$TOOL" in
  locust)
    run_locust || LOCUST_RESULT=$?
    ;;
  k6)
    run_k6 || K6_RESULT=$?
    run_k6_websocket || true
    ;;
  both)
    run_locust || LOCUST_RESULT=$?
    run_k6 || K6_RESULT=$?
    run_k6_websocket || true
    ;;
  *)
    log_error "Unknown tool: ${TOOL}"
    exit 1
    ;;
esac

# ─── Generate Report ───────────────────────────────────────────────────────────

if [ "$GENERATE_REPORT" = true ]; then
  log_header "Generating Test Report"

  if check_dependency "python3" ""; then
    python3 "${SCRIPT_DIR}/analyze_results.py" \
      --results-dir "${RESULTS_DIR}/${TIMESTAMP}" \
      --profile "${PROFILE}" \
      --users "${USERS}" \
      --duration "${DURATION}" \
      --output "${RESULTS_DIR}/${TIMESTAMP}/report.html" 2>/dev/null || {
      log_warn "Report generation failed (non-critical)"
    }
  fi
fi

# ─── Final Summary ─────────────────────────────────────────────────────────────

log_header "Test Execution Complete"

echo -e "  ${BOLD}Results Directory:${NC}  ${RESULTS_DIR}/${TIMESTAMP}/"
echo ""

if [ -d "${RESULTS_DIR}/${TIMESTAMP}" ]; then
  echo -e "  ${BOLD}Generated Files:${NC}"
  ls -la "${RESULTS_DIR}/${TIMESTAMP}/" 2>/dev/null | tail -n +2 | while read -r line; do
    echo "    $line"
  done
fi

echo ""

OVERALL_EXIT=0
if [ $LOCUST_RESULT -ne 0 ] || [ $K6_RESULT -ne 0 ]; then
  log_error "SLA VIOLATION DETECTED - One or more tests failed"
  OVERALL_EXIT=1
else
  log_success "ALL TESTS PASSED - SLA targets met"
fi

exit $OVERALL_EXIT
