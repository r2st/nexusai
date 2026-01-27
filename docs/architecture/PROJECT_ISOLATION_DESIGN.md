# Project Isolation Design

## Overview

Projects provide an additional layer of data isolation within organizations, allowing teams to separate their work while maintaining organizational context.

## Design Principles

1. **Hierarchical Isolation**: Organization → Project → Resource
2. **Inheritance**: Projects inherit organization-level permissions
3. **Scoped Access**: Users can have different access levels per project
4. **Data Segregation**: All project data is isolated by `project_id` and `tenant_id`

## Data Model

### Project Model

**Location**: `backend/app/models/project.py`

```python
class Project(Base):
    id: str  # UUID
    tenant_id: str  # Tenant isolation
    organization_id: str  # Parent organization
    name: str
    key: str  # Short key like "PROJ"
    description: str | None
    settings: dict  # Project-specific settings
    dora_config: dict  # DORA metrics configuration
    is_active: bool
    is_public: bool
```

### Project Members

**Location**: `backend/app/models/project.py`

```python
class ProjectMember(Base):
    project_id: str
    user_id: str
    role: ProjectRole  # admin, maintainer, developer, viewer
    permissions: dict
```

## Isolation Mechanisms

### 1. Database-Level Isolation

All project-related tables include:
- `tenant_id`: For tenant isolation
- `project_id`: For project isolation
- `organization_id`: For organizational context

### 2. Query Scoping

All queries automatically filter by:
1. `tenant_id` (via RLS)
2. `project_id` (via application logic)
3. User permissions (via OpenFGA)

### 3. API Endpoints

All project endpoints:
- Require authentication
- Validate project access
- Scope results to user's accessible projects

## Access Control

### Project Roles

1. **admin**: Full project control
2. **maintainer**: Can manage resources
3. **developer**: Can create/edit resources
4. **viewer**: Read-only access

### Permission Inheritance

```
Organization Admin
  └─> Project Admin (inherits org admin permissions)
      └─> Project Maintainer
          └─> Project Developer
              └─> Project Viewer
```

## Usage Examples

### Creating a Project

```python
from app.services.project import ProjectService

service = ProjectService(db=db, user_id=user_id)
project = await service.create_project(
    organization_id=org_id,
    name="My Project",
    key="MYPROJ",
    description="Project description"
)
```

### Accessing Project Data

```python
from app.api.deps import get_current_project

@router.get("/metrics")
async def get_metrics(
    project: Project = Depends(get_current_project)
):
    # Project is automatically scoped to user's access
    metrics = await get_project_metrics(project.id)
    return metrics
```

## Integration with DevLake

Projects map to DevLake projects:
- Each NexusAI project can have one or more DevLake projects
- DORA metrics are calculated per project
- Blueprints are scoped to projects
- Connections are shared at organization level but scoped to projects

## Security Considerations

1. **Project Visibility**: Projects can be public (within org) or private
2. **Member Validation**: All project members are validated
3. **Resource Access**: Resources inherit project access rules
4. **Audit Trail**: All project access is logged

## Configuration

Project settings include:
- DORA metrics configuration
- Data retention policies
- Notification preferences
- Integration settings

## Testing

Project isolation is tested in:
- `backend/tests/unit/test_organizations.py`
- `backend/tests/integration/test_organization_flow.py`
