---
sidebar_position: 1
slug: /
---

# Welcome to NexusAI

NexusAI is an **AI-powered chat and analytics platform** designed for enterprise teams. It provides a comprehensive solution for AI-assisted conversations, document analysis, code generation, and DevOps metrics visualization.

## Key Features

### 🤖 Multi-Model AI Support

NexusAI integrates with multiple AI providers:

- **OpenAI** (GPT-4, GPT-4o)
- **Anthropic** (Claude 3 Opus, Sonnet, Haiku)
- **Google** (Gemini Pro)
- **Azure OpenAI**
- **AWS Bedrock**
- **Local Models** (Ollama)

### 📄 Document Intelligence

Upload and analyze documents with AI:

- PDF, Word, Excel, and text file support
- Automatic text extraction and summarization
- Semantic search across your document library
- RAG (Retrieval-Augmented Generation) for context-aware responses

### 🔧 AI Agents

Specialized agents for different tasks:

- **DORA Metrics Agent** - Track deployment frequency, lead time, MTTR
- **Code Analysis Agent** - Review and explain code
- **DevOps Agent** - CI/CD pipeline insights
- **Custom Agents** - Build your own with MCP tools

### 📊 Analytics Dashboard

Comprehensive analytics and reporting:

- Usage metrics and cost tracking
- Team productivity insights
- AI model performance comparison
- Custom dashboard creation

### 🔒 Enterprise Security

Built with security-first principles:

- Multi-tenant data isolation
- Role-based access control (RBAC)
- Fine-grained authorization (OpenFGA)
- SSO integration (Keycloak, OAuth2)
- Audit logging

## Quick Links

- [Getting Started](/docs/getting-started/installation)
- [API Reference](/docs/api/overview)
- [Deployment Guide](/docs/deployment/docker)
- [Security Documentation](/docs/architecture/security)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│                    (Next.js + React)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                     Traefik Proxy                           │
│               (TLS, Rate Limiting, Auth)                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                    Backend API                              │
│                      (FastAPI)                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │   Chat   │ │  Agents  │ │   Docs   │ │ Analytics│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                     Data Layer                              │
├──────────────┬──────────────┬──────────────┬───────────────┤
│  PostgreSQL  │    Redis     │  Meilisearch │   OpenBao     │
│  (pgvector)  │   (Cache)    │   (Search)   │  (Secrets)    │
└──────────────┴──────────────┴──────────────┴───────────────┘
```

## Getting Help

- **Documentation**: You're here!
- **GitHub Issues**: [Report bugs or request features](https://github.com/nexusai/nexusai/issues)
- **Discord**: [Join our community](https://discord.gg/nexusai)
- **Email**: support@nexusai.example.com
