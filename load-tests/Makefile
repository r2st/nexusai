# ═══════════════════════════════════════════════════════════════
#  NexusAI Load Testing - Makefile
# ═══════════════════════════════════════════════════════════════

.PHONY: help install infra-up infra-down smoke load stress spike endurance breakpoint \
        locust-ui k6-smoke k6-spike k6-ws clean report

TARGET_URL ?= http://localhost:8000
RESULTS_DIR ?= results

help: ## Show this help
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  NexusAI Load Testing Commands"
	@echo "═══════════════════════════════════════════════════════════"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ──────────────────────────────────────────────────────

install: ## Install Python dependencies
	pip install -r requirements.txt

infra-up: ## Start infrastructure (PostgreSQL + Redis + App)
	docker compose up -d postgres redis app
	@echo "Waiting for services..."
	@sleep 10
	@curl -sf $(TARGET_URL)/health > /dev/null && echo "✅ App is ready" || echo "⏳ App still starting..."

infra-down: ## Stop all infrastructure
	docker compose down -v

# ─── Quick Tests ────────────────────────────────────────────────

smoke: ## Smoke test (10 users, 1 min)
	./scripts/run_tests.sh --profile smoke --target $(TARGET_URL)

load: ## Load test (1,000 users, 5 min)
	./scripts/run_tests.sh --profile load --target $(TARGET_URL)

stress: ## Stress test (5,000 users, 10 min)
	./scripts/run_tests.sh --profile stress --target $(TARGET_URL)

spike: ## Spike test (0 → 10,000 users, 5 min)
	./scripts/run_tests.sh --profile spike --target $(TARGET_URL)

endurance: ## Endurance test (2,000 users, 30 min)
	./scripts/run_tests.sh --profile endurance --target $(TARGET_URL)

breakpoint: ## Breakpoint test (ramp to 15,000 users)
	./scripts/run_tests.sh --profile breakpoint --target $(TARGET_URL)

# ─── Tool-Specific Tests ───────────────────────────────────────

locust-ui: ## Start Locust with web UI (http://localhost:8089)
	locust -f locust/locustfile.py --host=$(TARGET_URL)

locust-smoke: ## Locust smoke test only
	./scripts/run_tests.sh --profile smoke --tool locust --target $(TARGET_URL)

k6-smoke: ## k6 smoke test only
	k6 run --env TARGET_URL=$(TARGET_URL) --env PROFILE=smoke k6/load_test.js

k6-spike: ## k6 spike test (10K users)
	k6 run --env TARGET_URL=$(TARGET_URL) --env PROFILE=spike k6/load_test.js

k6-ws: ## k6 WebSocket test
	k6 run --env TARGET_URL=$(TARGET_URL) --env PROFILE=smoke k6/websocket_test.js

# ─── Docker-based Tests ────────────────────────────────────────

docker-loadtest: ## Run load tests via Docker Compose (includes infra)
	docker compose --profile loadtest up --abort-on-container-exit

# ─── Monitoring ─────────────────────────────────────────────────

monitoring-up: ## Start Prometheus + Grafana dashboards
	docker compose --profile monitoring up -d
	@echo "📊 Grafana:    http://localhost:3001 (admin/loadtest)"
	@echo "📈 Prometheus: http://localhost:9090"

monitoring-down: ## Stop monitoring stack
	docker compose --profile monitoring down

# ─── Reports & Cleanup ─────────────────────────────────────────

report: ## Analyze latest results
	@LATEST=$$(ls -td $(RESULTS_DIR)/*/ 2>/dev/null | head -1); \
	if [ -n "$$LATEST" ]; then \
		python3 scripts/analyze_results.py --results-dir "$$LATEST" --output "$$LATEST/report.html"; \
	else \
		echo "No results found. Run a test first."; \
	fi

clean: ## Clean up test results
	rm -rf $(RESULTS_DIR)/*
	@echo "✅ Results cleaned"

clean-all: clean infra-down ## Full cleanup (results + infrastructure)
	@echo "✅ Full cleanup complete"
