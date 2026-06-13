const PRESETS = {
    'default-light': {
        theme: 'light',
        primary: '#6366f1',
        bg: '#f5f7fa',
        surface: '#ffffff',
        text: '#1f2937',
        userBubble: '#6366f1',
        botBubble: '#e5e7eb'
    },
    'default-dark': {
        theme: 'dark',
        primary: '#818cf8',
        bg: '#1a1a2e',
        surface: '#16213e',
        text: '#e5e7eb',
        userBubble: '#818cf8',
        botBubble: '#374151'
    },
    'ocean': {
        theme: 'ocean',
        primary: '#60a5fa',
        bg: '#1e3a5f',
        surface: '#2d5a87',
        text: '#f1f5f9',
        userBubble: '#60a5fa',
        botBubble: '#1e40af'
    },
    'forest': {
        theme: 'forest',
        primary: '#4ade80',
        bg: '#1a2f1a',
        surface: '#2d4a2d',
        text: '#f1f5f9',
        userBubble: '#4ade80',
        botBubble: '#14532d'
    }
};

let currentTheme = JSON.parse(localStorage.getItem('themeSettings')) || {
    mode: 'light',
    primary: '#6366f1',
    bg: '#f5f7fa',
    surface: '#ffffff',
    text: '#1f2937',
    userBubble: '#6366f1',
    botBubble: '#e5e7eb'
};

function applyTheme() {
    const root = document.documentElement;
    if (currentTheme.mode === 'dark') {
        root.setAttribute('data-theme', 'dark');
    } else if (currentTheme.mode === 'ocean') {
        root.setAttribute('data-theme', 'ocean');
    } else if (currentTheme.mode === 'forest') {
        root.setAttribute('data-theme', 'forest');
    } else {
        root.removeAttribute('data-theme');
    }

    root.style.setProperty('--primary-color', currentTheme.primary);
    root.style.setProperty('--bg-color', currentTheme.bg);
    root.style.setProperty('--surface-color', currentTheme.surface);
    root.style.setProperty('--text-primary', currentTheme.text);
    root.style.setProperty('--user-bubble', currentTheme.userBubble);
    root.style.setProperty('--bot-bubble', currentTheme.botBubble);

    document.getElementById('primaryColor').value = currentTheme.primary;
    document.getElementById('bgColor').value = currentTheme.bg;
    document.getElementById('surfaceColor').value = currentTheme.surface;
    document.getElementById('textColor').value = currentTheme.text;
    document.getElementById('userBubbleColor').value = currentTheme.userBubble;
    document.getElementById('botBubbleColor').value = currentTheme.botBubble;

    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === currentTheme.mode);
    });
}

function saveTheme() {
    localStorage.setItem('themeSettings', JSON.stringify(currentTheme));
}

function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const targetId = `${tab.dataset.tab}-section`;
            document.getElementById(targetId).classList.add('active');
        });
    });
}

function initNpsSlider() {
    const npsSlider = document.getElementById('npsScore');
    const npsValueDisplay = document.getElementById('npsValue');

    npsSlider.addEventListener('input', () => {
        npsValueDisplay.textContent = npsSlider.value;
    });
}

function initFeedbackForm() {
    const form = document.getElementById('feedbackForm');
    const responseBox = document.getElementById('feedbackResponse');
    const responseText = document.getElementById('responseText');
    const responseCategories = document.getElementById('responseCategories');
    const categoryTags = document.getElementById('categoryTags');
    const responseNps = document.getElementById('responseNps');
    const npsScoreDisplay = document.getElementById('npsScoreDisplay');
    const kbRefTags = document.getElementById('kbRefTags');
    const responseKbRefs = document.getElementById('responseKbRefs');
    const submitBtn = document.getElementById('submitFeedbackBtn');
    const submitBtnText = document.getElementById('submitBtnText');
    const submitSpinner = document.getElementById('submitSpinner');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const npsScore = parseInt(document.getElementById('npsScore').value);

        const formData = {
            product: document.getElementById('product').value,
            feedback_text: document.getElementById('feedbackText').value,
            nps_score: npsScore,
            user_id: document.getElementById('userId').value || null
        };

        submitBtn.disabled = true;
        submitBtnText.textContent = 'Processing...';
        submitSpinner.classList.remove('hidden');

        responseBox.classList.remove('hidden', 'success', 'error');
        responseBox.style.display = 'block';
        responseText.innerHTML = '<div class="processing-indicator"><span class="spinner" style="margin-right:8px;"></span>Processing your feedback...</div>';
        responseKbRefs.classList.add('hidden');
        responseCategories.classList.add('hidden');
        document.getElementById('responseClassifications').classList.add('hidden');
        responseNps.classList.add('hidden');
        document.getElementById('responseReview').classList.add('hidden');

        try {
            const response = await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                let errMsg = `Server error (${response.status})`;
                try {
                    const errBody = await response.json();
                    errMsg = errBody.detail || errBody.message || errMsg;
                } catch (_) {}
                responseBox.classList.add('error');
                responseText.textContent = `Error: ${errMsg}`;
                return;
            }

            const result = await response.json();

            if (result.success) {
                responseBox.classList.add('success');
                responseText.innerHTML = `<strong>Thank you for your feedback!</strong><br><br><strong>Sent Response:</strong><br>${result.llm_response}`;

                if (result.kb_references && result.kb_references.length > 0) {
                    kbRefTags.innerHTML = result.kb_references.map(ref =>
                        `<span class="kb-ref-tag">${ref}</span>`
                    ).join('');
                    responseKbRefs.classList.remove('hidden');
                }

                if (result.categories && result.categories.length > 0) {
                    categoryTags.innerHTML = result.categories.map(cat =>
                        `<span class="category-tag">${cat}</span>`
                    ).join('');
                    responseCategories.classList.remove('hidden');
                }

                showClassifications(result);

                npsScoreDisplay.textContent = result.nps_score;
                responseNps.classList.remove('hidden');

                const responseReview = document.getElementById('responseReview');
                if (result.needs_review) {
                    const responseTeam = document.getElementById('responseTeam');
                    const responseStatus = document.getElementById('responseStatus');
                    responseTeam.innerHTML = `Assigned to: <strong>${result.assigned_team}</strong>`;
                    responseStatus.textContent = 'Flagged for Support Review';
                    responseReview.classList.remove('hidden');
                } else {
                    responseReview.classList.add('hidden');
                }

                form.reset();
                document.getElementById('npsScore').value = 5;
                document.getElementById('npsValue').textContent = '5';
            } else {
                responseBox.classList.add('error');
                responseText.textContent = `Error: ${result.message || JSON.stringify(result)}`;
            }
        } catch (error) {
            responseBox.classList.add('error');
            responseText.textContent = `Error: ${error.message || 'Unknown error'}`;
        } finally {
            submitBtn.disabled = false;
            submitBtnText.textContent = 'Submit Feedback';
            submitSpinner.classList.add('hidden');
        }
    });
}

function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChat');
    const chatMessages = document.getElementById('chatMessages');
    const productFilter = document.getElementById('chatProductFilter');
    const minNps = document.getElementById('minNps');
    const maxNps = document.getElementById('maxNps');
    const categoryFilter = document.getElementById('categoryFilter');

    let chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');

    function restoreChatHistory() {
        if (chatHistory.length > 0) {
            chatMessages.innerHTML = '';
            chatHistory.forEach(msg => addMessage(msg.text, msg.sender, false));
        }
    }

    function saveToHistory(text, sender) {
        chatHistory.push({ text, sender, timestamp: Date.now() });
        if (chatHistory.length > 50) chatHistory.shift();
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    }

    function clearHistory() {
        chatHistory = [];
        localStorage.removeItem('chatHistory');
        chatMessages.innerHTML = '';
        addWelcomeMessage();
    }

    function addWelcomeMessage() {
        addMessage('Hello! I\'m your product insights assistant. Ask me questions about user feedback, such as:\n- "What are users struggling with?"\n- "What features do users like most?"\n- "What are the top complaints for Product X?"\n- "Show me detractors (NPS 1-6)"\n- "What feedback about billing?"', 'bot', false);
    }

    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        addMessage(message, 'user');
        saveToHistory(message, 'user');
        chatInput.value = '';

        const typingIndicator = addTypingIndicator();

        const chatRequest = {
            message: message,
            product_filter: productFilter.value || null
        };

        if (minNps.value) {
            chatRequest.min_nps = parseInt(minNps.value);
        }
        if (maxNps.value) {
            chatRequest.max_nps = parseInt(maxNps.value);
        }
        if (categoryFilter.value) {
            chatRequest.categories = [categoryFilter.value];
        }

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(chatRequest)
            });

            const result = await response.json();
            typingIndicator.remove();

            if (result.success) {
                addMessage(result.response, 'bot');
                saveToHistory(result.response, 'bot');
            } else {
                addMessage(`Error: ${result.response}`, 'bot');
                saveToHistory(`Error: ${result.response}`, 'bot');
            }
        } catch (error) {
            typingIndicator.remove();
            addMessage(`Error: ${error.message}`, 'bot');
            saveToHistory(`Error: ${error.message}`, 'bot');
        }
    }

    function formatText(text) {
        if (!text) return '';
        let formatted = text
            .replace(/^## (.+)$/gm, '<h3>$1</h3>')
            .replace(/^### (.+)$/gm, '<h4>$1</h4>')
            .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
            .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        const lines = formatted.split('\n');
        let inList = false;
        let result = [];
        
        for (let line of lines) {
            if (line.startsWith('<li>')) {
                if (!inList) {
                    result.push('<ul>');
                    inList = true;
                }
                result.push(line);
            } else {
                if (inList) {
                    result.push('</ul>');
                    inList = false;
                }
                if (line.trim()) {
                    result.push(`<p>${line}</p>`);
                }
            }
        }
        if (inList) result.push('</ul>');
        
        return result.join('');
    }

    function addMessage(text, sender, save = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        const formattedText = sender === 'bot' ? formatText(text) : text;
        messageDiv.innerHTML = `<div class="message-content">${formattedText}</div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addTypingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';
        messageDiv.id = 'typingIndicator';
        messageDiv.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageDiv;
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    document.getElementById('clearChat')?.addEventListener('click', () => {
        if (confirm('Clear all chat history?')) clearHistory();
    });

    restoreChatHistory();
}

function initSettings() {
    const modal = document.getElementById('settingsModal');
    const openBtn = document.getElementById('settingsBtn');
    const closeBtn = document.getElementById('closeSettings');
    const resetBtn = document.getElementById('resetTheme');

    openBtn.addEventListener('click', () => {
        modal.classList.remove('hidden');
    });

    closeBtn.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });

    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentTheme.mode = btn.dataset.mode;
            applyTheme();
            saveTheme();
        });
    });

    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const preset = PRESETS[btn.dataset.preset];
            currentTheme = {
                ...currentTheme,
                mode: preset.theme,
                primary: preset.primary,
                bg: preset.bg,
                surface: preset.surface,
                text: preset.text,
                userBubble: preset.userBubble,
                botBubble: preset.botBubble
            };
            applyTheme();
            saveTheme();
        });
    });

    const colorInputs = ['primaryColor', 'bgColor', 'surfaceColor', 'textColor', 'userBubbleColor', 'botBubbleColor'];
    const themeKeys = ['primary', 'bg', 'surface', 'text', 'userBubble', 'botBubble'];

    colorInputs.forEach((inputId, index) => {
        document.getElementById(inputId).addEventListener('input', (e) => {
            currentTheme[themeKeys[index]] = e.target.value;
            applyTheme();
            saveTheme();
        });
    });

    resetBtn.addEventListener('click', () => {
        currentTheme = {
            mode: 'light',
            primary: '#6366f1',
            bg: '#f5f7fa',
            surface: '#ffffff',
            text: '#1f2937',
            userBubble: '#6366f1',
            botBubble: '#e5e7eb'
        };
        applyTheme();
        saveTheme();
    });
}

function initProviderSettings() {
    const llmProvider = document.getElementById('llmProvider');
    const embeddingProvider = document.getElementById('embeddingProvider');
    const llmProviderInfo = document.getElementById('llmProviderInfo');
    const embeddingProviderInfo = document.getElementById('embeddingProviderInfo');
    const providerStatus = document.getElementById('providerStatus');

    const providerModels = {
        'ollama': {
            'llm': 'llama3.2:1b',
            'embedding': 'nomic-embed-text'
        },
        'openai': {
            'llm': 'gpt-4o-mini',
            'embedding': 'text-embedding-3-small'
        },
        'google': {
            'llm': 'gemini-2.0-flash',
            'embedding': 'text-embedding-004'
        }
    };

    function updateProviderInfo() {
        const llm = llmProvider.value;
        const embedding = embeddingProvider.value;

        llmProviderInfo.textContent = `Model: ${providerModels[llm].llm}`;
        embeddingProviderInfo.textContent = `Model: ${providerModels[embedding].embedding}`;
    }

    function validateProviders() {
        let messages = [];

        if (llmProvider.value === 'ollama') {
            messages.push('Chat: Using Ollama (local). Ensure Ollama server is running.');
        } else if (llmProvider.value === 'openai') {
            messages.push('Chat: Using OpenAI (cloud).');
        } else if (llmProvider.value === 'google') {
            messages.push('Chat: Using Google Gemini (cloud).');
        }

        if (embeddingProvider.value === 'ollama') {
            messages.push('Embedding: Using Ollama (local).');
        } else if (embeddingProvider.value === 'openai') {
            messages.push('Embedding: Using OpenAI (cloud).');
        } else if (embeddingProvider.value === 'google') {
            messages.push('Embedding: Using Google (cloud).');
        }

        if (llmProvider.value === 'ollama' || embeddingProvider.value === 'ollama') {
            providerStatus.className = 'provider-status warning';
            providerStatus.textContent = '⚠️ Ollama selected. Please ensure Ollama server is running at http://localhost:11434';
        } else {
            providerStatus.className = 'provider-status success';
            providerStatus.textContent = '✓ Using cloud providers. Configuration OK.';
        }
    }

    llmProvider.addEventListener('change', () => {
        updateProviderInfo();
        validateProviders();
    });

    embeddingProvider.addEventListener('change', () => {
        updateProviderInfo();
        validateProviders();
    });

    updateProviderInfo();
    validateProviders();
}

async function initCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.innerHTML = '<option value="">All Categories</option>';
            data.categories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat;
                option.textContent = cat;
                categoryFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

let selectedReviewId = null;
let queueRefreshInterval = null;
let currentQueueFilter = 'all';

async function initSupportQueue() {
    const queueList = document.getElementById('queueList');
    const teamFilter = document.getElementById('teamFilter');
    const queueActions = document.getElementById('queueActions');
    const filterTabs = document.querySelectorAll('.filter-tab');

    await loadTeams();
    await loadReviews();
    startAutoRefresh();

    teamFilter.addEventListener('change', loadReviews);

    filterTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentQueueFilter = tab.dataset.filter;
            loadReviews();
        });
    });

    document.getElementById('viewFeedback')?.addEventListener('click', viewFeedbackDetails);
    document.getElementById('addNotes')?.addEventListener('click', addReviewNotes);
    document.getElementById('sendFollowup')?.addEventListener('click', sendFollowup);
    document.getElementById('resolveReview')?.addEventListener('click', resolveReview);

    async function loadTeams() {
        try {
            const response = await fetch('/api/teams');
            const teams = await response.json();
            const savedValue = teamFilter.value;
            teamFilter.innerHTML = '<option value="">All Teams</option>';
            teams.forEach(team => {
                const option = document.createElement('option');
                option.value = team.name;
                option.textContent = team.name;
                teamFilter.appendChild(option);
            });
            if (savedValue) teamFilter.value = savedValue;
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    async function loadReviews() {
        const team = teamFilter.value;
        const url = team ? `/api/reviews?team=${encodeURIComponent(team)}` : '/api/reviews';

        try {
            const response = await fetch(url);
            const allReviews = await response.json();

            let filteredReviews = allReviews;
            if (currentQueueFilter === 'pending') {
                filteredReviews = allReviews.filter(r => r.status !== 'resolved');
            } else if (currentQueueFilter === 'resolved') {
                filteredReviews = allReviews.filter(r => r.status === 'resolved');
            }

            updateStats(allReviews);
            updateCategorySummary(allReviews);

            if (filteredReviews.length === 0) {
                queueList.innerHTML = '<div class="queue-empty">No reviews found</div>';
                queueActions.classList.add('hidden');
                return;
            }

            queueList.innerHTML = filteredReviews.map(review => `
                <div class="queue-card ${review.status === 'resolved' ? 'resolved' : ''}" data-id="${review.id}">
                    <div class="queue-card-header">
                        <span class="queue-card-email">${review.user_id}</span>
                        <div class="queue-card-meta">
                            <span>NPS: ${review.nps_score}</span>
                            <span>${formatTimeAgo(review.created_at)}</span>
                        </div>
                    </div>
                    <div class="queue-card-meta">
                        <span class="team-badge">${review.assigned_team}</span>
                        <span class="status-badge status-${review.status}">${review.status}</span>
                    </div>
                    <div class="queue-card-categories">
                        ${review.categories[0] ? `<span class="category-tag">${review.categories[0]}</span>` : ''}
                    </div>
                    <div class="queue-card-feedback">"${review.feedback_text.substring(0, 150)}${review.feedback_text.length > 150 ? '...' : ''}"</div>
                </div>
            `).join('');

            queueList.querySelectorAll('.queue-card').forEach(card => {
                card.addEventListener('click', () => selectReview(card.dataset.id));
            });
        } catch (error) {
            queueList.innerHTML = '<div class="queue-empty">Error loading reviews</div>';
        }
    }

    function updateStats(reviews) {
        const total = reviews.length;
        const pending = reviews.filter(r => r.status !== 'resolved').length;
        const resolved = reviews.filter(r => r.status === 'resolved').length;

        document.getElementById('totalCount').textContent = total;
        document.getElementById('pendingCount').textContent = pending;
        document.getElementById('resolvedCount').textContent = resolved;
    }

    function updateCategorySummary(reviews) {
        const categoryCounts = {};
        reviews.forEach(r => {
            const primaryCat = r.categories[0];
            if (primaryCat) {
                categoryCounts[primaryCat] = (categoryCounts[primaryCat] || 0) + 1;
            }
        });

        const summaryEl = document.getElementById('categorySummary');
        if (Object.keys(categoryCounts).length === 0) {
            summaryEl.innerHTML = '';
            return;
        }

        const sortedCats = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]);
        summaryEl.innerHTML = sortedCats.map(([cat, count]) =>
            `<span class="category-stat"><span class="category-name">${cat}</span>: <span class="category-count">${count}</span></span>`
        ).join('');
    }

    function startAutoRefresh() {
        queueRefreshInterval = setInterval(loadReviews, 10000);
    }

    function selectReview(reviewId) {
        selectedReviewId = reviewId;
        queueList.querySelectorAll('.queue-card').forEach(c => c.classList.remove('selected'));
        queueList.querySelector(`[data-id="${reviewId}"]`)?.classList.add('selected');
        queueActions.classList.remove('hidden');
    }

    async function viewFeedbackDetails() {
        if (!selectedReviewId) return;
        try {
            const response = await fetch(`/api/reviews/${selectedReviewId}`);
            if (!response.ok) {
                alert('Failed to load feedback details (server error)');
                return;
            }
            const review = await response.json();

            const modal = document.getElementById('feedbackDetailModal') || createDetailModal();
            document.getElementById('detailUser').textContent = review.user_id || 'Anonymous';
            document.getElementById('detailNps').textContent = review.nps_score;
            document.getElementById('detailTeam').textContent = review.assigned_team || 'Unassigned';
            document.getElementById('detailStatus').textContent = review.status;
            document.getElementById('detailCategories').textContent = (review.categories || []).join(', ');
            document.getElementById('detailFeedbackText').textContent = review.feedback_text;
            document.getElementById('detailOriginalResponse').textContent = review.original_response || 'No response';
            document.body.classList.add('modal-open');
            modal.classList.add('show');
        } catch (error) {
            alert('Failed to load feedback details: ' + error.message);
        }
    }

    function createDetailModal() {
        const modal = document.createElement('div');
        modal.id = 'feedbackDetailModal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Feedback Details <button class="modal-close">&times;</button></h3>
                <div class="detail-row"><strong>User:</strong> <span id="detailUser"></span></div>
                <div class="detail-row"><strong>NPS:</strong> <span id="detailNps"></span></div>
                <div class="detail-row"><strong>Team:</strong> <span id="detailTeam"></span></div>
                <div class="detail-row"><strong>Status:</strong> <span id="detailStatus"></span></div>
                <div class="detail-row"><strong>Categories:</strong> <span id="detailCategories"></span></div>
                <div class="detail-section"><strong>Feedback:</strong><p id="detailFeedbackText"></p></div>
                <div class="detail-section"><strong>AI Response:</strong><p id="detailOriginalResponse"></p></div>
                <div style="text-align:right;margin-top:16px;">
                    <button class="btn secondary btn-close-modal">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target.closest('.modal-close, .btn-close-modal') || e.target === modal) {
                modal.classList.remove('show');
                document.body.classList.remove('modal-open');
            }
        });
        return modal;
    }

    function showInputDialog(title, placeholder, confirmLabel) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            overlay.innerHTML = `
                <div class="modal-content" style="max-width:450px;">
                    <h3>${title} <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button></h3>
                    <textarea id="dialogInput" placeholder="${placeholder}"
                        style="width:100%;min-height:100px;margin:12px 0;padding:8px;border-radius:8px;
                        border:1px solid var(--border-color);background:var(--bg-color);
                        color:var(--text-color);resize:vertical;font-family:inherit;font-size:0.9rem;
                        box-sizing:border-box;"></textarea>
                    ${title === 'Send Follow-up' ? '<p style="color:var(--warning-color);font-size:0.85rem;margin:-8px 0 12px 0;">This will resolve the review after sending.</p>' : ''}
                    <div style="display:flex;gap:8px;justify-content:flex-end;">
                        <button class="btn secondary" id="dialogCancel">Cancel</button>
                        <button class="btn primary" id="dialogConfirm">${confirmLabel}</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);
            setTimeout(() => overlay.classList.add('show'), 10);

            const input = overlay.querySelector('#dialogInput');
            setTimeout(() => input.focus(), 100);

            overlay.querySelector('#dialogCancel').onclick = () => { overlay.remove(); resolve(null); };
            overlay.querySelector('#dialogConfirm').onclick = () => {
                const val = input.value.trim();
                overlay.remove();
                resolve(val || null);
            };
            overlay.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') { overlay.remove(); resolve(null); }
                if (e.key === 'Enter' && e.ctrlKey) {
                    const val = input.value.trim();
                    overlay.remove();
                    resolve(val || null);
                }
            });
            overlay.addEventListener('click', (e) => { if (e.target === overlay) { overlay.remove(); resolve(null); } });
        });
    }

    async function addReviewNotes() {
        if (!selectedReviewId) return;
        const notes = await showInputDialog('Add Notes', 'Enter internal notes...', 'Save Notes');
        if (!notes) return;
        try {
            await fetch(`/api/reviews/${selectedReviewId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'add_notes', notes })
            });
        } catch (e) {
            alert('Failed to save notes');
        }
        loadReviews();
    }

    async function sendFollowup() {
        if (!selectedReviewId) return;
        const text = await showInputDialog('Send Follow-up', 'Enter your response to the user...', 'Send & Resolve');
        if (!text) return;
        try {
            await fetch(`/api/reviews/${selectedReviewId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'send_followup', final_response: text })
            });
        } catch (e) {
            alert('Failed to send follow-up');
        }
        loadReviews();
    }

    async function resolveReview() {
        if (!selectedReviewId) return;
        const notes = await showInputDialog('Resolve Review', 'Optional resolution note...', 'Resolve');
        if (notes === null) return;
        try {
            await fetch(`/api/reviews/${selectedReviewId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'add_notes', notes: notes || 'Resolved without notes' })
            });
            await fetch(`/api/reviews/${selectedReviewId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'resolve' })
            });
        } catch (e) {
            alert('Failed to resolve review');
        }
        selectedReviewId = null;
        queueActions.classList.add('hidden');
        loadReviews();
    }
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000 / 60);
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    return `${Math.floor(diff / 1440)}d ago`;
}

let previewAutoRefresh = null;
let currentPreviewFilter = 'all';
let currentPreviewUser = '';

async function initPreviewUser() {
    const previewBtn = document.getElementById('previewUserBtn');
    const closeBtn = document.getElementById('closePreview');
    const overlay = document.getElementById('previewOverlay');
    const refreshBtn = document.getElementById('refreshPreview');
    const userSelect = document.getElementById('previewUserFilter');
    const filterBtns = document.querySelectorAll('.filter-btn');

    previewBtn.addEventListener('click', () => {
        document.getElementById('previewPanel').classList.add('open');
        overlay.classList.add('show');
        loadUserIds();
        loadPreviewData();
        startAutoRefresh();
    });

    function closePreview() {
        document.getElementById('previewPanel').classList.remove('open');
        overlay.classList.remove('show');
        stopAutoRefresh();
    }

    closeBtn.addEventListener('click', closePreview);
    overlay.addEventListener('click', closePreview);

    refreshBtn.addEventListener('click', loadPreviewData);

    userSelect.addEventListener('change', () => {
        currentPreviewUser = userSelect.value;
        loadPreviewData();
    });

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPreviewFilter = btn.dataset.filter;
            loadPreviewData();
        });
    });

    async function loadUserIds() {
        try {
            const response = await fetch('/api/user-ids');
            const userIds = await response.json();
            const savedValue = userSelect.value;
            userSelect.innerHTML = '<option value="">All Users</option>';
            userIds.forEach(uid => {
                const option = document.createElement('option');
                option.value = uid;
                option.textContent = uid;
                userSelect.appendChild(option);
            });
            if (savedValue && userIds.includes(savedValue)) {
                userSelect.value = savedValue;
            }
        } catch (error) {
            console.error('Failed to load user IDs:', error);
        }
    }

    async function loadPreviewData() {
        try {
            const url = `/api/preview-user${currentPreviewUser ? '?user_id=' + encodeURIComponent(currentPreviewUser) : ''}`;
            console.log('Loading preview data from:', url);
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error('Failed to fetch preview data: ' + response.status);
            }
            
            const data = await response.json();
            console.log('Preview data:', data);

            document.getElementById('statTotal').textContent = data.stats.total;
            document.getElementById('statAI').textContent = data.stats.ai_responses;
            document.getElementById('statHuman').textContent = data.stats.human_followups;
            document.getElementById('statResolved').textContent = data.stats.resolved;

            let feedbacks = data.feedbacks || [];
            console.log('Feedbacks to render:', feedbacks.length);

            const listEl = document.getElementById('previewFeedbackList');
            console.log('List element:', listEl);
            console.log('Rendering', feedbacks.length, 'feedbacks');
            
            if (feedbacks.length === 0) {
                listEl.innerHTML = '<div class="queue-empty">No feedbacks found</div>';
            } else {
                const cardsHtml = feedbacks.map(f => `
                    <div class="feedback-card">
                        <div class="feedback-card-header">
                            <span class="feedback-user">${f.user_id || 'Anonymous'}</span>
                            <span class="feedback-date">${formatTimeAgo(f.created_at)}</span>
                            <span class="status-badge status-${f.status}">${f.status}</span>
                        </div>
                        <div class="feedback-original">
                            <div class="feedback-original-label">Your Feedback</div>
                            <div class="feedback-original-text">"${escapeHtml(f.feedback_text)}"</div>
                        </div>
                        <div class="response-section">
                            <div class="response-label">
                                <span class="badge-auto">Auto</span> AI Response
                            </div>
                            <div class="response-text ai-response">${escapeHtml(f.ai_response) || 'No response yet'}</div>
                            ${f.kb_references && f.kb_references.length > 0 ? `
                            <div class="preview-kb-refs">
                                <span class="preview-kb-label">Based on:</span>
                                <div class="preview-kb-tags">${f.kb_references.map(ref => `<span class="preview-kb-tag">${escapeHtml(ref)}</span>`).join('')}</div>
                            </div>
                            ` : ''}
                        </div>
                        ${f.human_response ? `
                        <div class="response-section">
                            <div class="response-label">
                                <span class="badge-human">Human</span> Team Follow-up
                            </div>
                            <div class="response-text human-response">${escapeHtml(f.human_response)}</div>
                        </div>
                        ` : ''}
                    </div>
                `).join('');
                listEl.innerHTML = cardsHtml;
                console.log('Rendered', feedbacks.length, 'cards');
            }

            document.getElementById('lastUpdated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        } catch (error) {
            console.error('Failed to load preview data:', error);
            document.getElementById('previewFeedbackList').innerHTML = 
                '<div class="queue-empty">Error loading data: ' + error.message + '</div>';
        }
    }

    function startAutoRefresh() {
        loadUserIds();
        loadPreviewData();
        let refreshCount = 0;
        previewAutoRefresh = setInterval(() => {
            refreshCount++;
            loadPreviewData();
            if (refreshCount % 3 === 0) {
                loadUserIds();
            }
        }, 15000);
    }

    function stopAutoRefresh() {
        if (previewAutoRefresh) {
            clearInterval(previewAutoRefresh);
            previewAutoRefresh = null;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ── Dashboard (Observability) ──────────────────────────────────────────

let latencyChartInstance = null;
let confidenceChartInstance = null;
let categoryChartInstance = null;
let dashboardRefreshInterval = null;

async function initDashboard() {
    await loadDashboardMetrics();
    startDashboardRefresh();
    document.querySelector('[data-tab="dashboard"]')?.addEventListener('click', () => {
        loadDashboardMetrics();
    });
}

async function loadDashboardMetrics() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();
        updateMetricCards(data);
        renderLatencyChart(data);
        renderConfidenceChart(data);
        renderCategoryChart(data);
        renderAccuracyMatrix(data);
        renderMetricsDetail(data);
    } catch (e) {
        console.error('Dashboard load failed:', e);
    }
}

function updateMetricCards(data) {
    document.getElementById('metricTotal').textContent = data.total_processed || 0;
    document.getElementById('metricAuto').textContent = data.auto_tagged || 0;
    document.getElementById('metricReview').textContent = data.needs_review || 0;
    document.getElementById('metricLatency').textContent = (data.avg_latency_ms || 0) + 'ms';
    document.getElementById('metricConfidence').textContent = ((data.avg_confidence || 0) * 100).toFixed(1) + '%';
    document.getElementById('metricThroughput').textContent = data.throughput_per_hour || 0;
}

function renderLatencyChart(data) {
    const ctx = document.getElementById('latencyChart').getContext('2d');
    const points = data.latency_over_time || [];
    if (latencyChartInstance) latencyChartInstance.destroy();
    if (points.length === 0) {
        latencyChartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels: ['No data'], datasets: [{ label: 'Latency (ms)', data: [0] }] },
            options: { responsive: true, plugins: { legend: { display: false } } }
        });
        return;
    }
    latencyChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: points.map(p => p.time),
            datasets: [{
                label: 'Latency (ms)',
                data: points.map(p => p.latency),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99,102,241,0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'ms' } }
            }
        }
    });
}

function renderConfidenceChart(data) {
    const ctx = document.getElementById('confidenceChart').getContext('2d');
    const buckets = data.confidence_histogram || [];
    if (confidenceChartInstance) confidenceChartInstance.destroy();
    const labels = ['0-10%', '10-20%', '20-30%', '30-40%', '40-50%', '50-60%', '60-70%', '70-80%', '80-90%', '90-100%'];
    confidenceChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Count',
                data: buckets,
                backgroundColor: buckets.map((v, i) => i >= 8 ? '#22c55e' : i >= 5 ? '#eab308' : '#ef4444'),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Count' } }
            }
        }
    });
}

function renderCategoryChart(data) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    const dist = data.category_distribution || {};
    const entries = Object.entries(dist).slice(0, 15);
    if (categoryChartInstance) categoryChartInstance.destroy();
    if (entries.length === 0) {
        categoryChartInstance = new Chart(ctx, {
            type: 'bar',
            data: { labels: ['No data'], datasets: [{ label: 'Count', data: [0] }] },
            options: { responsive: true, indexAxis: 'y', plugins: { legend: { display: false } } }
        });
        return;
    }
    const colors = ['#6366f1','#8b5cf6','#a855f7','#d946ef','#ec4899','#f43f5e','#ef4444','#f97316','#eab308','#22c55e','#14b8a6','#06b6d4','#3b82f6','#2563eb','#1d4ed8'];
    categoryChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: entries.map(e => e[0]),
            datasets: [{
                label: 'Count',
                data: entries.map(e => e[1]),
                backgroundColor: entries.map((_, i) => colors[i % colors.length]),
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, title: { display: true, text: 'Mentions' } }
            }
        }
    });
}

function renderAccuracyMatrix(data) {
    const container = document.getElementById('accuracyMatrix');
    const dist = data.category_distribution || {};
    const entries = Object.entries(dist).slice(0, 15);
    if (entries.length === 0) {
        container.innerHTML = '<div class="no-data">No classification data yet. Submit feedback to see accuracy metrics.</div>';
        return;
    }
    const maxCount = Math.max(...entries.map(e => e[1]), 1);
    container.innerHTML = entries.map(([cat, count]) => {
        const pct = (count / data.total_processed * 100).toFixed(1);
        const barWidth = (count / maxCount * 100).toFixed(0);
        const intensity = Math.min(Math.round(count / maxCount * 200), 200);
        const r = Math.min(99 + intensity, 255);
        const g = Math.min(102 + intensity, 255);
        const b = Math.max(241 - intensity, 50);
        return `
            <div class="accuracy-row">
                <span class="accuracy-label">${cat}</span>
                <div class="accuracy-bar-bg">
                    <div class="accuracy-bar" style="width:${barWidth}%;background:rgb(${255-intensity/2},${255-intensity/3},${Math.max(50,241-intensity)})"></div>
                </div>
                <span class="accuracy-value">${count} (${pct}%)</span>
            </div>
        `;
    }).join('');
}

function renderMetricsDetail(data) {
    const container = document.getElementById('metricsDetailContent');
    const metrics = [
        { label: 'Total Processed', value: data.total_processed },
        { label: 'Auto-Tagged', value: data.auto_tagged },
        { label: 'Needs Review (HITL)', value: data.needs_review },
        { label: 'Avg Latency', value: data.avg_latency_ms + ' ms' },
        { label: 'P95 Latency', value: data.p95_latency_ms + ' ms' },
        { label: 'P99 Latency', value: data.p99_latency_ms + ' ms' },
        { label: 'Avg Confidence', value: (data.avg_confidence * 100).toFixed(1) + '%' },
        { label: 'Error Rate', value: (data.error_rate * 100).toFixed(2) + '%' },
        { label: 'Throughput (per hr)', value: data.throughput_per_hour },
        { label: 'Uptime', value: data.uptime_hours + ' hours' }
    ];
    container.innerHTML = metrics.map(m => `
        <div class="metrics-detail-item">
            <span class="metrics-detail-label">${m.label}</span>
            <span class="metrics-detail-value">${m.value}</span>
        </div>
    `).join('');
}

function startDashboardRefresh() {
    if (dashboardRefreshInterval) clearInterval(dashboardRefreshInterval);
    dashboardRefreshInterval = setInterval(loadDashboardMetrics, 5000);
}

// ── Reports (STO Reports + Trend Analysis) ──────────────────────────────

async function initReports() {
    document.getElementById('generateReport').addEventListener('click', generateReport);
    document.getElementById('analyzeTrends').addEventListener('click', analyzeTrends);
    document.getElementById('copyReport').addEventListener('click', copyReportContent);
    document.getElementById('exportReport').addEventListener('click', exportReportContent);

    document.querySelector('[data-tab="reports"]')?.addEventListener('click', () => {
        if (!document.getElementById('reportOutput').classList.contains('hidden')) {
            loadFeedbackCount();
        }
    });
}

async function generateReport() {
    const team = document.getElementById('reportTeam').value;
    const days = parseInt(document.getElementById('reportDays').value);
    const btn = document.getElementById('generateReport');
    const btnText = document.getElementById('reportBtnText');
    const spinner = document.getElementById('reportSpinner');

    btn.disabled = true;
    btnText.textContent = 'Generating...';
    spinner.classList.remove('hidden');

    try {
        const fbResponse = await fetch('/api/preview-user');
        const fbData = await fbResponse.json();
        const allFeedbacks = fbData.feedbacks || [];

        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - days);
        const filtered = allFeedbacks.filter(f => new Date(f.created_at) >= cutoff);

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `Generate a ${team} team report based on ${filtered.length} feedback items from the last ${days} days. Cover: key themes, NPS trends, top issues, and recommended actions.`,
                categories: [team.replace(' Team', '').toLowerCase()]
            })
        });
        const result = await response.json();

        const reportOutput = document.getElementById('reportOutput');
        const reportTitle = document.getElementById('reportTitle');
        const reportContent = document.getElementById('reportContent');
        const reportMetrics = document.getElementById('reportMetrics');

        reportTitle.textContent = `${team} — CX Summary (Last ${days} Days)`;
        reportContent.innerHTML = result.response ? formatReportText(result.response) : '<p>No report generated.</p>';

        const npsScores = filtered.map(f => f.nps_score).filter(s => s);
        const avgNps = npsScores.length ? (npsScores.reduce((a, b) => a + b, 0) / npsScores.length).toFixed(1) : 'N/A';
        const promoters = npsScores.filter(s => s >= 9).length;
        const detractors = npsScores.filter(s => s <= 6).length;
        const passives = npsScores.length - promoters - detractors;

        reportMetrics.innerHTML = `
            <div class="report-metrics-grid">
                <div class="report-metric-item">
                    <span class="report-metric-value">${filtered.length}</span>
                    <span class="report-metric-label">Items</span>
                </div>
                <div class="report-metric-item">
                    <span class="report-metric-value">${avgNps}</span>
                    <span class="report-metric-label">Avg NPS</span>
                </div>
                <div class="report-metric-item">
                    <span class="report-metric-value">${promoters}</span>
                    <span class="report-metric-label">Promoters</span>
                </div>
                <div class="report-metric-item">
                    <span class="report-metric-value">${detractors}</span>
                    <span class="report-metric-label">Detractors</span>
                </div>
                <div class="report-metric-item">
                    <span class="report-metric-value">${passives}</span>
                    <span class="report-metric-label">Passives</span>
                </div>
            </div>
        `;
        reportOutput.classList.remove('hidden');
    } catch (e) {
        alert('Failed to generate report: ' + e.message);
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Generate Report';
        spinner.classList.add('hidden');
    }
}

function formatReportText(text) {
    if (!text) return '';
    let formatted = text
        .replace(/^## (.+)$/gm, '<h4>$1</h4>')
        .replace(/^### (.+)$/gm, '<h5>$1</h5>')
        .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
        .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    const lines = formatted.split('\n');
    let inList = false, result = [];
    for (let line of lines) {
        if (line.startsWith('<li>')) {
            if (!inList) { result.push('<ul>'); inList = true; }
            result.push(line);
        } else {
            if (inList) { result.push('</ul>'); inList = false; }
            if (line.trim()) result.push(`<p>${line}</p>`);
        }
    }
    if (inList) result.push('</ul>');
    return result.join('');
}

function copyReportContent() {
    const content = document.getElementById('reportContent').innerText;
    navigator.clipboard.writeText(content).then(() => {
        const btn = document.getElementById('copyReport');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy', 2000);
    });
}

function exportReportContent() {
    const title = document.getElementById('reportTitle').textContent;
    const content = document.getElementById('reportContent').innerText;
    const metrics = document.getElementById('reportMetrics').innerText;
    const blob = new Blob([`${title}\n\n${'='.repeat(50)}\n\n${content}\n\n${'─'.repeat(30)}\n\n${metrics}`], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

async function analyzeTrends() {
    const days = parseInt(document.getElementById('trendDays').value);
    const btn = document.getElementById('analyzeTrends');
    const btnText = document.getElementById('trendBtnText');
    const spinner = document.getElementById('trendSpinner');

    btn.disabled = true;
    btnText.textContent = 'Analyzing...';
    spinner.classList.remove('hidden');

    try {
        const trendsResponse = await fetch(`/api/metrics/trends?days=${days}`);
        const trendsData = await trendsResponse.json();

        const chatResponse = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `Analyze these CX trends from the last ${days} days: Top categories: ${Object.entries(trendsData.category_counts || {}).slice(0, 10).map(([k, v]) => `${k}(${v})`).join(', ')}. Total feedbacks: ${trendsData.total_in_period}. Flagged for review: ${trendsData.needs_review_count}. What are the key takeaways and actions?`
            })
        });
        const result = await chatResponse.json();

        const output = document.getElementById('trendOutput');
        output.innerHTML = `
            <div class="trend-summary">
                <div class="trend-stat">
                    <span class="trend-stat-value">${trendsData.total_in_period}</span>
                    <span class="trend-stat-label">Feedbacks</span>
                </div>
                <div class="trend-stat">
                    <span class="trend-stat-value">${(trendsData.avg_confidence * 100).toFixed(1)}%</span>
                    <span class="trend-stat-label">Avg Confidence</span>
                </div>
                <div class="trend-stat">
                    <span class="trend-stat-value">${trendsData.needs_review_count}</span>
                    <span class="trend-stat-label">Flagged</span>
                </div>
            </div>
            <div class="trend-analysis-content">${formatReportText(result.response || 'No analysis available.')}</div>
        `;
        output.classList.remove('hidden');
    } catch (e) {
        alert('Trend analysis failed: ' + e.message);
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Analyze Trends';
        spinner.classList.add('hidden');
    }
}

async function loadFeedbackCount() {
    try {
        const response = await fetch('/api/preview-user');
        const data = await response.json();
        const total = (data.feedbacks || []).length;
        document.querySelector('.reports-subtitle').textContent = `Based on ${total} total feedback entries`;
    } catch (e) {}
}

// ── Enhanced Feedback Response Display ─────────────────────────────────

function showClassifications(result) {
    if (!result || !result.classifications || result.classifications.length === 0) return;
    const container = document.getElementById('responseClassifications');
    const tags = document.getElementById('classificationTags');
    const confidence = document.getElementById('confidenceDisplay');
    container.classList.remove('hidden');
    tags.innerHTML = result.classifications.map(c => {
        const isPrimary = c.is_primary ? ' classification-primary' : '';
        const label = c.subcategory ? `${c.category}.${c.subcategory}` : c.category;
        return `<span class="classification-tag${isPrimary}">${label} <span class="classification-conf">${(c.confidence * 100).toFixed(0)}%</span></span>`;
    }).join('');
    const avgConf = result.classifications.reduce((s, c) => s + c.confidence, 0) / result.classifications.length;
    confidence.innerHTML = `Average confidence: <strong>${(avgConf * 100).toFixed(1)}%</strong> ${avgConf >= 0.9 ? '✅ High' : avgConf >= 0.7 ? '⚠️ Medium' : '🔴 Low'}`;
    if (result.confidence && result.confidence > 0) {
        confidence.innerHTML += ` (API: ${(result.confidence * 100).toFixed(1)}%)`;
    }
}

// ── Init ───────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    applyTheme();
    initTabs();
    initNpsSlider();
    initFeedbackForm();
    initChat();
    initSettings();
    initCategories();
    initProviderSettings();
    initSupportQueue();
    initPreviewUser();
    initDashboard();
    initReports();
});