"""
JARVIS AI - Memory Service
Implements the 4-Layer Memory System from the PRD:
  Layer 1: Working Memory (in-memory, session context)
  Layer 2: Episodic Memory (recent conversations, auto-summarized)
  Layer 3: Semantic Memory (long-term facts, permanent)
  Layer 4: Procedural Memory (user workflow patterns)

Uses a SINGLE shared SQLite connection with WAL mode to prevent 'database is locked' errors.
"""

import aiosqlite
import json
import uuid
import re
import os
from datetime import datetime
from typing import List, Optional
from models import MemoryRecord

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_memory.db")

# ─── Shared Database Connection ───────────────────────────────
_db_connection: aiosqlite.Connection = None


async def get_db() -> aiosqlite.Connection:
    """Get or create the shared database connection with WAL mode."""
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DB_PATH)
        _db_connection.row_factory = aiosqlite.Row
        # Enable WAL mode for concurrent reads
        await _db_connection.execute("PRAGMA journal_mode=WAL")
        await _db_connection.execute("PRAGMA busy_timeout=5000")
    return _db_connection


async def close_db():
    """Close the shared database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None


# ─── Fact Extraction Patterns ─────────────────────────────────
FACT_PATTERNS = [
    # Name patterns
    (r"(?:mera|my)\s+(?:naam|name)\s+(?:hai|is|h)\s+(\w+)", "identity", "name"),
    (r"(?:i am|i'm|main|mai)\s+(\w+)\b", "identity", "name"),
    (r"(?:call me|mujhe|mujhko)\s+(\w+)\s+(?:bolo|bula|kaho|call)", "identity", "name"),
    
    # Location patterns
    (r"(?:main|mai|i)\s+(?:rehta|rehti|live|stay|rahta|rahti)\s+(?:hoon|hu|hun|in)\s+(.+?)(?:\.|$)", "location", "residence"),
    (r"(?:mera|my)\s+(?:ghar|home|house)\s+(?:hai|is|h)\s+(?:in\s+)?(.+?)(?:\.|$)", "location", "home"),
    
    # Work patterns
    (r"(?:main|mai|i)\s+(?:kaam|work|job)\s+(?:karta|karti|krti|do)\s+(?:hoon|hu|hun|at|in|pe|par)\s+(.+?)(?:\.|$)", "work", "workplace"),
    (r"(?:mera|my)\s+(?:boss|manager)\s+(?:ka naam|is|hai)\s+(.+?)(?:\.|$)", "work", "boss"),
    
    # Preference patterns
    (r"(?:mujhe|i)\s+(?:pasand|like|love|prefer)\s+(?:hai|h|karta|karti)?\s*(.+?)(?:\.|$)", "preference", "likes"),
    (r"(?:meri|my)\s+(?:favourite|favorite|fav)\s+(.+?)\s+(?:hai|is|h)\s+(.+?)(?:\.|$)", "preference", "favorite"),
    
    # Relationship patterns
    (r"(?:mera|meri|my)\s+(bhai|brother|sister|behen|wife|husband|friend|dost)\s+(?:ka naam|is|hai)\s+(.+?)(?:\.|$)", "relationship", "family"),
    (r"(?:mera|meri|my)\s+(bhai|brother|sister|behen|wife|husband|friend|dost)\s+(.+?)(?:\.|$)", "relationship", "family"),
    
    # Age pattern
    (r"(?:meri|my)\s+(?:age|umar)\s+(?:hai|is|h)\s+(\d+)", "identity", "age"),
    (r"(?:i am|main|mai)\s+(\d+)\s+(?:years?|saal|sal)", "identity", "age"),
]


async def init_db():
    """Initialize SQLite database with memory tables."""
    db = await get_db()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
            user_id TEXT DEFAULT 'default_user',
            type TEXT CHECK(type IN ('working', 'episodic', 'semantic', 'procedural')),
            content TEXT NOT NULL,
            confidence REAL DEFAULT 0.9,
            source TEXT DEFAULT 'inferred',
            created_at TEXT,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]'
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_id TEXT DEFAULT 'default_user',
            role TEXT,
            content TEXT,
            emotion TEXT DEFAULT 'neutral',
            created_at TEXT
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            user_name TEXT DEFAULT '',
            preferences TEXT DEFAULT '{}',
            onboarding_complete INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    await db.commit()


# ─── Working Memory (Layer 1) ─────────────────────────────────
# In-memory storage for current session context
_working_memory: dict = {}  # session_id -> list of recent messages


def get_working_memory(session_id: str) -> list:
    """Get the last 50 exchanges for a session."""
    return _working_memory.get(session_id, [])[-50:]


def add_to_working_memory(session_id: str, role: str, content: str):
    """Add a message to working memory."""
    if session_id not in _working_memory:
        _working_memory[session_id] = []
    _working_memory[session_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    # Keep only last 50 exchanges
    if len(_working_memory[session_id]) > 100:
        _working_memory[session_id] = _working_memory[session_id][-50:]


# ─── Episodic Memory (Layer 2) ─────────────────────────────────
async def save_conversation(session_id: str, role: str, content: str, emotion: str = "neutral"):
    """Save conversation to episodic memory (SQLite)."""
    db = await get_db()
    await db.execute("""
        INSERT INTO conversations (session_id, role, content, emotion, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, role, content, emotion, datetime.now().isoformat()))
    await db.commit()


async def get_recent_conversations(user_id: str = "default_user", limit: int = 20) -> list:
    """Get recent conversations for context."""
    db = await get_db()
    cursor = await db.execute("""
        SELECT role, content, emotion, created_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))
    rows = await cursor.fetchall()
    return [dict(row) for row in reversed(rows)]


# ─── Semantic Memory (Layer 3) ─────────────────────────────────
async def extract_and_store_facts(text: str, user_id: str = "default_user"):
    """
    Extract facts from user message and store as semantic memories.
    Uses regex patterns to identify personal information.
    """
    text_clean = text.strip()
    extracted = []

    for pattern, category, subcategory in FACT_PATTERNS:
        matches = re.findall(pattern, text_clean, re.IGNORECASE)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    fact_content = f"{subcategory}: {' '.join(match).strip()}"
                else:
                    fact_content = f"{subcategory}: {match.strip()}"

                # Check if similar memory already exists
                existing = await search_memories(match if isinstance(match, str) else match[-1], user_id)
                if not any(subcategory.lower() in m.get("content", "").lower() for m in existing):
                    memory = MemoryRecord(
                        memory_id=str(uuid.uuid4()),
                        user_id=user_id,
                        type="semantic",
                        content=fact_content,
                        confidence=0.85,
                        source="explicit_statement",
                        tags=[category, subcategory]
                    )
                    await store_memory(memory)
                    extracted.append(fact_content)

    return extracted


async def store_memory(memory: MemoryRecord):
    """Store a memory record in SQLite."""
    db = await get_db()
    await db.execute("""
        INSERT OR REPLACE INTO memories 
        (memory_id, user_id, type, content, confidence, source, created_at, last_accessed, access_count, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        memory.memory_id, memory.user_id, memory.type, memory.content,
        memory.confidence, memory.source, memory.created_at,
        memory.last_accessed, memory.access_count, json.dumps(memory.tags)
    ))
    await db.commit()


async def search_memories(query: str, user_id: str = "default_user", limit: int = 5) -> list:
    """
    Search memories by keyword matching.
    MVP version of vector similarity search.
    """
    db = await get_db()
    cursor = await db.execute("""
        SELECT * FROM memories
        WHERE user_id = ? AND content LIKE ?
        ORDER BY access_count DESC, created_at DESC
        LIMIT ?
    """, (user_id, f"%{query}%", limit))
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_all_memories(user_id: str = "default_user", memory_type: str = None) -> list:
    """Get all memories for the dashboard."""
    db = await get_db()
    if memory_type:
        cursor = await db.execute("""
            SELECT * FROM memories WHERE user_id = ? AND type = ?
            ORDER BY created_at DESC
        """, (user_id, memory_type))
    else:
        cursor = await db.execute("""
            SELECT * FROM memories WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["tags"] = json.loads(d.get("tags", "[]"))
        result.append(d)
    return result


async def delete_memory(memory_id: str):
    """Delete a specific memory."""
    db = await get_db()
    await db.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
    await db.commit()


async def update_memory_access(memory_id: str):
    """Update access count and last_accessed timestamp."""
    db = await get_db()
    await db.execute("""
        UPDATE memories SET access_count = access_count + 1, last_accessed = ?
        WHERE memory_id = ?
    """, (datetime.now().isoformat(), memory_id))
    await db.commit()


# ─── Procedural Memory (Layer 4) ──────────────────────────────
async def store_procedural_memory(user_id: str, workflow: str, pattern: str):
    """Store how the user likes tasks done."""
    memory = MemoryRecord(
        user_id=user_id,
        type="procedural",
        content=f"Workflow: {workflow} | Pattern: {pattern}",
        tags=["workflow", "habit"]
    )
    await store_memory(memory)


# ─── User Profile ─────────────────────────────────────────────
async def get_user_profile(user_id: str = "default_user") -> dict:
    """Get or create user profile."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if row:
        d = dict(row)
        d["preferences"] = json.loads(d.get("preferences", "{}"))
        return d
    else:
        await db.execute("""
            INSERT INTO user_profiles (user_id, created_at)
            VALUES (?, ?)
        """, (user_id, datetime.now().isoformat()))
        await db.commit()
        return {"user_id": user_id, "user_name": "", "preferences": {}, "onboarding_complete": 0}


async def update_user_profile(user_id: str, name: str = None, preferences: dict = None, onboarded: bool = None):
    """Update user profile."""
    db = await get_db()
    if name is not None:
        await db.execute("UPDATE user_profiles SET user_name = ? WHERE user_id = ?", (name, user_id))
        # Also store name as semantic memory
        mem = MemoryRecord(
            user_id=user_id, type="semantic",
            content=f"name: {name}", source="explicit_statement",
            tags=["identity", "name"]
        )
        await store_memory(mem)
    if preferences is not None:
        await db.execute("UPDATE user_profiles SET preferences = ? WHERE user_id = ?",
                       (json.dumps(preferences), user_id))
    if onboarded is not None:
        await db.execute("UPDATE user_profiles SET onboarding_complete = ? WHERE user_id = ?",
                       (1 if onboarded else 0, user_id))
    await db.commit()


# ─── Context Builder ──────────────────────────────────────────
async def build_memory_context(query: str, session_id: str, user_id: str = "default_user") -> str:
    """
    Build the full memory context for the LLM prompt.
    Combines all 4 layers of memory.
    """
    context_parts = []

    # Layer 1: Working Memory (current session)
    working = get_working_memory(session_id)
    if working:
        context_parts.append("### Recent Conversation Context:")
        for msg in working[-10:]:
            context_parts.append(f"  {msg['role']}: {msg['content']}")

    # Layer 3: Semantic Memory (search relevant facts)
    keywords = query.split()
    all_relevant = []
    for kw in keywords:
        if len(kw) > 2:
            memories = await search_memories(kw, user_id, limit=3)
            for m in memories:
                if m["memory_id"] not in [x["memory_id"] for x in all_relevant]:
                    all_relevant.append(m)
                    await update_memory_access(m["memory_id"])

    # Also get all semantic memories (for small MVP datasets)
    all_semantic = await get_all_memories(user_id, "semantic")
    for m in all_semantic:
        if m["memory_id"] not in [x["memory_id"] for x in all_relevant] and len(all_relevant) < 10:
            all_relevant.append(m)

    if all_relevant:
        context_parts.append("\n### User's Stored Memories (Things you know about the user):")
        for m in all_relevant[:10]:
            tags = m.get("tags", [])
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            context_parts.append(f"  - {m['content']}{tag_str}")

    # User profile
    profile = await get_user_profile(user_id)
    if profile.get("user_name"):
        context_parts.append(f"\n### User Profile: Name is {profile['user_name']}")

    return "\n".join(context_parts) if context_parts else ""
