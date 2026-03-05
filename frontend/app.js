/* ═══════════════════════════════════════════════════════════════
   JARVIS AI — Frontend Application Logic
   Handles WebSocket streaming, chat UI, memory dashboard,
   onboarding, voice input, and all user interactions.
   ═══════════════════════════════════════════════════════════════ */

// ─── State ────────────────────────────────────────────────────
const state = {
    ws: null,
    sessionId: 'session_' + Date.now(),
    userName: '',
    language: 'hinglish',
    isStreaming: false,
    currentStreamEl: null,
    onboardingStep: 1,
    reconnectAttempts: 0,
    maxReconnects: 5,
    isListening: false,
    recognition: null
};

// ─── DOM References ───────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    // Onboarding
    onboarding: $('#onboardingOverlay'),
    step1: $('#step1'),
    step2: $('#step2'),
    step3: $('#step3'),
    userName: $('#userName'),
    nextBtn: $('#nextBtn'),
    prevBtn: $('#prevBtn'),
    dots: $$('.step-dots .dot'),
    optionBtns: $$('.option-btn'),

    // App
    appContainer: $('#appContainer'),
    chatView: $('#chatView'),
    brainView: $('#brainView'),
    settingsView: $('#settingsView'),

    // Chat
    chatMessages: $('#chatMessages'),
    chatInput: $('#chatInput'),
    sendBtn: $('#sendBtn'),
    voiceBtn: $('#voiceBtn'),
    welcomeMessage: $('#welcomeMessage'),
    headerStatus: $('#headerStatus'),
    emotionBadge: $('#emotionBadge'),
    emotionIcon: $('#emotionIcon'),
    emotionText: $('#emotionText'),
    suggestionArea: $('#suggestionArea'),
    suggestionChips: $('#suggestionChips'),
    charCount: $('#inputCharCount'),

    // Navigation
    navChat: $('#navChat'),
    navBrain: $('#navBrain'),
    navSettings: $('#navSettings'),
    sidebar: $('#sidebar'),
    sidebarUserName: $('#sidebarUserName'),

    // Brain
    memoryList: $('#memoryList'),
    totalMemories: $('#totalMemories'),
    semanticCount: $('#semanticCount'),
    episodicCount: $('#episodicCount'),
    addMemoryBtn: $('#addMemoryBtn'),
    addMemoryModal: $('#addMemoryModal'),
    newMemoryContent: $('#newMemoryContent'),
    newMemoryTags: $('#newMemoryTags'),
    cancelAddMemory: $('#cancelAddMemory'),
    confirmAddMemory: $('#confirmAddMemory'),

    // Settings
    settingsName: $('#settingsName'),
    saveSettings: $('#saveSettings'),
    clearAllMemories: $('#clearAllMemories')
};

// ─── Initialize ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await checkOnboarding();
    setupEventListeners();
    setupVoiceInput();
});

// ═══════════════════════════════════════════════════════════════
// ONBOARDING
// ═══════════════════════════════════════════════════════════════
async function checkOnboarding() {
    try {
        const res = await fetch('/api/v1/profile');
        const profile = await res.json();
        if (profile.onboarding_complete) {
            state.userName = profile.user_name || '';
            skipOnboarding();
        }
    } catch {
        // First time or server not ready — show onboarding
    }
}

function skipOnboarding() {
    dom.onboarding.style.display = 'none';
    dom.appContainer.style.display = 'flex';
    updateUserDisplay();
    connectWebSocket();
}

function updateOnboardingStep(step) {
    state.onboardingStep = step;
    [dom.step1, dom.step2, dom.step3].forEach((el, i) => {
        el.classList.toggle('active', i + 1 === step);
    });
    dom.dots.forEach((dot, i) => {
        dot.classList.toggle('active', i + 1 === step);
    });
    dom.prevBtn.style.visibility = step > 1 ? 'visible' : 'hidden';
    dom.nextBtn.textContent = step === 3 ? 'Start JARVIS 🚀' : 'Next →';
}

// ═══════════════════════════════════════════════════════════════
// WEBSOCKET CONNECTION
// ═══════════════════════════════════════════════════════════════
function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/chat`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log('✅ JARVIS WebSocket connected');
        dom.headerStatus.textContent = 'Online — Ready to chat';
        state.reconnectAttempts = 0;
    };

    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerEvent(data);
    };

    state.ws.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        dom.headerStatus.textContent = 'Reconnecting...';
        if (state.reconnectAttempts < state.maxReconnects) {
            state.reconnectAttempts++;
            setTimeout(connectWebSocket, 2000 * state.reconnectAttempts);
        }
    };

    state.ws.onerror = (err) => {
        console.error('❌ WebSocket error:', err);
    };
}

function sendMessage(text) {
    if (!text.trim() || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;

    // Hide welcome message
    if (dom.welcomeMessage) {
        dom.welcomeMessage.style.display = 'none';
    }

    // Add user message to chat
    addMessageToChat('user', text);

    // Show typing indicator
    showTypingIndicator();

    // Send via WebSocket
    state.ws.send(JSON.stringify({
        event: 'user_message',
        payload: {
            text: text,
            session_id: state.sessionId
        }
    }));

    // Clear input
    dom.chatInput.value = '';
    dom.chatInput.style.height = 'auto';
    dom.sendBtn.classList.remove('active');
    dom.charCount.textContent = '0';
    dom.suggestionArea.style.display = 'none';
}

// ─── Handle Server Events ─────────────────────────────────────
function handleServerEvent(data) {
    const { event, payload } = data;

    switch (event) {
        case 'processing_started':
            dom.headerStatus.textContent = `Thinking... (${payload.intent})`;
            updateEmotionBadge(payload.emotion);
            break;

        case 'text_stream':
            removeTypingIndicator();
            if (!state.isStreaming) {
                state.isStreaming = true;
                state.currentStreamEl = addMessageToChat('assistant', '', true);
            }
            appendStreamChunk(payload.chunk);
            break;

        case 'stream_complete':
            state.isStreaming = false;
            state.currentStreamEl = null;
            dom.headerStatus.textContent = 'Online — Ready to chat';
            removeTypingIndicator();

            // Show suggestion chips
            if (payload.suggestions && payload.suggestions.length > 0) {
                showSuggestions(payload.suggestions);
            }
            break;

        case 'onboarding_complete':
            console.log('✅ Onboarding saved for:', payload.name);
            break;

        case 'error':
            removeTypingIndicator();
            addMessageToChat('assistant', `⚠️ ${payload.message}`);
            dom.headerStatus.textContent = 'Online — Ready to chat';
            break;
    }
}

// ═══════════════════════════════════════════════════════════════
// CHAT UI
// ═══════════════════════════════════════════════════════════════
function addMessageToChat(role, text, isStreaming = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatarText = role === 'assistant' ? 'J' : (state.userName?.[0]?.toUpperCase() || 'U');

    msgDiv.innerHTML = `
        <div class="message-avatar">${avatarText}</div>
        <div class="message-bubble">${isStreaming ? '' : escapeHtml(text)}</div>
    `;

    dom.chatMessages.appendChild(msgDiv);
    scrollToBottom();

    return msgDiv;
}

function appendStreamChunk(chunk) {
    if (state.currentStreamEl) {
        const bubble = state.currentStreamEl.querySelector('.message-bubble');
        if (bubble) {
            bubble.textContent += chunk;
            scrollToBottom();
        }
    }
}

function showTypingIndicator() {
    removeTypingIndicator();
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `
        <div class="message-avatar" style="background:var(--accent-gradient);color:white;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;">J</div>
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    dom.chatMessages.appendChild(indicator);
    scrollToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

function showSuggestions(suggestions) {
    dom.suggestionChips.innerHTML = '';
    suggestions.forEach(text => {
        const chip = document.createElement('button');
        chip.className = 'chip';
        chip.textContent = text;
        chip.addEventListener('click', () => {
            sendMessage(text);
            dom.suggestionArea.style.display = 'none';
        });
        dom.suggestionChips.appendChild(chip);
    });
    dom.suggestionArea.style.display = 'block';
}

function updateEmotionBadge(emotion) {
    const emotionIcons = {
        frustrated: '😤',
        excited: '🤩',
        confused: '😕',
        stressed: '😰',
        sad: '😢',
        happy: '😊',
        neutral: '😊'
    };
    dom.emotionIcon.textContent = emotionIcons[emotion] || '😊';
    dom.emotionText.textContent = emotion;
    dom.emotionBadge.style.display = 'flex';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        dom.emotionBadge.style.display = 'none';
    }, 5000);
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ═══════════════════════════════════════════════════════════════
// VOICE INPUT (Web Speech API)
// ═══════════════════════════════════════════════════════════════
function setupVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        dom.voiceBtn.style.display = 'none';
        return;
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    state.recognition = new SpeechRec();
    state.recognition.continuous = false;
    state.recognition.interimResults = true;
    state.recognition.lang = 'hi-IN'; // Hinglish / Hindi

    state.recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
            .map(r => r[0].transcript)
            .join('');
        dom.chatInput.value = transcript;
        updateSendButton();
    };

    state.recognition.onend = () => {
        state.isListening = false;
        dom.voiceBtn.classList.remove('listening');
        // Auto-send if we got text
        if (dom.chatInput.value.trim()) {
            sendMessage(dom.chatInput.value.trim());
        }
    };

    state.recognition.onerror = () => {
        state.isListening = false;
        dom.voiceBtn.classList.remove('listening');
    };
}

function toggleVoice() {
    if (!state.recognition) return;
    if (state.isListening) {
        state.recognition.stop();
        state.isListening = false;
        dom.voiceBtn.classList.remove('listening');
    } else {
        state.recognition.start();
        state.isListening = true;
        dom.voiceBtn.classList.add('listening');
    }
}

// ═══════════════════════════════════════════════════════════════
// MEMORY DASHBOARD (THE BRAIN)
// ═══════════════════════════════════════════════════════════════
async function loadMemories(type = '') {
    try {
        const url = type ? `/api/v1/memory?type=${type}` : '/api/v1/memory';
        const res = await fetch(url);
        const data = await res.json();

        const memories = data.data || [];

        // Update stats
        dom.totalMemories.textContent = memories.length;
        dom.semanticCount.textContent = memories.filter(m => m.type === 'semantic').length;
        dom.episodicCount.textContent = memories.filter(m => m.type === 'episodic').length;

        // Render memory list
        if (memories.length === 0) {
            dom.memoryList.innerHTML = `
                <div class="memory-empty">
                    <p>🧠 No memories yet. Start chatting with JARVIS to build your digital brain!</p>
                </div>
            `;
            return;
        }

        dom.memoryList.innerHTML = memories.map(m => {
            const tags = (m.tags || []).map(t => `<span class="memory-tag">${t}</span>`).join(' ');
            const date = new Date(m.created_at).toLocaleDateString('en-IN', {
                day: 'numeric', month: 'short', year: 'numeric'
            });
            return `
                <div class="memory-card" data-id="${m.memory_id}">
                    <div class="memory-info">
                        <div class="memory-content">${escapeHtml(m.content)}</div>
                        <div class="memory-meta">
                            <span>${m.type}</span>
                            <span>${date}</span>
                            ${tags}
                        </div>
                    </div>
                    <button class="memory-delete" onclick="deleteMemoryCard('${m.memory_id}')" title="Delete memory">🗑️</button>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Failed to load memories:', err);
    }
}

async function deleteMemoryCard(memoryId) {
    try {
        await fetch(`/api/v1/memory/${memoryId}`, { method: 'DELETE' });
        const card = document.querySelector(`[data-id="${memoryId}"]`);
        if (card) {
            card.style.opacity = '0';
            card.style.transform = 'translateX(20px)';
            card.style.transition = '0.3s ease';
            setTimeout(() => {
                card.remove();
                loadMemories(); // Refresh stats
            }, 300);
        }
    } catch (err) {
        console.error('Failed to delete memory:', err);
    }
}
// Make it globally accessible for onclick
window.deleteMemoryCard = deleteMemoryCard;

async function addNewMemory() {
    const content = dom.newMemoryContent.value.trim();
    if (!content) return;

    const tags = dom.newMemoryTags.value.split(',').map(t => t.trim()).filter(Boolean);

    try {
        await fetch('/api/v1/memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, tags, type: 'semantic' })
        });
        dom.addMemoryModal.style.display = 'none';
        dom.newMemoryContent.value = '';
        dom.newMemoryTags.value = '';
        loadMemories();
    } catch (err) {
        console.error('Failed to add memory:', err);
    }
}

// ═══════════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════════
function switchView(view) {
    // Update nav buttons
    [dom.navChat, dom.navBrain, dom.navSettings].forEach(btn => btn.classList.remove('active'));

    // Show/hide views
    dom.chatView.style.display = 'none';
    dom.brainView.style.display = 'none';
    dom.settingsView.style.display = 'none';

    switch (view) {
        case 'chat':
            dom.chatView.style.display = 'flex';
            dom.navChat.classList.add('active');
            break;
        case 'brain':
            dom.brainView.style.display = 'flex';
            dom.navBrain.classList.add('active');
            loadMemories();
            break;
        case 'settings':
            dom.settingsView.style.display = 'flex';
            dom.navSettings.classList.add('active');
            dom.settingsName.value = state.userName;
            break;
    }

    // Close sidebar on mobile
    dom.sidebar.classList.remove('open');
}

function updateUserDisplay() {
    if (state.userName) {
        dom.sidebarUserName.textContent = state.userName;
        const avatarEl = document.querySelector('.user-avatar');
        if (avatarEl) avatarEl.textContent = state.userName[0].toUpperCase();
    }
}

function updateSendButton() {
    const hasText = dom.chatInput.value.trim().length > 0;
    dom.sendBtn.classList.toggle('active', hasText);
    dom.charCount.textContent = dom.chatInput.value.length;
}

// ═══════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════
function setupEventListeners() {
    // ─── Onboarding ───
    dom.nextBtn.addEventListener('click', () => {
        if (state.onboardingStep === 1) {
            const name = dom.userName.value.trim();
            if (!name) {
                dom.userName.style.borderColor = 'var(--danger)';
                dom.userName.focus();
                return;
            }
            state.userName = name;
            updateOnboardingStep(2);
        } else if (state.onboardingStep === 2) {
            updateOnboardingStep(3);
        } else if (state.onboardingStep === 3) {
            // Complete onboarding
            dom.onboarding.style.opacity = '0';
            dom.onboarding.style.transition = '0.4s ease';
            setTimeout(() => {
                dom.onboarding.style.display = 'none';
                dom.appContainer.style.display = 'flex';
                updateUserDisplay();
                connectWebSocket();
                // Send onboarding data
                setTimeout(() => {
                    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                        state.ws.send(JSON.stringify({
                            event: 'onboarding',
                            payload: {
                                name: state.userName,
                                preferences: { language: state.language }
                            }
                        }));
                    }
                }, 1000);
            }, 400);
        }
    });

    dom.prevBtn.addEventListener('click', () => {
        if (state.onboardingStep > 1) {
            updateOnboardingStep(state.onboardingStep - 1);
        }
    });

    dom.userName.addEventListener('input', () => {
        dom.userName.style.borderColor = '';
    });
    dom.userName.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') dom.nextBtn.click();
    });

    // Language option buttons
    dom.optionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            dom.optionBtns.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            state.language = btn.dataset.lang;
        });
    });

    // ─── Chat Input ───
    dom.chatInput.addEventListener('input', () => {
        updateSendButton();
        // Auto-resize textarea
        dom.chatInput.style.height = 'auto';
        dom.chatInput.style.height = Math.min(dom.chatInput.scrollHeight, 120) + 'px';
    });

    dom.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (dom.chatInput.value.trim()) {
                sendMessage(dom.chatInput.value.trim());
            }
        }
    });

    dom.sendBtn.addEventListener('click', () => {
        if (dom.chatInput.value.trim()) {
            sendMessage(dom.chatInput.value.trim());
        }
    });

    dom.voiceBtn.addEventListener('click', toggleVoice);

    // ─── Welcome Chips ───
    document.querySelectorAll('.welcome-chips .chip').forEach(chip => {
        chip.addEventListener('click', () => {
            sendMessage(chip.dataset.msg);
        });
    });

    // ─── Navigation ───
    dom.navChat.addEventListener('click', () => switchView('chat'));
    dom.navBrain.addEventListener('click', () => switchView('brain'));
    dom.navSettings.addEventListener('click', () => switchView('settings'));

    // Menu toggle (mobile)
    $$('.menu-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            dom.sidebar.classList.toggle('open');
        });
    });

    // ─── Memory Tabs ───
    $$('.tab-btn').forEach(tab => {
        tab.addEventListener('click', () => {
            $$('.tab-btn').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            loadMemories(tab.dataset.type);
        });
    });

    // ─── Add Memory Modal ───
    dom.addMemoryBtn.addEventListener('click', () => {
        dom.addMemoryModal.style.display = 'flex';
    });
    dom.cancelAddMemory.addEventListener('click', () => {
        dom.addMemoryModal.style.display = 'none';
    });
    dom.confirmAddMemory.addEventListener('click', addNewMemory);

    // ─── Settings ───
    dom.saveSettings.addEventListener('click', async () => {
        const name = dom.settingsName.value.trim();
        if (name) {
            state.userName = name;
            await fetch('/api/v1/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            updateUserDisplay();
            dom.saveSettings.textContent = '✓ Saved!';
            setTimeout(() => dom.saveSettings.textContent = 'Save Changes', 2000);
        }
    });

    dom.clearAllMemories.addEventListener('click', async () => {
        if (confirm('Are you sure? This will delete ALL your memories permanently.')) {
            const res = await fetch('/api/v1/memory');
            const data = await res.json();
            for (const m of data.data || []) {
                await fetch(`/api/v1/memory/${m.memory_id}`, { method: 'DELETE' });
            }
            loadMemories();
            alert('All memories cleared! 🧹');
        }
    });
}
