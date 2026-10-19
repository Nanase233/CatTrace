/**
 * DashboardPage - 财务看板独立页面模块
 */
const DashboardPage = {
    summary: null,
    categories: null,
    currentPage: 1,
    totalPages: 1,
    currentFilter: { type: '', category: '' },

    async init() {
        await this.loadSummary();
        await this.loadTransactions();
        await this.loadMonthlyTrend();
        this.bindEvents();
    },

    async loadSummary() {
        try {
            const resp = await fetch('/api/finance/summary');
            const data = await resp.json();
            if (!data.success) {
                Toast.show('加载财务数据失败', 2000, 'error');
                return;
            }

            this.summary = data.summary;
            this.categories = data.categories;

            // 更新概览卡片
            this._updateOverviewCards();

            // 渲染分类统计
            this._renderCategoryStats(data.income_by_category, data.expense_by_category);

            // 填充分类筛选下拉框
            this._populateCategoryFilter();
        } catch (err) {
            console.error('加载财务概览失败:', err);
            Toast.show('网络异常', 2000, 'error');
        }
    },

    _updateOverviewCards() {
        const s = this.summary;
        if (!s) return;
        
        const setEl = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.textContent = text;
        };
        
        setEl('totalIncome', `¥${s.total_income.toLocaleString()}`);
        setEl('totalExpense', `¥${s.total_expense.toLocaleString()}`);
        setEl('balance', `¥${s.balance.toLocaleString()}`);
        setEl('monthIncome', `¥${s.month_income.toLocaleString()}`);
        setEl('monthExpense', `¥${s.month_expense.toLocaleString()}`);
        setEl('transactionCount', s.transaction_count);
    },

    _renderCategoryStats(incomeByCat, expenseByCat) {
        const incomeList = document.getElementById('incomeCategoryList');
        const expenseList = document.getElementById('expenseCategoryList');

        if (!incomeList || !expenseList) return;

        // 收入分类
        const incomeItems = Object.entries(incomeByCat).map(([key, amount]) => {
            const cat = this.categories.income[key] || { name: key, icon: '💰', color: '#b2bec3' };
            const percent = this.summary.total_income > 0 
                ? (amount / this.summary.total_income * 100).toFixed(1) 
                : 0;
            return `<div class="finance-category-item">
                <div class="finance-category-info">
                    <span class="finance-category-icon">${cat.icon}</span>
                    <span class="finance-category-name">${this._esc(cat.name)}</span>
                </div>
                <div class="finance-category-amount">¥${amount.toLocaleString()}</div>
                <div class="finance-category-bar">
                    <div class="finance-category-bar-fill" style="width:${percent}%; background:${cat.color}"></div>
                </div>
                <div class="finance-category-percent">${percent}%</div>
            </div>`;
        });

        incomeList.innerHTML = incomeItems.length > 0 
            ? incomeItems.join('') 
            : '<div class="finance-empty">暂无收入记录</div>';

        // 支出分类
        const expenseItems = Object.entries(expenseByCat).map(([key, amount]) => {
            const cat = this.categories.expense[key] || { name: key, icon: '💸', color: '#b2bec3' };
            const percent = this.summary.total_expense > 0 
                ? (amount / this.summary.total_expense * 100).toFixed(1) 
                : 0;
            return `<div class="finance-category-item">
                <div class="finance-category-info">
                    <span class="finance-category-icon">${cat.icon}</span>
                    <span class="finance-category-name">${this._esc(cat.name)}</span>
                </div>
                <div class="finance-category-amount">¥${amount.toLocaleString()}</div>
                <div class="finance-category-bar">
                    <div class="finance-category-bar-fill" style="width:${percent}%; background:${cat.color}"></div>
                </div>
                <div class="finance-category-percent">${percent}%</div>
            </div>`;
        });

        expenseList.innerHTML = expenseItems.length > 0 
            ? expenseItems.join('') 
            : '<div class="finance-empty">暂无支出记录</div>';
    },

    _populateCategoryFilter() {
        const select = document.getElementById('transCategoryFilter');
        if (!select || !this.categories) return;

        let options = '<option value="">全部分类</option>';
        
        // 收入分类
        Object.entries(this.categories.income).forEach(([key, cat]) => {
            options += `<option value="${key}">${cat.icon} ${cat.name}</option>`;
        });
        
        // 支出分类
        Object.entries(this.categories.expense).forEach(([key, cat]) => {
            options += `<option value="${key}">${cat.icon} ${cat.name}</option>`;
        });

        select.innerHTML = options;
    },

    async loadTransactions() {
        const list = document.getElementById('transactionsList');
        if (!list) return;

        list.innerHTML = '<div class="finance-loading">加载中...</div>';

        try {
            let url = `/api/finance/transactions?page=${this.currentPage}&per_page=10`;
            if (this.currentFilter.type) url += `&type=${this.currentFilter.type}`;
            if (this.currentFilter.category) url += `&category=${this.currentFilter.category}`;

            const resp = await fetch(url);
            const data = await resp.json();

            if (!data.success) {
                list.innerHTML = '<div class="finance-empty">加载失败</div>';
                return;
            }

            this.totalPages = data.total_pages || 1;
            this._updatePagination();

            const transactions = data.transactions || [];
            if (transactions.length === 0) {
                list.innerHTML = '<div class="finance-empty">暂无交易记录</div>';
                return;
            }

            const items = transactions.map(t => {
                const cat = (t.type === 'income' 
                    ? this.categories.income[t.category] 
                    : this.categories.expense[t.category]) 
                    || { name: t.category, icon: '📦', color: '#b2bec3' };
                
                const amountClass = t.type === 'income' ? 'amount-income' : 'amount-expense';
                const amountPrefix = t.type === 'income' ? '+' : '-';
                const partyInfo = t.type === 'income' 
                    ? (t.donor || '匿名') 
                    : (t.vendor || '未知');

                return `<div class="finance-transaction-item">
                    <div class="trans-left">
                        <div class="trans-icon" style="background:${cat.color}20; color:${cat.color}">
                            ${cat.icon}
                        </div>
                        <div class="trans-info">
                            <div class="trans-desc">${this._esc(t.description)}</div>
                            <div class="trans-meta">
                                <span class="trans-category">${this._esc(cat.name)}</span>
                                <span class="trans-party">${this._esc(partyInfo)}</span>
                            </div>
                        </div>
                    </div>
                    <div class="trans-right">
                        <div class="trans-amount ${amountClass}">${amountPrefix}¥${t.amount.toLocaleString()}</div>
                        <div class="trans-date">${this._formatDate(t.date)}</div>
                    </div>
                </div>`;
            });

            list.innerHTML = items.join('');
        } catch (err) {
            console.error('加载交易记录失败:', err);
            list.innerHTML = '<div class="finance-empty">网络异常，请刷新重试</div>';
        }
    },

    async loadMonthlyTrend() {
        const chart = document.getElementById('monthlyChart');
        if (!chart) return;

        try {
            const resp = await fetch('/api/finance/monthly');
            const data = await resp.json();

            if (!data.success || !data.monthly || data.monthly.length === 0) {
                chart.innerHTML = '<div class="finance-empty">暂无月度数据</div>';
                return;
            }

            const monthly = data.monthly;
            const maxAmount = Math.max(...monthly.map(m => Math.max(m.income, m.expense)));

            const bars = monthly.map(m => {
                const incomeHeight = maxAmount > 0 ? (m.income / maxAmount * 100) : 0;
                const expenseHeight = maxAmount > 0 ? (m.expense / maxAmount * 100) : 0;
                const monthLabel = m.month.slice(5); // MM

                return `<div class="chart-month">
                    <div class="chart-bars">
                        <div class="chart-bar income-bar" style="height:${incomeHeight}%" title="收入: ¥${m.income}">
                            <span class="chart-bar-label">¥${m.income}</span>
                        </div>
                        <div class="chart-bar expense-bar" style="height:${expenseHeight}%" title="支出: ¥${m.expense}">
                            <span class="chart-bar-label">¥${m.expense}</span>
                        </div>
                    </div>
                    <div class="chart-month-label">${monthLabel}月</div>
                </div>`;
            });

            chart.innerHTML = `
                <div class="chart-legend">
                    <span class="legend-item"><span class="legend-dot income-dot"></span>收入</span>
                    <span class="legend-item"><span class="legend-dot expense-dot"></span>支出</span>
                </div>
                <div class="chart-container">${bars.join('')}</div>
            `;
        } catch (err) {
            console.error('加载月度趋势失败:', err);
            chart.innerHTML = '<div class="finance-empty">加载失败</div>';
        }
    },

    _updatePagination() {
        const p = document.getElementById('financePagination');
        if (!p) return;

        p.style.display = this.totalPages > 1 ? 'flex' : 'none';
        const prev = document.getElementById('prevPageBtn');
        const next = document.getElementById('nextPageBtn');
        const info = document.getElementById('pageInfo');

        if (prev) prev.disabled = this.currentPage <= 1;
        if (next) next.disabled = this.currentPage >= this.totalPages;
        if (info) info.textContent = `第 ${this.currentPage} / ${this.totalPages} 页`;
    },

    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
            this.loadTransactions();
            window.scrollTo({ top: document.querySelector('.finance-transactions-section').offsetTop - 100, behavior: 'smooth' });
        }
    },

    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadTransactions();
            window.scrollTo({ top: document.querySelector('.finance-transactions-section').offsetTop - 100, behavior: 'smooth' });
        }
    },

    bindEvents() {
        const typeFilter = document.getElementById('transTypeFilter');
        const categoryFilter = document.getElementById('transCategoryFilter');

        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                this.currentFilter.type = e.target.value;
                this.currentPage = 1;
                this.loadTransactions();
            });
        }

        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.currentFilter.category = e.target.value;
                this.currentPage = 1;
                this.loadTransactions();
            });
        }
    },

    _esc(text) {
        if (!text) return '';
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    },

    _formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return dateStr;
            return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
        } catch {
            return dateStr;
        }
    }
};