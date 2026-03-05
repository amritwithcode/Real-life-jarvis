# JARVIS AI - API Contracts (Internal APIs)

This document defines the primary API signatures for communication between the Frontend Clients and the JARVIS Backend (API Gateway).

## 1. REST APIs (Standard Operations)

### 1.1 Authentication & User Management

**`POST /api/v1/auth/login`**

- **Description:** Authenticates user and returns JWT.
- **Body:** `{ "email": "...", "password": "..." }` or `{ "oauth_token": "..." }`
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhb...",
    "refresh_token": "def...",
    "user": { "id": "uuid", "tier": "pro" }
  }
  ```

### 1.2 Memory Management

**`GET /api/v1/memory`**

- **Description:** Fetch all readable memories for the user dashboard.
- **Query Params:** `?type=semantic&limit=50&offset=0`
- **Response (200 OK):**
  ```json
  {
    "data": [
      {
        "memory_id": "uuid",
        "content": "Lives in Delhi.",
        "tags": ["location"]
      }
    ],
    "total": 1
  }
  ```

**`DELETE /api/v1/memory/{memory_id}`**

- **Description:** Hard deletes a specific memory from Postgres and Vector DB.
- **Response (204 No Content)**

## 2. WebSocket Standard (Real-Time Conversation)

Because a < 4s latency and streaming text are strict requirements, the core conversational loop happens over WebSockets.

**Endpoint:** `wss://api.jarvis.ai/v1/chat/stream?session_id={uuid}`

### 2.1 Client to Server (Input)

```json
{
  "event": "user_message",
  "payload": {
    "text": "Mera next meeting kab hai?",
    "audio_bytes": null, // Base64 if voice input
    "context": {
      "active_app": "VSCode",
      "os": "macOS"
    }
  }
}
```

### 2.2 Server to Client (Output Stream)

The server sends multiple events as the Orchestrator processes the query.

**1. Acknowledgment (Immediate < 200ms)**

```json
{
  "event": "processing_started",
  "payload": { "intent_identified": "calendar_query" }
}
```

**2. Tool Execution (Optional)**

```json
{
  "event": "tool_call",
  "payload": {
    "tool": "google_calendar",
    "status": "fetching_events"
  }
}
```

**3. Text Stream (Tokens arriving from LLM)**

```json
{
  "event": "text_stream",
  "payload": {
    "chunk": "Tumhari next meeting "
  }
}
{
  "event": "text_stream",
  "payload": {
    "chunk": "3 baje hai."
  }
}
```

**4. End of Stream**

```json
{
  "event": "stream_complete",
  "payload": {
    "full_text": "Tumhari next meeting 3 baje hai.",
    "metrics": {
      "ttft_ms": 780,
      "total_latency_ms": 2100
    }
  }
}
```
