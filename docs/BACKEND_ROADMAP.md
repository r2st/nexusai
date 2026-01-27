# Backend Architecture Roadmap

> Tracking implementation of event-driven architecture + query services for software intelligence platform.

**Created**: 2026-01-19
**Last Updated**: 2026-01-19

---

## Implementation Status

### Legend
- ✅ Complete
- 🔄 In Progress
- 📋 Planned
- ⏸️ Blocked

---

## Phase 1: Event-Driven Foundation (High Priority)

### 1.1 Event Ingestion Service
**Status**: ✅ Complete
**Location**: `backend/app/services/events/`
**Priority**: P0 (Critical)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Event Models | ✅ | `models.py` | Raw event schema, envelope |
| Event Store | ✅ | `store.py` | S3-backed immutable store |
| Webhook Receiver | ✅ | `webhooks.py` | Generic webhook endpoint |
| Event Publisher | ✅ | `publisher.py` | NATS JetStream publisher |
| API Endpoints | ✅ | `api/events.py` | Webhook & query endpoints |
| Tests | ✅ | `tests/test_events.py` | Unit tests |
| DB Migration | ✅ | `alembic/versions/20260119_001_events_index.py` | events_index table |

**Acceptance Criteria**:
- [x] Generic webhook receiver for any source
- [x] Store raw events to S3 with tenant isolation
- [x] Publish events to NATS JetStream
- [x] Replay capability from event store
- [x] Schema versioning support

---

### 1.2 Entity Service
**Status**: ✅ Complete
**Location**: `backend/app/services/entities/`
**Priority**: P0 (Critical)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Canonical Models | ✅ | `models.py` | Repo, Commit, PR, Build, Deploy, Incident, Service, Team, Developer, Environment |
| Entity Store | ✅ | `store.py` | PostgreSQL with tenant isolation + relationships |
| Identity Resolver | ✅ | `identity.py` | Cross-source identity mapping with confidence |
| Normalizers | ✅ | `normalizers/` | Source-specific transformers |
| GitHub Normalizer | ✅ | `normalizers/github.py` | GitHub → canonical |
| GitLab Normalizer | ✅ | `normalizers/gitlab.py` | GitLab → canonical |
| Jira Normalizer | ✅ | `normalizers/jira.py` | Jira → canonical (via JiraConnector) |
| DB Migration | ✅ | `alembic/versions/20260119_002_entities.py` | entities, entity_relations, identity_mappings |

**Acceptance Criteria**:
- [x] Canonical entity schema for all domain objects
- [x] Deduplication on ingest (via domain_id)
- [x] Identity resolution across sources
- [x] Tenant-scoped queries (RLS)
- [x] Relationship graph support

---

### 1.3 Message Queue Integration
**Status**: ✅ Complete
**Location**: `backend/app/services/queue/`
**Priority**: P0 (Critical)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Queue Config | ✅ | `config.py` | NATS JetStream settings |
| Queue Client | ✅ | `client.py` | Async NATS client with TLS/auth |
| Streams | ✅ | `streams.py` | Stream management |
| Consumer | ✅ | `consumer.py` | Pull-based consumer with DLQ |
| Worker | ✅ | `worker.py` | Worker pool with signal handling |

**Acceptance Criteria**:
- [x] NATS JetStream connection management
- [x] Durable consumers for reliability
- [x] Message replay from stream
- [x] Dead letter queue for failures
- [x] Graceful shutdown

---

## Phase 2: Connectors (High Priority)

### 2.1 Connector Framework
**Status**: ✅ Complete
**Location**: `backend/app/services/connectors/`
**Priority**: P1 (High)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Base Connector | ✅ | `base.py` | Abstract connector interface |
| Connector Registry | ✅ | `registry.py` | Connector management |
| Connection Config | ✅ | `base.py` | ConnectorConfig model |
| GitHub Connector | ✅ | `github.py` | Webhooks + API polling |
| GitLab Connector | ✅ | `gitlab.py` | Webhooks + API polling |
| Jira Connector | ✅ | `jira.py` | Webhooks + API polling, JQL search |
| Slack Connector | ✅ | `slack.py` | Events API, messages, channels |
| PagerDuty Connector | ✅ | `pagerduty.py` | Webhooks + Events API |
| Kubernetes Connector | ✅ | `kubernetes.py` | Resources, deployments, pods, logs |

**Acceptance Criteria**:
- [x] Unified connector interface
- [x] OAuth token refresh handling
- [x] Webhook signature verification
- [x] Rate limit tracking
- [x] Connection health monitoring

---

## Phase 3: Materialized Analytics (Medium Priority)

### 3.1 Precomputed Rollups
**Status**: ✅ Complete
**Location**: `backend/app/services/rollups/`
**Priority**: P2 (Medium)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Rollup Models | ✅ | `models.py` | DORArollup, SPACERollup, RollupQuery |
| Rollup Service | ✅ | `service.py` | Compute DORA/SPACE metrics |
| Rollup Worker | ✅ | `worker.py` | Background computation + backfill |
| Rollup API | ✅ | `api/rollups.py` | Query + compute endpoints |
| DB Migration | ✅ | `alembic/versions/20260119_003_metric_rollups.py` | metric_rollups table |

**Acceptance Criteria**:
- [x] Hourly DORA/SPACE rollups per project/team
- [x] Daily aggregates for dashboards
- [x] Incremental computation
- [x] Backfill capability
- [x] Gap filling in queries

---

### 3.2 Query Gateway
**Status**: ✅ Complete
**Location**: `backend/app/services/query/`
**Priority**: P2 (Medium)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Query Models | ✅ | `models.py` | QueryRequest, QueryResponse, DashboardQuery |
| Query Gateway | ✅ | `gateway.py` | Multi-source aggregation |
| Dashboard Queries | ✅ | `models.py` | Pre-defined dashboards |
| Query API | ✅ | `api/query.py` | Unified query endpoint |

**Acceptance Criteria**:
- [x] Single endpoint for dashboard data
- [x] Cross-store aggregation (metrics, entities, events)
- [x] Tenant enforcement
- [x] Response caching
- [x] Pre-defined dashboard queries

---

## Phase 4: LLM Enhancements (Medium Priority)

### 4.1 Prompt Registry
**Status**: ✅ Complete
**Location**: `backend/app/services/prompts/`
**Priority**: P2 (Medium)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Prompt Models | ✅ | `models.py` | Prompt, PromptVersion, PromptExperiment |
| Prompt Registry | ✅ | `registry.py` | Version management + rendering |
| A/B Testing | ✅ | `registry.py` | Experiment assignment + tracking |
| Performance | ✅ | `registry.py` | Execution metrics |
| DB Migration | ✅ | `alembic/versions/20260119_004_prompts.py` | All tables |

**Acceptance Criteria**:
- [x] Versioned prompt storage
- [x] A/B test assignment (consistent hashing)
- [x] Performance tracking
- [x] Template variable substitution
- [x] Rollback via version history

---

### 4.2 Evaluation Framework
**Status**: ✅ Complete
**Location**: `backend/app/services/evaluation/`
**Priority**: P2 (Medium)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Eval Models | ✅ | `models.py` | TestCase, TestSet, EvalRun, EvalResult |
| Evaluators | ✅ | `evaluator.py` | ExactMatch, Contains, Regex, Semantic, LLMJudge |
| Eval Runner | ✅ | `runner.py` | Batch execution + baseline comparison |
| DB Migration | ✅ | `alembic/versions/20260119_005_evaluation.py` | All tables |

**Acceptance Criteria**:
- [x] Test set management
- [x] Automated evaluation runs
- [x] Multiple evaluator types (exact, contains, regex, semantic, LLM judge)
- [x] Regression detection (baseline comparison)
- [x] CI integration support (git commit tracking, triggered_by)

---

## Phase 5: Enterprise Features (Lower Priority)

### 5.1 SSO Integration
**Status**: ✅ Complete
**Location**: `backend/app/services/sso/`
**Priority**: P3 (Low)

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| SSO Config | ✅ | `config.py` | Provider settings, well-known providers |
| OIDC Provider | ✅ | `oidc.py` | OpenID Connect with PKCE |
| SAML Provider | ✅ | `saml.py` | SAML 2.0, AuthnRequest, assertion parsing |
| SSO Service | ✅ | `service.py` | Unified SSO service |
| SSO API | ✅ | `api/sso.py` | Full REST endpoints |

**Acceptance Criteria**:
- [x] OIDC authentication with PKCE support
- [x] SAML 2.0 SP-initiated SSO
- [x] Multiple provider support
- [x] Session management
- [x] User provisioning

---

### 5.2 API Versioning
**Status**: ✅ Complete
**Priority**: P3 (Low)
**Location**: `backend/app/api/versioning.py`

| Component | Status | Notes |
|-----------|--------|-------|
| Version Router | ✅ | VersionedRoute class, `/api/v1/`, `/api/v2/` |
| Deprecation Headers | ✅ | Sunset, Deprecation, Link headers |
| Migration Guide | ✅ | v1 to v2 migration guide built-in |
| Version Info API | ✅ | `/api/versions` endpoint |

**Acceptance Criteria**:
- [x] Versioned API routing
- [x] Deprecation headers on old versions
- [x] Migration guide endpoint
- [x] Sunset date enforcement

---

## Database Migrations Required

| Migration | Status | Description |
|-----------|--------|-------------|
| Raw events table | 📋 | Event store metadata |
| Canonical entities | 📋 | Repo, Commit, PR, Build, Deploy, Incident |
| Identity mappings | 📋 | Cross-source identity |
| Metric rollups | 📋 | Precomputed aggregates |
| Prompt templates | 📋 | Versioned prompts |
| Eval test sets | 📋 | Evaluation data |

---

## Docker Services to Add

| Service | Status | Notes |
|---------|--------|-------|
| NATS JetStream | 📋 | Message queue |
| MinIO | 📋 | Local S3 for dev |

---

## Implementation Order

1. **Event Ingestion** → Foundation for all data
2. **Message Queue** → Async processing
3. **Entity Service** → Canonical data model
4. **Connectors** → Data sources
5. **Rollups** → Fast dashboards
6. **Query Gateway** → Unified API
7. **Prompt Registry** → LLM improvements
8. **Evaluation** → Quality assurance
9. **SSO** → Enterprise auth
10. **API Versioning** → API stability

---

## Progress Log

### 2026-01-19
- Created roadmap document
- ✅ Completed Phase 1.1: Event Ingestion Service
- ✅ Completed Phase 1.3: Message Queue Integration  
- ✅ Completed Phase 1.2: Entity Service (canonical models, store, identity resolver, normalizers)
- ✅ Completed Phase 2.1: Connector Framework (base, registry, GitHub, GitLab)
- ✅ Completed Phase 3.1: Precomputed Rollups (DORA/SPACE, worker, API)
- ✅ Completed Phase 3.2: Query Gateway (unified query, dashboard queries)
- ✅ Completed Phase 4.1: Prompt Registry (versioning, A/B testing, performance)
- ✅ Completed Phase 4.2: Evaluation Framework (test sets, evaluators, regression detection)

### 2026-01-20
- ✅ Completed Phase 5.1: SSO Integration (OIDC + SAML)
- ✅ Completed Phase 5.2: API Versioning (router, deprecation headers, migration guide)
- ✅ Completed Phase 2.1: Additional Connectors (Jira, Slack, PagerDuty, Kubernetes)

**All phases complete!**

