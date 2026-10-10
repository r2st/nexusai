"""
LangServe API endpoints for deploying NexusAI Chat as a LangChain service.

LangServe provides standardized REST API endpoints for LangChain runnables,
including streaming, batch processing, and a playground UI.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import json
import structlog

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.langserve.runnable import ChatRunnable

logger = structlog.get_logger()

router = APIRouter()


class InvokeRequest(BaseModel):
    """Request model for LangServe invoke endpoint."""
    input: dict[str, Any] | str
    config: dict[str, Any] | None = None


class StreamRequest(BaseModel):
    """Request model for LangServe stream endpoint."""
    input: dict[str, Any] | str
    config: dict[str, Any] | None = None


class BatchRequest(BaseModel):
    """Request model for LangServe batch endpoint."""
    inputs: list[dict[str, Any] | str]
    config: dict[str, Any] | None = None


@router.get("/health")
async def langserve_health():
    """Health check for LangServe endpoints."""
    return {"status": "healthy", "service": "langserve"}


@router.get("/info")
async def langserve_info():
    """Get information about the LangServe deployment."""
    return {
        "name": "NexusAI Chat Service",
        "version": "1.0.0",
        "description": "NexusAI chat service with MCP tool support, exposed via LangServe",
        "capabilities": [
            "Streaming responses",
            "MCP tool integration",
            "Multi-provider LLM support",
            "Conversation management",
        ],
        "endpoints": {
            "invoke": "/api/v1/langserve/chat/invoke",
            "stream": "/api/v1/langserve/chat/stream",
            "batch": "/api/v1/langserve/chat/batch",
        },
    }


@router.post("/chat/invoke")
async def langserve_invoke(
    request: InvokeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    LangServe-compatible invoke endpoint.
    
    POST /api/v1/langserve/chat/invoke
    Body: {"input": {"message": "Hello"}, "config": {}}
    """
    try:
        runnable = ChatRunnable(
            db=db,
            user_id=str(user.id),
            enable_mcp_tools=True,
        )
        
        result = await runnable.ainvoke(request.input, request.config)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error("LangServe invoke failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Request failed. Please try again later.",
        )


@router.post("/chat/stream")
async def langserve_stream(
    request: StreamRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    LangServe-compatible stream endpoint.
    
    POST /api/v1/langserve/chat/stream
    Body: {"input": {"message": "Hello"}, "config": {}}
    
    Returns Server-Sent Events (SSE) stream.
    """
    async def generate():
        try:
            runnable = ChatRunnable(
                db=db,
                user_id=str(user.id),
                enable_mcp_tools=True,
            )
            
            async for chunk in runnable.astream(request.input, request.config):
                # Format as SSE
                data = json.dumps(chunk)
                yield f"data: {data}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("LangServe stream failed", error=str(e), exc_info=True)
            error_chunk = {"error": "Streaming failed. Please try again.", "type": "error"}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/batch")
async def langserve_batch(
    request: BatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    LangServe-compatible batch endpoint.
    
    POST /api/v1/langserve/chat/batch
    Body: {"inputs": [{"message": "Hello"}, {"message": "Hi"}], "config": {}}
    
    Processes multiple inputs in parallel.
    """
    try:
        runnable = ChatRunnable(
            db=db,
            user_id=str(user.id),
            enable_mcp_tools=True,
        )
        
        # Process inputs in parallel
        import asyncio
        results = await asyncio.gather(
            *[runnable.ainvoke(input_data, request.config) for input_data in request.inputs],
            return_exceptions=True,
        )
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "error": str(result),
                    "input_index": i,
                })
            else:
                formatted_results.append(result)
        
        return JSONResponse(content={"outputs": formatted_results})
    except Exception as e:
        logger.error("LangServe batch failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch processing failed. Please try again later.",
        )


@router.get("/chat/playground")
async def langserve_playground():
    """
    LangServe playground UI endpoint.
    
    Returns a simple HTML page for testing the chat service.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NexusAI Chat - LangServe Playground</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                border-radius: 8px;
                padding: 24px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 { color: #333; margin-top: 0; }
            .input-group {
                margin-bottom: 16px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: #555;
            }
            textarea {
                width: 100%;
                min-height: 100px;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: monospace;
                font-size: 14px;
            }
            button {
                background: #6366f1;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
            }
            button:hover { background: #4f46e5; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            .output {
                margin-top: 24px;
                padding: 16px;
                background: #f9f9f9;
                border-radius: 4px;
                border: 1px solid #ddd;
                min-height: 100px;
                white-space: pre-wrap;
                font-family: monospace;
                font-size: 14px;
            }
            .error {
                color: #dc2626;
                background: #fee2e2;
                padding: 12px;
                border-radius: 4px;
                margin-top: 16px;
            }
            .endpoint-info {
                background: #e0e7ff;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 24px;
                font-size: 14px;
            }
            .endpoint-info code {
                background: white;
                padding: 2px 6px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 NexusAI Chat - LangServe Playground</h1>
            
            <div class="endpoint-info">
                <strong>Endpoints:</strong><br>
                • <code>POST /api/v1/langserve/chat/invoke</code> - Non-streaming<br>
                • <code>POST /api/v1/langserve/chat/stream</code> - Streaming<br>
                • <code>POST /api/v1/langserve/chat/batch</code> - Batch processing
            </div>
            
            <div class="input-group">
                <label for="message">Message:</label>
                <textarea id="message" placeholder='Enter a message or JSON: {"message": "Hello, how can you help?"}'>{"message": "Hello! What tools do you have available?"}</textarea>
            </div>
            
            <div>
                <button onclick="invoke()">Invoke (Non-streaming)</button>
                <button onclick="stream()">Stream</button>
                <button onclick="clearOutput()">Clear</button>
            </div>
            
            <div id="output" class="output">Output will appear here...</div>
            <div id="error" class="error" style="display: none;"></div>
        </div>
        
        <script>
            const API_BASE = '/api/v1/langserve';
            
            async function invoke() {
                const messageEl = document.getElementById('message');
                const outputEl = document.getElementById('output');
                const errorEl = document.getElementById('error');
                
                errorEl.style.display = 'none';
                outputEl.textContent = 'Processing...';
                
                try {
                    let input = messageEl.value.trim();
                    // Try to parse as JSON, fallback to string
                    try {
                        input = JSON.parse(input);
                    } catch {
                        input = { message: input };
                    }
                    
                    const response = await fetch(`${API_BASE}/chat/invoke`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
                        },
                        body: JSON.stringify({ input }),
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
                    }
                    
                    const result = await response.json();
                    outputEl.textContent = JSON.stringify(result, null, 2);
                } catch (error) {
                    errorEl.textContent = `Error: ${error.message}`;
                    errorEl.style.display = 'block';
                    outputEl.textContent = '';
                }
            }
            
            async function stream() {
                const messageEl = document.getElementById('message');
                const outputEl = document.getElementById('output');
                const errorEl = document.getElementById('error');
                
                errorEl.style.display = 'none';
                outputEl.textContent = '';
                
                try {
                    let input = messageEl.value.trim();
                    try {
                        input = JSON.parse(input);
                    } catch {
                        input = { message: input };
                    }
                    
                    const response = await fetch(`${API_BASE}/chat/stream`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
                        },
                        body: JSON.stringify({ input }),
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
                    }
                    
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let fullContent = '';
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\n');
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const data = line.slice(6);
                                if (data === '[DONE]') continue;
                                
                                try {
                                    const parsed = JSON.parse(data);
                                    if (parsed.content) {
                                        fullContent += parsed.content;
                                        outputEl.textContent = fullContent;
                                    }
                                } catch {
                                    // Ignore parse errors
                                }
                            }
                        }
                    }
                } catch (error) {
                    errorEl.textContent = `Error: ${error.message}`;
                    errorEl.style.display = 'block';
                }
            }
            
            function clearOutput() {
                document.getElementById('output').textContent = 'Output will appear here...';
                document.getElementById('error').style.display = 'none';
            }
        </script>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)
