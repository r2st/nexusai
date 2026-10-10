"""API routes."""

from fastapi import APIRouter

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.websocket import router as websocket_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.organizations import router as organizations_router
from app.api.ai_analytics import router as ai_analytics_router
from app.api.metrics import router as metrics_router
from app.api.blueprints import router as blueprints_router
from app.api.tokens import router as tokens_router
from app.api.agents import router as agents_router
from app.api.knowledge_graph import router as knowledge_graph_router
from app.api.devops_agents import router as devops_agents_router
from app.api.openapi_actions import router as openapi_actions_router
from app.api.trials import router as trials_router
from app.api.subscriptions import router as subscriptions_router
from app.api.setup_chatbot import router as setup_chatbot_router
from app.api.llm import router as llm_router
from app.api.costs import router as costs_router
from app.api.hallucination import router as hallucination_router
from app.api.ragas import router as ragas_router
from app.api.code_review import router as code_review_router
from app.api.predictive import router as predictive_router
from app.api.security import router as security_router
from app.api.extensions import router as extensions_router
from app.api.quality_gate import router as quality_gate_router
from app.api.notifications import router as notifications_router
from app.api.events import router as events_router
from app.api.rollups import router as rollups_router
from app.api.query import router as query_router
from app.api.compliance import router as compliance_router
from app.api.workflows import router as workflows_router
from app.api.hipaa import router as hipaa_router
from app.api.collaboration import router as collaboration_router
from app.api.residency import router as residency_router
from app.api.chatbot import router as chatbot_router
from app.api.audit import router as audit_router
from app.api.ide_mcp import router as ide_mcp_router
from app.api.scheduler import router as scheduler_router
from app.api.mcp_transport import include_mcp_transport_routes
from app.api.devlake import router as devlake_router
from app.api.langserve import router as langserve_router
from app.api.signed_urls import router as signed_urls_router
from app.api.grafana_rbac import router as grafana_rbac_router

api_router = APIRouter()

# Core routes
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(websocket_router, prefix="/ws", tags=["websocket"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])

# DevLake Analytics
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

# Multi-tenancy
api_router.include_router(organizations_router, prefix="/organizations", tags=["organizations"])

# AI Analytics (Cursor, Claude Code, Copilot, etc.)
api_router.include_router(ai_analytics_router, prefix="/ai-analytics", tags=["ai-analytics"])

# Engineering Metrics (DORA, SPACE, Business, Productivity)
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])

# Blueprint Pipeline Management
api_router.include_router(blueprints_router, prefix="/pipelines", tags=["pipelines"])

# Personal Access Tokens
api_router.include_router(tokens_router, prefix="/tokens", tags=["tokens"])

# Agents
api_router.include_router(agents_router)

# Knowledge Graph
api_router.include_router(knowledge_graph_router)

# DevOps Agents (DORA, Dashboard, Summary workflows)
api_router.include_router(devops_agents_router)

# OpenAPI Actions
api_router.include_router(openapi_actions_router)

# Trials and Subscriptions
api_router.include_router(trials_router, prefix="/trials", tags=["trials"])
api_router.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])

# Setup Assistant Chatbot
api_router.include_router(setup_chatbot_router)

# LLM Gateway
api_router.include_router(llm_router)

# Cost Analytics
api_router.include_router(costs_router)

# Hallucination Detection
api_router.include_router(hallucination_router)

# RAGAS - RAG Evaluation Framework
api_router.include_router(ragas_router)

# Code Review Automation
api_router.include_router(code_review_router)

# Predictive Analytics
api_router.include_router(predictive_router)

# Security Scanner & Secret Rotation
api_router.include_router(security_router)

# IDE Extension API
api_router.include_router(extensions_router)

# Quality Gate (CI/CD Integration)
api_router.include_router(quality_gate_router)

# Notifications (Slack, Teams, Discord, Email)
api_router.include_router(notifications_router)

# Event Ingestion Service
api_router.include_router(events_router, prefix="/events", tags=["events"])

# Precomputed Rollups (DORA/SPACE Metrics)
api_router.include_router(rollups_router, prefix="/rollups", tags=["rollups"])

# Query Gateway
api_router.include_router(query_router, prefix="/query", tags=["query"])

# Compliance (GDPR, SOC 2)
api_router.include_router(compliance_router)

# Workflow Automation Engine
api_router.include_router(workflows_router)

# HIPAA Compliance
api_router.include_router(hipaa_router)

# Real-time Collaboration
api_router.include_router(collaboration_router)

# Data Residency Controls
api_router.include_router(residency_router)

# Slack/Teams Chatbot
api_router.include_router(chatbot_router)

# Audit Logging & Approvals
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])

# IDE MCP Integration
api_router.include_router(ide_mcp_router)

# Background Agent Scheduler
api_router.include_router(scheduler_router)

# MCP HTTP Transport (for external LLM clients)
include_mcp_transport_routes(api_router)

# DevLake Pipeline Status (for frontend polling)
api_router.include_router(devlake_router)

# LangServe - LangChain-compatible API endpoints
api_router.include_router(langserve_router, prefix="/langserve", tags=["langserve"])

# Signed URLs - Secure file transfer
api_router.include_router(signed_urls_router, prefix="/signed-urls", tags=["signed-urls"])

# Grafana RBAC - Role-based access control for Grafana
api_router.include_router(grafana_rbac_router, prefix="/grafana/rbac", tags=["grafana-rbac"])
