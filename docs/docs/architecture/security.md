---
sidebar_position: 5
---

# Security

NexusAI supports a layered security model. Exact behavior depends on which optional services are enabled.

## Authentication (OIDC)

- **Keycloak** provides identity (users, realms, clients).
- **OAuth2 Proxy** can sit in front of the frontend as an auth gateway.

See `docker/compose/services/docker-compose.auth.yml`.

## Authorization (fine-grained)

- **OpenFGA** enables relationship-based access control for org/project/resource permissions.
- Backend permission checks live under `backend/app/services/security/` and `backend/app/core/authorization.py`.

## Secrets management

- **OpenBao** (Vault fork) can store secrets with tenant isolation strategies.

## Multi-tenancy

When enabled, tenant context and per-tenant rate limiting are enforced via middleware (see `backend/app/core/middleware.py`).

