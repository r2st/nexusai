# Grafana RBAC Implementation

## Overview

NexusAI integrates with Grafana's Role-Based Access Control (RBAC) to provide fine-grained access control to dashboards and data sources, ensuring users only see data they're authorized to access.

## Architecture

### 1. Grafana Integration

**Location**: `docker/compose/services/docker-compose.monitoring.yml`

Grafana is deployed with:
- RBAC enabled
- Service account authentication
- Organization-based access
- Dashboard provisioning

### 2. RBAC Service

**Location**: `backend/app/services/grafana/rbac.py` (to be created)

Provides:
- User synchronization
- Role assignment
- Permission management
- Dashboard access control

### 3. OpenFGA Integration

Grafana RBAC integrates with OpenFGA:
- User permissions are checked via OpenFGA
- Dashboard access is gated by project/organization permissions
- Role inheritance from NexusAI to Grafana

## Setup

### 1. Configure Grafana

```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=secure-password
GRAFANA_URL=http://localhost:3002
```

### 2. Enable RBAC

Grafana RBAC is enabled by default in the configuration.

### 3. Create Service Account

```bash
# Create Grafana service account
curl -X POST http://localhost:3002/api/serviceaccounts \
  -H "Authorization: Bearer $GRAFANA_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nexusai-service",
    "role": "Admin"
  }'
```

## RBAC Model

### Roles

1. **Admin**: Full access to all dashboards and data sources
2. **Editor**: Can edit dashboards and queries
3. **Viewer**: Read-only access to dashboards
4. **Custom Roles**: Project-specific roles

### Permissions

- **Dashboard Access**: View/edit/delete dashboards
- **DataSource Access**: Query data sources
- **Organization Access**: Access organization-level resources
- **Project Access**: Access project-specific dashboards

## Implementation

### 1. User Synchronization

Sync NexusAI users to Grafana:

```python
from app.services.grafana.rbac import GrafanaRBACService

service = GrafanaRBACService()
await service.sync_user(
    user_id=user_id,
    email=user.email,
    name=user.full_name,
    role="Viewer"  # Based on NexusAI permissions
)
```

### 2. Role Assignment

Assign roles based on NexusAI permissions:

```python
# Check user's NexusAI permissions
has_admin = await check_permission(
    user=user_id,
    relation="can_manage",
    object=f"project:{project_id}"
)

# Assign Grafana role accordingly
grafana_role = "Admin" if has_admin else "Viewer"
await service.assign_role(user_id, grafana_role)
```

### 3. Dashboard Access Control

Control dashboard access:

```python
# Create dashboard with access control
dashboard = await service.create_dashboard(
    title="Project Dashboard",
    project_id=project_id,
    access_control={
        "viewers": [user_id1, user_id2],
        "editors": [user_id3],
        "admins": [user_id4]
    }
)
```

## Integration with OpenFGA

### Permission Mapping

NexusAI permissions map to Grafana roles:

```
NexusAI Permission → Grafana Role
─────────────────────────────────
org:admin          → Admin
project:admin      → Admin
project:maintainer → Editor
project:developer  → Editor
project:viewer     → Viewer
```

### Permission Check

Before granting Grafana access:

```python
from app.core.authorization import get_openfga_client

client = get_openfga_client()
has_access = await client.check(
    user=f"user:{user_id}",
    relation="can_view",
    object=f"project:{project_id}"
)

if has_access:
    await grant_grafana_access(user_id, project_id)
```

## Dashboard Provisioning

### 1. Organization Dashboards

Organization-level dashboards:
- Accessible to all org members
- Based on organization permissions
- Inherit org-level RBAC

### 2. Project Dashboards

Project-specific dashboards:
- Accessible to project members
- Based on project permissions
- Scoped to project data

### 3. User Dashboards

Personal dashboards:
- Accessible only to creator
- Can be shared with team
- Respect sharing permissions

## API Endpoints

### Sync User

```http
POST /api/v1/grafana/rbac/sync-user
```

Syncs NexusAI user to Grafana with appropriate role.

### Assign Role

```http
POST /api/v1/grafana/rbac/assign-role
```

Assigns Grafana role to user.

### Get Dashboard Access

```http
GET /api/v1/grafana/rbac/dashboards/{dashboard_id}/access
```

Returns users with access to dashboard.

## Configuration

Set in environment variables:
- `GRAFANA_URL`: Grafana server URL
- `GRAFANA_ADMIN_TOKEN`: Admin API token
- `GRAFANA_RBAC_ENABLED`: Enable RBAC integration

## Security Considerations

1. **Token Management**: Store Grafana tokens securely in OpenBao
2. **Role Inheritance**: Roles inherit from NexusAI permissions
3. **Access Validation**: All access is validated via OpenFGA
4. **Audit Logging**: All RBAC operations are logged

## Monitoring

Monitor Grafana RBAC:
- User sync status
- Role assignment success rate
- Access denial rate
- Dashboard access patterns

## Troubleshooting

### User Not Synced

Check:
1. Grafana service account token is valid
2. User exists in NexusAI
3. Sync service is running
4. Permissions are correct

### Access Denied

Check:
1. User has correct NexusAI permissions
2. Role is assigned in Grafana
3. Dashboard access control is correct
4. OpenFGA check passes

## References

- [Grafana RBAC Documentation](https://grafana.com/docs/grafana/latest/administration/roles-and-permissions/)
- [Grafana API](https://grafana.com/docs/grafana/latest/developers/http_api/)
- OpenFGA Integration: `backend/app/core/authorization.py`
