# JARVIS AI - Computation Logic & Engine Spec

This document details the exact computational flow for the **Orchestrator** and **Response Generation Engine**.

## 1. The Core Conversational Loop (LangGraph Logic)

The Orchestrator acts as a State Machine.
**Input:** `user_text`

1.  **Node: Language Detection & Formatting**
    - _Compute:_ IF Hinglish, map tokens correctly. Output normalized string.
2.  **Node: Intent Classification**
    - _Compute:_ Fast Groq LLM API call: `Classify intent into [chat, system_task, web_research, memory_query]`.
    - _Output:_ Route decision.
3.  **Parallel Execution Block:**
    - **Branch A (Memory Search):** `user_text` -> text-embedding-3-large -> Qdrant (Cosine Similarity) -> Top 10 nodes -> Cohere Rerank -> Top 3 memories.
    - **Branch B (Context Fetch):** Fetch Active Windows, Current Time, Calendar status (if allowed).
4.  **Node: Action Planner (If intent == system_task)**
    - _Compute:_ Claude 3.5 Sonnet generates a JSON array of tool calls.
5.  **Node: Final Synthesis**
    - _Compute:_ Combine LLM System Prompt + Top 3 Memories + Action Results + `user_text`.
    - _Call:_ Claude / OpenAI streaming API. Streams tokens to Client.

## 2. Memory Aging & Compression Algorithm

To prevent infinite context bloat:

1.  **Trigger:** Nightly cron job runs at 3:00 AM user local time.
2.  **Identification:** Fetch all `episodic` memories older than 30 days.
3.  **Summarization:** Pass batch to Claude: "Summarize this 1-month chat history into 5 bullet points of facts".
4.  **Transformation:** Save the 5 bullet points as `semantic` memories. Delete the raw `episodic` chat logs from Vector DB (keep in MongoDB for auditing).

## 3. Dynamic Model Routing Strategy

- **Latency-Critical Route:** Simple greetings ("Hi", "Good morning") -> Route to **Groq**. Cost is near zero, TTFT is <200ms.
- **Logic-Heavy Route:** Multi-step coding / reasoning ("Write a Python script to scrape x and save to y") -> Route to **Claude 3.5 Sonnet**.
- **Fallback Strategy:** If Claude times out (>2s) -> Route to **GPT-4o**.
