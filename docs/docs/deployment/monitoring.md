---
sidebar_position: 4
---

# Monitoring

NexusAI can run an optional monitoring stack (Prometheus + Grafana + Loki).

## Docker Compose

See `docker/compose/services/docker-compose.monitoring.yml`.

## What you get

- Prometheus scrapes exporters (Redis/Postgres/host) and service metrics
- Grafana dashboards for visualization
- Loki + Promtail for container log aggregation

