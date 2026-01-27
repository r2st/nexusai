# LLM Services Architecture Roadmap

> Enterprise-grade LLM infrastructure for Software Intelligence platform

## Overview

This document tracks the implementation of LLM services that power NexusAI's AI capabilities for **LLM-Powered Software Engineering Intelligence**:

- **MCP Integration Layer** - "USB-C port" for AI tools - standardized protocol replacing fragmented integrations
- **Tool Calling Runtime** - Model↔Tool interaction loop with RBAC and audit trails
- **RAG Service** - Retrieval-Augmented Generation for code, docs, tickets, incidents
- **Agent Orchestration** - LangGraph-based multi-step workflows with human-in-loop
- **Model Router** - Multi-model routing by task, cost, latency, and data sensitivity
- **Code Sandbox** - Ephemeral isolated execution for agents
- **Governance Layer** - Prompt management, PII redaction, RBAC, audit logging

### Design Philosophy

> "Teams spin up demos in days, but turning LLMs into dependable systems is far more difficult...
> Without a foundation for governance, observability, and control, LLM adoption stalls or creates unacceptable risk."

Our implementation follows enterprise-grade patterns:
1. **Defense in depth** - Multiple layers of security and validation
2. **Tenant isolation** - All operations scoped to tenant with RBAC
3. **Audit everything** - Full traceability of prompt → tool → result
4. **Fail gracefully** - Automatic fallbacks and human escalation

---

## Implementation Priority

| Priority | Service | ROI | Complexity |
|----------|---------|-----|------------|
| 1 | Tool Calling Runtime + RBAC + Audit | High | Medium |
| 2 | RAG for Codebase Q&A | High | Medium |
| 3 | MCP Integration Layer | High | Medium |
| 4 | PR Review Agent | High | Medium |
| 5 | Agent Orchestration (LangGraph) | High | High |
| 6 | Model Router Service | Medium | Medium |
| 7 | Code Sandbox Service | Medium | High |
| 8 | Prompt/Policy/Governance | High | Medium |

---

## Phase 1: Tool Calling Runtime
**Status**: ✅ Complete

### 1.1 Tool Registry & Execution
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Tool Base Class | ✅ Complete | `services/tools/base.py` | Abstract tool interface with OpenAI/Anthropic format |
| Tool Registry | ✅ Complete | `services/tools/registry.py` | Tool discovery, registration, filtering |
| Tool Executor | ✅ Complete | `services/tools/executor.py` | Safe execution with timeouts & retries |
| Built-in Tools | ✅ Complete | `services/tools/builtins/` | 9 core platform tools |

### 1.2 RBAC & Permissions
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Tool Permissions | ✅ Complete | `services/tools/permissions.py` | Per-tool RBAC with role hierarchy |
| Tenant Scoping | ✅ Complete | `services/tools/permissions.py` | Tenant-level overrides |
| Rate Limiting | ✅ Complete | `services/tools/executor.py` | Redis-based rate limiting |

### 1.3 Audit Logging
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Audit Logger | ✅ Complete | `services/tools/audit.py` | Full call trace with redaction |
| Audit Models | ✅ Complete | `services/tools/audit.py` | SQLAlchemy models with indexes |
| Audit Query | ✅ Complete | `services/tools/audit.py` | Query by user, tool, execution |

**Acceptance Criteria**:
- [x] Tools are registered with metadata (name, description, params, permissions)
- [x] Tool execution is tenant-scoped and permission-checked
- [x] All tool calls are audit-logged with inputs/outputs
- [x] Rate limiting per user/tenant
- [x] Timeout and error handling

---

## Phase 2: RAG Service
**Status**: ✅ Complete

### 2.1 Indexing Pipeline
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Code Indexer | ✅ Complete | `services/rag/indexers.py` | AST-aware chunking + language detection |
| Doc Indexer | ✅ Complete | `services/rag/indexers.py` | Markdown/README with title extraction |
| Ticket Indexer | ✅ Complete | `services/rag/indexers.py` | Jira/Linear/GitHub Issues + comments |
| Incident Indexer | ✅ Complete | `services/rag/indexers.py` | Postmortems, RCA, timelines |

### 2.2 Retrieval Engine
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Hybrid Retriever | ✅ Complete | `services/rag/retrieval.py` | RRF fusion of keyword + vector |
| Cross-Encoder Reranker | ✅ Complete | `services/rag/retrieval.py` | Optional reranking |
| Context Builder | ✅ Complete | `services/rag/context_builder.py` | Token-aware context assembly |

### 2.3 Vector Store
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Embeddings Service | ✅ Complete | `services/rag/embeddings.py` | OpenAI + Voyage + fallbacks |
| Vector Store | ✅ Complete | `services/rag/vector_store.py` | Qdrant backend with tenant isolation |
| Code Chunker | ✅ Complete | `services/rag/chunking.py` | Language-aware AST chunking |

**Acceptance Criteria**:
- [x] Index code with AST-aware chunking
- [x] Index docs, tickets, PR reviews, incidents
- [x] Hybrid search (BM25 + vector)
- [x] Reranking for relevance
- [x] Tenant-isolated indices
- [x] Incremental updates on webhooks

---

## Phase 3: MCP Integration Layer
**Status**: ✅ Complete

### 3.1 MCP Servers (Expose NexusAI capabilities)
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| MCP Protocol | ✅ Complete | `services/mcp/protocol.py` | Full JSON-RPC implementation |
| MCP Server | ✅ Complete | `services/mcp/server.py` | Tools, resources, prompts |
| CodeSearchHandler | ✅ Complete | `services/mcp/server.py` | Code search via MCP |
| FileReadHandler | ✅ Complete | `services/mcp/server.py` | File access via MCP |
| CILogsHandler | ✅ Complete | `services/mcp/server.py` | CI/CD logs via MCP |

### 3.2 MCP Client (Consume external tools)
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| MCP Client | ✅ Complete | `services/mcp/client.py` | Stdio + WebSocket transport |
| Server Registry | ✅ Complete | `services/mcp/client.py` | Multi-server management |
| Tool Discovery | ✅ Complete | `services/mcp/client.py` | Auto-discover tools |

**Acceptance Criteria**:
- [x] MCP servers expose NexusAI capabilities
- [x] External LLM clients can connect (Claude, Cursor, etc.)
- [x] MCP client can consume external MCP servers
- [x] Authentication & tenant isolation
- [x] Tool call routing through MCP

---

## Phase 4: Agent Orchestration
**Status**: ✅ Complete

### 4.1 LangGraph-Style Orchestration
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Agent Graph | ✅ Complete | `services/agents/orchestration/graph.py` | Node types: action, tool, LLM, conditional, parallel, human |
| Agent State | ✅ Complete | `services/agents/orchestration/state.py` | Messages, tool calls, errors, approvals |
| State Store | ✅ Complete | `services/agents/orchestration/state.py` | Persistent storage with checkpointing |
| Checkpoint Manager | ✅ Complete | `services/agents/orchestration/state.py` | Version-based checkpoints, rollback |
| Workflow Engine | ✅ Complete | `services/agents/orchestration/workflow.py` | Registration, execution, resume, cancel |
| Human-in-Loop | ✅ Complete | `services/agents/orchestration/human_loop.py` | Approval requests, expiration, notifications |

### 4.2 Built-in Agents
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| PR Review Agent | ✅ Complete | `services/agents/pr_review/` | Diff analysis, risk assessment, review generation |
| Diff Analyzer | ✅ Complete | `services/agents/pr_review/analyzer.py` | Security, performance, maintainability patterns |
| Review Generator | ✅ Complete | `services/agents/pr_review/reviewer.py` | Comments, summary, GitHub formatting |

### 4.3 Workflow Features
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Conditional Branching | ✅ Complete | `services/agents/orchestration/graph.py` | Branch based on conditions |
| Parallel Execution | ✅ Complete | `services/agents/orchestration/graph.py` | Execute branches concurrently |
| Subgraph Composition | ✅ Complete | `services/agents/orchestration/graph.py` | Nested workflow graphs |

**Acceptance Criteria**:
- [x] LangGraph-style workflow execution
- [x] Durable checkpoints for long-running tasks
- [x] Human-in-the-loop approval gates
- [x] Workflow registration and management
- [x] PR Review Agent with diff analysis

---

## Phase 5: Model Router Service
**Status**: ✅ Complete

### 5.1 Router Core
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Router Engine | ✅ Complete | `services/llm_router/engine.py` | 5 routing strategies |
| Model Registry | ✅ Complete | `services/llm_router/registry.py` | OpenAI + Anthropic models |
| Cost Tracker | ✅ Complete | `services/llm_router/cost.py` | Per-tenant cost tracking |
| Health Tracking | ✅ Complete | `services/llm_router/engine.py` | Auto-failover on errors |

### 5.2 Optimizations
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Semantic Cache | ✅ Complete | `services/llm_router/cache.py` | TTL + similarity matching |
| Budget Management | ✅ Complete | `services/llm_router/cost.py` | Monthly budgets per tenant |
| Usage Reports | ✅ Complete | `services/llm_router/cost.py` | By model, user, task |

**Acceptance Criteria**:
- [x] Route requests by task type
- [x] Automatic fallback on failures
- [x] Semantic caching for repeated queries
- [x] Cost tracking per tenant
- [x] Multiple provider support (OpenAI, Anthropic, etc.)

---

## Phase 6: Code Sandbox Service
**Status**: ✅ Complete

### 6.1 Sandbox Runtime
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Container Manager | ✅ Complete | `services/sandbox/containers.py` | Ephemeral Docker containers |
| Container Config | ✅ Complete | `services/sandbox/containers.py` | Memory, CPU, network, security |
| Sandbox Executor | ✅ Complete | `services/sandbox/executor.py` | Multi-language code execution |
| Resource Limits | ✅ Complete | `services/sandbox/containers.py` | CPU shares, memory limits, timeouts |

### 6.2 Supported Operations
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Test Runner | ✅ Complete | `services/sandbox/runners.py` | pytest, Jest support |
| Linter Runner | ✅ Complete | `services/sandbox/runners.py` | Ruff, ESLint support |
| Build Runner | ✅ Complete | `services/sandbox/runners.py` | Python/npm package building |
| REPL Runner | ✅ Complete | `services/sandbox/runners.py` | Expression evaluation |

### 6.3 Multi-Language Support
| Language | Status | Runtime |
|----------|--------|---------|
| Python | ✅ | python:3.12-slim |
| JavaScript | ✅ | node:22-slim |
| TypeScript | ✅ | node:22-slim |
| Go | ✅ | golang:1.21-alpine |
| Rust | ✅ | rust:1.75-slim |
| Java | ✅ | eclipse-temurin:21-jdk |
| Ruby | ✅ | ruby:3.3-slim |

**Acceptance Criteria**:
- [x] Ephemeral container execution
- [x] Strict network isolation
- [x] Resource quotas per tenant
- [x] Artifact capture
- [x] Timeout enforcement
- [x] Multi-language support

---

## Phase 7: Prompt/Policy/Governance
**Status**: ✅ Complete

### 7.1 Prompt Management
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Template Engine | ✅ Complete | `services/prompts/registry.py` | Version-controlled prompts |
| Variable Injection | ✅ Complete | `services/prompts/variables.py` | Safe variable substitution with validation |
| A/B Testing | ✅ Complete | `services/prompts/experiments.py` | Full experimentation framework |

### 7.2 Content Filtering
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| PII Detector | ✅ Complete | `services/guardrails/pii.py` | Detect PII |
| Secret Filter | ✅ Complete | `services/guardrails/secrets.py` | 15+ secret patterns (AWS, GCP, GitHub, etc.) |
| Content Filter | ✅ Complete | `services/guardrails/content_filter.py` | Safety checks |
| Output Redactor | ✅ Complete | `services/guardrails/redactor.py` | Pipeline-based redaction |

### 7.3 Compliance
| Component | Status | File | Notes |
|-----------|--------|------|-------|
| SOC2 Logging | ✅ Complete | `services/compliance/soc2.py` | Audit trails |
| GDPR Handler | ✅ Complete | `services/compliance/gdpr.py` | Data handling |
| HIPAA Handler | ✅ Complete | `services/compliance/hipaa/` | PHI protection |

**Acceptance Criteria**:
- [x] Version-controlled prompt templates
- [x] Safe variable injection with type validation
- [x] Prompt A/B testing with statistical significance
- [x] PII/secret detection and redaction
- [x] Full audit trail of LLM interactions
- [x] RBAC for model access
- [x] Compliance reporting

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend / IDE / CLI                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API Gateway                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ /chat       │  │ /agents     │  │ /tools      │  │ /mcp       │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Model Router   │    │ Tool Executor   │    │ Agent Orchestr. │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │ OpenAI    │  │    │  │ Registry  │  │    │  │ LangGraph │  │
│  │ Anthropic │  │    │  │ RBAC      │  │    │  │ Workflows │  │
│  │ HuggingFace│ │    │  │ Audit     │  │    │  │ Checkpts  │  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RAG Service   │    │  MCP Layer      │    │ Code Sandbox    │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │ Vector DB │  │    │  │ Servers   │  │    │  │ Containers│  │
│  │ Embeddings│  │    │  │ Client    │  │    │  │ Isolation │  │
│  │ Reranker  │  │    │  │ Protocol  │  │    │  │ Quotas    │  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Data & External Services                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐│
│  │PostgreSQL│  │ Redis    │  │ Qdrant   │  │ GitHub   │  │ Jira  ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └───────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Changelog

#### 2026-01-19
- Created LLM Services roadmap document
- Defined 7 major service phases
- Identified implementation priorities
- Mapped existing components
- ✅ **Phase 1 Complete**: Tool Calling Runtime
  - Tool base classes with OpenAI/Anthropic format conversion
  - Registry with category/tag filtering
  - Executor with RBAC, rate limiting, audit logging
  - 9 built-in tools (code search, diff, file read, static analysis, CI logs, create PR, Jira)
- ✅ **Phase 2 Complete**: RAG Service
  - Multi-source indexers (code, docs, tickets, incidents)
  - AST-aware code chunking by language
  - Hybrid retrieval with RRF fusion
  - Cross-encoder reranking
  - Token-aware context building
- ✅ **Phase 3 Complete**: MCP Integration
  - Full MCP protocol implementation
  - Server for exposing NexusAI tools
  - Client for consuming external MCP servers
  - Stdio + WebSocket transports
- ✅ **Phase 5 Complete**: Model Router
  - Multi-strategy routing (quality, cost, latency, balanced)
  - Model health tracking with auto-failover
  - Semantic caching
  - Per-tenant cost tracking and budgets
- ✅ **Phase 4 Complete**: Agent Orchestration (LangGraph-style)
  - Graph-based workflow with node types: action, tool, LLM, conditional, parallel, human
  - Durable state with checkpointing and rollback
  - Human-in-the-loop approval system with expiration
  - Workflow engine with registration, execution, resume
  - PR Review Agent with diff analysis and risk assessment
- ✅ **Phase 6 Complete**: Code Sandbox Service
  - Container manager with Docker integration
  - Multi-language support (Python, JS, TS, Go, Rust, Java, Ruby)
  - Test/Lint/Build/REPL runners
  - Resource isolation (CPU, memory, network)
  - Artifact capture and timeout enforcement
- ✅ **Phase 7 Complete**: Prompt/Policy/Governance
  - Variable injection with type validation and sanitization
  - Prompt A/B testing with traffic splitting and statistical analysis
  - Secret detection (15+ patterns: AWS, GCP, GitHub, Slack, JWT, etc.)
  - Output redaction pipeline with PII/secret/internal info filtering
  - Full compliance integration (SOC2, GDPR, HIPAA)

**🎉 All 7 phases complete!**

---

## Summary of Implemented Services

| Service | Files | Key Features |
|---------|-------|--------------|
| Tool Calling | `services/tools/` | Registry, executor, RBAC, audit, 9 built-in tools |
| RAG | `services/rag/` | Embeddings, vector store, chunking, retrieval, indexers |
| MCP | `services/mcp/` | Protocol, server, client, tool handlers |
| Agent Orchestration | `services/agents/orchestration/` | Graph, state, workflow engine, human-in-loop |
| PR Review | `services/agents/pr_review/` | Diff analyzer, risk assessment, review generator |
| Model Router | `services/llm_router/` | Registry, routing engine, cache, cost tracking |
| Code Sandbox | `services/sandbox/` | Containers, executor, test/lint/build runners |
| Prompts | `services/prompts/` | Variables, A/B testing, experiments |
| Guardrails | `services/guardrails/` | Secrets, redactor, PII, content filter |

**Total: 40+ new service files implementing complete LLM infrastructure**

