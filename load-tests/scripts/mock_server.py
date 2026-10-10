"""
NexusAI Mock API Server
========================
Lightweight FastAPI server that simulates the real NexusAI backend
for load testing validation. Mimics all endpoints targeted by the
load test suite with realistic response shapes and latencies.

Usage:
    uvicorn mock_server:app --host 0.0.0.0 --port 8000 --workers 4
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="NexusAI Mock Server", version="1.0.0-mock")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-Memory State ───────────────────────────────────────────────────────────

# Simulated JWT tokens
VALID_TOKENS: dict[str, dict] = {}

# Test users (matches dev-seeded users)
TEST_USERS = {
    "admin@nexusai.dev": {"password": "admin123", "role": "admin", "id": str(uuid.uuid4()), "username": "admin"},
    "user@nexusai.dev": {"password": "user123", "role": "user", "id": str(uuid.uuid4()), "username": "testuser"},
    "viewer@nexusai.dev": {"password": "viewer123", "role": "viewer", "id": str(uuid.uuid4()), "username": "viewer"},
}

# Pre-generated data
CONVERSATIONS = [
    {"id": str(uuid.uuid4()), "title": f"Conversation {i}", "model_provider": "openai",
     "model_name": "gpt-4", "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat()}
    for i in range(25)
]

DOCUMENTS = [
    {"id": str(uuid.uuid4()), "filename": f"doc_{i}.pdf", "file_type": "pdf",
     "file_size": random.randint(10000, 5000000), "created_at": datetime.utcnow().isoformat()}
    for i in range(20)
]

ORGANIZATIONS = [
    {"id": str(uuid.uuid4()), "name": f"Org {i}", "slug": f"org-{i}",
     "tier": random.choice(["free", "starter", "professional", "enterprise"]),
     "max_members": random.choice([5, 25, 100, 500]), "created_at": datetime.utcnow().isoformat()}
    for i in range(5)
]


# ─── Models ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ConversationCreate(BaseModel):
    title: str
    model_provider: Optional[str] = "openai"
    model_name: Optional[str] = "gpt-4"

class MessageCreate(BaseModel):
    content: str
    role: Optional[str] = "user"

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


# ─── Auth Helpers ───────────────────────────────────────────────────────────────

def verify_token(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.replace("Bearer ", "")
    user = VALID_TOKENS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

def generate_token() -> str:
    return f"mock_jwt_{uuid.uuid4().hex}"


# ─── Health Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/healthz")
@app.get("/api/health")
@app.get("/api/healthz")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "version": "1.0.0-mock"}


# ─── Auth Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    user = TEST_USERS.get(request.email)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = generate_token()
    refresh_token = generate_token()

    VALID_TOKENS[access_token] = {
        "id": user["id"],
        "email": request.email,
        "role": user["role"],
        "username": user["username"],
    }
    VALID_TOKENS[refresh_token] = VALID_TOKENS[access_token]

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": request.email,
            "role": user["role"],
            "username": user["username"],
        },
    }

@app.post("/api/v1/auth/refresh")
async def refresh_token(request: RefreshRequest):
    user = VALID_TOKENS.get(request.refresh_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access = generate_token()
    new_refresh = generate_token()
    VALID_TOKENS[new_access] = user
    VALID_TOKENS[new_refresh] = user

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }

@app.post("/api/v1/auth/register")
async def register():
    return {
        "id": str(uuid.uuid4()),
        "email": f"user_{uuid.uuid4().hex[:6]}@example.com",
        "access_token": generate_token(),
    }


# ─── Conversation Endpoints ────────────────────────────────────────────────────

@app.get("/api/v1/chat/conversations")
async def list_conversations(
    authorization: Optional[str] = Header(None),
    limit: int = Query(20),
    offset: int = Query(0),
):
    verify_token(authorization)
    return CONVERSATIONS[offset:offset + limit]

@app.post("/api/v1/chat/conversations")
async def create_conversation(
    request: ConversationCreate,
    authorization: Optional[str] = Header(None),
):
    verify_token(authorization)
    conv = {
        "id": str(uuid.uuid4()),
        "title": request.title,
        "model_provider": request.model_provider,
        "model_name": request.model_name,
        "created_at": datetime.utcnow().isoformat(),
    }
    CONVERSATIONS.append(conv)
    return conv

@app.post("/api/v1/chat/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: MessageCreate,
    authorization: Optional[str] = Header(None),
):
    verify_token(authorization)
    return {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "content": f"Mock response to: {request.content[:50]}...",
        "role": "assistant",
        "created_at": datetime.utcnow().isoformat(),
    }


# ─── Document Endpoints ────────────────────────────────────────────────────────

@app.get("/api/v1/documents")
async def list_documents(
    authorization: Optional[str] = Header(None),
    limit: int = Query(20),
    offset: int = Query(0),
):
    verify_token(authorization)
    return DOCUMENTS[offset:offset + limit]

@app.post("/api/v1/documents/search")
async def search_documents(
    request: SearchRequest,
    authorization: Optional[str] = Header(None),
):
    verify_token(authorization)
    results = random.sample(DOCUMENTS, min(request.limit, len(DOCUMENTS)))
    for r in results:
        r["relevance_score"] = round(random.uniform(0.6, 0.99), 3)
    return {"results": results, "query": request.query, "total": len(results)}


# ─── Metrics Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/v1/metrics/dora/{project_name}")
async def get_dora_metrics(
    project_name: str,
    authorization: Optional[str] = Header(None),
    period: str = Query("30d"),
):
    verify_token(authorization)
    return {
        "project": project_name,
        "period": period,
        "metrics": {
            "deployment_frequency": 4.5,
            "lead_time_for_changes_hours": 12.3,
            "mean_time_to_recovery_hours": 2.1,
            "change_failure_rate": 0.05,
        },
        "trend": "stable",
        "computed_at": datetime.utcnow().isoformat(),
    }

@app.get("/api/v1/metrics/space/{project_name}")
async def get_space_metrics(
    project_name: str,
    authorization: Optional[str] = Header(None),
    period: str = Query("30d"),
):
    verify_token(authorization)
    return {
        "project": project_name,
        "period": period,
        "metrics": {
            "satisfaction": 4.2,
            "performance": 85.0,
            "activity": 120,
            "communication": 4.0,
            "efficiency": 0.82,
        },
        "computed_at": datetime.utcnow().isoformat(),
    }


# ─── Organization Endpoints ────────────────────────────────────────────────────

@app.get("/api/v1/organizations")
async def list_organizations(authorization: Optional[str] = Header(None)):
    verify_token(authorization)
    return ORGANIZATIONS

@app.get("/api/v1/organizations/{org_id}")
async def get_organization(org_id: str, authorization: Optional[str] = Header(None)):
    verify_token(authorization)
    for org in ORGANIZATIONS:
        if org["id"] == org_id:
            return org
    raise HTTPException(status_code=404, detail="Organization not found")


# ─── WebSocket Endpoint ────────────────────────────────────────────────────────

@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    if not token or token not in VALID_TOKENS:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            import json
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "unknown")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": msg.get("timestamp")})
                elif msg_type == "heartbeat":
                    await websocket.send_json({"type": "heartbeat_ack", "timestamp": msg.get("timestamp")})
                elif msg_type == "chat_message":
                    await asyncio.sleep(random.uniform(0.01, 0.05))
                    await websocket.send_json({
                        "type": "chat_response",
                        "content": "Mock streaming response...",
                        "timestamp": msg.get("timestamp"),
                    })
                else:
                    await websocket.send_json({"type": "ack", "original_type": msg_type})
            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON")
    except WebSocketDisconnect:
        pass


# ─── Token cleanup (prevent memory leak during load tests) ─────────────────────

@app.on_event("startup")
async def start_token_cleanup():
    async def cleanup_loop():
        while True:
            await asyncio.sleep(60)
            # Keep only last 50K tokens to prevent OOM
            if len(VALID_TOKENS) > 50000:
                keys = list(VALID_TOKENS.keys())
                for k in keys[:len(keys) - 25000]:
                    VALID_TOKENS.pop(k, None)
    asyncio.create_task(cleanup_loop())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)
