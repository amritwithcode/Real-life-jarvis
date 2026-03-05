"""
JARVIS AI - Orchestrator Service
The "Brain of the Brain" — handles intent classification, task decomposition,
memory retrieval, emotion detection, action routing, and coordinates all services.
Based on 08-computation-logic-engine-spec.md + Action Command Architecture
"""

from emotion_engine import detect_emotion, get_emotion_prompt_injection
from memory_service import (
    get_working_memory, add_to_working_memory,
    save_conversation, extract_and_store_facts,
    build_memory_context, get_user_profile
)
from llm_service import build_full_prompt, generate_streaming_response, generate_action_json, generate_task_plan
from action_commands import execute_action, SUPPORTED_ACTIONS, ActionCommand
from typing import AsyncGenerator


# ─── Intent Classification (Layer 1 — Fast) ───────────────────
# Keywords for FAST intent pre-classification (no LLM needed)
ACTION_KEYWORDS = {
    "system_action": [
        "open", "close", "kholo", "band", "karo", "start", "stop",
        "create", "delete", "banao", "hatao", "file", "folder",
        "screenshot", "lock", "shutdown", "restart", "install",
        "cpu", "ram", "disk", "battery", "system info", "process",
        "task manager", "calculator", "notepad", "chrome", "vscode",
        "explorer", "terminal", "cmd", "app", "python", "run",
    ],
    "online_action": [
        "search", "google", "youtube", "website", "web",
        "email", "mail", "bhejo", "weather", "mausam",
        "whatsapp", "github", "chatgpt", "maps", "translate",
        "open youtube", "open google", "open website",
    ],
    "memory_query": [
        "yaad", "remember", "recall", "naam kya", "kya tha",
        "bola tha", "pata hai", "stored", "memory", "brain",
        "yaad hai", "kab", "kahan", "kaun", "konsa"
    ],
    "complex_trigger": [
        "and", "then", "after that", "fir", "phir", "firse",
        "baad", "pehle", "first", "next", "also", "karke",
    ],
    "productivity": [
        "note", "task", "todo", "workflow", "automation", "save", "list",
        "remind", "reminder", "schedule", "priority", "status",
    ]
}


def classify_intent(text: str) -> str:
    """
    FAST intent classification using keyword matching (Layer 1).
    Returns: system_action, online_action, memory_query, or chat
    """
    text_lower = text.lower()

    scores = {}
    for intent, keywords in ACTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[intent] = score

    if not scores:
        return "chat"

    best_intent = max(scores, key=scores.get)
    
    # Check for complex task trigger
    for trigger in ACTION_KEYWORDS["complex_trigger"]:
        if f" {trigger} " in f" {text_lower} " or text_lower.endswith(trigger):
            return "complex_task"

    # Require at least 2 keyword matches for action intents (to avoid false positives)
    if scores[best_intent] >= 1 and best_intent in ["system_action", "online_action"]:
        return best_intent
    
    return best_intent if scores[best_intent] >= 1 else "chat"


# ─── Main Orchestration Pipeline ──────────────────────────────
async def process_message(
    user_message: str,
    session_id: str,
    user_id: str = "default_user"
) -> AsyncGenerator[str, None]:
    """
    Main orchestration pipeline — the core conversational loop.
    
    FLOW (Hybrid Architecture):
    1. Fast intent classification (keywords)
    2. If ACTION intent → LLM generates structured JSON → execute
    3. If CHAT intent → full LLM streaming with memory/emotion context
    4. Post-processing (fact extraction, memory storage)
    """

    # Step 1: Add to working memory
    add_to_working_memory(session_id, "user", user_message)

    # Step 2: Fast Intent Classification
    intent = classify_intent(user_message)

    # Step 3: Emotion Detection
    emotion_state = detect_emotion(user_message)
    emotion_prompt = get_emotion_prompt_injection(emotion_state)

    # ─── ACTION PATH (System / Online / Complex) ───────────────
    if intent in ["system_action", "online_action", "complex_task"]:
        
        # Scenario 1: Complex Multi-Step Task
        if intent == "complex_task" or any(t in user_message.lower() for t in [" and ", " then ", " fir "]):
            yield "🔍 *Task Decomposing... Planning steps.*"
            plan = await generate_task_plan(user_message)
            
            if plan and plan.get("type") == "complex_task":
                steps = plan.get("steps", [])
                yield f"🧠 **JARVIS Plan:** {plan.get('goal', 'Executing multi-step task')}\n"
                
                full_status = ""
                for step in steps:
                    action_name = step.get("action")
                    params = step.get("parameters", {})
                    
                    yield f"⏳ *Executing Step {step['step_id']}: {action_name}...*"
                    
                    # Convert to ActionCommand internal format
                    cmd_json = {
                        "type": "system_action" if action_name in SUPPORTED_ACTIONS["system_action"] else "online_action",
                        "action": action_name,
                        "parameters": params,
                        "meta": {"confidence": 0.95, "requires_confirmation": False}
                    }
                    
                    result = await execute_action(cmd_json)
                    yield f"✅ {result.message}\n"
                    full_status += f"Step {step['step_id']} ({action_name}): {result.message}\n"
                
                # Save to memory
                add_to_working_memory(session_id, "assistant", full_status)
                await save_conversation(session_id, "user", user_message, emotion_state.emotion)
                await save_conversation(session_id, "assistant", "Multi-step task completed.", "neutral")
                return

        # Scenario 2: Single Action
        action_json = await generate_action_json(user_message)

        if action_json and action_json.get("type") != "chat":
            # Execute the action!
            result = await execute_action(action_json)

            # Special Case: Action redirected to a workflow (complex task)
            if result.action == "complex_task" and result.data:
                yield f"🔄 **Workflow Triggered:** {result.message}\n"
                steps = result.data
                for step in steps:
                    action_name = step.get("action")
                    params = step.get("parameters", {})
                    yield f"⏳ *Step: {action_name}...*"
                    
                    cmd_json = {
                        "type": "system_action" if action_name in SUPPORTED_ACTIONS["system_action"] else "online_action",
                        "action": action_name,
                        "parameters": params,
                        "meta": {"confidence": 0.95, "requires_confirmation": False}
                    }
                    step_res = await execute_action(cmd_json)
                    yield f"✅ {step_res.message}\n"
                return

            # Build response message
            action_response = result.message

            # If action needs confirmation, append prompt
            if result.requires_confirmation:
                action_response += "\n\n⚠️ Confirm karo — 'Haan, kar do!' ya 'Cancel karo'"

            # Yield the action result as streamed text
            yield action_response

            # Save to memory
            add_to_working_memory(session_id, "assistant", action_response)
            await save_conversation(session_id, "user", user_message, emotion_state.emotion)
            await save_conversation(session_id, "assistant", action_response, "neutral")
            await extract_and_store_facts(user_message, user_id)
            return

    # ─── CHAT PATH (Regular conversation with streaming) ───────
    # Step 4: Memory Context Building
    memory_context = await build_memory_context(user_message, session_id, user_id)

    # Step 5: Get user profile
    profile = await get_user_profile(user_id)
    user_name = profile.get("user_name", "")

    # Step 6: Build full system prompt
    system_prompt = build_full_prompt(
        emotion_context=emotion_prompt,
        memory_context=memory_context,
        user_name=user_name
    )

    # Step 7: Get conversation history from working memory
    history = get_working_memory(session_id)

    # Step 8: Stream LLM response
    full_response = ""
    async for chunk in generate_streaming_response(user_message, history, system_prompt):
        full_response += chunk
        yield chunk

    # Step 9: Post-processing (after response is complete)
    add_to_working_memory(session_id, "assistant", full_response)
    await save_conversation(session_id, "user", user_message, emotion_state.emotion)
    await save_conversation(session_id, "assistant", full_response, "neutral")
    await extract_and_store_facts(user_message, user_id)


async def get_suggestion_chips(intent: str, emotion: str) -> list:
    """Generate contextual suggestion chips based on intent and emotion."""
    suggestions = {
        "chat": [
            "Tell me a joke 😄",
            "Aaj ka plan batao",
            "Kuch interesting batao",
            "Meri memory dikha"
        ],
        "memory_query": [
            "Aur kya yaad hai?",
            "Memory dashboard kholo",
            "Sab memories dikha",
            "Ye memory delete karo"
        ],
        "system_action": [
            "Chrome open karo",
            "System info dikha",
            "Screenshot le lo",
            "CPU usage batao"
        ],
        "online_action": [
            "YouTube open karo",
            "Google pe search karo",
            "Weather batao",
            "WhatsApp open karo"
        ],
    }

    # Modify based on emotion
    if emotion == "stressed":
        suggestions["chat"] = [
            "Break le lete hain 🧘",
            "Priority list banao",
            "Kya urgent hai?",
            "Relax technique batao"
        ]
    elif emotion == "frustrated":
        suggestions["chat"] = [
            "Step by step solve karte hain",
            "Kya error aa raha hai?",
            "Alternative approach try karein?",
            "Log file check karein"
        ]

    return suggestions.get(intent, suggestions["chat"])[:4]
