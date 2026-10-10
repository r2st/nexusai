---
sidebar_position: 2
---

# Authentication

NexusAI uses Bearer tokens for API authentication.

## Login

```bash
curl -sS -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@nexusai.dev","password":"user123"}'
```

Use the returned token:

```bash
curl -sS http://localhost:8000/api/v1/health \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## OpenAPI

See `http://localhost:8000/docs` for the full auth endpoint list and schemas.

