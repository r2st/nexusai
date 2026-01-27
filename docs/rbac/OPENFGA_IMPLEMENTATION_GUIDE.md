# OpenFGA Implementation Guide

## Overview

NexusAI uses OpenFGA (open-source fork of Google Zanzibar) for Relationship-Based Access Control (ReBAC), providing fine-grained, scalable authorization.

## What is OpenFGA?

OpenFGA is a high-performance authorization system that:
- Supports relationship-based access control
- Scales to millions of authorization checks per second
- Provides flexible permission models
- Enables fine-grained access control

## Architecture

### 1. OpenFGA Client

**Location**: `backend/app/core/authorization.py`

The `OpenFGAClient` provides:
- Authorization checks
- Tuple writes (granting permissions)
- Tuple deletes (revoking permissions)
- Model management

### 2. Authorization Model

The authorization model defines:
- Object types (user, organization, project, etc.)
- Relations between objects
- Permission inheritance rules

### 3. Tuples

Tuples represent relationships:
- `user:alice` has `admin` relation to `project:project1`
- `project:project1` belongs to `organization:org1`
- Permissions inherit through relationships

## Setup

### 1. Start OpenFGA

```bash
# Using Docker Compose
docker-compose -f docker/compose/services/docker-compose.auth.yml up -d openfga
```

### 2. Configure Environment

```env
OPENFGA_URL=http://localhost:8080
OPENFGA_STORE_ID=your-store-id
OPENFGA_MODEL_ID=your-model-id
OPENFGA_TOKEN=your-token
```

### 3. Initialize Store

```python
from app.core.authorization import get_openfga_client

client = get_openfga_client()
await client.create_store("NexusAI")
```

### 4. Deploy Model

The authorization model is automatically deployed on first use, or can be deployed manually:

```python
await client.write_authorization_model(OPENFGA_MODEL)
```

## Authorization Model

### Object Types

1. **user**: System users
2. **organization**: Organizations (tenants)
3. **project**: Projects within organizations
4. **connection**: Data source connections
5. **document**: Documents and files

### Relations

#### Organization Relations

```
organization:org1
  ├─ owner: [user:alice]
  ├─ admin: [user:bob] or owner
  ├─ member: [user:charlie] or admin
  └─ viewer: [user:dave] or member
```

#### Project Relations

```
project:project1
  ├─ organization: [organization:org1]
  ├─ admin: [user:alice] or admin from organization
  ├─ maintainer: [user:bob] or admin
  ├─ developer: [user:charlie] or maintainer
  └─ viewer: [user:dave] or developer
```

## Usage Examples

### Check Permission

```python
# Check if user can view project
allowed = await client.check(
    user="user:alice",
    relation="can_view",
    object="project:project1"
)
```

### Grant Permission

```python
# Make user admin of project
await client.write(
    writes=[
        AuthorizationTuple(
            user="user:alice",
            relation="admin",
            object="project:project1"
        )
    ]
)
```

### List Permissions

```python
# List all users who can view project
users = await client.list_users(
    relation="can_view",
    object="project:project1"
)
```

## Integration Points

### 1. API Endpoints

All protected endpoints check permissions:

```python
from app.core.authorization import check_permission

@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user)
):
    has_access = await check_permission(
        user=str(user.id),
        relation="can_view",
        object=f"project:{project_id}"
    )
    if not has_access:
        raise HTTPException(403, "Access denied")
```

### 2. Tool Execution

MCP tools check permissions before execution:

```python
from app.services.mcp.permissions import PermissionChecker

checker = PermissionChecker()
has_permission, error = await checker.check_permission(
    user_id=user_id,
    tool_name="devlake_create_project",
    roles=user_roles,
    organization_id=org_id
)
```

### 3. Resource Access

All resource access is gated by OpenFGA:

```python
# Automatically checked via middleware
@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    user: User = Depends(get_current_user)
):
    # Permission check happens automatically
    document = await get_document(doc_id)
    return document
```

## Performance

OpenFGA is optimized for:
- High-throughput authorization checks
- Low-latency responses (<10ms typical)
- Caching of common checks
- Batch operations

## Monitoring

Monitor OpenFGA:
- Check health: `GET /healthz`
- View metrics: `GET /metrics`
- Check logs: OpenFGA container logs

## Troubleshooting

### OpenFGA Unavailable

If OpenFGA is down:
- System falls back to role-based checks
- Basic permissions are enforced
- Full ReBAC features are disabled

### Permission Denied

Check:
1. User has correct role
2. Tuple exists in OpenFGA
3. Model allows the relation
4. Inheritance chain is correct

## Best Practices

1. **Use Relations**: Prefer relations over direct permissions
2. **Inherit Permissions**: Use inheritance for hierarchical access
3. **Cache Checks**: Cache common permission checks
4. **Batch Operations**: Batch multiple checks when possible
5. **Monitor Performance**: Track authorization check latency

## References

- [OpenFGA Documentation](https://openfga.dev/)
- [Authorization Model](https://openfga.dev/docs/modeling)
- [API Reference](https://openfga.dev/api)
