# RBAC Implementation Guide

## Overview

NexusAI implements Role-Based Access Control (RBAC) with fine-grained permissions using OpenFGA for relationship-based authorization.

## Architecture

### 1. Permission System

**Location**: `backend/app/services/security/permissions.py`

Defines:
- System permissions (org, project, metrics, agent, tool, etc.)
- Predefined roles with permission sets
- Permission checking logic

### 2. OpenFGA Integration

**Location**: `backend/app/core/authorization.py`

Provides:
- Relationship-Based Access Control (ReBAC)
- Fine-grained permissions at object level
- Dynamic permission evaluation
- Team and organizational hierarchy support

### 3. Permission Checker

**Location**: `backend/app/services/mcp/permissions.py`

Handles:
- Tool execution permissions
- Resource access permissions
- Role-based policy enforcement

## Permission Types

### Organization Permissions

- `org:read` - Read organization data
- `org:write` - Modify organization data
- `org:admin` - Full organization control
- `org:delete` - Delete organization

### Project Permissions

- `project:read` - Read project data
- `project:write` - Modify project data
- `project:admin` - Full project control
- `project:delete` - Delete project

### Metrics Permissions

- `metrics:read` - View metrics
- `metrics:export` - Export metrics data

### Agent Permissions

- `agent:read` - View agents
- `agent:execute` - Execute agents
- `agent:admin` - Manage agents

### Tool Permissions

- `tool:read` - View tools
- `tool:execute` - Execute tools
- `tool:admin` - Manage tools

## Roles

### Organization Roles

1. **owner**: Full organization control
2. **admin**: Administrative access
3. **member**: Standard member access
4. **viewer**: Read-only access

### Project Roles

1. **admin**: Full project control
2. **maintainer**: Can manage resources
3. **developer**: Can create/edit resources
4. **viewer**: Read-only access

## OpenFGA Model

**Location**: `backend/app/core/authorization.py` (lines 415-455)

The authorization model defines relationships:

```python
type organization
  relations
    define owner: [user]
    define admin: [user] or owner
    define member: [user] or admin
    define viewer: [user] or member

type project
  relations
    define organization: [organization]
    define admin: [user] or admin from organization
    define maintainer: [user] or admin
    define developer: [user] or maintainer
    define viewer: [user] or developer
```

## Usage

### Checking Permissions

```python
from app.core.authorization import get_openfga_client

client = get_openfga_client()
has_access = await client.check(
    user="user:alice",
    relation="can_view",
    object="project:project1"
)
```

### Granting Permissions

```python
from app.core.authorization import AuthorizationTuple

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

### API Endpoint Protection

```python
from app.services.mcp.permissions import PermissionChecker

checker = PermissionChecker()
has_permission, error = await checker.check_permission(
    user_id=user_id,
    tool_name="devlake_create_project",
    roles=user_roles,
    organization_id=org_id,
    resource_context={"project_id": project_id}
)
```

## Configuration

Set in environment variables:
- `OPENFGA_URL`: OpenFGA server URL
- `OPENFGA_STORE_ID`: OpenFGA store identifier
- `OPENFGA_MODEL_ID`: Authorization model ID
- `OPENFGA_TOKEN`: Authentication token

## Fallback Behavior

If OpenFGA is unavailable:
- System falls back to role-based checks
- Basic permissions are enforced
- Full ReBAC features are disabled

## Testing

RBAC is tested in:
- `backend/tests/unit/test_security.py`
- `backend/tests/unit/test_organizations.py`
