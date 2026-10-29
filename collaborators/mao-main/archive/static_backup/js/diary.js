/**
 * DiaryPage - 猫咪日记独立页面模块
 */
const DiaryPage = {
    cats: [], currentCatFilter: 'all', currentPage: 1,
    perPage: 10, totalPages: 1, currentSort: 'date-desc',
    currentDetailDiary: null,

    async init() {
        await this.loadCats();
        this.renderCatFilters();
        await this.loadDiaries();
        this.bindEvents();
    },
    async loadCats() {
        try { const r = await fetch('/api/cats'); const d = await r.json(); this.cats = d.cats || d || []; } catch { this.cats = []; }
    },
    renderCatFilters() {
        const c = document.getElementById('catFilterBtns');
        if (!c) return;
        c.innerHTML = this.cats.map(cat => `<button class="diary-filter-btn" data-cat="${cat.id}">${this._getEmoji(cat.id)} ${cat.name || '猫咪'}</button>`).join('');
    },
    async loadDiaries() {
        const tl = document.getElementById('diaryTimeline');
        if (!tl) return;
        tl.innerHTML = '<div class="diary-loading"><div class="diary-loading-spinner"></div><p>正在翻阅猫咪日记...</p></div>';
        try {
            let url = `/api/diaries?page=${this.currentPage}&per_page=${this.perPage}`;
            if (this.currentCatFilter !== 'all') url += `&cat_id=${this.currentCatFilter}`;
            const resp = await fetch(url);
            const data = await resp.json();
            if (!data.success) { tl.innerHTML = '<div class="diary-empty"><div class="diary-empty-icon">😿</div><p>加载失败</p></div>'; return; }
            this.totalPages = data.total_pages || 1;
            this._updatePagination();
            const diaries = data.diaries || [];
            if (diaries.length === 0) { tl.innerHTML = '<div class="diary-empty"><div class="diary-empty-icon">📖</div><p class="diary-empty-text">暂无日记记录</p></div>'; return; }
            const sorted = this._sortDiaries(diaries);
            const groups = {};
            sorted.forEach(d => { const date = d.date || '未知日期'; if (!groups[date]) groups[date] = []; groups[date].push(d); });
            let html = '';
            for (const [date, entries] of Object.entries(groups)) {
                const ds = date.slice(5).split('-')[1] || '?';
                html += `<div class="diary-date-group"><div class="diary-date-badge">${ds}</div><div class="diary-date-title">📅 ${this._formatDateLabel(date)}</div>${entries.map((d, i) => this._renderEntry(d, i)).join('')}</div>`;
            }
            tl.innerHTML = html;
        } catch (err) { console.error('加载日记失败:', err); tl.innerHTML = '<div class="diary-empty"><div class="diary-empty-icon">⚠️</div><p>加载失败，请刷新重试</p></div>'; }
    },

    _renderEntry(d, idx) {
        const moods = { '开心': '😊', '慵懒': '😴', '警惕': '👀', '放松': '😌', '好奇': '🤔', '温柔': '🥰' };
        const moodE = moods[d.mood] || '🐱';
        const liked = localStorage.getItem(`diary_liked_${d.id}`) === '1';
        return `<div class="diary-entry" onclick="DiaryPage.showDetail(${d.id})" style="animation-delay:${idx*0.08}s">
            <div class="diary-entry-header">
                <div class="diary-entry-avatar">${this._getEmoji(d.cat_id)}</div>
                <div class="diary-entry-meta">
                    <span class="diary-entry-name">${this._esc(d.cat_name)}</span>
                    <span class="diary-entry-sub">
                        <span>${this._esc(d.cat_location || '')}</span>
                        <span class="diary-entry-mood">${moodE} ${d.mood || ''}</span>
                    </span>
                </div>
            </div>
            <div class="diary-entry-body">${this._esc(d.content || '')}</div>
            <div class="diary-entry-footer">
                <div class="diary-entry-stats">
                    <span class="diary-entry-stat">🐾 ${d.visits || 0} 次来访</span>
                    <span class="diary-entry-stat">⏱ ${d.duration || 0} 分钟</span>
                </div>
                <div class="diary-entry-actions">
                    <button class="diary-action-btn ${liked ? 'liked' : ''}" onclick="event.stopPropagation(); DiaryPage.toggleLike(${d.id}, this)">
                        ${liked ? '❤️' : '🤍'} <span class="like-count">${d.likes || 0}</span>
                    </button>
                    <button class="diary-action-btn" onclick="event.stopPropagation(); DiaryPage.showDetail(${d.id})">
                        💬 ${(d.comments || []).length}
                    </button>
                </div>
            </div>
        </div>`;
    },

    _sortDiaries(diaries) {
        const s = [...diaries];
        if (this.currentSort === 'date-desc') s.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
        else if (this.currentSort === 'date-asc') s.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
        else if (this.currentSort === 'likes') s.sort((a, b) => (b.likes || 0) - (a.likes || 0));
        return s;
    },

    _formatDateLabel(dateStr) {
        if (!dateStr) return '未知日期';
        const today = new Date().toISOString().slice(0, 10);
        const yd = new Date(); yd.setDate(yd.getDate() - 1);
        const ydStr = yd.toISOString().slice(0, 10);
        if (dateStr === today) return `${dateStr}（今天）`;
        if (dateStr === ydStr) return `${dateStr}（昨天）`;
        const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
        const d = new Date(dateStr + 'T00:00:00');
        return isNaN(d.getTime()) ? dateStr : `${dateStr}（${weekdays[d.getDay()]}）`;
    },

    async toggleLike(diaryId, btn) {
        const liked = localStorage.getItem(`diary_liked_${diaryId}`) === '1';
        if (liked) {
            localStorage.removeItem(`diary_liked_${diaryId}`);
            btn.classList.remove('liked');
            const c = btn.querySelector('.like-count');
            const n = Math.max(0, parseInt(c?.textContent || 0) - 1);
            btn.innerHTML = `🤍 <span class="like-count">${n}</span>`;
            return;
        }
        try {
            const resp = await fetch(`/api/diaries/${diaryId}/like`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
            const data = await resp.json();
            if (data.success) {
                localStorage.setItem(`diary_liked_${diaryId}`, '1');
                btn.classList.add('liked');
                btn.innerHTML = `❤️ <span class="like-count">${data.likes}</span>`;
                btn.style.transform = 'scale(1.2)';
                setTimeout(() => { btn.style.transform = ''; }, 200);
            }
        } catch { Toast.show('点赞失败', 2000, 'error'); }
    },

    async showDetail(diaryId) {
        const modal = document.getElementById('diaryDetailModal');
        const body = document.getElementById('diaryDetailBody');
        if (!modal || !body) return;
        body.innerHTML = '<div class="diary-loading"><div class="diary-loading-spinner"></div></div>';
        modal.classList.add('show');
        try {
            const resp = await fetch(`/api/diaries?page=1&per_page=50${this.currentCatFilter !== 'all' ? '&cat_id=' + this.currentCatFilter : ''}`);
            const data = await resp.json();
            const diary = (data.diaries || []).find(d => d.id === diaryId);
            if (!diary) { body.innerHTML = '<div class="diary-empty"><p>日记不存在</p></div>'; return; }
            this.currentDetailDiary = diary;
            const moodEmojis = { '开心': '😊', '慵懒': '😴', '警惕': '👀', '放松': '😌', '好奇': '🤔', '温柔': '🥰' };
            const moodEmoji = moodEmojis[diary.mood] || '🐱';
            const comments = diary.comments || [];
            body.innerHTML = `
                <div class="detail-cat-header">
                    <div class="detail-cat-avatar">${this._getEmoji(diary.cat_id)}</div>
                    <div class="detail-cat-info"><h3>${this._esc(diary.cat_name)}</h3><p>${this._esc(diary.cat_nickname || '')} · ${this._esc(diary.cat_location || '')}</p></div>
                </div>
                <div class="detail-diary-date">📅 ${this._formatDateLabel(diary.date)} · ${moodEmoji} ${diary.mood || ''}</div>
                <div class="detail-diary-text">${this._esc(diary.content || '')}</div>
                <div class="detail-diary-stats">
                    <span>🐾 来访 ${diary.visits || 0} 次</span>
                    <span>⏱ 停留 ${diary.duration || 0} 分钟</span>
                    <span>🤍 ${diary.likes || 0} 次点赞</span>
                </div>
                <div class="detail-comments-title">💬 评论 (${comments.length})</div>
                <div class="detail-comment-list" id="commentList">
                    ${comments.length > 0 ? comments.map(c => `
                        <div class="detail-comment-item">
                            <span class="detail-comment-user">${this._esc(c.user)}</span>
                            <span class="detail-comment-text">${this._esc(c.text)}</span>
                            <div class="detail-comment-time">${this._formatTime(c.time)}</div>
                        </div>`).join('') : '<div class="detail-comment-empty">暂无评论，来留下第一条吧！</div>'}
                </div>
                <div class="detail-comment-form">
                    <div class="detail-comment-input-wrap">
                        <input type="text" id="commentUser" placeholder="你的昵称" maxlength="32">
                        <textarea id="commentText" placeholder="写下你的评论..." rows="2" maxlength="500"></textarea>
                    </div>
                    <button class="detail-comment-submit" onclick="DiaryPage.submitComment(${diary.id})">发送</button>
                </div>`;
        } catch { body.innerHTML = '<div class="diary-empty"><p>加载失败</p></div>'; }
    },

    async submitComment(diaryId) {
        const userEl = document.getElementById('commentUser');
        const textEl = document.getElementById('commentText');
        if (!userEl || !textEl) return;
        const user = userEl.value.trim();
        const text = textEl.value.trim();
        if (!user) { Toast.show('请填写昵称', 2000, 'warning'); return; }
        if (!text) { Toast.show('评论内容不能为空', 2000, 'warning'); return; }
        try {
            const resp = await fetch(`/api/diaries/${diaryId}/comment`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user, text })
            });
            const data = await resp.json();
            if (data.success) {
                Toast.show('评论成功！', 2000, 'success');
                const list = document.getElementById('commentList');
                if (list) {
                    const empty = list.querySelector('.detail-comment-empty');
                    if (empty) empty.remove();
                    list.insertAdjacentHTML('beforeend', `<div class="detail-comment-item" style="animation:diarySlideIn 0.3s ease"><span class="detail-comment-user">${this._esc(data.comment.user)}</span><span class="detail-comment-text">${this._esc(data.comment.text)}</span><div class="detail-comment-time">刚刚</div></div>`);
                }
                textEl.value = '';
                const title = document.querySelector('.detail-comments-title');
                if (title) title.innerHTML = `💬 评论 (${data.comment_count})`;
                this.loadDiaries();
            } else { Toast.show(data.message || '评论失败', 2000, 'error'); }
        } catch { Toast.show('网络异常', 2000, 'error'); }
    },

    closeDetail() {
        const m = document.getElementById('diaryDetailModal');
        if (m) m.classList.remove('show');
    },
    nextPage() {
        if (this.currentPage < this.totalPages) { this.currentPage++; this.loadDiaries(); window.scrollTo({ top: 0, behavior: 'smooth' }); }
    },
    prevPage() {
        if (this.currentPage > 1) { this.currentPage--; this.loadDiaries(); window.scrollTo({ top: 0, behavior: 'smooth' }); }
    },

    _updatePagination() {
        const p = document.getElementById('diaryPagination');
        if (!p) return;
        p.style.display = this.totalPages > 1 ? 'flex' : 'none';
        const prev = document.getElementById('prevPageBtn');
        const next = document.getElementById('nextPageBtn');
        const info = document.getElementById('pageInfo');
        if (prev) prev.disabled = this.currentPage <= 1;
        if (next) next.disabled = this.currentPage >= this.totalPages;
        if (info) info.textContent = `第 ${this.currentPage} / ${this.totalPages} 页`;
    },

    bindEvents() {
        document.querySelectorAll('.diary-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.diary-filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentCatFilter = btn.dataset.cat;
                this.currentPage = 1;
                this.loadDiaries();
            });
        });
        const sortSelect = document.getElementById('diarySort');
        if (sortSelect) sortSelect.addEventListener('change', (e) => { this.currentSort = e.target.value; this.loadDiaries(); });
        const modal = document.getElementById('diaryDetailModal');
        if (modal) modal.addEventListener('click', (e) => { if (e.target === modal) this.closeDetail(); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') this.closeDetail(); });
    },

    _getEmoji(catId) { return { 1: '🐱', 2: '🐈‍⬛', 3: '🐈', 4: '😺' }[catId] || '🐱'; },
    _esc(text) { if (!text) return ''; const d = document.createElement('div'); d.textContent = text; return d.innerHTML; },
    _formatTime(timeStr) {
        if (!timeStr) return '';
        try {
            const d = new Date(timeStr); if (isNaN(d.getTime())) return timeStr;
            const diffMin = Math.floor((Date.now() - d) / 60000);
            if (diffMin < 1) return '刚刚';
            if (diffMin < 60) return `${diffMin} 分钟前`;
            const h = Math.floor(diffMin / 60);
            if (h < 24) return `${h} 小时前`;
            const day = Math.floor(h / 24);
            if (day < 7) return `${day} 天前`;
            return d.toLocaleDateString('zh-CN');
        } catch { return timeStr; }
    }
};

