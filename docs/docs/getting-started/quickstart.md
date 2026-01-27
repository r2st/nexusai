---
sidebar_position: 2
---

# Quick Start

Get up and running with NexusAI in 5 minutes.

## Create Your First Chat

### 1. Access the Application

Open your browser and navigate to:
- **Local**: http://localhost:3000
- **Production**: https://your-domain.com

### 2. Sign Up or Log In

If authentication is enabled, you'll need to:
1. Click "Sign Up" to create an account
2. Verify your email (if required)
3. Log in with your credentials

### 3. Start a Conversation

1. Click "New Chat" in the sidebar
2. Type your message in the input field
3. Press Enter or click Send

Example prompts to try:
```
"Explain the concept of microservices architecture"
"Write a Python function to calculate fibonacci numbers"
"Summarize the key points of agile methodology"
```

## Using AI Agents

Agents are specialized AI assistants for specific tasks.

### DORA Metrics Agent

Track your team's DevOps performance:

```
@dora-agent Show me deployment frequency for the last 30 days
```

### Code Analysis Agent

Get code reviews and explanations:

```
@code-agent Review this function for potential bugs:
def process_data(data):
    return data.split(',')[0]
```

## Document Analysis

### Upload Documents

1. Click the attachment icon in the chat
2. Select your document (PDF, DOCX, TXT)
3. Wait for processing to complete

### Ask Questions

Once uploaded, ask questions about your documents:

```
"What are the main points in the uploaded document?"
"Summarize the quarterly report"
"Find all mentions of 'revenue' in my documents"
```

## API Quick Start

### Authentication

First, get an API token:

```bash
# Using username/password
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your-password"}'
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Create a Chat Completion

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "model": "gpt-4"
  }'
```

### Upload a Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Send message |
| `Ctrl+N` | New chat |
| `Ctrl+K` | Search |
| `Ctrl+/` | Show shortcuts |
| `Escape` | Cancel action |

## Next Steps

- [Configuration Guide](/docs/getting-started/configuration)
- [API Reference](/docs/api/overview)
- [Agent Documentation](/docs/features/agents)
