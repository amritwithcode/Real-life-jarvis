# JARVIS AI - Testing Strategy

Given the unpredictable nature of Large Language Models (LLMs) and the strict latency constraints of JARVIS, a robust, multi-layered testing strategy is required.

## 1. Unit Testing & Component Testing

- **Frontend (Next.js & Electron):**
  - Jest + React Testing Library for standard UI component logic.
  - Mock WebSocket endpoints to verify the chat UI renders streaming tokens correctly without stuttering.
- **Backend (Python/Node):**
  - PyTest for Orchestrator logic.
  - Test Intent Routing: Hardcode inputs (e.g., "Schedule a meeting") and assert that the LangGraph router selects the "Automation" node.
  - _LLM Mocking:_ Do not hit actual OpenAI/Anthropic APIs in unit tests. Mock the JSON/text responses.

## 2. Automation & E2E Testing (Playwright / Selenium)

Testing system automation is critical since JARVIS interacts with the real world.

- **Sandbox Environments:** Dedicated Google Workspaces accounts used purely for testing Email drafting and Calendar insertions.
- **OS-Level Testing:** Run Electron test suites inside isolated Docker containers or ephemeral CI VMs to test File System manipulation safely (e.g., "Create a folder on the desktop").

## 3. LLM Eval & Model Testing

Standard code tests cannot verify if an AI gave a "good" answer. We use an automated Eval framework.

- **Golden Dataset:** A carefully curated list of 500 Hinglish prompts and ideal expected responses / intents.
- **Automated Evaluation:**
  - Run the dataset against any new model prompt changes.
  - **Metric 1 - Intent Accuracy:** Did the model pick the correct internal tool? (Target > 95%).
  - **Metric 2 - BLEU / Semantic Similarity:** Compare generated text against the "Golden" text using an evaluator LLM (LLM-as-a-judge).
- **Regression Testing:** Ensure that fine-tuning or tweaking the prompt for "calendar logic" didn't break "web research logic".

## 4. Performance & Load Testing

- **Tool:** Locust or Artillery.io.
- **Goal:** Simulate 10,000 concurrent WebSocket connections.
- **Metric Tracking:**
  - Verify API Gateway does not drop connections.
  - Verify Time-to-First-Token (TTFT) remains < 800ms under load.
  - Verify Qdrant Vector Search latency remains < 200ms when 1000 users query simultaneously.

## 5. Security & Penetration Testing

- **Prompt Injection Testing:** Run specific automated suites that attempt to trick JARVIS into revealing its system prompts, bypassing PII restrictions, or deleting system files.
- **Auth Penetration:** Standard checks for JWT token hijacking, CSRF, and XSS across the Web and Desktop apps.
