# JARVIS AI - User Stories & Acceptance Criteria

This document details the critical user journeys, translating the PRD into actionable Jira-style User Stories with exact Acceptance Criteria (AC).

## Epic 1: Conversational AI & NLP

### Story 1.1: Natural Hinglish Conversation

**As a** user,
**I want to** communicate with JARVIS in mixed Hinglish (Hindi + English),
**So that** I feel like I am talking to a real human friend without worrying about formatting or strict language rules.

**Acceptance Criteria:**

- **AC1:** Given the user types "Kal ki meeting cancel kardo please", JARVIS correctly identifies the intent as `calendar.cancel_event`.
- **AC2:** Given a mixed query, JARVIS replies in the corresponding tone and language mixture.
- **AC3:** The system must stream the first response token within 800ms.

### Story 1.2: Emotional Awareness & Tone Adaptation

**As a** user,
**I want** JARVIS to detect when I am stressed, frustrated, or happy,
**So that** it can adjust its tone to be comforting, direct, or enthusiastic appropriately.

**Acceptance Criteria:**

- **AC1:** If sentiment analysis detects high stress (>0.8 threshold), JARVIS responds with a calmer, shorter, and supportive tone.
- **AC2:** JARVIS does not use forced humor if the detected intent is urgent (e.g., "My computer crashed").

## Epic 2: Advanced Memory System

### Story 2.1: Semantic Fact Recall

**As a** user,
**I want** JARVIS to remember explicit facts I tell it (e.g., "Mera bhai US mein rehta hai"),
**So that** I don't have to repeat myself in future conversations.

**Acceptance Criteria:**

- **AC1:** Given the user stated a fact 3 months ago, when asked "Mera bhai kahan rehta hai?", JARVIS retrieves the exact location fact.
- **AC2:** The vector DB retrieval latency must be < 200ms.
- **AC3:** JARVIS responds conversationally: "Haan, tumhara bhai US mein rehta hai."

### Story 2.2: Memory Management Dashboard

**As a** user,
**I want** to see, edit, and delete what JARVIS remembers about me,
**So that** I maintain full control and privacy over my personal digital brain.

**Acceptance Criteria:**

- **AC1:** The settings page displays categorized memories (People, Preferences, Work).
- **AC2:** Users can click a "Delete" icon to instantly purge a memory node from both Postgres and the Vector DB.
- **AC3:** If a conflict arises (user manually changes their favorite color from Red to Blue), the Vector DB updates the semantic weight accordingly.

## Epic 3: System Automation

### Story 3.1: Desktop File Management

**As a** power user (Desktop App),
**I want** to tell JARVIS to organize my desktop or find lost files,
**So that** I save time navigating folders manually.

**Acceptance Criteria:**

- **AC1:** When user says "Clean up my downloads folder", JARVIS categorizes loose files into "Images", "Documents", "Installers" folders automatically.
- **AC2:** JARVIS explicitly asks for confirmation ("Downloads mein 45 files hain, sort kar doon?") before executing destructive/moving actions.
- **AC3:** If the OS denies permission, JARVIS gracefully explains the issue.

### Story 3.2: Calendar & Meeting Scheduling

**As a** professional,
**I want** JARVIS to schedule meetings for me seamlessly,
**So that** I don't have to open my calendar app and manually invite people.

**Acceptance Criteria:**

- **AC1:** Upon "Set a meeting with Rahul tomorrow at 3 PM", JARVIS verifies Rahul's email from Semantic Memory or Contacts.
- **AC2:** JARVIS checks for conflicts in Google Calendar. If conflicted, it proposes the next available slot.
- **AC3:** It sends a Google Calendar invite and confirms verbally/in-text with the user.
