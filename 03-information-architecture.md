# JARVIS AI - Information Architecture & User Flows

This document outlines the Information Architecture (IA), Sitemap, and structural layout of the JARVIS AI platform across Web, Mobile, and Desktop variants.

## 1. High-Level Sitemap (Web / Desktop App)

```text
[ Root / Home ]
 ??? [ Onboarding Flow ]
 ?    ??? Step 1: Language & Persona Preferences
 ?    ??? Step 2: Integrations Connecting (Google, Microsoft, GitHub)
 ?    ??? Step 3: Permissions (Desktop file access, Mic, Notifications)
 ?
 ??? [ Core Interface: The Chat UI ]
 ?    ??? Main Chat Canvas (Text & Voice Input)
 ?    ??? Streaming Response Area
 ?    ??? Suggestion Chips / Proactive Actions
 ?    ??? Context Panel (Right Sidebar - collapses)
 ?
 ??? [ Memory Dashboard ] (The "Brain")
 ?    ??? Episodic Tab: Recent Conversations & Summaries
 ?    ??? Semantic Tab: Facts, People, Relationships, Preferences
 ?    ??? Procedural Tab: Custom Workflows & Task Habits
 ?    ??? Memory Search & Management (Edit/Delete)
 ?
 ??? [ Automations & Integrations Hub ]
 ?    ??? Active Connections (Auth Status)
 ?    ??? Automation Logs (History of actions JARVIS took)
 ?    ??? Plugin Marketplace (Phase 3)
 ?
 ??? [ Settings & Privacy ]
      ??? Account Details & Subscriptions (Pro/Ultra)
      ??? Voice & Personality Tuning
      ??? Privacy Controls (One-click data wipe, PII guards)
      ??? API Keys (For Developers)
```

## 2. Core User Flows

### Flow 1: New User Onboarding

1. **Landing Page:** Value proposition and Login/Signup (OAuth Google/Apple).
2. **Setup Wizard:**
   - "Call me [Name]"
   - Connect Calendar (Google OAuth consent)
   - Enable Desktop capabilities (if via Electron app)
3. **Empty State Chat:** "Hi [Name], I'm JARVIS. I see you have 3 meetings today. Should I prepare a brief?"

### Flow 2: Multi-Turn Conversation with Action

1. **Input:** User hits 'Spacebar' globally (Desktop shortcut) or taps microphone. Says: "Summarize the last email from my boss."
2. **Processing UI:** Glowing JARVIS indicator (Processing...).
3. **Action Executing UI:** Embedded card appears in chat: "Fetching emails from [Boss Name]..."
4. **Output:** Formatted markdown summary streams into the chat canvas.
5. **Follow-up:** Suggestion chips appear: [Draft a reply], [Schedule a meeting], [Remind me tomorrow].

### Flow 3: Memory Inspection & Editing

1. **Trigger:** User gets curious about what JARVIS knows and clicks "Brain/Memory" icon on the left navbar.
2. **View:** Displaying a node-based UI or a clean table of facts categorized by tags (#work, #family, #preferences).
3. **Edit Action:** User searches "coffee". Sees record: "Prefers Black Coffee". User edits text to "Prefers Cappuccino" and clicks 'Save'.
4. **Background:** System instantly re-embeds the text and updates the Vector DB.

## 4. UI/UX Principles

- **Minimalist Conversational UI:** The chat takes center stage. No bloated menus. Everything happens functionally within the conversational flow whenever possible.
- **Speed Indications:** Ultra-fast micro-animations. Streaming text starts instantly to mask backend reasoning latency.
- **Frictionless Invocation:** JARVIS must be 1-keystroke away (e.g., `Cmd + J` or `Alt + Space`) universally on desktop.
- **Ambient Awareness:** Right panel subtly shows "Current Context" (Files open, active calendar events) so the user knows what JARVIS can "see".
