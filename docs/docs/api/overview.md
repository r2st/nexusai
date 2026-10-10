---
sidebar_position: 1
---

# API Overview

NexusAI provides a RESTful API for integrating AI capabilities into your applications.

## Base URL

- **Local Development**: `http://localhost:8000/api/v1`
- **Production**: `https://api.your-domain.com/api/v1`

## Authentication

All API requests require authentication using Bearer tokens.

### Getting a Token

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

### Using the Token

Include the token in the Authorization header:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## Rate Limiting

| Tier | Requests/Minute | Requests/Day |
|------|-----------------|--------------|
| Free | 60 | 1,000 |
| Pro | 300 | 10,000 |
| Enterprise | Custom | Custom |

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
```

## Response Format

All responses follow a consistent JSON format:

### Success Response

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

## API Endpoints

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/conversations` | Create a conversation |
| GET | `/chat/conversations` | List conversations |
| GET | `/chat/conversations/{conversation_id}` | Get conversation details |
| GET | `/chat/conversations/{conversation_id}/messages` | List messages |
| POST | `/chat/conversations/{conversation_id}/chat` | Send a message |
| DELETE | `/chat/conversations/{conversation_id}` | Delete conversation |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/upload` | Upload a document |
| GET | `/documents` | List documents |
| GET | `/documents/{id}` | Get document details |
| DELETE | `/documents/{id}` | Delete document |
| POST | `/documents/search` | Search documents |

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents` | List available agents |
| POST | `/agents/{id}/execute` | Execute an agent |
| GET | `/agents/{id}/status` | Get execution status |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/usage` | Get usage statistics |
| GET | `/analytics/costs` | Get cost breakdown |
| GET | `/analytics/models` | Get model performance |

## SDKs

Official SDKs are available for:

- **Python**: `pip install nexusai`
- **JavaScript/TypeScript**: `npm install @nexusai/sdk`
- **Go**: `go get github.com/nexusai/nexusai-go`

### Python Example

```python
from nexusai import NexusAI

client = NexusAI(api_key="your-api-key")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### TypeScript Example

```typescript
import { NexusAI } from '@nexusai/sdk';

const client = new NexusAI({ apiKey: 'your-api-key' });

const response = await client.chat.completions.create({
  model: 'gpt-4',
  messages: [
    { role: 'user', content: 'Hello!' }
  ]
});

console.log(response.choices[0].message.content);
```

## OpenAPI Specification

The full OpenAPI specification is available at:
- **Interactive Docs**: `/docs` (Swagger UI)
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`
