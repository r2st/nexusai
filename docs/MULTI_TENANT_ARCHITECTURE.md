# Multi-Tenant Architecture

## Overview

NexusAI implements a comprehensive multi-tenant architecture with strict data isolation, ensuring that each organization's data is completely segregated from others.

## Architecture Components

### 1. Tenant Isolation Service

**Location**: `backend/app/services/security/tenant_isolation.py`

The `TenantIsolationService` provides:
- Row-Level Security (RLS) enforcement
- Cross-tenant access prevention
- Tenant context validation
- Data boundary enforcement

### 2. Row-Level Security (RLS)

PostgreSQL Row-Level Security policies ensure that:
- All queries are automatically scoped to the current tenant
- Cross-tenant data access is prevented at the database level
- Even direct SQL queries respect tenant boundaries

**Isolated Tables**:
- `organizations`
- `organization_members`
- `projects`
- `project_members`
- `connections`
- `blueprints`
- `pipelines`
- `conversations`
- `messages`
- `documents`
- `document_chunks`
- `ai_usage_logs`
- `ai_analytics_metrics`
- `agents`
- `agent_tools`
- `agent_executions`
- `openapi_actions`
- `workflow_executions`
- `audit_logs`

### 3. Tenant Context

**Location**: `backend/app/services/security/tenant_isolation.py`

The `TenantContext` dataclass holds:
- `tenant_id`: Current tenant identifier
- `user_id`: Current user identifier
- `scope`: Access scope (ORGANIZATION, PROJECT, TEAM, PERSONAL)
- `project_id`: Optional project identifier
- `team_id`: Optional team identifier
- `is_admin`: Admin flag
- `permissions`: Set of permissions

### 4. Tenant Middleware

**Location**: `backend/app/core/middleware.py`

The `TenantMiddleware` automatically:
- Extracts tenant ID from request headers or user context
- Sets tenant context for the request
- Validates tenant access
- Enforces tenant isolation

### 5. Database Session Management

**Location**: `backend/app/core/multitenancy.py`

Functions for:
- Creating RLS policies
- Setting session tenant context
- Validating tenant access

## Usage

### Setting Tenant Context

```python
from app.services.security.tenant_isolation import TenantIsolationService

service = TenantIsolationService()
await service.set_session_tenant(session, tenant_id="tenant-uuid")
```

### Accessing Tenant Context

```python
from app.services.security.tenant_isolation import get_current_tenant_context

context = get_current_tenant_context()
if context:
    tenant_id = context.tenant_id
    user_id = context.user_id
```

### API Dependency

```python
from app.api.deps import get_db_with_tenant

@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_db_with_tenant)):
    # All queries are automatically scoped to current tenant
    items = await db.execute(select(Item))
    return items.scalars().all()
```

## Security Considerations

1. **Strict Mode**: When enabled, queries without tenant context are rejected
2. **RLS Enforcement**: Database-level policies prevent data leakage
3. **Context Validation**: All tenant contexts are validated before use
4. **Audit Logging**: All tenant access is logged for compliance

## Configuration

Set in environment variables:
- `MULTI_TENANT_ENABLED=true`
- `TENANT_ISOLATION_STRICT_MODE=true` (recommended for production)

## Testing

Multi-tenant isolation is tested in:
- `backend/tests/unit/test_multitenancy.py`
- `backend/tests/integration/test_organization_flow.py`
