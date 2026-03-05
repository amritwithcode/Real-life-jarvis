"""
JARVIS AI - Data Models
Pydantic models and database schemas for the JARVIS AI assistant.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
import uuid


# ─── Auth Models ───────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user: dict


# ─── Memory Models ─────────────────────────────────────────────
class MemoryRecord(BaseModel):
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    type: Literal["working", "episodic", "semantic", "procedural"] = "semantic"
    content: str
    confidence: float = 0.9
    source: Literal["explicit_statement", "inferred", "external"] = "inferred"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = Field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    tags: List[str] = []


class MemoryResponse(BaseModel):
    data: List[MemoryRecord]
    total: int


# ─── Chat Models ───────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class WebSocketInput(BaseModel):
    event: str = "user_message"
    payload: dict


class WebSocketOutput(BaseModel):
    event: str
    payload: dict


# ─── Emotion Models ────────────────────────────────────────────
class EmotionState(BaseModel):
    emotion: str = "neutral"
    confidence: float = 0.5
    frustration_level: float = 0.0
    energy_level: float = 0.5
    stress_level: float = 0.0
    tone_instruction: str = "balanced and friendly"


# ─── Session Models ────────────────────────────────────────────
class UserSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    user_name: str = ""
    preferences: dict = {}
    onboarding_complete: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
