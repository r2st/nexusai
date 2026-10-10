/**
 * NexusAI WebSocket Performance Test
 * ====================================
 * Tests real-time WebSocket chat under concurrent load.
 *
 * Usage:
 *   k6 run --env PROFILE=smoke websocket_test.js
 */

import http from "k6/http";
import ws from "k6/ws";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

// ─── Metrics ───────────────────────────────────────────────────────────────────

const wsConnectDuration = new Trend("ws_connect_duration", true);
const wsMessageLatency = new Trend("ws_message_latency", true);
const wsErrors = new Counter("ws_errors");
const wsMessagesReceived = new Counter("ws_messages_received");
const wsMessagesSent = new Counter("ws_messages_sent");
const wsConnectionErrors = new Rate("ws_connection_error_rate");

// ─── Config ────────────────────────────────────────────────────────────────────

const BASE_URL = __ENV.TARGET_URL || "http://localhost:8000";
const WS_URL = __ENV.WS_URL || BASE_URL.replace("http", "ws");
const API_PREFIX = `${BASE_URL}/api/v1`;
const WS_ENDPOINT = `${WS_URL}/api/v1/ws`;

const PROFILES = {
  smoke: {
    stages: [
      { duration: "15s", target: 5 },
      { duration: "30s", target: 5 },
      { duration: "10s", target: 0 },
    ],
  },
  load: {
    stages: [
      { duration: "1m", target: 100 },
      { duration: "3m", target: 500 },
      { duration: "1m", target: 0 },
    ],
  },
  stress: {
    stages: [
      { duration: "1m", target: 500 },
      { duration: "2m", target: 2000 },
      { duration: "3m", target: 2000 },
      { duration: "1m", target: 0 },
    ],
  },
};

const profile = __ENV.PROFILE || "smoke";

export const options = {
  stages: (PROFILES[profile] || PROFILES.smoke).stages,
  thresholds: {
    ws_connect_duration: ["p(95)<500"],
    ws_message_latency: ["p(95)<300"],
    ws_connection_error_rate: ["rate<0.05"],
  },
};

// ─── Helper ────────────────────────────────────────────────────────────────────

function authenticate() {
  const res = http.post(
    `${API_PREFIX}/auth/login`,
    JSON.stringify({
      email: "user@nexusai.dev",
      password: "user123",
    }),
    { headers: { "Content-Type": "application/json" } }
  );

  if (res.status === 200) {
    try {
      return JSON.parse(res.body).access_token;
    } catch {
      return null;
    }
  }
  return null;
}

// ─── Main Test ─────────────────────────────────────────────────────────────────

export default function () {
  const token = authenticate();
  if (!token) {
    wsConnectionErrors.add(true);
    sleep(1);
    return;
  }

  const wsUrl = `${WS_ENDPOINT}?token=${token}`;
  const connectStart = Date.now();

  const res = ws.connect(wsUrl, {}, function (socket) {
    const connectDuration = Date.now() - connectStart;
    wsConnectDuration.add(connectDuration);

    wsConnectionErrors.add(false);

    socket.on("open", () => {
      // Send a ping to measure latency
      const pingPayload = JSON.stringify({
        type: "ping",
        timestamp: Date.now(),
        vu: __VU,
      });

      socket.send(pingPayload);
      wsMessagesSent.add(1);

      // Simulate a chat message after brief delay
      socket.setTimeout(() => {
        const chatPayload = JSON.stringify({
          type: "chat_message",
          content: "What are the current DORA metrics?",
          conversation_id: null,
          timestamp: Date.now(),
        });
        socket.send(chatPayload);
        wsMessagesSent.add(1);
      }, randomIntBetween(500, 2000));

      // Send periodic heartbeats
      socket.setInterval(() => {
        socket.send(
          JSON.stringify({
            type: "heartbeat",
            timestamp: Date.now(),
          })
        );
        wsMessagesSent.add(1);
      }, 5000);
    });

    socket.on("message", (msg) => {
      wsMessagesReceived.add(1);
      try {
        const data = JSON.parse(msg);
        if (data.timestamp) {
          const latency = Date.now() - data.timestamp;
          wsMessageLatency.add(latency);
        }
      } catch {
        // Non-JSON message, just count it
      }
    });

    socket.on("error", (e) => {
      wsErrors.add(1);
      wsConnectionErrors.add(true);
    });

    socket.on("close", () => {
      // Connection closed normally
    });

    // Keep connection alive for a realistic duration
    socket.setTimeout(() => {
      socket.close();
    }, randomIntBetween(10000, 30000));
  });

  check(res, {
    "WebSocket connection established": (r) => r && r.status === 101,
  });

  sleep(randomIntBetween(1, 5));
}

// ─── Summary ───────────────────────────────────────────────────────────────────

export function handleSummary(data) {
  const connectP95 =
    data.metrics.ws_connect_duration?.values?.["p(95)"] || 0;
  const latencyP95 =
    data.metrics.ws_message_latency?.values?.["p(95)"] || 0;
  const connErrorRate =
    data.metrics.ws_connection_error_rate?.values?.rate || 0;

  const summary = {
    timestamp: new Date().toISOString(),
    test: "websocket_performance",
    profile: profile,
    ws_connect_p95_ms: Math.round(connectP95 * 100) / 100,
    ws_message_latency_p95_ms: Math.round(latencyP95 * 100) / 100,
    ws_connection_error_rate: Math.round(connErrorRate * 10000) / 100,
    sla_compliance: {
      connect_under_500ms: connectP95 < 500,
      latency_under_300ms: latencyP95 < 300,
      error_rate_under_5pct: connErrorRate < 0.05,
    },
  };

  return {
    "results/ws_summary.json": JSON.stringify(summary, null, 2),
    stdout: JSON.stringify(summary, null, 2),
  };
}
