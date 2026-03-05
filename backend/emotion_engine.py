"""
JARVIS AI - Emotion Detection Engine
Based on the Conversation Engine + AI Assistant Emotion & System Prompt Framework (emotions.md)
Detects user emotional state and adapts response tone accordingly.
"""

from models import EmotionState


# ─── Emotion Keywords ──────────────────────────────────────────
EMOTION_KEYWORDS = {
    "frustrated": {
        "keywords": [
            "problem", "error", "issue", "slow", "nahi ho raha", "kaam nahi",
            "nahi chal raha", "broken", "crash", "fail", "galat", "stuck",
            "bug", "fix", "kharab", "pareshan", "tang", "irritate", "damn",
            "useless", "bakwas", "bekar", "worst", "hate", "pagal",
            "frustrate", "thak gaya", "fed up", "hopeless"
        ],
        "weight": 0.8
    },
    "excited": {
        "keywords": [
            "amazing", "awesome", "great", "let's go", "start karte",
            "build", "create", "wow", "fantastic", "brilliant", "love it",
            "mast", "badiya", "zabardast", "kamaal", "sahi hai", "chalo",
            "banate", "excited", "ready", "perfect", "excellent", "best"
        ],
        "weight": 0.7
    },
    "confused": {
        "keywords": [
            "samajh nahi", "kaise", "kya matlab", "confused", "unclear",
            "nahi pata", "explain", "what", "why", "how", "kyu",
            "confuse", "doubt", "lost", "understand nahi", "complicated",
            "mushkil", "hard", "difficult"
        ],
        "weight": 0.6
    },
    "stressed": {
        "keywords": [
            "pressure", "deadline", "urgent", "jaldi", "time nahi",
            "bahut kaam", "overload", "stress", "tension", "anxiety",
            "worried", "panic", "rush", "asap", "important", "critical",
            "kal tak", "aaj hi", "abhi", "emergency"
        ],
        "weight": 0.75
    },
    "sad": {
        "keywords": [
            "sad", "dukhi", "down", "low", "upset", "depressed",
            "lonely", "miss", "hurt", "cry", "emotional", "feeling low",
            "unmotivated", "tired", "thak", "bore", "bored"
        ],
        "weight": 0.7
    },
    "happy": {
        "keywords": [
            "happy", "khush", "good", "nice", "thank", "shukriya",
            "dhanyawad", "helped", "solved", "done", "complete",
            "working", "chal gaya", "ho gaya", "yay", "haha", "lol"
        ],
        "weight": 0.6
    }
}

# ─── Tone Adaptation Rules (from emotions.md §7.2) ────────────
TONE_RULES = {
    "frustrated": {
        "tone": "calm, reassuring, and structured",
        "rules": [
            "Start with reassurance - 'Dekh, ye fix hoga'",
            "Break solution into clear steps",
            "Avoid blame tone completely",
            "Be patient and supportive"
        ]
    },
    "excited": {
        "tone": "energetic, motivational, and action-oriented",
        "rules": [
            "Match the user's energy level",
            "Encourage action and progress",
            "Be enthusiastic but practical"
        ]
    },
    "confused": {
        "tone": "simple, clear, and educational",
        "rules": [
            "Simplify explanation significantly",
            "Use real-world examples",
            "Break down complex concepts",
            "Ask if they want more detail"
        ]
    },
    "stressed": {
        "tone": "calm, prioritizing, and structured",
        "rules": [
            "Prioritize tasks for them",
            "Provide calm structured response",
            "Help them focus on one thing at a time",
            "Offer to handle some tasks"
        ]
    },
    "sad": {
        "tone": "empathetic, warm, and supportive",
        "rules": [
            "Show genuine empathy",
            "Be a good listener",
            "Don't dismiss feelings",
            "Gently suggest positive actions"
        ]
    },
    "happy": {
        "tone": "warm, friendly, and celebratory",
        "rules": [
            "Share in their happiness",
            "Acknowledge their achievement",
            "Be genuinely warm"
        ]
    },
    "neutral": {
        "tone": "balanced, friendly, and direct",
        "rules": [
            "Be helpful and efficient",
            "Get to the point",
            "Maintain warm conversational tone"
        ]
    }
}


def detect_emotion(text: str, history: list = None) -> EmotionState:
    """
    Detect user emotional state from text using keyword-based scoring.
    Returns EmotionState with detected emotion, confidence, and tone instructions.
    """
    text_lower = text.lower()
    scores = {}

    # Score each emotion based on keyword matches
    for emotion, config in EMOTION_KEYWORDS.items():
        score = 0
        matched = 0
        for keyword in config["keywords"]:
            if keyword in text_lower:
                score += config["weight"]
                matched += 1
        if matched > 0:
            # Normalize score based on number of matches
            scores[emotion] = min(score, 1.0)

    # Determine dominant emotion
    if not scores:
        detected = "neutral"
        confidence = 0.5
    else:
        detected = max(scores, key=scores.get)
        confidence = min(scores[detected], 1.0)

    # Calculate individual levels
    frustration = scores.get("frustrated", 0.0)
    stress = scores.get("stressed", 0.0)
    energy = scores.get("excited", 0.3)
    if detected == "sad":
        energy = max(0.1, energy - 0.3)

    # Get tone instruction
    tone_rule = TONE_RULES.get(detected, TONE_RULES["neutral"])
    tone_instruction = tone_rule["tone"]

    return EmotionState(
        emotion=detected,
        confidence=round(confidence, 2),
        frustration_level=round(frustration * 10, 1),
        energy_level=round(energy * 10, 1),
        stress_level=round(stress * 10, 1),
        tone_instruction=tone_instruction
    )


def get_emotion_prompt_injection(emotion_state: EmotionState) -> str:
    """
    Generate the emotion-aware prompt injection for the system prompt.
    This is injected before the LLM call to guide response tone.
    """
    rules = TONE_RULES.get(emotion_state.emotion, TONE_RULES["neutral"])

    injection = f"""
[EMOTIONAL CONTEXT - INTERNAL, DO NOT SHARE WITH USER]
Detected User Emotion: {emotion_state.emotion} (confidence: {emotion_state.confidence})
Frustration Level: {emotion_state.frustration_level}/10
Stress Level: {emotion_state.stress_level}/10
Energy Level: {emotion_state.energy_level}/10

Required Response Tone: {rules['tone']}
Behavioral Rules:
"""
    for rule in rules["rules"]:
        injection += f"- {rule}\n"

    return injection
