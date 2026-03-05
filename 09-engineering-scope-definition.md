# JARVIS AI - Engineering Scope Definition

## 1. In Scope (MVP Launch Q3 2026)

- **Conversational Logic:** Full support for Hinglish text-based conversation via Web App.
- **Memory Level 1-3:** Working (Session), Episodic (Recent chats), and Semantic (Explicit facts) memory.
- **Cloud Architecture:** AWS/GCP based infrastructure with PostgreSQL + Qdrant.
- **Basic Integrations:** Google Calendar (Read/Write), Gmail (Drafts/Read), Local File Search (Electron App only).
- **Authentication:** Google OAuth2 and Standard Email/Password.
- **User Interface:** Next.js Web Application and an Electron Desktop wrapper for basic OS actions.

## 2. Out of Scope (For MVP / Will be added in V2+)

- **Voice I/O Engine:** Real-time deeply integrated voice interrupting (like OpenAI Advanced Voice mode). MVP will only use basic Whisper speech-to-text.
- **Mobile Applications:** Native iOS/Android apps are deferred to Phase 2 (Q4 2026).
- **Plugin Marketplace:** Third-party developer SDK and marketplace are out of scope.
- **Deep Memory Level 4:** Procedural memory (learning a user's specific complex workflows blindly) is deferred.
- **Autonomous Agent Mode:** JARVIS acting completely autonomously while the user is asleep (e.g., auto-replying to emails without draft approval).

## 3. Scope Constraints

- **Dependency:** We are highly dependent on Anthropic and OpenAI's API uptime.
- **Cost Scope:** The LLM cost per user per month must not exceed $2.00 for the Free Tier. Rate limiting must be strictly enforced on backend.
