"""
JARVIS AI - Main FastAPI Server
The entry point for the JARVIS AI backend.
Handles WebSocket streaming, REST APIs, and serves the frontend.
"""

import asyncio
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from memory_service import (
    init_db, close_db, get_all_memories, delete_memory,
    get_user_profile, update_user_profile, store_memory
)
from orchestrator import process_message, get_suggestion_chips, classify_intent
from emotion_engine import detect_emotion
from models import MemoryRecord
from productivity_service import init_prod_db

# ─── App Setup ─────────────────────────────────────────────────
app = FastAPI(
    title="JARVIS AI - Personal AI Assistant",
    version="1.0.0",
    description="Next-generation Hinglish AI Assistant with 4-layer memory"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Startup ──────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()
    print("✨ JARVIS AI Backend Started! Memory system initialized.")
    await init_prod_db()
    print("📈 Productivity system initialized.")
    print("🧠 Database: jarvis_memory.db")
    print("🌐 Frontend: http://localhost:8000")


@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown."""
    await close_db()
    print("👋 JARVIS AI shutting down. Database closed.")


# ─── Health Check ─────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "JARVIS AI", "version": "1.0.0"}


# ─── Serve Frontend ──────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/styles.css")
async def serve_css():
    return FileResponse(os.path.join(FRONTEND_DIR, "styles.css"), media_type="text/css")


@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(FRONTEND_DIR, "app.js"), media_type="application/javascript")


# ─── Auth API ─────────────────────────────────────────────────
@app.post("/api/v1/auth/login")
async def login(data: dict):
    """Simple auth for MVP — no real auth, just session creation."""
    return JSONResponse({
        "access_token": "jarvis_mvp_token",
        "user": {"id": "default_user", "tier": "pro"}
    })


# ─── Memory APIs ──────────────────────────────────────────────
@app.get("/api/v1/memory")
async def get_memories(type: str = None):
    """Fetch all memories for the dashboard."""
    memories = await get_all_memories("default_user", type)
    return {"data": memories, "total": len(memories)}


@app.delete("/api/v1/memory/{memory_id}")
async def remove_memory(memory_id: str):
    """Delete a specific memory."""
    await delete_memory(memory_id)
    return JSONResponse(status_code=204, content=None)


@app.post("/api/v1/memory")
async def add_memory(data: dict):
    """Manually add a memory."""
    memory = MemoryRecord(
        content=data.get("content", ""),
        type=data.get("type", "semantic"),
        tags=data.get("tags", []),
        source="explicit_statement"
    )
    await store_memory(memory)
    return {"memory_id": memory.memory_id, "status": "stored"}


# ─── User Profile APIs ───────────────────────────────────────
@app.get("/api/v1/profile")
async def get_profile():
    """Get user profile."""
    profile = await get_user_profile("default_user")
    return profile


@app.post("/api/v1/profile")
async def save_profile(data: dict):
    """Update user profile (onboarding)."""
    await update_user_profile(
        "default_user",
        name=data.get("name"),
        preferences=data.get("preferences"),
        onboarded=data.get("onboarding_complete")
    )
    return {"status": "updated"}


# ─── WebSocket Chat (Real-time Streaming) ─────────────────────
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming conversation.
    Protocol based on 06-api-contracts.md:
    
    Client → Server: { "event": "user_message", "payload": { "text": "...", "session_id": "..." } }
    Server → Client: 
      1. { "event": "processing_started", "payload": { "intent": "...", "emotion": "..." } }
      2. { "event": "text_stream", "payload": { "chunk": "..." } }
      3. { "event": "stream_complete", "payload": { "full_text": "...", "suggestions": [...] } }
    """
    await websocket.accept()
    session_id = "default_session"

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()
            data = json.loads(raw)

            event = data.get("event", "user_message")
            payload = data.get("payload", {})

            if event == "user_message":
                user_text = payload.get("text", "")
                session_id = payload.get("session_id", session_id)

                if not user_text.strip():
                    continue

                # Step 1: Send processing acknowledgment
                intent = classify_intent(user_text)
                emotion = detect_emotion(user_text)

                await websocket.send_json({
                    "event": "processing_started",
                    "payload": {
                        "intent": intent,
                        "emotion": emotion.emotion,
                        "emotion_confidence": emotion.confidence
                    }
                })

                # Step 2: Stream response tokens
                full_response = ""
                async for chunk in process_message(user_text, session_id):
                    full_response += chunk
                    await websocket.send_json({
                        "event": "text_stream",
                        "payload": {"chunk": chunk}
                    })

                # Step 3: Send completion with suggestions
                suggestions = await get_suggestion_chips(intent, emotion.emotion)
                await websocket.send_json({
                    "event": "stream_complete",
                    "payload": {
                        "full_text": full_response,
                        "suggestions": suggestions,
                        "intent": intent,
                        "emotion": emotion.emotion
                    }
                })

            elif event == "onboarding":
                # Handle onboarding data
                name = payload.get("name", "")
                preferences = payload.get("preferences", {})
                await update_user_profile(
                    "default_user",
                    name=name,
                    preferences=preferences,
                    onboarded=True
                )
                await websocket.send_json({
                    "event": "onboarding_complete",
                    "payload": {"name": name}
                })

    except WebSocketDisconnect:
        print(f"🔌 Client disconnected (session: {session_id})")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_json({
                "event": "error",
                "payload": {"message": str(e)[:200]}
            })
        except:
            pass


# ─── Run Server ───────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
