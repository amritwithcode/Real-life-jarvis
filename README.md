# JARVIS AI 🧠

**JARVIS (Joint Artificial Real-time Virtual Intelligence System)** is a next-generation Personal AI Assistant. It serves as a fully autonomous digital brain that maintains long-term memory, reasoning, and handles human-like Hinglish conversations while automating complex system-level tasks.

---

## ✨ Core Features

### 🧠 4-Layer Memory System

- **Working Memory:** Immediate session context (last 50 turns).
- **Episodic Memory:** Short-term logs (7-30 days), auto-summarized for context retention.
- **Semantic Memory:** Long-term facts, entities, user preferences, and permanent habits.
- **Procedural Memory:** Learned user workflows and specific interaction patterns.

### 🤖 Autonomous Orchestration

- **OS Automation:** File manipulation, process management, and PC optimization.
- **Communication:** Drafts and sends emails (Gmail/Outlook) and messages (WhatsApp/Telegram).
- **Productivity:** Intelligent calendar management and script execution (Python, JS, C++).

### 🗣️ Advanced Conversational AI

- **Hinglish Support:** Natural flow in mixed Hindi and English.
- **Real-time Streaming:** Token-by-token streaming over WebSockets for zero perceived latency.
- **Emotion Engine:** Adapts tone based on user sentiment (casual, formal, or emotional support).

---

## 🛠️ Technology Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python), Uvicorn, OpenAI GPT-4o / Llama 3.
- **Frontend:** Vanilla JavaScript, HTML5, CSS3 (Modern Glassmorphic Design).
- **Database:** [SQLite](https://www.sqlite.org/) (with `aiosqlite` for async operations).
- **Intelligence:** Groq (for speed), Claude-3.5-Sonnet (for reasoning), Whisper (Speech-to-Text).

---

## 📂 Project Structure

```text
persona_ai/
├── backend/            # FastAPI Server & AI Services
│   ├── main.py         # Entry point
│   ├── orchestrator.py  # Intent & logic orchestration
│   ├── memory_service.py # 4-layer memory management
│   └── llm_service.py   # LLM integration (OpenAI/Groq)
├── frontend/           # Web-based UI Dashboard
│   ├── index.html      # Main layout
│   ├── app.js          # Chat & WebSocket logic
│   └── styles.css      # Modern UI styling
├── docs/               # Technical specs & requirements
└── README.md           # This file
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Browser (Chrome/Edge/Firefox)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-repo/persona_ai.git
   cd persona_ai
   ```

2. **Install dependencies:**

   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Configure Environment:**
   Create a `.env` file in the `backend/` directory and add your API keys:

   ```env
   OPENAI_API_KEY=your_key_here
   GROQ_API_KEY=your_key_here
   ```

4. **Launch the backend:**

   ```bash
   python backend/main.py
   ```

5. **Access the Dashboard:**
   Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)

---

## 📄 Documentation

For more detailed technical specifications, refer to:

- [Product Requirements](01-product-requirements.md)
- [System Architecture](04-system-architecture.md)
- [API Contracts](06-api-contracts.md)

---

Developed with ❤️ for the future of Personal AI.
