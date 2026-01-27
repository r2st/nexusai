# NexusAI Helm Chart

A Helm chart for deploying NexusAI - an AI-powered chat and analytics platform - on Kubernetes.

## Prerequisites

- Kubernetes 1.25+
- Helm 3.10+
- PV provisioner support in the underlying infrastructure (for persistence)
- cert-manager (optional, for TLS)
- Prometheus Operator (optional, for ServiceMonitor)

## Installation

### Add Helm Dependencies

```bash
helm dependency update ./helm/nexusai
```

### Install with Default Values

```bash
helm install nexusai ./helm/nexusai -n nexusai --create-namespace
```

### Install for Development

```bash
helm install nexusai ./helm/nexusai -n nexusai-dev --create-namespace \
  -f ./helm/nexusai/values-dev.yaml
```

### Install for Staging

```bash
helm install nexusai ./helm/nexusai -n nexusai-staging --create-namespace \
  -f ./helm/nexusai/values-staging.yaml \
  --set secrets.secretKey="your-secret-key" \
  --set secrets.openaiApiKey="sk-xxx" \
  --set secrets.anthropicApiKey="sk-ant-xxx"
```

### Install for Production

```bash
helm install nexusai ./helm/nexusai -n nexusai-prod --create-namespace \
  -f ./helm/nexusai/values-prod.yaml \
  --set externalDatabase.host="your-db-host" \
  --set externalRedis.host="your-redis-host" \
  --set secrets.secretKey="your-secret-key" \
  --set secrets.databasePassword="your-db-password" \
  --set secrets.redisPassword="your-redis-password" \
  --set secrets.openaiApiKey="sk-xxx" \
  --set secrets.anthropicApiKey="sk-ant-xxx"
```

## Configuration

### Global Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global Docker image registry | `ghcr.io` |
| `global.imagePullSecrets` | Global Docker registry secret names | `[]` |
| `global.storageClass` | Global storage class for PVCs | `""` |

### Backend Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `backend.enabled` | Enable backend deployment | `true` |
| `backend.replicaCount` | Number of backend replicas | `3` |
| `backend.image.repository` | Backend image repository | `your-org/nexusai/backend` |
| `backend.image.tag` | Backend image tag | `latest` |
| `backend.resources.limits.cpu` | CPU limit | `2` |
| `backend.resources.limits.memory` | Memory limit | `2Gi` |
| `backend.autoscaling.enabled` | Enable HPA | `true` |
| `backend.autoscaling.minReplicas` | Minimum replicas | `3` |
| `backend.autoscaling.maxReplicas` | Maximum replicas | `20` |

### Frontend Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.enabled` | Enable frontend deployment | `true` |
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `frontend.image.repository` | Frontend image repository | `your-org/nexusai/frontend` |
| `frontend.image.tag` | Frontend image tag | `latest` |
| `frontend.resources.limits.cpu` | CPU limit | `1` |
| `frontend.resources.limits.memory` | Memory limit | `512Mi` |

### Worker Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `worker.enabled` | Enable worker deployment | `true` |
| `worker.replicaCount` | Number of worker replicas | `2` |
| `worker.command` | Worker command | `["python", "-m", "arq", "..."]` |
| `worker.terminationGracePeriodSeconds` | Graceful shutdown period | `300` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts[0].host` | Hostname | `nexusai.example.com` |
| `ingress.tls` | TLS configuration | `[]` |

### Database Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Deploy embedded PostgreSQL | `true` |
| `postgresql.auth.username` | PostgreSQL username | `nexusai` |
| `postgresql.auth.database` | PostgreSQL database | `nexusai` |
| `externalDatabase.host` | External database host | `""` |
| `externalDatabase.port` | External database port | `5432` |

### Redis Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Deploy embedded Redis | `true` |
| `redis.auth.enabled` | Enable Redis authentication | `true` |
| `externalRedis.host` | External Redis host | `""` |
| `externalRedis.port` | External Redis port | `6379` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.appName` | Application name | `NexusAI` |
| `config.environment` | Environment name | `production` |
| `config.debug` | Enable debug mode | `false` |
| `config.logLevel` | Log level | `info` |
| `config.tenantIsolation` | Enable tenant isolation | `true` |

### Secrets Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.secretKey` | Application secret key | `""` |
| `secrets.openaiApiKey` | OpenAI API key | `""` |
| `secrets.anthropicApiKey` | Anthropic API key | `""` |
| `secrets.databasePassword` | Database password | `""` |
| `secrets.redisPassword` | Redis password | `""` |

### Security Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `networkPolicy.enabled` | Enable network policies | `true` |
| `serviceMonitor.enabled` | Enable ServiceMonitor | `true` |
| `podSecurityContext.runAsNonRoot` | Run as non-root | `true` |
| `securityContext.readOnlyRootFilesystem` | Read-only filesystem | `true` |

## Architecture

```
                    ┌─────────────┐
                    │   Ingress   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Frontend │ │ Backend  │ │  Worker  │
        │   (3)    │ │   (3)    │ │   (2)    │
        └──────────┘ └────┬─────┘ └────┬─────┘
                          │            │
              ┌───────────┴────────────┘
              │
    ┌─────────┼─────────┬─────────────┐
    ▼         ▼         ▼             ▼
┌────────┐ ┌───────┐ ┌────────────┐ ┌─────────────┐
│PostgreSQL│ │ Redis │ │ Meilisearch │ │ External APIs │
└────────┘ └───────┘ └────────────┘ └─────────────┘
```

## Upgrading

```bash
helm upgrade nexusai ./helm/nexusai -n nexusai -f values.yaml
```

## Uninstalling

```bash
helm uninstall nexusai -n nexusai
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n nexusai -l app.kubernetes.io/instance=nexusai
```

### View Logs

```bash
kubectl logs -n nexusai -l app.kubernetes.io/component=backend -f
```

### Check HPA

```bash
kubectl get hpa -n nexusai
```

### Debug Template Rendering

```bash
helm template nexusai ./helm/nexusai -f values.yaml --debug
```

## License

MIT
