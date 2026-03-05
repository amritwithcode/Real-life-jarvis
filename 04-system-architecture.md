# JARVIS AI - System Architecture

This document describes the high-level system architecture and data flow for the JARVIS AI platform. It is designed to achieve the <3-4s end-to-end latency constraint.

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    Client[Web/Mobile/Desktop App] -->|HTTPS/WSS| API[API Gateway / Load Balancer]

    API -->|Auth/Route| Orch[Orchestrator Service]
    API -->|Logs| Analytics[Analytics Service]

    Orch -->|Intent & Routing| NLP[NLP / LLM Service]
    Orch -->|Action Planning| Auto[Automation Engine]
    Orch -->|Context Injection| Mem[Memory Service]

    NLP <-->|Fast Prompting| Groq[Groq LPU API]
    NLP <-->|Complex Reasoning| Claude[Claude 4 / OpenAI API]

    Mem <-->|Semantic Search| VDB[(Vector DB: Qdrant/Pinecone)]
    Mem <-->|CRUD| RDB[(PostgreSQL)]

    Auto <-->|Web/Action| Tools[Tool Manager & Plugins]

    classDef client fill:#3498db,stroke:#2980b9,color:#fff;
    classDef gateway fill:#2ecc71,stroke:#27ae60,color:#fff;
    classDef core fill:#9b59b6,stroke:#8e44ad,color:#fff;
    classDef db fill:#f1c40f,stroke:#f39c12;
    classDef external fill:#e74c3c,stroke:#c0392b,color:#fff;

    class Client client;
    class API gateway;
    class Orch,NLP,Auto,Mem,Tools core;
    class VDB,RDB db;
    class Groq,Claude external;
```

## 2. Core Microservices

1.  **API Gateway (Node.js/Express or Nginx):**
    - Handles SSL termination, rate limiting, and JWT validation.
    - Maintains WebSocket connections for real-time text streaming.

2.  **Orchestrator (Python / LangGraph):**
    - The "Brain of the Brain".
    - Receives raw text/audio, determines the required sub-tasks, and fires them off in parallel.

3.  **NLP Service (Python / FastAPI):**
    - Handles Prompt formatting.
    - Abstracts the underlying LLM provider (Claude, OpenAI, Groq), routing simple queries to Groq and difficult ones to Claude.

4.  **Memory Service (Python):**
    - Fetches User Context. Converts queries to Embeddings (OpenAI `text-embedding-3-large`).
    - Queries Vector DB and uses Cohere Rerank to find top 3-5 memories to inject into the Prompt.

5.  **Automation Engine (Node.js or Python):**
    - Executes actual commands (Calling Gmail API, OS-level Python scripts via Electron, Selenium/Puppeteer scraping).
    - Queues heavy background tasks via Celery + Redis.

## 3. Storage Layer

- **Relational (PostgreSQL 16):** User accounts, Subscription statuses, Auth logic, Structured logs, Audit trails.
- **Vector DB (Qdrant / Pinecone):** 1536-dimensional embeddings for memory nodes.
- **Cache (Redis 7.0):** Active session data (Layer 1 Memory), Rate-limit counters.
- **Unstructured (MongoDB):** Raw chat transcripts and conversation history for UI rendering.

## 4. Latency Mitigation Strategies

- **Parallel Execution:** Memory fetching and Intent Detection run simultaneously.
- **Response Streaming:** The NLP service streams tokens back through the Orchestrator directly to the Client WebSocket buffer.
- **Groq LPU:** Used specifically for "greeting", "chit-chat", or simple queries where TTFT (Time To First Token) dictates perceived speed.
