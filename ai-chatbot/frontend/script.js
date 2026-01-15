// API Configuration
const apiHost = window.location.hostname;
const apiPort = '8000';
const apiBaseUrl = `http://${apiHost}:${apiPort}/api/chatbot`;
const apiStreamUrl = `${apiBaseUrl}/stream/`;
const apiHistoryUrl = `${apiBaseUrl}/history/`;
const apiHealthUrl = `${apiBaseUrl}/health/`;

// State Management
let currentUserId = localStorage.getItem('chat_user_id');
if (!currentUserId) {
    currentUserId = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('chat_user_id', currentUserId);
}
let currentSessionId = null;  // Will be loaded and validated in DOMContentLoaded
let currentLanguage = localStorage.getItem('chat_language') || 'uz';
let currentTheme = localStorage.getItem('chat_theme') || 'light';
let isSidebarOpen = false;

// Translations Object for UI
const translations = {
    uz: {
        welcome_title: 'UzSWLU Intelligent Assistant',
        welcome_desc: "O'zbekiston Davlat Jahon Tillari Universiteti bo'yicha barcha savollaringizga javob beraman.",
        placeholder: 'Savolingizni yozing...',
        online: 'Server onlayn',
        offline: 'Server oflayn',
        newChat: 'Yangi suhbat',
        history: 'Suhbatlar tarixi',
        empty_history: 'Tarix mavjud emas',
        disclaimer: 'AI xato qilishi mumkin. Muhim ma\'lumotlarni rasmiy manbalardan tekshiring.',
        loading: 'Bot javob tayyorlamoqda...',
        user_label: 'Siz',
        bot_label: 'Assistant',
        suggested: [
            { category: 'Qabul', q: 'Qabul qachon boshlanadi?' },
            { category: 'Kontrakt', q: 'Kontrakt narxlari qancha?' },
            { category: 'Fakultetlar', q: 'Qanday fakultetlar bor?' },
            { category: 'Aloqa', q: 'Rektor bilan qanday bog\'lansa bo\'ladi?' }
        ],
        greeting: 'Salom! Men UzSWLU AI asistentiman. Sizga qanday yordam bera olaman?'
    },
    ru: {
        welcome_title: 'UzSWLU Intelligent Assistant',
        welcome_desc: "Я отвечу на все ваши вопросы об Узбекском государственном университете мировых языков.",
        placeholder: 'Введите ваш вопрос...',
        online: 'Сервер онлайн',
        offline: 'Сервер оффлайн',
        newChat: 'Новый чат',
        history: 'История чатов',
        empty_history: 'История пуста',
        disclaimer: 'AI может ошибаться. Проверяйте важную информацию в официальных источниках.',
        loading: 'Бот готовит ответ...',
        user_label: 'Вы',
        bot_label: 'Ассистент',
        suggested: [
            { category: 'Прием', q: 'Когда начинается прием?' },
            { category: 'Контракт', q: 'Какова стоимость контракта?' },
            { category: 'Факультеты', q: 'Какие есть факультеты?' },
            { category: 'Контакт', q: 'Как связаться с ректором?' }
        ],
        greeting: 'Здравствуйте! Я AI-ассистент УзГУМЯ. Чем я могу вам помочь?'
    },
    en: {
        welcome_title: 'UzSWLU Intelligent Assistant',
        welcome_desc: "I will answer all your questions about the Uzbekistan State World Languages University.",
        placeholder: 'Enter your question...',
        online: 'Server online',
        offline: 'Server offline',
        newChat: 'New chat',
        history: 'Chat history',
        empty_history: 'No history yet',
        disclaimer: 'AI may make mistakes. Verify important info from official sources.',
        loading: 'Bot is preparing answer...',
        user_label: 'You',
        bot_label: 'Assistant',
        suggested: [
            { category: 'Admission', q: 'When does admission start?' },
            { category: 'Tuition', q: 'How much is the tuition fee?' },
            { category: 'Faculties', q: 'What faculties are there?' },
            { category: 'Contact', q: 'How to contact the rector?' }
        ],
        greeting: 'Hello! I am the UzSWLU AI assistant. How can I help you today?'
    }
};

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initLanguage();
    initEventListeners();
    checkStatus();

    // Check if we have a valid session ID from localStorage
    const storedSessionId = localStorage.getItem('chat_session_id');

    console.log('Initializing app - Session ID:', storedSessionId || 'None');

    if (storedSessionId && storedSessionId.trim() !== '') {
        // We have a valid session, load its history
        currentSessionId = storedSessionId;
        loadHistory();
    } else {
        // No valid session, start fresh
        currentSessionId = null;
        localStorage.removeItem('chat_session_id');
        sessionStorage.removeItem('chat_session_id');
        document.getElementById('welcome-screen').classList.remove('hidden');
        renderSuggested();
    }

    refreshSessionHistory();
});

function initTheme() {
    document.documentElement.setAttribute('data-theme', currentTheme);
    const icon = document.querySelector('.icon-theme');
    if (icon) icon.textContent = currentTheme === 'light' ? '🌙' : '☀️';
}

function initLanguage() {
    const select = document.getElementById('language-select');
    select.value = currentLanguage;
    updateUIStrings();
}

function initEventListeners() {
    // Basic Actions
    document.getElementById('send-button').addEventListener('click', sendMessage);
    document.getElementById('user-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    document.getElementById('language-select').addEventListener('change', (e) => switchLanguage(e.target.value));

    // Sidebar Actions
    document.getElementById('sidebar-open-btn').addEventListener('click', () => toggleSidebar(true));
    document.getElementById('sidebar-close-btn').addEventListener('click', () => toggleSidebar(false));
    document.getElementById('new-chat-sidebar').addEventListener('click', startNewChat);

    // Auto-resize textarea
    const textarea = document.getElementById('user-input');
    textarea.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
}

// --- UI Logic ---

function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    localStorage.setItem('chat_theme', currentTheme);
    initTheme();
}

function switchLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('chat_language', lang);
    updateUIStrings();
    renderSuggested();
}

function updateUIStrings() {
    const t = translations[currentLanguage];
    document.getElementById('user-input').placeholder = t.placeholder;
    document.querySelector('.btn-new-chat-sidebar').innerHTML = `<span>＋</span> ${t.newChat}`;
    document.querySelector('.section-label').textContent = t.history;
    document.querySelector('.bot-disclaimer').textContent = t.disclaimer;
    document.getElementById('status-display-text').textContent = t.online;

    // Welcome screen text
    document.getElementById('welcome-screen').querySelector('h2').textContent = t.welcome_title;
    document.getElementById('welcome-screen').querySelector('p').textContent = t.welcome_desc;
}

function toggleSidebar(open) {
    const sidebar = document.getElementById('sidebar');
    if (open) {
        sidebar.classList.add('open');
    } else {
        sidebar.classList.remove('open');
    }
}

function renderSuggested() {
    const container = document.getElementById('suggested-questions-hero');
    const items = translations[currentLanguage].suggested;
    container.innerHTML = '';

    items.forEach(item => {
        const btn = document.createElement('button');
        btn.className = 'btn-suggested';
        btn.innerHTML = `<b>${item.category}</b><span>${item.q}</span>`;
        btn.onclick = () => {
            document.getElementById('user-input').value = item.q;
            sendMessage();
        };
        container.appendChild(btn);
    });
}

// --- Chat Core ---

async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    input.style.height = 'auto';

    // Hide welcome screen on first message
    document.getElementById('welcome-screen').classList.add('hidden');

    addMessage(text, 'user');

    const botMsgEl = addMessage('', 'bot', true);
    const contentDiv = botMsgEl.querySelector('.message-content');
    const loadingEl = document.getElementById('loading');
    loadingEl.classList.remove('hidden');

    try {
        console.log('Sending message with session_id:', currentSessionId);
        const response = await fetch(apiStreamUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: text,
                user_id: currentUserId,
                language: currentLanguage,
                session_id: currentSessionId  // Pass current session to backend
            })
        });

        if (!response.ok) throw new Error('Network error');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        loadingEl.classList.add('hidden');

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataString = line.slice(6).trim();
                    if (!dataString) continue;

                    try {
                        const data = JSON.parse(dataString);

                        if (data.session_id && !currentSessionId) {
                            currentSessionId = data.session_id;
                            localStorage.setItem('chat_session_id', currentSessionId);
                            console.log('Received new session_id from backend:', currentSessionId);
                            refreshSessionHistory();
                        }

                        if (data.chunk) {
                            fullText += data.chunk;
                            contentDiv.innerHTML = marked.parse(fullText);
                            scrollBottom();
                        }

                        if (data.done) {
                            contentDiv.innerHTML = marked.parse(fullText);
                            if (data.sources && data.sources.length > 0) {
                                renderSources(contentDiv, data.sources);
                            }
                            addCopyAction(contentDiv, fullText);
                        }

                        if (data.error) {
                            contentDiv.innerHTML = `<p style="color: #ef4444">Xatolik yuz berdi: ${data.error}</p>`;
                        }
                    } catch (e) { console.error("JSON Parse Error", e); }
                }
            }
        }
    } catch (err) {
        loadingEl.classList.add('hidden');
        contentDiv.innerHTML = `<p style="color: #ef4444">Xatolik: Tarmoq bilan muammo yuz berdi.</p>`;
    }
}

function addMessage(text, type, isInitialBot = false) {
    const container = document.getElementById('messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;

    const avatar = type === 'user' ? '👤' : '💠';

    msgDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            ${isInitialBot ? '<div class="typing-indicator-dot"></div>' : marked.parse(text)}
        </div>
    `;

    container.appendChild(msgDiv);
    scrollBottom();
    return msgDiv;
}

function renderSources(container, sources) {
    if (!sources || sources.length === 0) return;

    const sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'sources-container';

    sources.forEach(src => {
        const tag = document.createElement('div');
        tag.className = 'source-tag';
        const relevance = src.relevance !== undefined ? src.relevance : 0;
        tag.innerHTML = `<span>🔍</span> ${src.title} (${relevance}%)`;
        sourcesDiv.appendChild(tag);
    });

    container.appendChild(sourcesDiv);
}

function addCopyAction(container, text) {
    const btn = document.createElement('button');
    btn.className = 'copy-btn-mini';
    btn.innerHTML = '📋 Nusxa';
    btn.onclick = () => {
        navigator.clipboard.writeText(text);
        btn.innerHTML = '✅ Nusxalandi';
        setTimeout(() => btn.innerHTML = '📋 Nusxa', 2000);
    };
    container.appendChild(btn);
}

function scrollBottom() {
    const chatBox = document.getElementById('chat-box');
    chatBox.scrollTo({
        top: chatBox.scrollHeight,
        behavior: 'smooth'
    });
}

// --- Session & History ---

async function startNewChat() {
    // IMPORTANT: Completely clear current session from both memory and storage
    currentSessionId = null;
    localStorage.removeItem('chat_session_id');

    // Also clear from sessionStorage to prevent any caching issues
    sessionStorage.removeItem('chat_session_id');

    // Clear UI completely
    document.getElementById('messages').innerHTML = '';
    document.getElementById('welcome-screen').classList.remove('hidden');
    document.getElementById('user-input').value = '';
    document.getElementById('user-input').focus();
    renderSuggested();

    // Update sidebar to show empty state
    refreshSessionHistory();

    console.log('New chat started - all session data cleared');
}

async function refreshSessionHistory() {
    const list = document.getElementById('chat-history-list');
    list.innerHTML = '';

    if (currentSessionId) {
        const item = document.createElement('div');
        item.className = 'history-item active';
        item.textContent = `Suhbat: ${currentSessionId.substring(0, 8)}`;
        list.appendChild(item);
    } else {
        list.innerHTML = `<div class="history-empty">${translations[currentLanguage].empty_history}</div>`;
    }
}

async function loadHistory() {
    // CRITICAL: Only load history if we have a specific session ID
    if (!currentSessionId || currentSessionId.trim() === '') {
        console.log('No valid session ID - skipping history load');
        return;
    }

    console.log('Loading history for session:', currentSessionId);

    try {
        // Request history for THIS specific session only
        const res = await fetch(`${apiHistoryUrl}?user_id=${currentUserId}&session_id=${currentSessionId}`);
        if (res.ok) {
            const conversations = await res.json();
            if (conversations.length > 0) {
                const conv = conversations[0];

                // Verify this is the correct session
                if (conv.id !== currentSessionId) {
                    console.log('Session ID mismatch - aborting history load');
                    return;
                }

                console.log('Loading', conv.messages.length, 'messages');
                document.getElementById('welcome-screen').classList.add('hidden');
                document.getElementById('messages').innerHTML = '';

                conv.messages.forEach(msg => {
                    const type = msg.sender_type === 'user' ? 'user' : 'bot';
                    const botEl = addMessage(msg.text, type);
                    if (type === 'bot') {
                        const contentDiv = botEl.querySelector('.message-content');
                        // Add sources if available in metadata
                        if (msg.metadata && msg.metadata.sources && msg.metadata.sources.length > 0) {
                            renderSources(contentDiv, msg.metadata.sources);
                        }
                        addCopyAction(contentDiv, msg.text);
                    }
                });
                scrollBottom();
                refreshSessionHistory();
            } else {
                console.log('No conversations found for this session');
            }
        }
    } catch (e) {
        console.error("History load error", e);
    }
}

async function checkStatus() {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.getElementById('status-display-text');

    try {
        const res = await fetch(apiHealthUrl);
        if (res.ok) {
            statusDot.classList.remove('offline');
            statusText.textContent = translations[currentLanguage].online;
        } else {
            statusDot.classList.add('offline');
            statusText.textContent = translations[currentLanguage].offline;
        }
    } catch (e) {
        statusDot.classList.add('offline');
        statusText.textContent = translations[currentLanguage].offline;
    }
}
