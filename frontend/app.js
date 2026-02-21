// ============================================================
// Aliman AI - Frontend JavaScript
// ============================================================
// Barcha UI mantiqi, API chaqiruvlar va fokus rejimi shu yerda
// ============================================================

// API URL - Backend qayerda ishlayotganiga qarab o'zgartiring
const API_URL = 'http://localhost:8000';

// -------------------------------------------------------
// Global holat (State)
// -------------------------------------------------------
let token = localStorage.getItem('aliman_token') || null;
let username = localStorage.getItem('aliman_username') || null;
let focusSessionId = null;          // Joriy fokus sessiyasi ID
let focusTimerInterval = null;      // Taymer intervali
let focusMinutesLeft = 25;          // Qolgan daqiqalar
let focusSecondsLeft = 0;           // Qolgan soniyalar
let selectedFocusMinutes = 25;      // Tanlangan fokus vaqti
let isPageLeaving = false;          // Sahifadan chiqilayotganmi

// -------------------------------------------------------
// Ilova Ishga Tushishi
// -------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    // Token bo'lsa, to'g'ridan-to'g'ri dashboard'ga
    if (token && username) {
        showApp();
        loadDashboard();
    }
    
    // Enter tugmasi bilan login/register
    document.getElementById('login-password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') login();
    });
    
    // Sahifadan chiqishni nazorat qilish (fokus rejimida)
    window.addEventListener('beforeunload', handlePageLeave);
    document.addEventListener('visibilitychange', handleVisibilityChange);
});

// -------------------------------------------------------
// AUTH FUNKSIYALARI
// -------------------------------------------------------

/**
 * Login va Register tablarini almashtirish
 */
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach((b, i) => {
        b.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'register'));
    });
    document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
    document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
}

/**
 * Ro'yxatdan o'tish
 */
async function register() {
    const username_val = document.getElementById('reg-username').value.trim();
    const password_val = document.getElementById('reg-password').value;
    const errorEl = document.getElementById('reg-error');
    
    if (!username_val || !password_val) {
        errorEl.textContent = "Iltimos, barcha maydonlarni to'ldiring";
        return;
    }
    
    try {
        const res = await apiCall('/api/register', 'POST', { username: username_val, password: password_val });
        saveAuth(res.token, res.username);
        showApp();
        loadDashboard();
    } catch (e) {
        errorEl.textContent = e.message;
    }
}

/**
 * Tizimga kirish
 */
async function login() {
    const username_val = document.getElementById('login-username').value.trim();
    const password_val = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');
    
    if (!username_val || !password_val) {
        errorEl.textContent = "Iltimos, barcha maydonlarni to'ldiring";
        return;
    }
    
    try {
        const res = await apiCall('/api/login', 'POST', { username: username_val, password: password_val });
        saveAuth(res.token, res.username);
        showApp();
        loadDashboard();
    } catch (e) {
        errorEl.textContent = e.message;
    }
}

/**
 * Tizimdan chiqish
 */
function logout() {
    localStorage.removeItem('aliman_token');
    localStorage.removeItem('aliman_username');
    token = null;
    username = null;
    
    document.getElementById('app').classList.add('hidden');
    document.getElementById('auth-page').classList.remove('hidden');
}

/**
 * Auth ma'lumotlarini saqlash
 */
function saveAuth(t, u) {
    token = t;
    username = u;
    localStorage.setItem('aliman_token', t);
    localStorage.setItem('aliman_username', u);
}

// -------------------------------------------------------
// NAVIGATSIYA
// -------------------------------------------------------

/**
 * Asosiy ilovani ko'rsatish
 */
function showApp() {
    document.getElementById('auth-page').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('user-display').querySelector('.user-name').textContent = username;
}

/**
 * Sahifalar orasida o'tish
 */
function showSection(section) {
    // Barcha seksiyalarni yashirish
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    
    // Tanlangan seksiyani ko'rsatish
    document.getElementById(`section-${section}`).classList.add('active');
    document.querySelector(`[data-section="${section}"]`)?.classList.add('active');
    
    // Seksiyaga mos ma'lumotni yuklash
    if (section === 'plan') loadPlansPage();
    if (section === 'review') loadReview();
    if (section === 'chat') loadChatHistory();
}

// -------------------------------------------------------
// DASHBOARD
// -------------------------------------------------------

/**
 * Dashboard ma'lumotlarini yuklash
 */
async function loadDashboard() {
    try {
        const data = await apiCall('/api/dashboard', 'GET');
        
        // AI savolini ko'rsatish
        document.getElementById('ai-question').textContent = data.ai_question;
        
        // Statistikani yangilash
        document.getElementById('stat-minutes').textContent = data.stats.total_minutes || 0;
        document.getElementById('stat-sessions').textContent = data.stats.sessions || 0;
        document.getElementById('stat-distractions').textContent = data.stats.distractions || 0;
        
        // Rejalarni ko'rsatish
        renderPlansList(data.plans, 'plans-list', false);
        
    } catch (e) {
        console.error('Dashboard yuklanmadi:', e);
    }
}

/**
 * Tezkor reja qo'shish (Dashboard'dan)
 */
async function quickAddPlan() {
    const input = document.getElementById('quick-plan-input');
    const text = input.value.trim();
    if (!text) return;
    
    try {
        await apiCall('/api/plans', 'POST', { plan_text: text });
        input.value = '';
        loadDashboard(); // Ro'yxatni yangilash
    } catch (e) {
        alert('Reja qo\'shishda xato: ' + e.message);
    }
}

/**
 * Rejalar ro'yxatini render qilish
 */
function renderPlansList(plans, containerId, fullView = false) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (!plans || plans.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-400); font-size: 14px; text-align: center; padding: 20px;">Hali reja yo\'q. Yuqoridan qo\'shing! ☝️</p>';
        return;
    }
    
    container.innerHTML = plans.map(plan => `
        <div class="plan-item ${plan.completed ? 'completed' : ''}" id="plan-${plan.id}">
            <div class="plan-check ${plan.completed ? 'checked' : ''}" 
                 onclick="completePlan(${plan.id})" 
                 title="Bajarildi deb belgilash">
                ${plan.completed ? '✓' : ''}
            </div>
            <span class="plan-text">${escapeHtml(plan.plan_text)}</span>
        </div>
    `).join('');
}

/**
 * Rejani bajarildi deb belgilash
 */
async function completePlan(planId) {
    try {
        const res = await apiCall(`/api/plans/${planId}/complete`, 'PUT');
        // UI'ni yangilash (sahifani qayta yuklamasdan)
        const planEl = document.getElementById(`plan-${planId}`);
        if (planEl) {
            planEl.classList.add('completed');
            planEl.querySelector('.plan-check').classList.add('checked');
            planEl.querySelector('.plan-check').textContent = '✓';
            planEl.querySelector('.plan-text').style.textDecoration = 'line-through';
        }
        loadDashboard(); // Statistikani yangilash
    } catch (e) {
        console.error('Reja yangilanmadi:', e);
    }
}

// -------------------------------------------------------
// REJA SAHIFASI
// -------------------------------------------------------

/**
 * To'liq rejalar sahifasini yuklash
 */
async function loadPlansPage() {
    try {
        const data = await apiCall('/api/dashboard', 'GET');
        renderPlansList(data.plans, 'plans-full-list', true);
    } catch (e) {
        console.error('Rejalar yuklanmadi:', e);
    }
}

/**
 * Yangi reja qo'shish (Reja sahifasidan)
 */
async function addPlan() {
    const textarea = document.getElementById('plan-textarea');
    const text = textarea.value.trim();
    if (!text) return;
    
    try {
        await apiCall('/api/plans', 'POST', { plan_text: text });
        textarea.value = '';
        loadPlansPage();
    } catch (e) {
        alert('Reja qo\'shishda xato: ' + e.message);
    }
}

// -------------------------------------------------------
// FOKUS REJIMI
// -------------------------------------------------------

/**
 * Fokus vaqtini tanlash
 */
function selectTime(minutes, btn) {
    selectedFocusMinutes = minutes;
    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

/**
 * Focus Mode'ni boshlash
 */
async function startFocusMode() {
    try {
        const res = await apiCall('/api/focus/start', 'POST', { planned_minutes: selectedFocusMinutes });
        focusSessionId = res.session_id;
        
        // Fokus overlay'ni ko'rsatish
        document.getElementById('focus-overlay').classList.remove('hidden');
        document.getElementById('focus-complete').classList.add('hidden');
        document.getElementById('focus-ai-response').classList.add('hidden');
        
        // Taymerni boshlash
        focusMinutesLeft = selectedFocusMinutes;
        focusSecondsLeft = 0;
        updateTimerDisplay();
        
        focusTimerInterval = setInterval(tickTimer, 1000);
        
        // Fullscreen so'rash
        try {
            document.documentElement.requestFullscreen();
        } catch (e) {
            // Fullscreen ishlamasa ham davom et
        }
        
    } catch (e) {
        alert('Fokus rejimi boshlanmadi: ' + e.message);
    }
}

/**
 * Taymer bir soniya oldinga siljishi
 */
function tickTimer() {
    if (focusSecondsLeft > 0) {
        focusSecondsLeft--;
    } else if (focusMinutesLeft > 0) {
        focusMinutesLeft--;
        focusSecondsLeft = 59;
    } else {
        // VAQT TUGADI!
        clearInterval(focusTimerInterval);
        completeFocusSession();
        return;
    }
    updateTimerDisplay();
}

/**
 * Taymer ko'rsatuvini yangilash
 */
function updateTimerDisplay() {
    const m = String(focusMinutesLeft).padStart(2, '0');
    const s = String(focusSecondsLeft).padStart(2, '0');
    document.getElementById('timer-display').textContent = `${m}:${s}`;
    
    // Vaqt tugashiga yaqinlashganda rang o'zgartirish
    if (focusMinutesLeft < 5) {
        document.getElementById('timer-display').style.color = '#FCA5A5';
    }
}

/**
 * Fokus sessiyasi muvaffaqiyatli tugadi
 */
async function completeFocusSession() {
    if (!focusSessionId) return;
    
    try {
        const res = await apiCall('/api/focus/end', 'POST', {
            session_id: focusSessionId,
            exit_type: 'completed'
        });
        
        // Muvaffaqiyat ekranini ko'rsatish
        document.getElementById('focus-complete').classList.remove('hidden');
        document.getElementById('complete-message').textContent = 
            `${res.actual_minutes} daqiqa muvaffaqiyatli fokuslandingiz! Ajoyib! 🏆`;
        
    } catch (e) {
        console.error('Sessiya yakunlanmadi:', e);
        closeFocusMode();
    }
}

/**
 * Fokusdan chiqish ogohlantirishi
 */
function exitFocusConfirm() {
    clearInterval(focusTimerInterval);
    document.getElementById('exit-modal').classList.remove('hidden');
}

/**
 * Chiqish modalini yopish va taymerni davom ettirish
 */
function closeExitModal() {
    document.getElementById('exit-modal').classList.add('hidden');
    document.getElementById('exit-reason').value = '';
    
    // Taymerni davom ettirish
    focusTimerInterval = setInterval(tickTimer, 1000);
}

/**
 * Chiqishni tasdiqlash
 */
async function confirmExit() {
    const reason = document.getElementById('exit-reason').value.trim();
    document.getElementById('exit-modal').classList.add('hidden');
    
    if (focusSessionId) {
        try {
            const res = await apiCall('/api/focus/end', 'POST', {
                session_id: focusSessionId,
                exit_reason: reason || 'Sabab ko\'rsatilmadi',
                exit_type: 'distracted'
            });
            
            // AI javobi bo'lsa, ko'rsatish
            if (res.ai_response) {
                showAIWarning(res.ai_response);
            } else {
                closeFocusMode();
            }
            
        } catch (e) {
            closeFocusMode();
        }
    }
}

/**
 * AI tanbeh modalini ko'rsatish
 */
function showAIWarning(message) {
    document.getElementById('ai-warning-text').textContent = message;
    document.getElementById('ai-warning-modal').classList.remove('hidden');
}

/**
 * Fokusga qaytish (AI tanbehidan keyin)
 */
function returnToFocus() {
    document.getElementById('ai-warning-modal').classList.add('hidden');
    // Yangi sessiya boshlash
    startFocusMode();
}

/**
 * Fokus rejimini to'liq yopish
 */
function closeFocusMode() {
    clearInterval(focusTimerInterval);
    focusSessionId = null;
    focusTimerInterval = null;
    
    document.getElementById('focus-overlay').classList.add('hidden');
    document.getElementById('ai-warning-modal').classList.add('hidden');
    document.getElementById('exit-modal').classList.add('hidden');
    document.getElementById('timer-display').style.color = '';
    
    // Fullscreendan chiqish
    try {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        }
    } catch (e) {}
    
    // Dashboard'ni yangilash
    loadDashboard();
}

/**
 * Fokus vaqtida chat yuborish
 */
async function sendFocusChat() {
    const input = document.getElementById('focus-chat-input');
    const message = input.value.trim();
    if (!message) return;
    
    input.value = '';
    
    try {
        const res = await apiCall('/api/chat', 'POST', { message, context: 'focus' });
        
        const responseEl = document.getElementById('focus-ai-response');
        responseEl.textContent = res.reply;
        responseEl.classList.remove('hidden');
        
    } catch (e) {
        console.error('Fokus chat xatosi:', e);
    }
}

/**
 * Sahifadan chiqish (tab yopilganda)
 */
function handlePageLeave(e) {
    if (focusSessionId && !isPageLeaving) {
        e.preventDefault();
        e.returnValue = '⚠️ Fokus rejimida ekansiz! Sahifani tark etsangiz, sessiya to\'xtatiladi!';
        return e.returnValue;
    }
}

/**
 * Tab/oyna yashirilganda (focus chiqilganda)
 */
function handleVisibilityChange() {
    if (document.hidden && focusSessionId) {
        // Sahifa yashirildi - ogohlantirish
        clearInterval(focusTimerInterval);
        
        // AI ogohlantirish
        const warningMsg = `🔔 Sahifadan chiqdingiz!

Fokus rejimida boshqa tab yoki oynaga o'tish chalg'ish hisoblanadi.

Qaytib keling va fokusda davom eting! 💪`;
        
        // Sahifaga qaytganda modal ko'rsatish
        setTimeout(() => {
            if (!document.hidden && focusSessionId) {
                showAIWarning(warningMsg);
            }
        }, 100);
    } else if (!document.hidden && focusSessionId) {
        // Sahifaga qaytildi - taymerni davom ettirish
        if (!document.getElementById('ai-warning-modal').classList.contains('hidden')) {
            return; // Modal ko'rinayotgan bo'lsa kutish
        }
        focusTimerInterval = setInterval(tickTimer, 1000);
    }
}

// -------------------------------------------------------
// CHAT
// -------------------------------------------------------

/**
 * Chat tarixini yuklash
 */
async function loadChatHistory() {
    try {
        const data = await apiCall('/api/chat/history', 'GET');
        
        const container = document.getElementById('chat-messages');
        
        if (data.messages.length === 0) {
            container.innerHTML = `
                <div class="chat-message assistant">
                    <div class="msg-avatar">🤖</div>
                    <div class="msg-content">
                        Salom, ${username}! 👋 Men Aliman AI - fokuslanishga yordam beruvchi yordamchingizman.
                        Bugun nima haqida gaplashamiz?
                    </div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.messages.map(msg => `
            <div class="chat-message ${msg.role}">
                <div class="msg-avatar">${msg.role === 'assistant' ? '🤖' : '👤'}</div>
                <div class="msg-content">${escapeHtml(msg.content)}</div>
            </div>
        `).join('');
        
        // Eng pastga scroll
        container.scrollTop = container.scrollHeight;
        
    } catch (e) {
        console.error('Chat tarixi yuklanmadi:', e);
    }
}

/**
 * Chat xabari yuborish
 */
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;
    
    input.value = '';
    
    // Foydalanuvchi xabarini darhol ko'rsatish
    appendChatMessage('user', message);
    
    // "Yozmoqda..." ko'rsatish
    const thinkingId = appendChatMessage('assistant', '🤔 Yozmoqda...');
    
    try {
        const res = await apiCall('/api/chat', 'POST', { message, context: 'dashboard' });
        
        // "Yozmoqda..."ni AI javobi bilan almashtirish
        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) {
            thinkingEl.querySelector('.msg-content').textContent = res.reply;
        }
        
    } catch (e) {
        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) {
            thinkingEl.querySelector('.msg-content').textContent = 'Xabar yuborishda xato. Qayta urinib ko\'ring.';
        }
    }
}

/**
 * Chat containerga xabar qo'shish
 */
function appendChatMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const id = 'msg-' + Date.now();
    
    const el = document.createElement('div');
    el.className = `chat-message ${role}`;
    el.id = id;
    el.innerHTML = `
        <div class="msg-avatar">${role === 'assistant' ? '🤖' : '👤'}</div>
        <div class="msg-content">${escapeHtml(content)}</div>
    `;
    
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    
    return id;
}

// -------------------------------------------------------
// KUN YAKUNI TAHLILI
// -------------------------------------------------------

/**
 * Kun yakuni tahlilini yuklash
 */
async function loadReview() {
    const content = document.getElementById('review-content');
    content.textContent = 'Tahlil yuklanmoqda...';
    
    try {
        const data = await apiCall('/api/review', 'GET');
        content.textContent = data.analysis;
    } catch (e) {
        content.textContent = 'Tahlil yuklanmadi. Qayta urinib ko\'ring.';
    }
}

// -------------------------------------------------------
// API YORDAMCHI FUNKSIYA
// -------------------------------------------------------

/**
 * Barcha API chaqiruvlari uchun yagona funksiya
 */
async function apiCall(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);
    
    const res = await fetch(API_URL + endpoint, options);
    const data = await res.json();
    
    if (!res.ok) {
        throw new Error(data.detail || 'Xato yuz berdi');
    }
    
    return data;
}

// -------------------------------------------------------
// YORDAMCHI FUNKSIYALAR
// -------------------------------------------------------

/**
 * XSS hujumlaridan himoya qilish uchun HTML escape
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(text)));
    return div.innerHTML;
}

/**
 * Motivatsion iqtiboslar (fokus vaqtida)
 */
const FOCUS_QUOTES = [
    "\"Har bir buyuk natija - kichik, izchil harakatlar yig'indisi.\"",
    "\"Muvaffaqiyat - bu bir marta kelgan imkoniyat emas, har kun qilinadigan tanlov.\"",
    "\"Diqqat - bu eng qimmatli resurs. Uni oqilona sarfla.\"",
    "\"Zerikish - bu o'sish chegarasida turganingizning belgisi.\"",
    "\"Bir soatlik diqqatli ish - sakkiz soatlik chalg'ib ishlashdan ko'proq natija beradi.\"",
    "\"Hozir qiyin ko'ringan narsa - ertaga oddiy ko'rinadi.\"",
    "\"Maqsadingni ko'z o'ngingda tut. Har bir daqiqa shunga ketsin.\""
];

let quoteIndex = 0;
function rotateFocusQuotes() {
    quoteIndex = (quoteIndex + 1) % FOCUS_QUOTES.length;
    document.getElementById('focus-quote').textContent = FOCUS_QUOTES[quoteIndex];
}

// Har 30 soniyada iqtibosni almashtirish
setInterval(rotateFocusQuotes, 30000);
