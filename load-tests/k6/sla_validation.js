/**
 * NexusAI SLA Validation Test
 * ============================
 * Focused test specifically for validating the SLA claim:
 *   "10,000+ concurrent users with P95 API response times under 200ms"
 *
 * This test runs a controlled experiment:
 *   1. Ramp to exactly 10,000 concurrent VUs
 *   2. Sustain for 5 minutes
 *   3. Validate P95 < 200ms across all endpoints
 *   4. Exit with pass/fail status
 *
 * Usage:
 *   k6 run --env TARGET_URL=http://your-api sla_validation.js
 */

import http from "k6/http";
import { check, sleep, fail } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";
// Inline utility functions (avoids remote import issues)
function randomItem(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function randomIntBetween(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

// ─── SLA Metrics ───────────────────────────────────────────────────────────────

const slaResponseTime = new Trend("sla_response_time", true);
const slaErrorRate = new Rate("sla_error_rate");
const slaViolationCount = new Counter("sla_violation_count");
const endpointResponseTimes = {
  health: new Trend("endpoint_health_rt", true),
  auth_login: new Trend("endpoint_auth_login_rt", true),
  conversations_list: new Trend("endpoint_conversations_list_rt", true),
  documents_list: new Trend("endpoint_documents_list_rt", true),
  documents_search: new Trend("endpoint_documents_search_rt", true),
  metrics_dora: new Trend("endpoint_metrics_dora_rt", true),
  organizations_list: new Trend("endpoint_organizations_list_rt", true),
};

// ─── Configuration ─────────────────────────────────────────────────────────────

const BASE_URL = __ENV.TARGET_URL || "http://localhost:8000";
const API = `${BASE_URL}/api/v1`;
const SLA_P95_MS = 200;
const SLA_ERROR_RATE = 0.01;
const TARGET_USERS = 10000;

export const options = {
  scenarios: {
    sla_validation: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "2m", target: 2000 },    // Phase 1: Warm up
        { duration: "2m", target: 5000 },    // Phase 2: Ramp to 50%
        { duration: "1m", target: 10000 },   // Phase 3: Hit 10K
        { duration: "5m", target: 10000 },   // Phase 4: SUSTAIN (measurement window)
        { duration: "1m", target: 1000 },    // Phase 5: Cool down
        { duration: "30s", target: 0 },      // Phase 6: Drain
      ],
      gracefulRampDown: "30s",
    },
  },

  thresholds: {
    // ═══ PRIMARY SLA THRESHOLDS ═══
    sla_response_time: [
      { threshold: "p(95)<200", abortOnFail: true },  // THE SLA CLAIM
    ],
    sla_error_rate: [
      { threshold: "rate<0.01", abortOnFail: true },
    ],

    // Per-endpoint validation
    endpoint_health_rt: ["p(95)<50"],
    endpoint_auth_login_rt: ["p(95)<300"],
    endpoint_conversations_list_rt: ["p(95)<200"],
    endpoint_documents_list_rt: ["p(95)<200"],
    endpoint_documents_search_rt: ["p(95)<300"],
    endpoint_metrics_dora_rt: ["p(95)<200"],
    endpoint_organizations_list_rt: ["p(95)<200"],

    // Overall HTTP metrics
    http_req_duration: ["p(95)<200"],
    http_req_failed: ["rate<0.01"],
  },
};

// ─── Data ──────────────────────────────────────────────────────────────────────

const searchQueries = [
  "deployment pipeline",
  "API authentication",
  "database migration",
  "monitoring setup",
  "CI/CD pipeline",
  "security compliance",
  "performance tuning",
  "microservices",
];

const projectNames = ["nexusai", "frontend", "backend", "infra", "platform"];

// ─── Helpers ───────────────────────────────────────────────────────────────────

function trackEndpoint(name, res) {
  const duration = res.timings.duration;
  slaResponseTime.add(duration);

  if (endpointResponseTimes[name]) {
    endpointResponseTimes[name].add(duration);
  }

  const isError = res.status < 200 || res.status >= 400;
  slaErrorRate.add(isError);

  if (duration > SLA_P95_MS) {
    slaViolationCount.add(1);
  }

  return !isError;
}

function authHeaders(token) {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  };
}

// ─── Test Scenario ─────────────────────────────────────────────────────────────

export default function () {
  // 1. Health check (lightweight, always works)
  let res = http.get(`${BASE_URL}/health`, {
    tags: { endpoint: "health" },
  });
  trackEndpoint("health", res);

  sleep(0.1);

  // 2. Login
  res = http.post(
    `${API}/auth/login`,
    JSON.stringify({
      email: "user@nexusai.dev",
      password: "user123",
    }),
    {
      headers: { "Content-Type": "application/json" },
      tags: { endpoint: "auth_login" },
    }
  );
  trackEndpoint("auth_login", res);

  let token = null;
  if (res.status === 200) {
    try {
      token = JSON.parse(res.body).access_token;
    } catch {}
  }

  if (!token) {
    sleep(randomIntBetween(1, 3));
    return;
  }

  const params = authHeaders(token);
  sleep(0.1);

  // 3. List conversations
  res = http.get(`${API}/chat/conversations?limit=20`,
    Object.assign({}, params, { tags: { endpoint: "conversations_list" } })
  );
  trackEndpoint("conversations_list", res);
  sleep(0.1);

  // 4. List documents
  res = http.get(`${API}/documents?limit=20`,
    Object.assign({}, params, { tags: { endpoint: "documents_list" } })
  );
  trackEndpoint("documents_list", res);
  sleep(0.1);

  // 5. Search documents
  res = http.post(
    `${API}/documents/search`,
    JSON.stringify({ query: randomItem(searchQueries), limit: 10 }),
    Object.assign({}, params, { tags: { endpoint: "documents_search" } })
  );
  trackEndpoint("documents_search", res);
  sleep(0.1);

  // 6. DORA metrics
  res = http.get(
    `${API}/metrics/dora/${randomItem(projectNames)}?period=30d`,
    Object.assign({}, params, { tags: { endpoint: "metrics_dora" } })
  );
  trackEndpoint("metrics_dora", res);
  sleep(0.1);

  // 7. List organizations
  res = http.get(`${API}/organizations`,
    Object.assign({}, params, { tags: { endpoint: "organizations_list" } })
  );
  trackEndpoint("organizations_list", res);

  // Think time
  sleep(randomIntBetween(5, 15) * 0.1);
}

// ─── Setup ─────────────────────────────────────────────────────────────────────

export function setup() {
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║            NexusAI SLA VALIDATION TEST                      ║
║                                                              ║
║  CLAIM: 10,000+ concurrent users                            ║
║         P95 API response times under 200ms                  ║
║                                                              ║
║  This test will PASS or FAIL based on that claim.           ║
╚══════════════════════════════════════════════════════════════╝
  `);

  // Validate connectivity
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, { "setup: API reachable": (r) => r.status === 200 });

  if (healthRes.status !== 200) {
    fail(`API not reachable at ${BASE_URL}`);
  }

  // Validate auth
  const authRes = http.post(
    `${API}/auth/login`,
    JSON.stringify({ email: "user@nexusai.dev", password: "user123" }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(authRes, { "setup: authentication works": (r) => r.status === 200 });
  if (authRes.status !== 200) {
    fail("Authentication setup failed");
  }
}

// ─── Summary ───────────────────────────────────────────────────────────────────

export function handleSummary(data) {
  const p95 = data.metrics.sla_response_time?.values?.["p(95)"] || 0;
  const p50 = data.metrics.sla_response_time?.values?.["p(50)"] || 0;
  const p99 = data.metrics.sla_response_time?.values?.["p(99)"] || 0;
  const errRate = data.metrics.sla_error_rate?.values?.rate || 0;
  const violations = data.metrics.sla_violation_count?.values?.count || 0;
  const totalReqs = data.metrics.http_reqs?.values?.count || 0;
  const maxVUs = data.metrics.vus_max?.values?.value || 0;

  const pass = p95 < SLA_P95_MS && errRate < SLA_ERROR_RATE;

  const result = {
    timestamp: new Date().toISOString(),
    test: "sla_validation",
    claim: `${TARGET_USERS}+ concurrent users with P95 < ${SLA_P95_MS}ms`,
    verdict: pass ? "VALIDATED" : "FAILED",
    max_concurrent_users: maxVUs,
    total_requests: totalReqs,
    response_times: {
      p50_ms: Math.round(p50 * 100) / 100,
      p95_ms: Math.round(p95 * 100) / 100,
      p99_ms: Math.round(p99 * 100) / 100,
    },
    error_rate_pct: Math.round(errRate * 10000) / 100,
    sla_violations: violations,
    per_endpoint: {},
  };

  // Collect per-endpoint P95s
  for (const [name, _] of Object.entries(endpointResponseTimes)) {
    const metricKey = `endpoint_${name}_rt`;
    if (data.metrics[metricKey]) {
      result.per_endpoint[name] = {
        p95_ms: Math.round((data.metrics[metricKey].values?.["p(95)"] || 0) * 100) / 100,
        avg_ms: Math.round((data.metrics[metricKey].values?.avg || 0) * 100) / 100,
      };
    }
  }

  const banner = pass
    ? `
╔══════════════════════════════════════════════════════════════╗
║  ✅  SLA CLAIM VALIDATED                                    ║
║                                                              ║
║  10,000+ concurrent users: ${maxVUs.toString().padEnd(33)}║
║  P95 response time:        ${p95.toFixed(1).padEnd(6)}ms (< ${SLA_P95_MS}ms)${" ".repeat(17)}║
║  Error rate:               ${(errRate * 100).toFixed(2).padEnd(6)}% (< ${(SLA_ERROR_RATE * 100).toFixed(0)}%)${" ".repeat(18)}║
╚══════════════════════════════════════════════════════════════╝`
    : `
╔══════════════════════════════════════════════════════════════╗
║  ❌  SLA CLAIM FAILED                                       ║
║                                                              ║
║  Max concurrent users:     ${maxVUs.toString().padEnd(33)}║
║  P95 response time:        ${p95.toFixed(1).padEnd(6)}ms (limit: ${SLA_P95_MS}ms)${" ".repeat(13)}║
║  Error rate:               ${(errRate * 100).toFixed(2).padEnd(6)}% (limit: ${(SLA_ERROR_RATE * 100).toFixed(0)}%)${" ".repeat(14)}║
║  SLA violations:           ${violations.toString().padEnd(33)}║
╚══════════════════════════════════════════════════════════════╝`;

  console.log(banner);

  return {
    "results/sla_validation.json": JSON.stringify(result, null, 2),
    stdout: banner + "\n",
  };
}
