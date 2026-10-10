---
sidebar_position: 5
---

# Documents API

## Upload

```bash
curl -sS -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/document.pdf"
```

## Search

```bash
curl -sS -X POST http://localhost:8000/api/v1/documents/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"revenue"}'
```

See `http://localhost:8000/docs` for full parameters and responses.

