---
sidebar_position: 2
---

# Agents

Agents are specialized workflows executed by the backend (and, in some cases, background workers) to solve domain-specific tasks such as DevOps metrics analysis.

## Typical capabilities

- DevOps metrics analysis (DORA, trends, benchmarks)
- Tool calling via MCP-style handlers
- Scheduled/background execution via the ARQ worker

## Where it lives in the codebase

- API layer: `backend/app/api/agents.py` and `backend/app/api/devops_agents.py`
- Agent implementations: `backend/app/services/agents/`
- Background execution: `backend/app/worker.py` (ARQ)

