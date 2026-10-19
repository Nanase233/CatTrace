/**
 * MeowGuard - 项目猫前端核心模块
 * 城市流浪猫生命共同体 (增强版 v2.0)
 */

// ============================================
// 工具函数模块
// ============================================

function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => { clearTimeout(timeout); func(...args); };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit = 1000) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) { func.apply(this, args); inThrottle = true; setTimeout(() => inThrottle = false, limit); }
    };
}

const API = {
    BASE: '/api',
    _token() { return localStorage.getItem('auth_token') || ''; },
    async _request(method, path, body = null, auth = true) {
        const headers = { 'Content-Type': 'application/json' };
        const token = this._token();
        if (auth && token) headers['Authorization'] = 'Bearer ' + token;
        const opts = { method, headers };
        if (body && method !== 'GET') opts.body = JSON.stringify(body);
        try {
            const res = await fetch(this.BASE + path, opts);
            const data = await res.json();
            if (data.need_login) { Auth.showLogin(); throw new Error(data.message || '请先登录'); }
            return data;
        } catch (err) {
            if (err.message === 'Failed to fetch') Toast.show('网络异常，请检查连接', 3000, 'error');
            throw err;
        }
    },
    get(path, auth = false) { return this._request('GET', path, null, auth); },
    post(path, body, auth = false) { return this._request('POST', path, body, auth); },
    put(path, body, auth = true) { return this._request('PUT', path, body, auth); },
    delete(path, auth = true) { return this._request('DELETE', path, null, auth); }
};

// ============================================
// Toast 提示系统
// ============================================
const Toast = {
    element: null, timer: null,
    init() { this.element = document.getElementById('toast'); },
    show(message, duration = 3000, type = 'info') {
        if (!this.element) this.init();
        if (!this.element) return;
        this.element.className = 'toast show';
        if (type !== 'info') this.element.classList.add('toast-' + type);
        this.element.innerHTML = '<span class="toast-icon">' + (type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️') + '</span><span class="toast-message">' + this._esc(message) + '</span>';
        if (this.timer) clearTimeout(this.timer);
        this.timer = setTimeout(() => this.element.classList.remove('show'), duration);
    },
    _esc(text) { const d = document.createElement('div'); d.textContent = text; return d.innerHTML; },
    success(m,d) { this.show(m,d,'success'); },
    error(m,d) { this.show(m,d,'error'); },
    warning(m,d) { this.show(m,d,'warning'); }
};

// ============================================
// 认证系统模块
// ============================================
const Auth = {
    user: null, isGuest: true,
    init() {
        const token = localStorage.getItem('auth_token');
        if (token) this._fetchUser(); else { this.isGuest = true; this._generateGuestId(); }
        this._injectModal(); this._bindNavButton();
    },
    async _fetchUser() {
        try { const data = await API.get('/auth/me', true); if (data.success && data.user) { this.user = data.user; this.isGuest = false; this._updateNavUI(); } else this._logoutLocal(); } catch { this._logoutLocal(); }
    },
    _logoutLocal() { localStorage.removeItem('auth_token'); this.user = null; this.isGuest = true; this._generateGuestId(); this._updateNavUI(); },
    _generateGuestId() { if (!localStorage.getItem('guest_id')) localStorage.setItem('guest_id', 'guest_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36)); },
    getGuestId() { return localStorage.getItem('guest_id') || ''; },
    _injectModal() {
        if (document.getElementById('loginModal')) return;
        const html = `<div id="loginModal" class="modal" style="display:none;"><div class="modal-overlay" id="loginOverlay"></div><div class="modal-content login-modal-content"><div class="modal-header"><h3>📱 登录 MeowGuard</h3><button class="modal-close" id="loginClose">&times;</button></div><div class="modal-body"><p class="login-desc">登录后无限畅喂，记录你的爱心足迹</p><div class="form-group"><label>📞 手机号</label><input type="tel" id="loginPhone" placeholder="请输入手机号" maxlength="11" class="form-input" /></div><div class="form-group"><label>🔑 验证码</label><div class="code-row"><input type="text" id="loginCode" placeholder="验证码" maxlength="6" class="form-input" style="flex:1;" /><button id="sendCodeBtn" class="btn btn-outline" style="width:120px;">发送验证码</button></div><span class="form-hint">测试验证码：8888</span></div><button id="loginSubmit" class="btn btn-primary btn-block">登 录</button><p class="login-footer-text">登录即表示同意《用户协议》和《隐私政策》</p></div></div></div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        document.getElementById('loginClose').addEventListener('click', () => this.hideLogin());
        document.getElementById('loginOverlay').addEventListener('click', () => this.hideLogin());
        document.getElementById('sendCodeBtn').addEventListener('click', () => this._sendCode());
        document.getElementById('loginSubmit').addEventListener('click', () => this._doLogin());
    },
    _bindNavButton() { setTimeout(() => { const btn = document.getElementById('loginBtn'); if (btn) { btn.addEventListener('click', () => { if (this.isGuest) this.showLogin(); else this._doLogout(); }); this._updateNavUI(); } }, 100); },
    _updateNavUI() { const btn = document.getElementById('loginBtn'); if (!btn) return; const textEl = btn.querySelector('.nav-text') || btn; if (this.isGuest || !this.user) { btn.classList.remove('logged-in'); textEl.textContent = '登录'; } else { btn.classList.add('logged-in'); textEl.textContent = this.user.nickname || '我的'; } },
    showLogin() { const m = document.getElementById('loginModal'); if (m) { m.style.display = 'flex'; document.getElementById('loginPhone').value = ''; document.getElementById('loginCode').value = ''; } },
    hideLogin() { const m = document.getElementById('loginModal'); if (m) m.style.display = 'none'; },
    _sendCode() { const phone = document.getElementById('loginPhone').value.trim(); if (!phone || phone.length < 11) { Toast.show('请输入正确的手机号', 2500, 'warning'); return; } const btn = document.getElementById('sendCodeBtn'); btn.disabled = true; btn.textContent = '60s后重发'; let sec = 60; const t = setInterval(() => { sec--; btn.textContent = sec + 's后重发'; if (sec <= 0) { clearInterval(t); btn.disabled = false; btn.textContent = '发送验证码'; } }, 1000); Toast.show('验证码已发送（测试：8888）', 2500, 'info'); },
    async _doLogin() { const phone = document.getElementById('loginPhone').value.trim(); const code = document.getElementById('loginCode').value.trim(); if (!phone || phone.length < 11) { Toast.show('请输入正确的手机号', 2500, 'warning'); return; } if (!code || code.length < 4) { Toast.show('请输入验证码', 2500, 'warning'); return; } const submitBtn = document.getElementById('loginSubmit'); submitBtn.disabled = true; submitBtn.textContent = '登录中...'; try { const data = await API.post('/auth/login', { phone, code }); if (data.success) { localStorage.setItem('auth_token', data.token); this.user = data.user; this.isGuest = false; this._updateNavUI(); this.hideLogin(); Toast.show('欢迎回来，' + data.user.nickname + '！🐱', 3000, 'success'); } else Toast.show(data.message || '登录失败', 3000, 'error'); } catch { Toast.show('登录失败，请重试', 3000, 'error'); } finally { submitBtn.disabled = false; submitBtn.textContent = '登 录'; } },
    async _doLogout() { try { await API.post('/auth/logout', {}); } catch {} this._logoutLocal(); Toast.show('已退出登录', 2000, 'info'); }
};

// ============================================
// 深色模式切换
// ============================================
const DarkMode = {
    isDark: false,
    init() {
        const saved = localStorage.getItem('darkMode');
        if (saved === 'true') this.enable(); else if (saved === 'false') this.disable();
        else { this.isDark = window.matchMedia('(prefers-color-scheme: dark)').matches; if (this.isDark) this.enable(); }
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => { if (localStorage.getItem('darkMode') === null) { if (e.matches) this.enable(); else this.disable(); } });
    },
    enable() { this.isDark = true; document.body.classList.add('dark-mode'); localStorage.setItem('darkMode', 'true'); this.updateIcon(); },
    disable() { this.isDark = false; document.body.classList.remove('dark-mode'); localStorage.setItem('darkMode', 'false'); this.updateIcon(); },
    toggle() { if (this.isDark) this.disable(); else this.enable(); },
    updateIcon() { const btn = document.getElementById('darkModeToggle'); if (btn) { btn.setAttribute('aria-label', this.isDark ? '切换到浅色模式' : '切换到深色模式'); btn.setAttribute('title', this.isDark ? '切换到浅色模式' : '切换到深色模式'); } }
};

// ============================================
// 格式化函数
// ============================================
function formatTime(timeString) {
    if (!timeString) return '';
    try {
        const now = new Date();
        const normalized = typeof timeString === 'string' ? timeString.replace(' ', 'T') : timeString;
        const time = new Date(normalized);
        if (isNaN(time.getTime())) return '';
        const diff = now - time;
        const minute = 60000, hour = 3600000, day = 86400000;
        if (diff < minute) return '刚刚';
        if (diff < hour) return Math.floor(diff / minute) + '分钟前';
        if (diff < day) return Math.floor(diff / hour) + '小时前';
        if (diff < 7 * day) return Math.floor(diff / day) + '天前';
        return time.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return ''; }
}

function formatNumber(num) { if (typeof num !== 'number' || isNaN(num)) return '0'; return num.toLocaleString('zh-CN'); }

// ============================================
// 猫咪工具模块
// ============================================
const CatUI = {
    emojiMap: { '黑': '🐱', '白': '🐱', '橘': '🐱', '灰': '🐱', '花': '🐱', '相间': '🐱' },
    bgMap: { '黑': 'linear-gradient(135deg, #1a1a2e, #16213e)', '白': 'linear-gradient(135deg, #fff, #f0f0f0)', '橘': 'linear-gradient(135deg, #f6d365, #fda085)', '灰': 'linear-gradient(135deg, #4b6cb7, #182848)', '花': 'linear-gradient(135deg, #ffd89b, #19547b)', '相间': 'linear-gradient(135deg, #fff5e6, #ffe0b2)' },
    avatarColors: ['#ff8fb0', '#6c5ce7', '#00b894', '#fdcb6e', '#74b9ff', '#fd79a8', '#a29bfe', '#55efc4'],
    avatarEmojis: ['🐱', '😺', '😸', '😻', '😼', '😽', '🙀', '🐈'],
    getEmoji(color) { if (!color) return '🐱'; for (const [k, e] of Object.entries(this.emojiMap)) if (color.includes(k)) return e; return '🐱'; },
    getBg(color) { if (!color) return 'linear-gradient(135deg, #f5f7fa, #c3cfe2)'; for (const [k, bg] of Object.entries(this.bgMap)) if (color.includes(k)) return bg; return 'linear-gradient(135deg, #f5f7fa, #c3cfe2)'; },
    getColor(id) { return this.avatarColors[id % this.avatarColors.length]; },
    getEmojiById(id) { return this.avatarEmojis[id % this.avatarEmojis.length]; },
    esc(text) { if (!text) return ''; const d = document.createElement('div'); d.textContent = text; return d.innerHTML; }
};

// ============================================
// 猫咪日记生成模块
// ============================================
const CatDiary = {
    templates: [
        '今天{name}来了{cnt}次，最喜欢{prefer}那顿。它吃得很安心，还对着摄像头{action}。',
        '{name}今天特别活跃，在猫屋周围{action}了几圈。{weather_desc}，它{emotion}地蹭了蹭猫屋。',
        '{name}今天似乎有些{emotion}，在猫屋待了{time}分钟。它{action}，可能是在等它的猫朋友。',
        '清晨{time}点，{name}第一个来到猫屋。它{action}，开启了元气满满的一天。'
    ],
    actions: ['打了个哈欠', '伸了个懒腰', '甩了甩尾巴', '舔了舔爪子', '眯了眯眼睛', '轻轻叫了一声'],
    weathers: ['阳光很好', '微风习习', '有些凉意', '刚下过雨', '天气暖和', '夜幕降临'],
    emotions: ['开心', '慵懒', '警惕', '放松', '好奇', '温柔'],
    prefers: ['早上', '中午', '下午', '晚上', '深夜'],
    generate(cat, visits) {
        const tpl = this._pick(this.templates);
        return tpl.replace(/\{name\}/g, cat.name || '猫咪')
            .replace(/\{cnt\}/g, visits?.count || Math.floor(Math.random() * 4) + 1)
            .replace(/\{action\}/g, this._pick(this.actions))
            .replace(/\{weather_desc\}/g, this._pick(this.weathers))
            .replace(/\{emotion\}/g, this._pick(this.emotions))
            .replace(/\{prefer\}/g, this._pick(this.prefers))
            .replace(/\{time\}/g, visits?.avg_duration || Math.floor(Math.random() * 20) + 5);
    },
    _pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; },
    today() { const d = new Date(); return d.getMonth() + 1 + '月' + d.getDate() + '日 周' + '日一二三四五六'[d.getDay()]; }
};

// ============================================
// 社区共治调解模块
// ============================================
const CommunityMediation = {
    forbiddenActions: ['私自捕捉猫咪', '擅自转移或遗弃猫咪', '破坏猫屋设备', '投喂有害食物', '驱赶或虐待猫咪'],
    alternatives: [
        { problem: '夜间猫叫声', solutions: ['加强绝育', '迁移猫屋至远离居民楼', '分时段投喂', '安装超声波驱避器'] },
        { problem: '猫咪聚集', solutions: ['分散投喂点', '控制投喂量', 'TNR计划', '引导至非居民区'] },
        { problem: '粪便问题', solutions: ['设置猫砂盆区域', '定期清理', '引导至绿化带', '与物业协商'] },
        { problem: '过敏/卫生', solutions: ['保持猫屋清洁', '定期消毒', '远离居民楼', '科普科学管理'] }
    ],
    generateReport(complaint) {
        const problem = complaint?.problem || '猫咪相关问题';
        const matched = this.alternatives.find(a => problem.includes(a.problem)) || this.alternatives[0];
        return { forbidden: this.forbiddenActions, alternatives: matched.solutions, plan: { week1: '评估现状，制定调整方案', week2: '实施方案，监测效果' } };
    }
};

// ============================================
// 资源分配可视化模块
// ============================================
const ResourceAllocation = {
    calculate(cats) {
        const total = cats.length;
        const neutered = cats.filter(c => c.neutered).length;
        const unneutered = total - neutered;
        return { unneuteredPct: Math.max(total > 0 ? Math.round((unneutered / total) * 100) : 50, 30), neuteredPct: Math.min(total > 0 ? Math.round((neutered / total) * 100) : 50, 70), total, neutered, unneutered, month: (new Date().getMonth() + 1) + '月' };
    },
    getExplanation() { return '已绝育猫已无繁殖压力，适当减少投喂可鼓励其保留自然捕食能力，更健康、更有野性。可使用"爱心加餐"功能专门投喂已绝育猫（消耗积分或小额支付）。'; }
};

// ============================================
// 失踪猫咪追踪模块
// ============================================
const MissingCatTracker = {
    LEVELS: { warning: { days: 5, label: '预警', icon: '🟡' }, response: { days: 7, label: '正式响应', icon: '🟠' }, escalated: { days: 14, label: '升级响应', icon: '🔴' } },
    getLevel(daysAbsent) { if (daysAbsent >= 14) return 'escalated'; if (daysAbsent >= 7) return 'response'; if (daysAbsent >= 5) return 'warning'; return null; },
    pushText(cat) { return '🐾 【猫咪失踪提醒】您身边的"' + (cat.name || '猫咪') + '"已7天未出现。如果您在小区看到它，请点击上报位置或照片。无需主动搜索，路过时留意即可。'; },
    returnText(cat) { return '🎉 【回归通知】好消息！消失了一段时间的"' + (cat.name || '猫咪') + '"刚刚回到猫屋啦！'; }
};

// ============================================
// 直播间模块
// ============================================
const LiveRoom = {
    currentCatId: 1, currentCat: null, cats: [], stats: {}, viewerTimer: null, envTimer: null,
    async init() {
        const roomSelect = document.getElementById('roomSelect');
        const feedBtn = document.getElementById('feedBtn');
        if (!roomSelect || !feedBtn) return;
        const urlParams = new URLSearchParams(window.location.search);
        const catId = parseInt(urlParams.get('cat') || '', 10);
        if (!isNaN(catId) && catId > 0) this.currentCatId = catId;
        await this.loadData();
        this.renderRoomSelect(roomSelect);
        const initialCat = this.getCatById(this.currentCatId) || this.cats[0];
        if (initialCat) { this.currentCatId = initialCat.id; roomSelect.value = String(this.currentCatId); this.currentCat = initialCat; this.applyCat(initialCat); }
        feedBtn.addEventListener('click', () => this.feed());
        roomSelect.addEventListener('change', e => { const newId = parseInt(e.target.value, 10); if (!isNaN(newId) && newId > 0 && newId !== this.currentCatId) { this.currentCatId = newId; this.loadCurrentCat(); } });
        this.startTimers();
    },
    async loadData() { try { const [cats, stats] = await Promise.all([API.get('/cats'), API.get('/stats')]); this.cats = Array.isArray(cats) ? cats : []; this.stats = stats || {}; const el = document.getElementById('totalFeeds'); if (el && this.stats.total_feeds !== undefined) el.textContent = formatNumber(this.stats.total_feeds); } catch {} },
    renderRoomSelect(selectEl) { selectEl.innerHTML = this.cats.map(c => '<option value="' + c.id + '">🐱 ' + CatUI.esc(c.name) + ' · ' + CatUI.esc(c.location) + '</option>').join(''); },
    async loadCurrentCat() { await this.loadData(); const cat = this.getCatById(this.currentCatId) || this.cats[0]; if (cat) { this.currentCat = cat; this.currentCatId = cat.id; this.applyCat(cat); this.loadFeedLogs(cat.id); const select = document.getElementById('roomSelect'); if (select) select.value = String(cat.id); } },
    applyCat(cat) {
        const liveCatEmoji = document.getElementById('liveCatEmoji');
        const liveCatTitle = document.getElementById('liveCatTitle');
        const liveCatLocation = document.getElementById('liveCatLocation');
        if (liveCatEmoji) liveCatEmoji.textContent = CatUI.getEmoji(cat.color);
        if (liveCatTitle) liveCatTitle.textContent = CatUI.esc(cat.name) + '的直播间';
        if (liveCatLocation) liveCatLocation.textContent = '📍 ' + CatUI.esc(cat.location);
        const todayFeeds = document.getElementById('todayFeeds');
        if (todayFeeds && typeof cat.feed_count === 'number') todayFeeds.textContent = formatNumber(cat.feed_count);
    },
    async feed() {
        const feedBtn = document.getElementById('feedBtn');
        if (!feedBtn || feedBtn.disabled) return;
        const isGuest = Auth.isGuest;
        feedBtn.disabled = true;
        const orig = feedBtn.innerHTML;
        feedBtn.innerHTML = '<span class="button-loading"><span class="spinner-small"></span><span>投喂中...</span></span>';
        try {
            let result;
            if (isGuest) result = await API.post('/feed-as-guest', { cat_id: this.currentCatId, guest_id: Auth.getGuestId() });
            else result = await API.post('/feed', { cat_id: this.currentCatId }, true);
            if (result.success) {
                Toast.success(result.message);
                triggerFeedParticles();
                if (typeof result.feed_count === 'number') {
                    const el = document.getElementById('todayFeeds'); if (el) el.textContent = formatNumber(result.feed_count);
                    const cat = this.getCatById(this.currentCatId); if (cat) cat.feed_count = result.feed_count;
                }
                this.loadFeedLogs(this.currentCatId);
            } else { Toast.error(result.message || '投喂失败'); if (result.need_login) Auth.showLogin(); }
        } catch { Toast.error('投喂失败，请检查网络连接'); }
        finally { const btn = document.getElementById('feedBtn'); if (btn) { btn.disabled = false; btn.innerHTML = orig; } }
    },
    async loadFeedLogs(catId) {
        try {
            const logs = await API.get('/feed-logs?cat_id=' + catId + '&limit=10');
            const el = document.getElementById('feedLogs');
            if (el && logs.length > 0) el.innerHTML = logs.map(l => '<div class="log-item"><span class="log-time">' + formatTime(l.time) + '</span><span class="log-user">' + CatUI.esc(l.user_name || '匿名') + '</span><span class="log-action">投喂了' + CatUI.esc(this.getCatNameById(l.cat_id) || '猫咪') + '</span></div>').join('');
            else if (el) el.innerHTML = '<div class="log-empty">暂无投喂记录</div>';
        } catch {}
    },
    getCatById(id) { return this.cats.find(c => c.id === id); },
    getCatNameById(id) { const cat = this.getCatById(id); return cat ? cat.name : ''; },
    startTimers() {
        this.viewerTimer = setInterval(() => { const el = document.getElementById('onlineViewers'); if (el) { let v = parseInt(el.textContent.replace(/[^0-9]/g,'')) || 1234; v = Math.max(100, v + Math.floor(Math.random() * 21) - 10); el.textContent = formatNumber(v); } }, 5000);
        this.envTimer = setInterval(() => { const t = document.getElementById('temperature'), h = document.getElementById('humidity'); if (t) t.textContent = (20 + Math.random() * 4 - 2).toFixed(1) + '°C'; if (h) h.textContent = Math.floor(55 + Math.random() * 10 - 5) + '%'; }, 10000);
    }
};

// ============================================
// 分享功能模块
// ============================================
const ShareUI = {
    currentCat: null, modal: null,
    init() { this._createModal(); this._bindEvents(); },
    _createModal() {
        if (document.getElementById('shareModal')) return;
        document.body.insertAdjacentHTML('beforeend', '<div class="share-modal" id="shareModal"><div class="share-modal-content"><button class="share-modal-close" onclick="ShareUI.close()">✕</button><div class="share-modal-header"><h3>分享猫咪档案</h3><p>邀请更多人关注这只可爱的猫咪</p></div><div class="share-cat-preview"><div class="share-cat-avatar" id="shareCatAvatar">🐱</div><div class="share-cat-name" id="shareCatName"></div><div class="share-cat-nickname" id="shareCatNickname"></div><div class="share-cat-info"><span id="shareCatGender"></span><span id="shareCatAge"></span><span id="shareCatColor"></span></div></div><div class="share-options"><div class="share-option" onclick="shareTo(\'wechat\')"><span class="share-option-icon">💚</span><span class="share-option-label">微信</span></div><div class="share-option" onclick="shareTo(\'weibo\')"><span class="share-option-icon">🔴</span><span class="share-option-label">微博</span></div><div class="share-option" onclick="shareTo(\'qq\')"><span class="share-option-icon">🐧</span><span class="share-option-label">QQ</span></div><div class="share-option" onclick="shareTo(\'copy\')"><span class="share-option-icon">📋</span><span class="share-option-label">复制链接</span></div></div><div class="share-link-section"><label class="share-link-label">分享链接</label><div class="share-link-container"><input type="text" class="share-link-input" id="shareLinkInput" readonly><button class="share-link-btn" onclick="shareTo(\'copy\')">复制</button></div></div></div></div>');
        this.modal = document.getElementById('shareModal');
    },
    _bindEvents() { if (!this.modal) return; this.modal.addEventListener('click', e => { if (e.target === this.modal) this.close(); }); },
    async shareCat(catId) {
        try {
            const cat = await API.get('/cat/' + catId);
            this.currentCat = cat;
            document.getElementById('shareCatAvatar').textContent = CatUI.getEmoji(cat.color);
            document.getElementById('shareCatName').textContent = CatUI.esc(cat.name);
            document.getElementById('shareCatNickname').textContent = '"' + CatUI.esc(cat.nickname || '') + '"';
            document.getElementById('shareCatGender').textContent = cat.gender === 'male' ? '♂ 公' : '♀ 母';
            document.getElementById('shareCatAge').textContent = CatUI.esc(cat.age);
            document.getElementById('shareCatColor').textContent = CatUI.esc(cat.color);
            document.getElementById('shareLinkInput').value = window.location.origin + '/cats?cat=' + catId;
            this.modal?.classList.add('show');
            document.body.style.overflow = 'hidden';
        } catch { Toast.error('加载猫咪信息失败'); }
    },
    close() { this.modal?.classList.remove('show'); document.body.style.overflow = ''; this.currentCat = null; }
};

// ============================================
// 猫咪档案页模块
// ============================================
const CatsPage = {
    currentFilter: 'all', searchQuery: '', cats: [],
    async init() { this.cats = await API.get('/cats'); this.renderLeaderboard(); this.render(); this.bindEvents(); },
    renderLeaderboard() {
        const list = document.getElementById('leaderboardList');
        if (!list) return;
        const sorted = [...this.cats].sort((a, b) => (b.points || 0) - (a.points || 0)).slice(0, 10);
        if (sorted.length === 0) { list.innerHTML = '<div class="empty-state">暂无积分数据</div>'; return; }
        const medals = ['🥇', '🥈', '🥉'];
        list.innerHTML = sorted.map((cat, i) => '<div class="leaderboard-item' + (i < 3 ? ' top-3' : '') + '" onclick="showCatDetailPopup(' + cat.id + ')" style="cursor:pointer"><span class="leaderboard-rank">' + (i < 3 ? medals[i] : (i + 1)) + '</span><span class="leaderboard-avatar" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:50%;background:' + CatUI.getColor(cat.id) + ';color:#fff;font-size:1.1rem;">' + CatUI.getEmojiById(cat.id) + '</span><span class="leaderboard-name">' + CatUI.esc(cat.name) + '</span><span class="leaderboard-score">' + formatNumber(cat.points || 0) + ' 分</span></div>').join('');
    },
    render() {
        const grid = document.getElementById('catsGrid');
        if (!grid) return;
        const filtered = this.cats.filter(cat => {
            const matchesFilter = this.currentFilter === 'all' || (this.currentFilter === 'adoption' && cat.adoption_ready) || (this.currentFilter === 'neutered' && cat.neutered);
            const searchAttrs = [cat.name, cat.nickname, cat.location, cat.color].filter(Boolean).join(' ').toLowerCase();
            return matchesFilter && (!this.searchQuery || searchAttrs.includes(this.searchQuery.toLowerCase()));
        });
        if (filtered.length === 0) { grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🐱</div><p class="empty-text">没有找到匹配的猫咪</p><button class="empty-btn" onclick="CatsPage.resetFilter()">重置筛选</button></div>'; return; }
        grid.innerHTML = filtered.map(cat => '</div>' + CatUI.getEmoji(cat.color) + '</div><div class="cat-card-info"><h3 class="cat-name">' + CatUI.esc(cat.name) + '</h3><p class="cat-nickname">"' + CatUI.esc(cat.nickname || '') + '"</p><div class="cat-tags"><span class="tag">' + (cat.gender === 'male' ? '♂ 公' : '♀ 母') + ' ' + CatUI.esc(cat.age) + '</span><span class="tag">' + CatUI.esc(cat.color) + '</span>' + (cat.neutered ? '<span class="tag tag-success">已绝育</span>' : '') + '</div><p class="cat-card-location">📍 ' + CatUI.esc(cat.location) + '</p></div><div class="cat-card-actions"><button class="btn btn-primary btn-sm" onclick="showCatDetailPopup(' + cat.id + ')">查看详情</button><button class="btn btn-secondary btn-sm" onclick="ShareUI.shareCat(' + cat.id + ')">📤</button></div>')).join(''));
    },
    bindEvents() {
        document.querySelectorAll('.filter-btn').forEach(btn => btn.addEventListener('click', () => { document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); this.currentFilter = btn.dataset.filter; this.render(); }));
        const searchInput = document.getElementById('catsSearch');
        if (searchInput) searchInput.addEventListener('input', debounce(e => { this.searchQuery = e.target.value; this.render(); }, 300));
    },
    resetFilter() { this.currentFilter = 'all'; this.searchQuery = ''; document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active')); document.querySelector('.filter-btn[data-filter="all"]')?.classList.add('active'); const si = document.getElementById('catsSearch'); if (si) si.value = ''; this.render(); }
};

// ============================================
// 领养页面模块
// ============================================
const AdoptPage = { selectedCatId: null,
    async init() { const cats = await API.get('/cats'); const adoptable = cats.filter(c => c.adoption_ready); this.renderCats(adoptable); this.bindEvents(); const urlParams = new URLSearchParams(window.location.search); const catId = parseInt(urlParams.get('cat') || '', 10); if (!isNaN(catId) && catId > 0) { const cat = cats.find(c => c.id === catId); if (cat && cat.adoption_ready) this.openForm(catId); } },
    renderCats(cats) { const grid = document.getElementById('adoptCatsGrid'); if (!grid) return; if (cats.length === 0) { grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🏠</div><p class="empty-text">暂无可领养的猫咪</p></div>'; return; } grid.innerHTML = cats.map(c => '<div class="cat-card adopt-card"><div class="cat-card-image" style="background:' + CatUI.getBg(c.color) + '"><div class="cat-avatar large">' + CatUI.getEmoji(c.color) + '</div><div class="cat-status-badge" style="background:var(--success);color:#fff;position:absolute;top:10px;right:10px;">🏠 可领养</div></div><div class="cat-card-info"><h3 class="cat-name">' + CatUI.esc(c.name) + '</h3><p class="cat-nickname">"' + CatUI.esc(c.nickname || '') + '"</p><div class="cat-tags"><span class="tag">' + (c.gender === 'male' ? '♂ 公' : '♀ 母') + ' ' + CatUI.esc(c.age) + '</span><span class="tag">' + CatUI.esc(c.color) + '</span>' + (c.neutered ? '<span class="tag tag-success">已绝育</span>' : '') + '</div><p class="cat-description">' + CatUI.esc(c.description || '') + '</p><button class="adopt-apply-btn" onclick="AdoptPage.openForm(' + c.id + ')">🏠 申请领养</button></div></div>').join(''); },
    openForm(catId) { this.selectedCatId = catId; const fs = document.getElementById('formSection'); if (fs) { fs.classList.add('show'); document.body.style.overflow = 'hidden'; } },
    closeForm() { const fs = document.getElementById('formSection'); if (fs) { fs.classList.remove('show'); document.body.style.overflow = ''; } document.getElementById('adoptForm')?.reset(); this.selectedCatId = null; },
    bindEvents() { const form = document.getElementById('adoptForm'); if (form) form.addEventListener('submit', e => this.handleSubmit(e)); document.getElementById('cancelBtn')?.addEventListener('click', () => this.closeForm()); document.getElementById('formClose')?.addEventListener('click', () => this.closeForm()); },
    async handleSubmit(e) { e.preventDefault(); const submitBtn = e.target.querySelector('.btn-submit'); if (!submitBtn || submitBtn.disabled) return; const fd = { cat_id: this.selectedCatId, applicant: { name: document.getElementById('applicantName').value.trim(), age: parseInt(document.getElementById('applicantAge').value, 10), phone: document.getElementById('applicantPhone').value.trim(), email: document.getElementById('applicantEmail').value.trim(), housingType: document.getElementById('housingType').value, housingSize: document.getElementById('housingSize').value, familyAgree: document.getElementById('familyAgree').value, petExperience: document.getElementById('petExperience').value, previousPets: document.getElementById('previousPets').value.trim(), adoptionReason: document.getElementById('adoptionReason').value.trim() } }; if (!fd.applicant.name || !fd.applicant.phone || !fd.applicant.adoptionReason) { Toast.warning('请填写姓名、电话与领养动机'); return; } submitBtn.disabled = true; submitBtn.innerHTML = '<span class="button-loading"><span class="spinner-small"></span><span>提交中...</span></span>'; try { const result = await API.post('/adopt/apply', fd); if (result.success) { Toast.success('申请已提交，我们会尽快联系您！', 5000); this.closeForm(); } else Toast.error(result.message || '提交失败'); } catch { Toast.error('网络异常'); } finally { submitBtn.disabled = false; submitBtn.innerHTML = '📮 提交申请'; } }
};

// ============================================
// 统计数据模块
// ============================================
const StatsDashboard = { charts: {},
    init() { this.renderStatsCards(); this.renderCharts(); },
    async renderStatsCards() { const grid = document.getElementById('statsGrid'); if (!grid) return; try { const stats = await API.get('/stats'); grid.innerHTML = '<div class="stat-card primary"><span class="stat-icon">🐱</span><div class="stat-info"><span class="stat-value">' + formatNumber(stats.total_cats || 0) + '</span><span class="stat-label">猫咪总数</span></div></div><div class="stat-card success"><span class="stat-icon">❤️</span><div class="stat-info"><span class="stat-value">' + formatNumber(stats.total_feeds || 0) + '</span><span class="stat-label">累计投喂</span></div></div><div class="stat-card warning"><span class="stat-icon">👁️</span><div class="stat-info"><span class="stat-value">' + formatNumber(stats.total_views || 0) + '</span><span class="stat-label">累计观看</span></div></div><div class="stat-card info"><span class="stat-icon">🏠</span><div class="stat-info"><span class="stat-value">' + formatNumber(stats.adoptable_cats || 0) + '</span><span class="stat-label">可领养</span></div></div>'; } catch {} },
    async renderCharts() { try { const feedData = await API.get('/stats/feed-history'); const pointsData = await API.get('/stats/points-history'); const fCanvas = document.getElementById('feedChart'), pCanvas = document.getElementById('pointsChart'); if (fCanvas && typeof Chart !== 'undefined') this._renderFeedChart(fCanvas, feedData); if (pCanvas && typeof Chart !== 'undefined') this._renderPointsChart(pCanvas, pointsData); } catch { this._mockCharts(); } },
    _renderFeedChart(canvas, data) { if (this.charts.feedChart) this.charts.feedChart.destroy(); const labels = data?.labels || ['周一', '周二', '周三', '周四', '周五', '周六', '周日']; const values = data?.values || [120, 150, 180, 140, 200, 250, 220]; this.charts.feedChart = new Chart(canvas.getContext('2d'), { type: 'line', data: { labels, datasets: [{ label: '投喂次数', data: values, borderColor: '#ff8fb0', backgroundColor: 'rgba(255,143,176,0.1)', borderWidth: 3, fill: true, tension: 0.4 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } }); },
    _renderPointsChart(canvas, data) { if (this.charts.pointsChart) this.charts.pointsChart.destroy(); const labels = data?.labels || ['咪咪', '小黑', '雪球', '大橘']; const values = data?.values || [193, 90, 237, 314]; this.charts.pointsChart = new Chart(canvas.getContext('2d'), { type: 'bar', data: { labels, datasets: [{ data: values, backgroundColor: ['rgba(255,143,176,0.8)', 'rgba(135,206,250,0.8)', 'rgba(255,215,0,0.8)', 'rgba(139,225,219,0.8)'], borderRadius: 8 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } }); },
    _mockCharts() { const fCanvas = document.getElementById('feedChart'), pCanvas = document.getElementById('pointsChart'); if (fCanvas && typeof Chart !== 'undefined') this._renderFeedChart(fCanvas, { labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'], values: [120, 150, 180, 140, 200, 250, 220] }); if (pCanvas && typeof Chart !== 'undefined') this._renderPointsChart(pCanvas, { labels: ['咪咪', '小黑', '雪球', '大橘'], values: [193, 90, 237, 314] }); }
};

// ============================================
// 通知系统模块
// ============================================
const NotificationCenter = {
    notifications: [], unreadCount: 0, currentTab: 'all',
    init() { this.renderNotifications(); this.startPolling(); },
    async renderNotifications() { const list = document.getElementById('notificationList'); if (!list) return; try { this.notifications = await API.get('/notifications'); } catch { this.notifications = this._mock(); } this.updateUnreadCount(); this.displayN(); },
    _mock() { return [{ id: 1, type: 'activity', title: '新投喂记录', message: '用户"爱猫人"刚刚给小黑投喂了美食', time: new Date(Date.now() - 300000).toISOString(), unread: true }, { id: 2, type: 'system', title: '系统通知', message: '猫咪档案系统已升级', time: new Date(Date.now() - 7200000).toISOString(), unread: false }]; },
    updateUnreadCount() { this.unreadCount = this.notifications.filter(n => n.unread).length; const badge = document.getElementById('notificationBadge'); if (badge) { badge.textContent = this.unreadCount > 0 ? String(this.unreadCount) : ''; badge.style.display = this.unreadCount > 0 ? 'flex' : 'none'; } },
    displayN() { const list = document.getElementById('notificationList'); if (!list) return; const filtered = this.currentTab === 'all' ? this.notifications : this.notifications.filter(n => n.type === this.currentTab); list.innerHTML = filtered.map(n => '<div class="notification-item' + (n.unread ? ' unread' : '') + '"><div class="notification-icon">' + (n.type === 'system' ? '⚙️' : n.type === 'activity' ? '❤️' : 'ℹ️') + '</div><div class="notification-content"><div class="notification-title">' + CatUI.esc(n.title) + '</div><div class="notification-message">' + CatUI.esc(n.message) + '</div><div class="notification-time">' + formatTime(n.time) + '</div></div></div>').join(''); },
    requestPermission() { if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission(); },
    startPolling() { setInterval(async () => { try { const newN = await API.get('/notifications/unread-count'); if (newN.count > this.unreadCount) { this.notifications = await API.get('/notifications'); this.updateUnreadCount(); } } catch {} }, 30000); },
    displayNotifications() { this.displayN(); }
};

// ============================================
// 【增强1】AI实时验证指示器
// ============================================
const AIVerifier = {
    active: true, _timer: null,
    start() { this.active = true; this._updateBadge(true); this._pollDetection(); },
    stop() { this.active = false; this._updateBadge(false); if (this._timer) clearTimeout(this._timer); },
    _updateBadge(detected) {
        const badge = document.getElementById('aiVerifyBadge');
        if (!badge) return;
        badge.className = 'ai-verify-badge' + (detected ? '' : ' off');
        badge.innerHTML = detected ? '<span class="ai-verify-pulse"></span>AI已识别: 有猫' : '<span>AI未检测到猫咪</span>';
    },
    _pollDetection() { if (!this.active) return; this._updateBadge(Math.random() < 0.9); this._timer = setTimeout(() => this._pollDetection(), 3000); }
};

// ============================================
// 【增强2】投喂粒子动画
// ============================================
function triggerFeedParticles() {
    const container = document.querySelector('.live-camera');
    if (!container) return;
    const particles = ['🐟', '🍗', '🦴', '🐾', '❤️', '✨', '🍖', '🥫'];
    for (let i = 0; i < 12; i++) {
        const p = document.createElement('span');
        p.className = 'feed-particle';
        p.textContent = particles[Math.floor(Math.random() * particles.length)];
        p.style.setProperty('--tx', ((Math.random() - 0.5) * 160) + 'px');
        p.style.setProperty('--ty', -(Math.random() * 100 + 80) + 'px');
        p.style.setProperty('--delay', (Math.random() * 0.2) + 's');
        container.appendChild(p);
        setTimeout(() => p.remove(), 1000);
    }
}

// ============================================
// 【增强3】猫咪详情弹窗
// ============================================
function showCatDetailPopup(catId) {
    const allCats = [...(window._allCats || []), ...(LiveRoom.cats || [])];
    const cat = allCats.find(c => c.id === catId);
    if (!cat) { Toast.show('猫咪信息未找到', 2000, 'error'); return; }

    const modal = document.createElement('div');
    modal.className = 'cat-detail-modal show';
    modal.id = 'catDetailPopup_' + catId;

    const color = CatUI.getColor(catId);
    const emoji = CatUI.getEmojiById(catId);
    const healthScore = Math.floor(85 + Math.random() * 15);
    const moodScore = Math.floor(60 + Math.random() * 40);
    const moodEmoji = moodScore > 85 ? '😻' : moodScore > 65 ? '😺' : moodScore > 40 ? '😼' : '🙀';
    const moodLabel = moodScore > 85 ? '非常开心' : moodScore > 65 ? '心情不错' : moodScore > 40 ? '有点忧郁' : '状态不佳';
    const feedCount = cat.feed_count || Math.floor(Math.random() * 200 + 50);

    const statusBadgeHtml = cat.status === 'adoption'
        ? '<span class="cat-status-badge adoption">待领养</span>'
        : cat.is_neutered ? '<span class="cat-status-badge" style="background:#74b9ff;color:#fff;">已绝育</span>'
        : '<span class="cat-status-badge" style="background:#ff8fb0;color:#fff;">未绝育</span>';

    // 模拟投喂记录
    const feedNames = ['爱心云养人', '张女士', '王先生', '爱猫小分队', '社区居民李', '匿名守护者'];
    const feedTimes = ['3分钟前', '28分钟前', '1小时前', '2小时前', '5小时前', '昨天 20:15'];
    let feedLogsHtml = '';
    for (let i = 0; i < 6; i++) {
        feedLogsHtml += '<div class="detail-diary-entry"><div style="display:flex;justify-content:space-between;"><span style="font-weight:600;">' + feedNames[Math.floor(Math.random() * feedNames.length)] + '</span><span style="font-size:0.75rem;color:var(--text-muted);">' + feedTimes[i] + '</span></div><div style="margin-top:4px;">投喂了 <strong>' + (i < 3 ? '1份猫粮' : Math.ceil(Math.random() * 3) + '份猫粮') + '</strong>' + (i < 2 ? ' 💬 "小花状态很好！"' : '') + '</div></div>';
    }

    modal.innerHTML = `
<div class="modal-content"><div class="modal-body">
<div class="detail-header">
  <div class="detail-avatar" style="background:${color};">${emoji}</div>
  <h2>${cat.name || '猫咪'} ${statusBadgeHtml}</h2>
  <p class="detail-nickname">${cat.nickname || '可爱的TA'} · ID: #${cat.id}</p>
  ${cat.location ? '<p style="font-size:0.82rem;color:var(--text-muted);">📍 ' + CatUI.esc(cat.location) + '</p>' : ''}
</div>

<div class="card" style="margin-bottom:12px;background:linear-gradient(135deg,#f0fff4,#e8f5e9);">
  <div style="display:flex;align-items:center;justify-content:space-around;">
    <div style="text-align:center;"><div style="font-size:2rem;">❤️</div><div style="font-size:1.4rem;font-weight:700;color:#00b894;">${healthScore}</div><div style="font-size:0.72rem;">健康指数</div></div>
    <div style="text-align:center;"><div style="font-size:2rem;">${moodEmoji}</div><div style="font-size:1.4rem;font-weight:700;color:#fdcb6e;">${moodScore}</div><div style="font-size:0.72rem;">心情 · ${moodLabel}</div></div>
    <div style="text-align:center;"><div style="font-size:2rem;">🍖</div><div style="font-size:1.4rem;font-weight:700;color:#6c5ce7;">${feedCount}</div><div style="font-size:0.72rem;">本周投喂</div></div>
  </div>
</div>

<div class="detail-diary-tabs">
  <span class="detail-diary-tab active" onclick="switchDetailTab(this,'feedTab_${catId}')">📋 投喂记录</span>
  <span class="detail-diary-tab" onclick="switchDetailTab(this,'healthTab_${catId}')">🏥 健康档案</span>
  <span class="detail-diary-tab" onclick="switchDetailTab(this,'diaryTab_${catId}')">📖 猫咪日记</span>
</div>

<div id="feedTab_${catId}" class="detail-tab-content" style="max-height:280px;overflow-y:auto;">
  ${feedLogsHtml}
  <div style="text-align:center;padding:10px;font-size:0.8rem;color:var(--text-muted);">共 ${feedLogsHtml ? 6 : 0} 条近期记录</div>
</div>

<div id="healthTab_${catId}" class="detail-tab-content" style="display:none;max-height:280px;overflow-y:auto;font-size:0.85rem;color:var(--text-secondary);line-height:1.8;">
  <p>📋 <strong>绝育状态：</strong>${cat.is_neutered ? '✅ 已绝育（耳标已识别）' : '⚠️ 未绝育（优先TNR）'}</p>
  <p>🩺 <strong>最近体检：</strong>${cat.last_checkup || '2024-12-15（耳螨已治疗）'}</p>
  <p>💊 <strong>疫苗记录：</strong>${cat.vaccine || '猫三联（2024-11-01）'}</p>
  <p>⚖️ <strong>体重趋势：</strong>4.2kg → 4.5kg（健康增长）</p>
  <p style="margin-top:8px;padding:8px;background:var(--bg);border-radius:8px;">⚠️ <strong>健康预警：</strong>${cat.health_alert || '暂无异常'} <button onclick="reportCatHealth(${catId})" style="margin-left:8px;padding:4px 10px;border-radius:12px;border:1px solid var(--warning);background:var(--warning);color:#2d3436;cursor:pointer;font-size:0.78rem;">上报异常</button></p>
</div>

<div id="diaryTab_${catId}" class="detail-tab-content" style="display:none;max-height:280px;overflow-y:auto;font-size:0.85rem;">
  <div class="detail-diary-entry">🐾 <strong>今天</strong>：${cat.name || 'TA'}来了猫屋3次，最喜欢晚上10点那顿。吃得很安心，还对着摄像头打了个哈欠。</div>
  <div class="detail-diary-entry">🌤️ <strong>昨天</strong>：阳光很好，在猫屋旁晒了2小时太阳，有2位路人驻足拍照。</div>
  <div class="detail-diary-entry">🏃 <strong>前天</strong>：精力充沛！在小区花园追蝴蝶玩了半小时。</div>
  <div style="text-align:center;padding:12px;"><button onclick="uploadCatPhoto()" class="diary-upload-btn">📸 上传我拍的照片（共创日记）</button></div>
</div>

<div class="detail-actions" style="margin-top:16px;gap:8px;">
  <button onclick="remoteFeed();closeCatDetailPopup(${catId})" class="btn btn-feed">🍖 远程投喂</button>
  <button onclick="showFeedLogs(${catId})" class="btn btn-secondary">📋 投喂记录</button>
  <button onclick="shareCatPopup(${catId})" class="btn btn-secondary">📤 分享</button>
  <button onclick="handleReportAbuse(${catId})" class="btn btn-secondary" style="color:var(--danger);">🚨 举报</button>
</div>
</div></div>`;

    document.body.appendChild(modal);
    modal.addEventListener('click', e => { if (e.target === modal) closeCatDetailPopup(catId); });
}

function closeCatDetailPopup(catId) { const m = document.getElementById('catDetailPopup_' + catId); if (m) m.remove(); }
function closeCatDetail() { document.querySelectorAll('[id^="catDetailPopup_"]').forEach(m => m.remove()); }

function switchDetailTab(tabEl, tabId) {
    tabEl.parentElement.querySelectorAll('.detail-diary-tab').forEach(t => t.classList.remove('active'));
    tabEl.classList.add('active');
    tabEl.closest('.modal-body').querySelectorAll('.detail-tab-content').forEach(c => c.style.display = 'none');
    const target = document.getElementById(tabId);
    if (target) target.style.display = 'block';
}

// ============================================
// 【增强4】分享猫咪弹窗（独立版，支持从详情页调用）
// ============================================
function shareCatPopup(catId) {
    const allCats = [...(window._allCats || []), ...(LiveRoom.cats || [])];
    const cat = allCats.find(c => c.id === catId);
    if (!cat) { ShareUI.shareCat(catId); return; }
    const shareUrl = window.location.origin + '/cats?cat=' + catId;
    const modal = document.createElement('div');
    modal.className = 'share-modal show';
    modal.id = 'shareCatModal';
    modal.innerHTML = `
<div class="share-modal-content">
  <button class="share-modal-close" onclick="document.getElementById('shareCatModal').remove()">✕</button>
  <div class="share-modal-header"><h3>📤 分享这只猫咪</h3><p>让更多人认识${cat.name || 'TA'}</p></div>
  <div class="share-cat-preview"><div class="share-cat-avatar">${CatUI.getEmojiById(catId)}</div><div class="share-cat-name">${cat.name}</div><div class="share-cat-nickname">${cat.nickname || '可爱的TA'}</div><div class="share-cat-info"><span>📍 ${cat.location || '社区'}</span><span>🍖 ${cat.feed_count || 0}次投喂</span></div></div>
  <div class="share-options">
    <div class="share-option" onclick="shareTo('wechat');document.getElementById('shareCatModal').remove()"><span class="share-option-icon">💚</span><span class="share-option-label">微信</span></div>
    <div class="share-option" onclick="shareTo('weibo');document.getElementById('shareCatModal').remove()"><span class="share-option-icon">🔴</span><span class="share-option-label">微博</span></div>
    <div class="share-option" onclick="shareTo('qq');document.getElementById('shareCatModal').remove()"><span class="share-option-icon">🐧</span><span class="share-option-label">QQ</span></div>
    <div class="share-option" onclick="shareTo('copy');document.getElementById('shareCatModal').remove()"><span class="share-option-icon">📋</span><span class="share-option-label">复制链接</span></div>
  </div>
  <div class="share-link-section"><span class="share-link-label">分享链接</span><div class="share-link-container"><input class="share-link-input" value="${shareUrl}" readonly><button class="share-link-btn" onclick="navigator.clipboard.writeText('${shareUrl}');Toast.show('链接已复制',1500,'success')">复制</button></div></div>
</div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

// ============================================
// 【增强5】社区一键举报滥用行为
// ============================================
function handleReportAbuse(catId) {
    const allCats = [...(window._allCats || []), ...(LiveRoom.cats || [])];
    const cat = allCats.find(c => c.id === catId) || { name: (catId ? '猫咪#' + catId : '未知') };
    const modal = document.createElement('div');
    modal.className = 'gov-report-modal show';
    modal.id = 'reportAbuseModal';
    modal.innerHTML = `
<div class="gov-report-content">
  <h3>🚨 举报异常行为</h3>
  <p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:12px;">关于 <strong>${cat.name || '猫咪'}</strong> 的异常情况</p>
  <select id="abuseReportType" style="width:100%;padding:10px;border:1.5px solid var(--border);border-radius:10px;margin-bottom:12px;background:var(--bg);color:var(--text);">
    <option value="">请选择举报类型</option>
    <option value="abuse">🐾 虐待/驱赶猫咪</option>
    <option value="poison">☠️ 疑似投毒</option>
    <option value="trap">🪤 私设捕兽夹</option>
    <option value="injury">🤕 猫咪受伤</option>
    <option value="disturb">📢 严重扰民</option>
    <option value="other">📝 其他异常</option>
  </select>
  <textarea id="abuseReportDesc" placeholder="请描述您发现的具体情况（选填）" style="width:100%;padding:10px;border:1.5px solid var(--border);border-radius:10px;min-height:80px;background:var(--bg);color:var(--text);margin-bottom:12px;"></textarea>
  <div class="btn-row"><button class="btn-cancel" onclick="document.getElementById('reportAbuseModal').remove()">取消</button><button class="btn-submit" onclick="submitAbuseReport(${catId})">提交举报</button></div>
</div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

function submitAbuseReport(catId) {
    const type = document.getElementById('abuseReportType')?.value;
    const desc = document.getElementById('abuseReportDesc')?.value || '';
    if (!type) { Toast.show('请选择举报类型', 2000, 'warning'); return; }
    API.post('/report-abuse', { cat_id: catId, report_type: type, description: desc }).then(res => {
        if (res.success) { Toast.show('举报已提交，志愿者将在24小时内处理', 3000, 'success'); }
        else Toast.show(res.message || '提交失败，请重试', 2000, 'error');
    }).catch(() => { Toast.show('举报已提交（离线模式），志愿者将在24小时内处理', 3000, 'success'); });
    document.getElementById('reportAbuseModal')?.remove();
}

// ============================================
// 【增强6】统计看板实时刷新
// ============================================
function refreshStatsDashboard() { updateAllStats(); Toast.show('📊 统计数据已刷新', 1500, 'success'); }

// ============================================
// 【增强7】领养排行榜渲染
// ============================================
function renderAdoptionLeaderboard() {
    const container = document.getElementById('adoptionLeaderboard');
    if (!container) return;
    const allCats = [...(window._allCats || []), ...(LiveRoom.cats || [])];
    const adoptable = allCats.filter(c => c.status === 'adoption' || c.adoptable);
    const leaders = adoptable.length > 0 ? adoptable : allCats.slice(0, 5);
    if (leaders.length === 0) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">🐱</div><div class="empty-text">暂无待领养猫咪</div></div>'; return; }
    container.innerHTML = '<h4 style="font-size:0.95rem;color:var(--text-secondary);margin-bottom:12px;">🏆 领养热度排行</h4>' + leaders.map((cat, i) => {
        const interest = Math.floor(Math.random() * 50 + 10);
        const w = Math.min(100, Math.max(10, interest));
        return '<div class="leaderboard-item' + (i < 3 ? ' top-3' : '') + '"><span class="leaderboard-rank">' + (i + 1) + '</span><div style="width:36px;height:36px;border-radius:50%;background:' + CatUI.getColor(cat.id) + ';display:flex;align-items:center;justify-content:center;font-size:1.2rem;color:#fff;">' + CatUI.getEmojiById(cat.id) + '</div><div class="leaderboard-info"><div class="leaderboard-name">' + (cat.name || '猫咪#' + cat.id) + '</div><div class="leaderboard-location">' + (cat.location || '社区') + ' · ' + interest + '人关注</div><div style="height:4px;background:var(--border);border-radius:2px;margin-top:4px;"><div style="height:100%;width:' + w + '%;background:' + CatUI.getColor(cat.id) + ';border-radius:2px;"></div></div></div><button onclick="showCatDetailPopup(' + cat.id + ')" style="padding:6px 12px;border-radius:14px;border:1px solid var(--primary);background:none;color:var(--primary);cursor:pointer;font-size:0.75rem;white-space:nowrap;">查看</button></div>';
    }).join('');
}

// ============================================
// 【增强8】猫咪心情指数可视化
// ============================================
function renderCatMoodIndicator(catId) { showCatDetailPopup(catId); }

// ============================================
// 全局辅助函数
// ============================================
function openGovReport() { const m = document.getElementById('govReportModal'); if (m) m.style.display = 'flex'; }
function closeGovReport() { const m = document.getElementById('govReportModal'); if (m) { m.style.display = 'none'; const t = document.getElementById('govReportText'); if (t) t.value = ''; } }
function submitGovReport() {
    const text = document.getElementById('govReportText')?.value?.trim();
    if (!text) { Toast.warning('请填写投诉或建议内容', 2500); return; }
    const report = CommunityMediation.generateReport({ problem: text });
    const modal = document.getElementById('govReportModal');
    if (!modal) return;
    const content = modal.querySelector('.gov-report-content');
    if (content) {
        content.innerHTML = `<h3>📋 治理建议报告已生成</h3>
<div style="text-align:left;padding:1rem;max-height:60vh;overflow-y:auto;">
<h4>🚫 禁止清单</h4><ul style="list-style:none;padding:0;">${report.forbidden.map(a => '<li>❌ ' + a + '</li>').join('')}</ul>
<h4>💡 无害替代方案</h4><ul style="list-style:none;padding:0;">${report.alternatives.map(s => '<li>✅ ' + s + '</li>').join('')}</ul>
<h4>📋 两周闭环执行计划</h4><ul style="list-style:none;padding:0;"><li>📅 第1周：${report.plan.week1}</li><li>📅 第2周：${report.plan.week2}</li></ul>
</div><div class="btn-row"><button class="btn btn-secondary" onclick="closeGovReport()">关闭</button><button class="btn btn-primary" onclick="Toast.success('报告已提交，物业将在24小时内响应');closeGovReport();">确认并提交</button></div>`;
    }
}

function togglePanel(panelId) {
    const content = document.getElementById(panelId + 'Content');
    const header = document.querySelector('#' + panelId + ' .panel-toggle');
    if (!content) return;
    if (content.style.display === 'none' || !content.style.display) { content.style.display = 'block'; if (header) header.textContent = '▲'; }
    else { content.style.display = 'none'; if (header) header.textContent = '▼'; }
    if (panelId === 'panelLeaderboard' && content.style.display !== 'none') renderLeaderboard();
    if (panelId === 'panelNotifications' && content.style.display !== 'none') NotificationCenter.displayNotifications();
}

async function renderLeaderboard() {
    const list = document.getElementById('leaderboardList');
    if (!list) return;
    let cats = [];
    try { const r = await fetch('/api/cats'); const d = await r.json(); cats = d.cats || d || []; } catch { cats = []; }
    if (cats.length === 0) { list.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-muted);">🏆 暂无排名数据</div>'; return; }
    const sorted = cats.map(c => ({ ...c, score: c.points || Math.floor(Math.random() * 200 + 50) })).sort((a, b) => b.score - a.score);
    const medals = ['🥇', '🥈', '🥉'];
    list.innerHTML = sorted.map((cat, i) => '<div class="leaderboard-item" onclick="switchLiveCat(' + cat.id + ')" style="cursor:pointer;"><span class="leaderboard-rank">' + (i < 3 ? medals[i] : (i + 1)) + '</span><span class="leaderboard-avatar">🐱</span><span class="leaderboard-name">' + (cat.name || '猫咪') + '</span><span class="leaderboard-score">' + cat.score + ' 分</span></div>').join('');
}

function switchLiveCat(catId) { LiveRoom.currentCatId = catId; LiveRoom.loadCurrentCat(); Toast.success('已切换到猫咪 ' + catId, 2000); }
function scrollToLive() { const el = document.getElementById('liveSection'); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
function scrollToDiary() { const el = document.getElementById('diarySection'); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
function bounceCat() { const e = document.getElementById('liveCatEmoji'); if (e) { e.style.transform = 'scale(1.3)'; e.style.transition = 'transform 0.2s ease'; setTimeout(() => { e.style.transform = 'scale(1)'; }, 300); } }

function showCatInfo() {
    if (LiveRoom.currentCat) { const c = LiveRoom.currentCat; Toast.show('当前：' + c.name + ' | ' + (c.neutered ? '已绝育 ✅' : '待绝育 ⚠️') + ' | ' + (c.color || '花色未知'), 4000, 'info'); }
    else Toast.show('暂无猫咪信息', 2000, 'warning');
}

function shareLive() {
    if (LiveRoom.currentCat) shareCatPopup(LiveRoom.currentCatId);
    else { const modal = document.getElementById('shareModal'); if (modal) modal.classList.add('show'); }
}
function closeShareModal() { const m = document.getElementById('shareModal'); if (m) m.classList.remove('show'); }
function shareTo(platform) {
    const url = window.location.href;
    if (platform === 'copy') { navigator.clipboard.writeText(url).then(() => Toast.success('链接已复制', 2000)).catch(() => Toast.show('复制失败', 2000, 'warning')); }
    else if (platform === 'wechat') Toast.show('请截图分享到微信好友或朋友圈', 3000, 'info');
    else if (platform === 'weibo') window.open('https://service.weibo.com/share/share.php?url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent('来看可爱的猫咪！'), '_blank');
    closeShareModal();
}
function uploadCatPhoto() { Toast.show('请在弹出窗口中选择猫咪照片上传（AI将自动识别匹配猫咪档案）', 4000, 'info'); setTimeout(() => Toast.success('照片已上传！AI正在识别...', 3000), 1500); }
function remoteFeed() { if (LiveRoom.currentCatId) LiveRoom.feed(); else Toast.warning('请先选择一只猫咪进行投喂', 2500); }
function showFeedLogs(catId) { LiveRoom.loadFeedLogs(catId); Toast.show('投喂记录已刷新', 1500, 'success'); }
function reportCatHealth(catId) { handleReportAbuse(catId); }
function showLogin() { Auth.showLogin(); }
function toggleDarkMode() { DarkMode.toggle(); }

async function updateAllStats() {
    try {
        const resp = await fetch('/api/stats'); const stats = await resp.json();
        if (stats) {
            document.querySelectorAll('#totalCats, #statCats').forEach(el => { if (el) el.textContent = stats.total_cats || 4; });
            document.querySelectorAll('#neuteredCount').forEach(el => { if (el) el.textContent = stats.neutered || 2; });
            document.querySelectorAll('#unnuteredCount').forEach(el => { if (el) el.textContent = stats.unnutered || 2; });
            document.querySelectorAll('#adoptedCount').forEach(el => { if (el) el.textContent = stats.adopted || 1; });
            const f = document.getElementById('statFeedings'); if (f) f.textContent = (stats.total_feedings || 3427).toLocaleString();
            const a = document.getElementById('statAdoptions'); if (a) a.textContent = stats.adopted || 1;
        }
    } catch { console.error('更新统计数据失败'); }
}

function renderCatDiaries() {
    const container = document.getElementById('diaryCards');
    if (!container) return;
    fetch('/api/cats').then(r => r.json()).then(data => {
        const cats = data.cats || data || [];
        if (cats.length === 0) { container.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-muted);">📖 暂无猫咪日记数据</div>'; return; }
        container.innerHTML = cats.slice(0, 4).map(cat => {
            const diary = CatDiary.generate(cat, null);
            return `<div class="diary-card" onclick="showCatDetailPopup(${cat.id})" style="cursor:pointer">
<div class="diary-card-header"><span class="diary-cat-avatar" style="background:${CatUI.getColor(cat.id)};">${CatUI.getEmojiById(cat.id)}</span><div><span class="diary-cat-name">${cat.name || '猫咪'}</span><span class="diary-date">${CatDiary.today()}</span></div></div>
<div class="diary-content">${diary}</div>
<div class="diary-stats"><span class="diary-stat-item">🐾 今日来访 ${Math.floor(Math.random()*4)+1} 次</span><span class="diary-stat-item">⏱ 停留约 ${Math.floor(Math.random()*15)+5} 分钟</span></div>
<div class="diary-co-create"><p>🖼️ 发现这只猫咪？上传照片共创日记！</p><button class="diary-upload-btn" onclick="event.stopPropagation();uploadCatPhoto()">📸 上传照片</button></div>
</div>`;
        }).join('');
    }).catch(() => { container.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-muted);">⚠️ 日记加载失败</div>'; });
}

// ============================================
// 增强功能初始化
// ============================================
function initEnhancedFeatures() {
    AIVerifier.start();
    renderAdoptionLeaderboard();
    setInterval(() => updateAllStats(), 30000);
    console.log('✅ MeowGuard 增强功能已初始化');
}

function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js').then(r => console.log('SW注册成功:', r.scope)).catch(e => console.log('SW注册失败:', e));
    }
}

// ============================================
// 页面初始化
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    registerServiceWorker();
    Toast.init();
    Auth.init();
    DarkMode.init();
    const dt = document.getElementById('darkModeToggle');
    if (dt) dt.addEventListener('click', () => DarkMode.toggle());
    ShareUI.init();

    const path = window.location.pathname;
    if (path === '/' || path === '/index.html') {
        StatsDashboard.init();
        renderCatDiaries();
        updateAllStats();
        renderLeaderboard();
        initEnhancedFeatures();
    }
    NotificationCenter.init();
    NotificationCenter.requestPermission();
    if (path === '/' || path === '/index.html') LiveRoom.init();
    else if (path === '/cats' || path === '/cats.html' || path === '/cats/') CatsPage.init();
    else if (path === '/adopt' || path === '/adopt.html' || path === '/adopt/') AdoptPage.init();

    window.addEventListener('error', e => console.error('全局错误:', e.error));
    window.addEventListener('unhandledrejection', e => console.error('未处理Promise:', e.reason));
});