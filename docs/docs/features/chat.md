---
sidebar_position: 1
---

# Chat

NexusAI chat is built around **conversations** and **messages**.

## What it does

- Create/list conversations
- Send messages and stream responses (UI and websocket support)
- Persist conversation metadata and usage (tokens, timestamps)

## Key backend routes

All routes are under `http://localhost:8000/api/v1`.

- `POST /chat/conversations`
- `GET /chat/conversations`
- `GET /chat/conversations/{conversation_id}`
- `GET /chat/conversations/{conversation_id}/messages`
- `POST /chat/conversations/{conversation_id}/chat`

For exact request/response shapes, use the OpenAPI docs at `http://localhost:8000/docs`.

