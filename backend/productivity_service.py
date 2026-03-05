import aiosqlite
import os
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_productivity.db")

async def init_prod_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                steps TEXT, -- JSON string of steps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def create_note(title: str, content: str, tags: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)", (title, content, tags))
        await db.commit()
        return "✅ Note save ho gayi!"

async def list_notes():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM notes ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def delete_note(note_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        await db.commit()
        return f"🗑️ Note {note_id} delete kar di."

async def create_task(task_text: str, priority: str = "medium", due_date: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO tasks (task, priority, due_date) VALUES (?, ?, ?)", (task_text, priority, due_date))
        await db.commit()
        return "✅ Task add ho gaya!"

async def list_tasks(status: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM tasks"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def update_task(task_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        await db.commit()
        return f"✅ Task {task_id} update ho gaya: {status}"

async def create_workflow(name: str, steps: list):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO workflows (name, steps) VALUES (?, ?)", (name, json.dumps(steps)))
        await db.commit()
        return f"✅ Workflow '{name}' create ho gaya!"

async def list_workflows():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM workflows") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_workflow(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM workflows WHERE name = ?", (name,)) as cursor:
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                d['steps'] = json.loads(d['steps'])
                return d
            return None
