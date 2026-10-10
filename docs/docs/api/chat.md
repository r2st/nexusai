---
sidebar_position: 3
---

# Chat API

Chat endpoints are organized around conversations.

## Create a conversation

```bash
curl -sS -X POST http://localhost:8000/api/v1/chat/conversations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My first conversation"}'
```

## Send a message

```bash
curl -sS -X POST http://localhost:8000/api/v1/chat/conversations/CONVERSATION_ID/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```

Endpoints vary by enabled features (tools, agents, websockets). Use `http://localhost:8000/docs` for details.

