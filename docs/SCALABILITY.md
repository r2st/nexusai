# NexusAI Scalability Guide

This document describes the scalability features implemented in NexusAI to support thousands of concurrent clients.

## Architecture Overview

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │     (Nginx)     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Backend #1    │ │   Backend #2    │ │   Backend #3    │
│   (FastAPI)     │ │   (FastAPI)     │ │   (FastAPI)     │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
         ┌──────────▼──────┐ ┌────────▼────────┐
         │   PgBouncer     │ │      Redis      │
         │ (Connection     │ │   (Caching &    │
         │   Pooler)       │ │     Tasks)      │
         └────────┬────────┘ └─────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌────────────┐
│Primary │  │Replica │  │ ClickHouse │
│  DB    │  │  DB    │  │ (Analytics)│
└────────┘  └────────┘  └────────────┘
```

## Scalability Features

### 1. Database Layer

#### Connection Pooling
- **PgBouncer** for connection pooling in production
- SQLAlchemy async connection pool with configurable sizes
- Support for `NullPool` when using external poolers

```python
# config.py settings
DATABASE_POOL_SIZE=20        # Base pool size
DATABASE_MAX_OVERFLOW=30     # Additional connections under load
DATABASE_USE_NULL_POOL=false # Set true for PgBouncer
```

#### Read Replicas
- Separate read-only session factory for queries
- Automatic routing to replica for read operations
- Falls back to primary if replica not configured

```python
# Enable read replica
DATABASE_READ_REPLICA_URL=postgresql+asyncpg://user:pass@replica:5432/nexusai
```

### 2. Caching Layer (Redis)

#### Multi-Level Caching
```python
from app.core.cache import cache, cached, CacheConfig

# Function-level caching
@cached("metrics:dora", ttl=300)
async def get_dora_metrics(project_id: str):
    ...

# Manual caching
await cache.set("key", value, ttl=3600)
value = await cache.get("key")
```

#### Cache TTL Configuration
- `SHORT_TTL`: 60 seconds (frequently changing data)
- `MEDIUM_TTL`: 300 seconds (5 min, default)
- `LONG_TTL`: 3600 seconds (1 hour)
- `VERY_LONG_TTL`: 86400 seconds (24 hours)

### 3. Rate Limiting

#### Token Bucket Algorithm
```python
from app.core.cache import RateLimiter

# Pre-configured limiters
api_rate_limiter = RateLimiter(
    key_prefix="api",
    max_requests=60,      # requests
    window_seconds=60,    # per minute
)

# Usage
allowed, info = await api_rate_limiter.is_allowed(client_id)
```

#### Middleware-Based Limiting
- Automatic rate limiting on all API endpoints
- Configurable per-endpoint limits
- Rate limit headers in responses

### 4. Background Task Processing (ARQ)

#### Task Queue Architecture
```python
from app.core.tasks import task_queue, background_task

# Define background task
@background_task(queue="high", timeout=120)
async def process_document_task(ctx, document_id, tenant_id):
    ...

# Enqueue task
await task_queue.enqueue("process_document_task", doc_id, tenant_id)
```

#### Queue Priorities
- `HIGH_PRIORITY_QUEUE`: Immediate processing
- `DEFAULT_QUEUE`: Standard processing
- `LOW_PRIORITY_QUEUE`: Background processing
- `SCHEDULED_QUEUE`: Scheduled tasks

#### Running Workers
```bash
# Start ARQ worker
arq app.core.tasks.WorkerSettings

# Scale workers
docker-compose up -d --scale worker=4
```

### 5. Circuit Breakers

#### External Service Protection
```python
from app.core.middleware import get_circuit_breaker

cb = get_circuit_breaker("devlake")
result = await cb.call(devlake_client.get_metrics)
```

#### Pre-configured Breakers
- `devlake`: DevLake API
- `openbao`: Secret management
- `openfga`: Authorization
- `clickhouse`: Analytics
- `openai`: OpenAI API
- `anthropic`: Anthropic API

### 6. Horizontal Scaling

#### Docker Compose Scaling
```bash
# Scale backend instances
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=5

# Scale workers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale worker=3
```

#### Nginx Load Balancing
- Least connections algorithm
- Health check-based routing
- Automatic failover
- Connection keepalive

### 7. Database Migrations (Alembic)

#### Running Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Production Deployment

### Prerequisites
1. PostgreSQL 16+ with pgvector
2. Redis 7+
3. PgBouncer (recommended)
4. Nginx for load balancing

### Deployment Steps

1. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with production values
```

2. **Start Infrastructure**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres redis pgbouncer
```

3. **Run Migrations**
```bash
docker-compose exec backend alembic upgrade head
```

4. **Start Services**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=3 --scale worker=2
```

5. **Verify Health**
```bash
curl http://localhost/health
```

## Performance Tuning

### PostgreSQL Configuration
See `docker/postgres/postgresql.conf` for optimized settings:
- `shared_buffers`: 25% of RAM
- `effective_cache_size`: 75% of RAM
- `work_mem`: 64MB for complex queries
- `max_connections`: 200 (PgBouncer handles pooling)

### Redis Configuration
- `maxmemory`: Set based on available RAM
- `maxmemory-policy`: `allkeys-lru` for cache eviction
- Enable AOF persistence for durability

### Application Tuning
- `WORKERS`: Number of uvicorn workers (2 x CPU cores)
- `DATABASE_POOL_SIZE`: 20-50 per backend instance
- `RATE_LIMIT_PER_MINUTE`: Adjust based on expected traffic

## Monitoring

### Health Endpoints
- `/health`: Application health
- `/api/v1/health`: Detailed health with dependencies

### Metrics
- Prometheus metrics at `:9090`
- Jaeger tracing at `:16686`
- Grafana dashboards at `:3002`

### Key Metrics to Monitor
- Request latency (p50, p95, p99)
- Database connection pool utilization
- Redis memory usage
- Background task queue depth
- Circuit breaker states

## Capacity Planning

### Estimated Capacity (per backend instance)
- **Concurrent Users**: 200-500
- **Requests/Second**: 100-300
- **WebSocket Connections**: 1000-2000

### Scaling Guidelines
| Concurrent Users | Backend Instances | Workers | DB Connections |
|------------------|-------------------|---------|----------------|
| < 500            | 2                 | 2       | 50             |
| 500-2000         | 4                 | 4       | 100            |
| 2000-5000        | 8                 | 8       | 200            |
| 5000+            | 12+               | 12+     | 300+           |

## Troubleshooting

### High Latency
1. Check database query performance
2. Verify cache hit rates
3. Monitor circuit breaker states
4. Check background task queue depth

### Connection Errors
1. Increase pool size
2. Check PgBouncer settings
3. Verify network connectivity
4. Monitor connection exhaustion

### Memory Issues
1. Check Redis memory usage
2. Review cache TTLs
3. Monitor Python memory
4. Check for memory leaks in long-running tasks
