---
sidebar_position: 1
---

# User Management

## Development defaults

In development mode, the backend seeds test users on startup (see `backend/app/main.py`):

- `admin@nexusai.dev` / `admin123`
- `user@nexusai.dev` / `user123`
- `viewer@nexusai.dev` / `viewer123`

## Production

In production, user identity is typically managed via an IdP (for example Keycloak + OIDC).

