# JARVIS AI - Database Schema

This document details the relational (PostgreSQL) and Vector database structures.

## 1. Relational Database (PostgreSQL 16)

### Table: `users`

| Column           | Type           | Constraints      | Description                                 |
| :--------------- | :------------- | :--------------- | :------------------------------------------ |
| `id`             | `uuid`         | PRIMARY KEY      | Unique user identifier.                     |
| `email`          | `varchar(255)` | UNIQUE, NOT NULL | User's email address.                       |
| `password_hash`  | `varchar`      | NULLABLE         | Hash (if email/pass auth used).             |
| `oauth_provider` | `enum`         | NULLABLE         | E.g., 'google', 'apple'.                    |
| `tier`           | `enum`         | DEFAULT 'free'   | 'free', 'pro', 'ultra', 'enterprise'.       |
| `created_at`     | `timestamptz`  | DEFAULT NOW()    | Account creation time.                      |
| `settings`       | `jsonb`        |                  | User preferences (theme, default LLM tone). |

### Table: `sessions` (Conversations)

| Column       | Type          | Constraints   | Description                                |
| :----------- | :------------ | :------------ | :----------------------------------------- |
| `id`         | `uuid`        | PRIMARY KEY   | Unique session identifier.                 |
| `user_id`    | `uuid`        | FOREIGN KEY   | Links to `users`.                          |
| `title`      | `varchar`     |               | Auto-generated title summarizing the chat. |
| `created_at` | `timestamptz` | DEFAULT NOW() | Session start time.                        |

### Table: `messages` (Stored in MongoDB or Postgres JSONB for MVP)

_If using Postgres JSONB or relational structure:_
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | PRIMARY KEY | Unique message identifier. |
| `session_id` | `uuid` | FOREIGN KEY | Links to `sessions`. |
| `role` | `enum` | NOT NULL | 'user', 'assistant', 'system', 'tool'. |
| `content` | `text` | NOT NULL | The text content or JSON tool call. |
| `created_at` | `timestamptz` | DEFAULT NOW() | Message timestamp. |

## 2. Vector Database (Qdrant or Pinecone)

The Vector DB stores the "Semantic" and "Procedural" memories.

### Collection: `user_memories`

Each record (point) in the collection represents a single isolated fact or habit.

**Payload Schema:**

```json
{
  "memory_id": "uuid-v4",
  "user_id": "uuid-v4 (Used for filtering)",
  "type": "semantic | episodic | procedural",
  "content": "User prefers to be addressed casually as 'bhai'.",
  // Vector Field: [0.01, -0.04, 0.99, ...] (1536 dims via OpenAI text-embedding-3-large)
  "metadata": {
    "confidence": 0.98,
    "source": "inferred_from_chat",
    "created_at": "2026-03-01T10:30:00Z",
    "last_accessed_at": "2026-03-03T10:30:00Z",
    "access_count": 12,
    "tags": ["preference", "communication_style"]
  }
}
```

## 3. Redis Cache (In-Memory)

### Key-Value Structures

- `session:{session_id}:working_memory`: List of the last N turns of conversation.
- `rate_limit:{user_id}:daily_tokens`: Counter for enforcing the Free tier limits.
- `user:{user_id}:active_integrations`: Cached list of valid OAuth tokens for 3rd party APIs (Gmail, Drive) to prevent DB hits on every tool call.
