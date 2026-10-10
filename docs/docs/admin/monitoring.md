---
sidebar_position: 4
---

# Monitoring Operations

If you enable the monitoring stack:

- Prometheus runs at `prometheus.<DOMAIN>` (behind Traefik, if configured)
- Grafana runs at `grafana.<DOMAIN>`
- Loki stores aggregated logs

Compose definition: `docker/compose/services/docker-compose.monitoring.yml`.

