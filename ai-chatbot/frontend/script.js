// API Configuration - Use same hostname as frontend, but port 8000 for backend
const apiHost = window.location.hostname;
const apiPort = '8000';
const apiBaseUrl = `http://${apiHost}:${apiPort}/api/chatbot`;
const apiUrl = `${apiBaseUrl}/ask/`;
const apiStreamUrl = `${apiBaseUrl}/stream/`;
const apiListUrl = `${apiBaseUrl}/`;
const apiHistoryUrl = `${apiBaseUrl}/history/`;
const apiHealthUrl = `${apiBaseUrl}/health/`;

// Session management - preserve session on reload
let currentSessionId = localStorage.getItem('chat_session_id');
let useStreaming = true;
let currentLanguage = localStorage.getItem('chat_language') || 'uz';

// Til sozlamalari
const translations = {
    uz: {
        greeting: '👋 Salom! Men AI asistentman. Savolingizni bering va men javob berishga harakat qilaman.',
        placeholder: 'Savolingizni yozing...',
        sendButton: 'Yuborish',
        statusOnline: 'Ishga tushdi ✓',
        statusOffline: 'Ishga tushmadi ✗',
        statusConnecting: 'Ishga tushmoqda...',
        error: 'Xatolik',
        noResponse: 'Javob olinmadi',
        botLabel: '🤖 Bot:',
        userLabel: '👤 Siz:',
        copy: 'Nusxa olish',
        copied: 'Nusxalandi!',
        regenerate: 'Qayta generatsiya'
    },
    ru: {
        greeting: '👋 Привет! Я AI ассистент. Задайте свой вопрос, и я постараюсь ответить.',
        placeholder: 'Введите ваш вопрос...',
        sendButton: 'Отправить',
        statusOnline: 'Работает ✓',
        statusOffline: 'Не работает ✗',
        statusConnecting: 'Запускается...',
        error: 'Ошибка',
        noResponse: 'Ответ не получен',
        botLabel: '🤖 Бот:',
        userLabel: '👤 Вы:',
        copy: 'Копировать',
        copied: 'Скопировано!',
        regenerate: 'Перегенерировать'
    },
    en: {
        greeting: '👋 Hello! I am an AI assistant. Ask your question and I will try to answer.',
        placeholder: 'Type your question...',
        sendButton: 'Send',
        statusOnline: 'Online ✓',
        statusOffline: 'Offline ✗',
        statusConnecting: 'Connecting...',
        error: 'Error',
        noResponse: 'No response received',
        botLabel: '🤖 Bot:',
        userLabel: '👤 You:',
        copy: 'Copy',
        copied: 'Copied!',
        regenerate: 'Regenerate'
    }
};

// Til o'zgartirish funksiyasi
function changeLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('chat_language', lang);
    updateUIForLanguage(lang);
}

// UI'ni tilga moslashtirish
function updateUIForLanguage(lang) {
    const t = translations[lang];
    document.getElementById('user-input').placeholder = t.placeholder;
    document.getElementById('send-button').textContent = t.sendButton;
    document.getElementById('status-text').textContent = t.statusConnecting;

    // Greeting'ni yangilash
    const messagesDiv = document.getElementById('messages');
    const firstMessage = messagesDiv.querySelector('.message.bot');
    if (firstMessage) {
        firstMessage.innerHTML = `<div class="bot-label">${t.botLabel}</div><div class="bot-text">${t.greeting}</div>`;
    }
}

// Til tanlash event listener
document.addEventListener('DOMContentLoaded', () => {
    const langSelect = document.getElementById('language-select');
    if (langSelect) {
        langSelect.value = currentLanguage;
        langSelect.addEventListener('change', (e) => {
            changeLanguage(e.target.value);
        });
    }
    updateUIForLanguage(currentLanguage);

    // Initial greeting based on selected language
    const t = translations[currentLanguage] || translations['uz'];
    addMessageToChat(t.greeting, 'bot');

    checkApiStatus();
    renderSuggestedQuestions();

    // Load history if session exists
    if (currentSessionId) {
        loadHistory();
    }
});

async function loadHistory() {
    if (!currentSessionId) return;

    try {
        const response = await fetch(`${apiHistoryUrl}?session_id=${currentSessionId}`);
        if (response.ok) {
            const data = await response.json();

            // Set language if returned (auto-detected from server)
            if (data.language && data.language !== currentLanguage) {
                changeLanguage(data.language);
                const langSelect = document.getElementById('language-select');
                if (langSelect) langSelect.value = data.language;
            }

            // Render history
            if (data.history && data.history.length > 0) {
                const messagesDiv = document.getElementById('messages');
                // Clear default greeting if we have history
                if (messagesDiv.children.length > 0) {
                    messagesDiv.innerHTML = '';
                }

                data.history.forEach(turn => {
                    addMessageToChat(turn.user, 'user');

                    // Manually add bot message to attach actions/markdown
                    const messageElement = document.createElement('div');
                    messageElement.className = 'message bot';
                    const t = translations[currentLanguage] || translations['uz'];
                    messageElement.innerHTML = `<div class="bot-label">${t.botLabel}</div><div class="bot-text">${marked.parse(turn.bot)}</div>`;
                    messagesDiv.appendChild(messageElement);

                    // Add actions (copy/feedback) - using timestamp as psuedo-ID if needed or just random
                    addMessageActions(messageElement, null, turn.bot);
                });
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

async function checkApiStatus() {
    try {
        const response = await fetch(apiHealthUrl, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        if (response.ok) {
            const data = await response.json();
            const t = translations[currentLanguage] || translations['uz'];
            updateStatus(true, t.statusOnline);
            return true;
        } else {
            const t = translations[currentLanguage] || translations['uz'];
            updateStatus(false, `${t.error}: ${response.status} ✗`);
            return false;
        }
    } catch (error) {
        console.error('API status check error:', error);
        const t = translations[currentLanguage] || translations['uz'];
        updateStatus(false, `${t.statusOffline}: ${error.message} ✗`);
        return false;
    }
}

function updateStatus(isOnline, text) {
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');

    if (isOnline) {
        indicator.classList.add('online');
        indicator.classList.remove('offline');
    } else {
        indicator.classList.add('offline');
        indicator.classList.remove('online');
    }
    statusText.textContent = text;
}

document.getElementById('send-button').addEventListener('click', sendMessage);

document.getElementById('user-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

async function sendMessage() {
    const userInput = document.getElementById('user-input').value.trim();
    if (!userInput) return;

    document.getElementById('user-input').value = '';
    document.getElementById('send-button').disabled = true;
    document.getElementById('user-input').disabled = true;

    addMessageToChat(userInput, 'user');

    if (useStreaming) {
        await sendMessageStreaming(userInput);
    } else {
        await sendMessageRegular(userInput);
    }

    document.getElementById('send-button').disabled = false;
    document.getElementById('user-input').disabled = false;
    document.getElementById('user-input').focus();
}

async function sendMessageStreaming(userInput) {
    const messagesDiv = document.getElementById('messages');

    const messageElement = document.createElement('div');
    messageElement.className = 'message bot';
    const t = translations[currentLanguage] || translations['uz'];
    messageElement.innerHTML = `<div class="bot-label">${t.botLabel}</div><div class="bot-text"><span class="typing-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span></div>`;
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    const textContainer = messageElement.querySelector('.bot-text');
    let fullText = '';

    try {
        const response = await fetch(apiStreamUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: userInput,
                session_id: currentSessionId,
                language: currentLanguage
            })
        });

        if (!response.ok) {
            throw new Error('HTTP ' + response.status);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let firstChunk = true;

        while (true) {
            const result = await reader.read();
            if (result.done) break;

            const chunk = decoder.decode(result.value);
            const lines = chunk.split('\n').filter(l => l.trim());

            for (const line of lines) {
                const jsonStr = line.startsWith('data: ') ? line.slice(6) : line;

                try {
                    const data = JSON.parse(jsonStr);

                    // Update session_id if received
                    if (data.session_id) {
                        currentSessionId = data.session_id;
                        localStorage.setItem('chat_session_id', currentSessionId);
                    }

                    if (data.chunk) {
                        if (firstChunk) {
                            textContainer.innerHTML = '';
                            firstChunk = false;
                        }
                        fullText += data.chunk;
                        // Render markdown for streaming
                        textContainer.innerHTML = marked.parse(fullText) + '<span class="cursor"></span>';
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }

                    if (data.done) {
                        textContainer.innerHTML = marked.parse(fullText) || 'Javob olinmadi';
                        // Show sources if available
                        if (data.sources && data.sources.length > 0) {
                            const sourcesHtml = data.sources.map(src =>
                                `<div class="source-item">
                                    <span class="source-icon">📄</span>
                                    <span class="source-title">${src.title}</span>
                                    <span class="source-badge">${src.relevance}%</span>
                                </div>`
                            ).join('');
                            textContainer.innerHTML += `<div class="sources-container">
                                <div class="sources-header">Manbalar:</div>
                                ${sourcesHtml}
                            </div>`;
                        }

                        addMessageActions(messageElement, data.response_id, fullText);
                    }

                    if (data.error) {
                        textContainer.innerHTML = '<span class="error">❌ Xatolik: ' + data.error + '</span>';
                    }

                } catch (e) {
                    console.log('Parse error:', e);
                }
            }
        }

    } catch (error) {
        console.error('Streaming error:', error);
        let errorMessage = error.message;
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage = 'Backend serverga ulanib bo\'lmadi. Iltimos, backend ishlab turganini tekshiring.';
        }
        textContainer.innerHTML = '<span class="error">❌ Xatolik: ' + errorMessage + '</span>';
    }
}

async function sendMessageRegular(userInput) {
    const messagesDiv = document.getElementById('messages');

    const messageElement = document.createElement('div');
    messageElement.className = 'message bot';
    const t = translations[currentLanguage] || translations['uz'];
    messageElement.innerHTML = `<div class="bot-label">${t.botLabel}</div><div class="bot-text"><span class="typing-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span></div>`;
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    const textContainer = messageElement.querySelector('.bot-text');

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: userInput,
                session_id: currentSessionId,
                language: currentLanguage
            })
        });

        const data = await response.json();

        if (data.session_id) {
            currentSessionId = data.session_id;
            localStorage.setItem('chat_session_id', currentSessionId);
        }

        if (data.error) {
            textContainer.innerHTML = '<span class="error">❌ ' + data.error + '</span>';
        } else {
            textContainer.innerHTML = marked.parse(data.response) || 'Javob olinmadi';

            // Show sources if available
            if (data.sources && data.sources.length > 0) {
                const sourcesHtml = data.sources.map(src =>
                    `<div class="source-item" style="margin-top: 8px; padding: 6px; background: #f0f0f0; border-radius: 4px; font-size: 12px;">
                        📄 ${src.title} (${src.relevance}%)
                    </div>`
                ).join('');
                textContainer.innerHTML += `<div class="sources-container" style="margin-top: 10px;">${sourcesHtml}</div>`;
            }

            addMessageActions(messageElement, data.id, data.response);
        }

    } catch (error) {
        console.error('Error:', error);
        let errorMessage = error.message;
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage = 'Backend serverga ulanib bo\'lmadi. Iltimos, backend ishlab turganini tekshiring.';
        }
        textContainer.innerHTML = '<span class="error">❌ Xatolik: ' + errorMessage + '</span>';
    }
}

function addMessageToChat(text, type) {
    const messagesDiv = document.getElementById('messages');
    const messageElement = document.createElement('div');
    messageElement.className = 'message ' + type;

    const t = translations[currentLanguage] || translations['uz'];
    if (type === 'user') {
        messageElement.innerHTML = `<div class="user-text">${t.userLabel} ${text}</div>`;
    } else {
        // Render markdown for initial/regular bot messages
        messageElement.innerHTML = `<div class="bot-label">${t.botLabel}</div><div class="bot-text">${marked.parse(text)}</div>`;
    }

    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addMessageActions(messageElement, responseId = null, text = '') {
    // Check if actions already exist
    if (messageElement.querySelector('.message-actions')) {
        return;
    }

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';

    // Get response ID
    const msgId = responseId || messageElement.dataset.responseId || Date.now();
    messageElement.dataset.responseId = msgId;

    const t = translations[currentLanguage] || translations['uz'];

    actionsDiv.innerHTML = `
        <div class="feedback-btns">
            <button class="feedback-btn" onclick="sendFeedback('positive', this, '${msgId}')" title="Yaxshi javob">👍</button>
            <button class="feedback-btn" onclick="sendFeedback('negative', this, '${msgId}')" title="Yomon javob">👎</button>
        </div>
        <button class="copy-btn" onclick="copyToClipboard(this, \`${text.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)" title="${t.copy}">
            <span class="copy-icon">📋</span> <span class="copy-text">${t.copy}</span>
        </button>
        <button class="regen-btn" onclick="regenerateLastMessage()" title="${t.regenerate}">
            <span class="regen-icon">🔄</span> <span class="regen-text">${t.regenerate}</span>
        </button>
    `;
    messageElement.appendChild(actionsDiv);
}

async function copyToClipboard(btn, text) {
    try {
        await navigator.clipboard.writeText(text);
        const t = translations[currentLanguage] || translations['uz'];
        const copyText = btn.querySelector('.copy-text');
        const originalText = copyText.textContent;
        copyText.textContent = t.copied;
        btn.classList.add('copied');

        setTimeout(() => {
            copyText.textContent = originalText;
            btn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
    }
}

async function sendFeedback(type, btn, responseId) {
    const parent = btn.parentElement;
    const originalHTML = parent.innerHTML;

    // Disable buttons
    parent.querySelectorAll('button').forEach(b => b.disabled = true);

    try {
        const response = await fetch(`${apiBaseUrl}/feedback/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                response_id: responseId,
                rating: type,
                feedback_text: ''
            })
        });

        if (response.ok) {
            parent.innerHTML = type === 'positive'
                ? '✅ Rahmat! Fikringiz biz uchun muhim.'
                : '❌ Bildirganingiz uchun rahmat, yaxshilaymiz!';
        } else {
            throw new Error('Failed to save feedback');
        }
    } catch (error) {
        console.error('Feedback error:', error);
        parent.innerHTML = originalHTML;
        alert('Feedback yuborishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.');
    }
}

const suggestedQuestions = [
    "Admission start date?",
    "Tuition fees for international students?",
    "Where is the university located?",
    "How to apply for a scholarship?"
];

function renderSuggestedQuestions() {
    const container = document.getElementById('suggested-questions');
    if (!container) return;

    container.innerHTML = '';
    suggestedQuestions.forEach(q => {
        const btn = document.createElement('button');
        btn.className = 'suggested-btn';
        btn.textContent = q;
        btn.onclick = () => {
            document.getElementById('user-input').value = q;
            sendMessage();
        };
        container.appendChild(btn);
    });
}

// DOMContentLoaded event listener endi yuqorida qo'shilgan

// ==================== DOCUMENT UPLOAD FUNCTIONALITY ====================
const docUploadBtn = document.getElementById('doc-upload-btn');
const docUploadModal = document.getElementById('doc-upload-modal');
const modalCloseBtn = document.getElementById('modal-close-btn');
const cancelBtn = document.getElementById('cancel-btn');
const uploadBtn = document.getElementById('upload-btn');
const fileInput = document.getElementById('file-input');
const urlInput = document.getElementById('url-input');
const docTitle = document.getElementById('doc-title');
const docDescription = document.getElementById('doc-description');
const uploadProgress = document.getElementById('upload-progress');
const progressFill = document.getElementById('progress-fill');
const uploadStatus = document.getElementById('upload-status');

// Modal open/close
if (docUploadBtn) {
    docUploadBtn.addEventListener('click', () => {
        docUploadModal.classList.remove('hidden');
    });
}

function closeModal() {
    docUploadModal.classList.add('hidden');
    // Reset form
    fileInput.value = '';
    urlInput.value = '';
    docTitle.value = '';
    docDescription.value = '';
    uploadProgress.classList.add('hidden');
    progressFill.style.width = '0%';
    document.getElementById('file-name').textContent = '📁 Fayl tanlash';
}

if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', closeModal);
}

if (cancelBtn) {
    cancelBtn.addEventListener('click', closeModal);
}

// File selection display
if (fileInput) {
    fileInput.addEventListener('change', (e) => {
        const fileName = e.target.files[0]?.name || '📁 Fayl tanlash';
        document.getElementById('file-name').textContent = fileName;

        // Auto-fill title from filename
        if (!docTitle.value && e.target.files[0]) {
            const name = e.target.files[0].name.split('.')[0];
            docTitle.value = name;
        }
    });
}

// Upload document
if (uploadBtn) {
    uploadBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        const url = urlInput.value.trim();
        const title = docTitle.value.trim();
        const description = docDescription.value.trim();

        // Validation
        if (!file && !url) {
            alert('Fayl yoki URL manzilni kiriting!');
            return;
        }

        if (file && url) {
            alert('Faqat fayl yoki URL manzilni kiriting, ikkalasini emas!');
            return;
        }

        if (!title) {
            alert('Hujjat nomini kiriting!');
            return;
        }

        // Prepare FormData
        const formData = new FormData();
        formData.append('title', title);
        if (description) {
            formData.append('description', description);
        }

        if (file) {
            formData.append('file', file);
        } else if (url) {
            formData.append('url', url);
        }

        // Show progress
        uploadProgress.classList.remove('hidden');
        uploadBtn.disabled = true;
        uploadStatus.textContent = 'Yuklanmoqda...';
        progressFill.style.width = '30%';

        try {
            const documentsUrl = `http://${apiHost}:${apiPort}/api/documents/`;
            const response = await fetch(documentsUrl, {
                method: 'POST',
                body: formData
            });

            progressFill.style.width = '100%';

            if (response.ok) {
                const data = await response.json();
                uploadStatus.textContent = '✅ Muvaffaqiyatli yuklandi!';

                setTimeout(() => {
                    closeModal();
                    alert('Hujjat muvaffaqiyatli yuklandi va qayta ishlanmoqda!');
                }, 1500);
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            uploadStatus.textContent = '❌ Xatolik: ' + error.message;
            progressFill.style.width = '0%';
        } finally {
            uploadBtn.disabled = false;
        }
    });
}

/**
 * Regenerates the last bot response by resending the last user message.
 */
async function regenerateLastMessage() {
    const messagesDiv = document.getElementById('messages');
    const userMessages = messagesDiv.querySelectorAll('.message.user');
    if (userMessages.length === 0) return;

    const lastUserMessage = userMessages[userMessages.length - userMessages.length > 0 ? 1 : 0]; // Safety check
    const userTextEl = lastUserMessage.querySelector('.user-text');
    if (!userTextEl) return;

    const questionText = userTextEl.textContent;
    // Remove prefix "👤 Siz: " or "👤 Вы: " or "👤 You: "
    const question = questionText.replace(/^👤\s*(Siz|Вы|You):\s*/, '').trim();

    // Find the bot message(s) that followed this user message and remove them
    let nextEl = lastUserMessage.nextElementSibling;
    while (nextEl && !nextEl.classList.contains('user')) {
        const toRemove = nextEl;
        nextEl = nextEl.nextElementSibling;
        if (toRemove.classList.contains('bot')) {
            toRemove.remove();
        }
    }

    // Prepare UI for regeneration
    document.getElementById('send-button').disabled = true;
    document.getElementById('user-input').disabled = true;

    if (useStreaming) {
        await sendMessageStreaming(question);
    } else {
        await sendMessageRegular(question);
    }

    document.getElementById('send-button').disabled = false;
    document.getElementById('user-input').disabled = false;
}
