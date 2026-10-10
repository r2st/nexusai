/**
 * NexusAI k6 Performance Test Suite
 * ==================================
 * Validates P95 < 200ms response times under 10,000+ concurrent users.
 *
 * Usage:
 *   # Smoke test
 *   k6 run --env PROFILE=smoke load_test.js
 *
 *   # Full load test (10K users)
 *   k6 run --env PROFILE=spike load_test.js
 *
 *   # With HTML report
 *   k6 run --out json=results.json load_test.js
 */

import http from "k6/http";
import ws from "k6/ws";
import { check, sleep, group, fail } from "k6";
import { Counter, Rate, Trend, Gauge } from "k6/metrics";
import { SharedArray } from "k6/data";
// Inline utility functions (avoids remote import issues)
function randomItem(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function randomIntBetween(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

// ─── Custom Metrics ────────────────────────────────────────────────────────────

const slaP95 = new Trend("sla_p95_response_time", true);
const loginDuration = new Trend("login_duration", true);
const chatDuration = new Trend("chat_message_duration", true);
const metricsDuration = new Trend("metrics_fetch_duration", true);
const searchDuration = new Trend("document_search_duration", true);
const errorRate = new Rate("error_rate");
const slaViolations = new Counter("sla_violations");
const requestsPerEndpoint = new Counter("requests_per_endpoint");
const activeUsers = new Gauge("active_users");

// ─── Configuration ─────────────────────────────────────────────────────────────

const BASE_URL = __ENV.TARGET_URL || "http://localhost:8000";
const API_PREFIX = `${BASE_URL}/api/v1`;

const PROFILES = {
  smoke: {
    stages: [
      { duration: "30s", target: 10 },
      { duration: "30s", target: 10 },
      { duration: "10s", target: 0 },
    ],
  },
  load: {
    stages: [
      { duration: "2m", target: 500 },
      { duration: "3m", target: 1000 },
      { duration: "2m", target: 1000 },
      { duration: "1m", target: 0 },
    ],
  },
  stress: {
    stages: [
      { duration: "2m", target: 1000 },
      { duration: "3m", target: 3000 },
      { duration: "3m", target: 5000 },
      { duration: "2m", target: 5000 },
      { duration: "2m", target: 0 },
    ],
  },
  spike: {
    stages: [
      { duration: "1m", target: 100 },
      { duration: "30s", target: 10000 },
      { duration: "3m", target: 10000 },
      { duration: "1m", target: 100 },
      { duration: "30s", target: 0 },
    ],
  },
  endurance: {
    stages: [
      { duration: "2m", target: 2000 },
      { duration: "26m", target: 2000 },
      { duration: "2m", target: 0 },
    ],
  },
  breakpoint: {
    stages: [
      { duration: "1m", target: 1000 },
      { duration: "1m", target: 3000 },
      { duration: "1m", target: 5000 },
      { duration: "1m", target: 7500 },
      { duration: "1m", target: 10000 },
      { duration: "1m", target: 12000 },
      { duration: "1m", target: 15000 },
      { duration: "3m", target: 15000 },
      { duration: "1m", target: 0 },
    ],
  },
};

const profile = __ENV.PROFILE || "smoke";
const selectedProfile = PROFILES[profile] || PROFILES.smoke;

// ─── k6 Options ────────────────────────────────────────────────────────────────

export const options = {
  stages: selectedProfile.stages,

  thresholds: {
    // PRIMARY SLA: P95 response time under 200ms
    http_req_duration: [
      { threshold: "p(50)<100", abortOnFail: false },
      { threshold: "p(95)<200", abortOnFail: true },
      { threshold: "p(99)<500", abortOnFail: false },
      { threshold: "max<2000", abortOnFail: false },
    ],

    // Error rate under 1%
    error_rate: [{ threshold: "rate<0.01", abortOnFail: true }],

    // Endpoint-specific thresholds
    login_duration: ["p(95)<300"],
    chat_message_duration: ["p(95)<500"],
    metrics_fetch_duration: ["p(95)<200"],
    document_search_duration: ["p(95)<300"],

    // HTTP-level checks
    http_req_failed: ["rate<0.01"],
    http_reqs: [`rate>${profile === "smoke" ? 10 : 500}`],
  },

  // Connection tuning for high concurrency
  batch: 20,
  batchPerHost: 10,
  dns: { ttl: "1m", select: "roundRobin", policy: "preferIPv4" },
  noConnectionReuse: false,
  userAgent: "NexusAI-LoadTest/1.0",

  // Tags for analysis
  tags: { testProfile: profile },

  // Summary export
  summaryTrendStats: [
    "avg",
    "min",
    "med",
    "max",
    "p(50)",
    "p(90)",
    "p(95)",
    "p(99)",
    "count",
  ],
};

// ─── Test Data ─────────────────────────────────────────────────────────────────

const searchQueries = [
  "deployment pipeline configuration",
  "API authentication flow",
  "database migration steps",
  "monitoring and alerting",
  "CI/CD best practices",
  "security compliance",
  "performance optimization",
  "microservices architecture",
  "incident response procedures",
  "cost optimization strategies",
];

const chatMessages = [
  "What are the deployment metrics for this week?",
  "Show me the error rate trends",
  "Analyze the code review throughput",
  "What's the lead time for changes?",
  "Summarize the DORA metrics",
  "Help me understand CI/CD performance",
  "What security vulnerabilities were found?",
  "Generate a sprint retrospective summary",
];

const projectNames = ["nexusai", "frontend", "backend", "infra", "platform"];

const credentials = {
  admin: { email: "admin@nexusai.dev", password: "admin123" },
  user: { email: "user@nexusai.dev", password: "user123" },
  viewer: { email: "viewer@nexusai.dev", password: "viewer123" },
};

// ─── Helper Functions ──────────────────────────────────────────────────────────

function getAuthHeaders(token) {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  };
}

function login(email, password) {
  const res = http.post(
    `${API_PREFIX}/auth/login`,
    JSON.stringify({ email, password }),
    { headers: { "Content-Type": "application/json" }, tags: { endpoint: "auth_login" } }
  );

  loginDuration.add(res.timings.duration);
  slaP95.add(res.timings.duration);

  const success = check(res, {
    "login: status 200": (r) => r.status === 200,
    "login: has access_token": (r) => {
      try {
        return JSON.parse(r.body).access_token !== undefined;
      } catch {
        return false;
      }
    },
    "login: response time < 300ms": (r) => r.timings.duration < 300,
  });

  errorRate.add(!success);
  if (!success) slaViolations.add(1);

  if (res.status === 200) {
    try {
      return JSON.parse(res.body);
    } catch {
      return null;
    }
  }
  return null;
}

function trackResponse(res, endpointName, slaMs = 200) {
  slaP95.add(res.timings.duration);

  const success = check(res, {
    [`${endpointName}: status OK`]: (r) => r.status >= 200 && r.status < 400,
    [`${endpointName}: P95 < ${slaMs}ms`]: (r) => r.timings.duration < slaMs,
  });

  errorRate.add(!success);
  if (res.timings.duration > slaMs) slaViolations.add(1);
  requestsPerEndpoint.add(1, { endpoint: endpointName });

  return success;
}

// ─── Main Test Scenario ────────────────────────────────────────────────────────

export default function () {
  // Select user type weighted: 60% regular, 25% active, 15% admin
  const roll = Math.random();
  let creds;
  if (roll < 0.6) {
    creds = credentials.user;
  } else if (roll < 0.85) {
    creds = credentials.user;
  } else {
    creds = credentials.admin;
  }

  activeUsers.add(1);

  // ── Phase 1: Authentication ──────────────────────────────────────────────
  const authData = login(creds.email, creds.password);
  if (!authData) {
    errorRate.add(true);
    sleep(1);
    return;
  }

  const token = authData.access_token;
  const params = getAuthHeaders(token);

  // ── Phase 2: Read Operations (majority of traffic) ───────────────────────

  group("Health Check", () => {
    const res = http.get(`${BASE_URL}/health`, {
      tags: { endpoint: "health" },
    });
    trackResponse(res, "health", 100);
  });

  sleep(randomIntBetween(1, 3) * 0.1);

  group("List Conversations", () => {
    const res = http.get(
      `${API_PREFIX}/chat/conversations?limit=20&offset=0`,
      Object.assign({}, params, { tags: { endpoint: "list_conversations" } })
    );
    trackResponse(res, "list_conversations", 200);
  });

  sleep(randomIntBetween(1, 3) * 0.1);

  group("List Documents", () => {
    const res = http.get(
      `${API_PREFIX}/documents?limit=20`,
      Object.assign({}, params, { tags: { endpoint: "list_documents" } })
    );
    trackResponse(res, "list_documents", 200);
  });

  sleep(randomIntBetween(1, 3) * 0.1);

  group("DORA Metrics", () => {
    const project = randomItem(projectNames);
    const res = http.get(
      `${API_PREFIX}/metrics/dora/${project}?period=30d`,
      Object.assign({}, params, { tags: { endpoint: "dora_metrics" } })
    );
    metricsDuration.add(res.timings.duration);
    trackResponse(res, "dora_metrics", 200);
  });

  sleep(randomIntBetween(1, 3) * 0.1);

  group("SPACE Metrics", () => {
    const project = randomItem(projectNames);
    const res = http.get(
      `${API_PREFIX}/metrics/space/${project}?period=30d`,
      Object.assign({}, params, { tags: { endpoint: "space_metrics" } })
    );
    metricsDuration.add(res.timings.duration);
    trackResponse(res, "space_metrics", 200);
  });

  sleep(randomIntBetween(1, 3) * 0.1);

  group("List Organizations", () => {
    const res = http.get(
      `${API_PREFIX}/organizations`,
      Object.assign({}, params, { tags: { endpoint: "list_organizations" } })
    );
    trackResponse(res, "list_organizations", 200);
  });

  sleep(randomIntBetween(1, 3) * 0.1);

  // ── Phase 3: Search Operations ───────────────────────────────────────────

  group("Document Search", () => {
    const query = randomItem(searchQueries);
    const res = http.post(
      `${API_PREFIX}/documents/search`,
      JSON.stringify({ query, limit: 10 }),
      Object.assign({}, params, { tags: { endpoint: "document_search" } })
    );
    searchDuration.add(res.timings.duration);
    trackResponse(res, "document_search", 300);
  });

  sleep(randomIntBetween(1, 3) * 0.1);

  // ── Phase 4: Write Operations (conditional) ──────────────────────────────

  // Only 30% of users create conversations per iteration
  if (Math.random() < 0.3) {
    group("Create Conversation", () => {
      const res = http.post(
        `${API_PREFIX}/chat/conversations`,
        JSON.stringify({
          title: `k6-test-${Date.now()}-${__VU}`,
          model_provider: "openai",
          model_name: "gpt-4",
        }),
        Object.assign({}, params, { tags: { endpoint: "create_conversation" } })
      );
      trackResponse(res, "create_conversation", 300);
    });
  }

  sleep(randomIntBetween(1, 3) * 0.1);

  // ── Phase 5: Token Refresh ───────────────────────────────────────────────

  if (authData.refresh_token && Math.random() < 0.2) {
    group("Token Refresh", () => {
      const res = http.post(
        `${API_PREFIX}/auth/refresh`,
        JSON.stringify({ refresh_token: authData.refresh_token }),
        Object.assign({}, params, { tags: { endpoint: "token_refresh" } })
      );
      trackResponse(res, "token_refresh", 200);
    });
  }

  sleep(randomIntBetween(5, 15) * 0.1);
}

// ─── Setup & Teardown ──────────────────────────────────────────────────────────

export function setup() {
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║          NexusAI k6 Performance Test Suite                  ║
║  Profile: ${profile.padEnd(48)}║
║  Target:  ${BASE_URL.padEnd(48)}║
║  SLA:     P95 < 200ms | Error Rate < 1%                    ║
╚══════════════════════════════════════════════════════════════╝
  `);

  // Verify target is reachable
  const healthRes = http.get(`${BASE_URL}/health`);
  if (healthRes.status !== 200) {
    console.warn(`WARNING: Health check returned ${healthRes.status}`);
  }

  // Verify auth works
  const authData = login(credentials.user.email, credentials.user.password);
  if (!authData) {
    console.error("FATAL: Cannot authenticate. Aborting test.");
    fail("Authentication setup failed");
  }

  return { setupToken: authData.access_token };
}

export function teardown(data) {
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║          Test Complete - Check thresholds above              ║
║  SLA Target: P95 < 200ms for 10,000+ concurrent users      ║
╚══════════════════════════════════════════════════════════════╝
  `);
}

// ─── Custom Summary Handler ────────────────────────────────────────────────────

export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration?.values?.["p(95)"] || 0;
  const p99 = data.metrics.http_req_duration?.values?.["p(99)"] || 0;
  const p50 = data.metrics.http_req_duration?.values?.["p(50)"] || 0;
  const avg = data.metrics.http_req_duration?.values?.avg || 0;
  const maxVUs = data.metrics.vus_max?.values?.value || 0;
  const totalReqs = data.metrics.http_reqs?.values?.count || 0;
  const errRate = data.metrics.error_rate?.values?.rate || 0;
  const failedRate = data.metrics.http_req_failed?.values?.rate || 0;

  const slaResult = {
    timestamp: new Date().toISOString(),
    profile: profile,
    target_url: BASE_URL,
    max_vus: maxVUs,
    total_requests: totalReqs,
    response_times: {
      p50_ms: Math.round(p50 * 100) / 100,
      p95_ms: Math.round(p95 * 100) / 100,
      p99_ms: Math.round(p99 * 100) / 100,
      avg_ms: Math.round(avg * 100) / 100,
    },
    error_rate: Math.round(errRate * 10000) / 100,
    http_failure_rate: Math.round(failedRate * 10000) / 100,
    sla_compliance: {
      p95_under_200ms: p95 < 200,
      error_rate_under_1pct: errRate < 0.01,
      overall_pass: p95 < 200 && errRate < 0.01,
    },
    thresholds: data.thresholds || {},
  };

  const summaryText = `
═══════════════════════════════════════════════════════════════
               NexusAI PERFORMANCE TEST RESULTS
═══════════════════════════════════════════════════════════════
  Profile:          ${profile}
  Max VUs:          ${maxVUs.toLocaleString()}
  Total Requests:   ${totalReqs.toLocaleString()}
───────────────────────────────────────────────────────────────
  RESPONSE TIMES
  P50 (Median):     ${p50.toFixed(1)}ms    (SLA: <100ms)
  P95:              ${p95.toFixed(1)}ms    (SLA: <200ms)  ← KEY
  P99:              ${p99.toFixed(1)}ms    (SLA: <500ms)
  Average:          ${avg.toFixed(1)}ms
───────────────────────────────────────────────────────────────
  ERROR RATES
  Custom Error:     ${(errRate * 100).toFixed(2)}%   (SLA: <1%)
  HTTP Failures:    ${(failedRate * 100).toFixed(2)}%
───────────────────────────────────────────────────────────────
  SLA COMPLIANCE
  P95 < 200ms:      ${p95 < 200 ? "✅ PASS" : "❌ FAIL"}
  Error Rate < 1%:  ${errRate < 0.01 ? "✅ PASS" : "❌ FAIL"}
  OVERALL:          ${p95 < 200 && errRate < 0.01 ? "✅ ALL SLA TARGETS MET" : "❌ SLA VIOLATED"}
═══════════════════════════════════════════════════════════════
`;

  console.log(summaryText);

  return {
    "results/k6_summary.json": JSON.stringify(slaResult, null, 2),
    stdout: summaryText,
  };
}
