/**
 * 定时任务管理器
 * 职责：定时任务列表、表单、执行记录与运行状态展示
 */
class ScheduledTaskManager {
    constructor() {
        this.tasks = [];
        this.filteredTasks = [];
        this.historyRecords = [];
        this.runtimeStatus = this.createFallbackRuntimeStatus();
        this.currentFilter = 'all';
        this.currentLayout = 'grid';
        this.currentSearch = '';
        this.selectedTaskId = '';
        this.initialized = false;
        this.apiWarningShown = false;
        this._autoRefreshTimer = null;

        this.init();
    }

    async init() {
        if (this.initialized) {
            await this.refreshData({ silent: true });
            return;
        }

        this.bindEvents();
        this.resetForm({ keepSelection: false, silent: true });
        await this.refreshData({ silent: true });
        this.initialized = true;
    }

    bindEvents() {
        const viewRoot = this.getViewRoot();
        if (!viewRoot) {
            return;
        }

        const searchInput = document.getElementById('scheduled-task-search');
        searchInput?.addEventListener('input', (event) => {
            this.currentSearch = event.target.value.trim().toLowerCase();
            this.applyFilters();
        });

        const sidebarTree = document.getElementById('scheduled-task-sidebar-tree');
        sidebarTree?.addEventListener('click', (event) => {
            const treeItem = event.target.closest('.tree-item[data-filter]');
            if (!treeItem) {
                return;
            }

            this.currentFilter = treeItem.dataset.filter || 'all';
            this.applyFilters();
        });

        viewRoot.querySelectorAll('.view-btn').forEach((button) => {
            button.addEventListener('click', () => {
                viewRoot.querySelectorAll('.view-btn').forEach((item) => {
                    item.classList.remove('active');
                });
                button.classList.add('active');
                this.currentLayout = button.dataset.layout || 'grid';
                this.renderTasks();
            });
        });

        document.getElementById('scheduled-task-refresh-btn')?.addEventListener('click', async () => {
            await this.refreshData();
            this.showNotification('定时任务数据已刷新', 'success');
        });

        document.getElementById('scheduled-task-runtime-refresh-btn')?.addEventListener('click', async () => {
            await this.loadRuntimeStatus();
            this.showNotification('运行状态已刷新', 'success');
        });

        document.getElementById('scheduled-task-history-refresh-btn')?.addEventListener('click', async () => {
            if (!this.selectedTaskId) {
                this.showNotification('请先选择一个任务', 'warning');
                return;
            }
            await this.loadTaskRecords(this.selectedTaskId);
            this.showNotification('执行记录已刷新', 'success');
        });

        document.getElementById('scheduled-task-create-btn')?.addEventListener('click', () => {
            this.resetForm({ keepSelection: false, silent: false });
        });

        document.getElementById('scheduled-task-reset-btn')?.addEventListener('click', () => {
            this.resetForm({ keepSelection: false, silent: false });
        });

        document.getElementById('scheduled-task-schedule-type')?.addEventListener('change', () => {
            this.updateScheduleFieldVisibility();
        });

        document.getElementById('scheduled-task-form')?.addEventListener('submit', async (event) => {
            event.preventDefault();
            await this.saveTask();
        });

        const taskGrid = document.getElementById('scheduled-task-grid');
        taskGrid?.addEventListener('click', async (event) => {
            const taskCard = event.target.closest('.scheduled-task-card');
            if (!taskCard) {
                return;
            }

            const taskId = taskCard.dataset.taskId || '';
            const task = this.tasks.find((item) => item.task_id === taskId);
            if (!task) {
                return;
            }

            const actionButton = event.target.closest('[data-action]');
            if (!actionButton) {
                await this.selectTask(taskId);
                return;
            }

            const action = actionButton.dataset.action;
            if (action === 'select') {
                await this.selectTask(taskId);
                return;
            }

            if (action === 'run-now') {
                this.runTaskNow(task);
                return;
            }

            if (action === 'toggle') {
                await this.toggleTask(task);
                return;
            }

            if (action === 'delete') {
                this.deleteTask(task);
            }
        });
    }

    getViewRoot() {
        return document.getElementById('scheduled-task-manager-view');
    }

    async refreshData(options = {}) {
        await Promise.all([
            this.loadTasks(options),
            this.loadRuntimeStatus(options)
        ]);

        if (this.selectedTaskId) {
            const selectedTask = this.tasks.find((task) => task.task_id === this.selectedTaskId);
            if (selectedTask) {
                this.fillTaskForm(selectedTask);
                await this.loadTaskRecords(this.selectedTaskId, options);
                return;
            }
        }

        this.renderHistoryEmpty('选择任务后查看执行记录。');
    }

    async loadTasks(options = {}) {
        try {
            const result = await this.fetchJson('/api/scheduled-tasks', {}, '加载任务列表失败');
            const taskList = this.extractCollection(result, 'tasks');

            this.tasks = taskList
                .map((task, index) => this.normalizeTask(task, index))
                .sort((left, right) => this.sortTasks(left, right));

            this.applyFilters();
            this.updateSidebarStats();
        } catch (error) {
            this.tasks = [];
            this.applyFilters();
            this.updateSidebarStats();
            this.handleApiError(error, options);
        }
    }

    async loadRuntimeStatus(options = {}) {
        try {
            const result = await this.fetchJson(
                '/api/scheduled-tasks/runtime/status',
                {},
                '加载运行状态失败'
            );

            this.runtimeStatus = this.normalizeRuntimeStatus(result);
            this.renderRuntimeStatus();
            this.renderSidebarTree();
            this.updateSidebarStats();
        } catch (error) {
            this.runtimeStatus = this.createFallbackRuntimeStatus(error.message);
            this.renderRuntimeStatus();
            this.renderSidebarTree();
            this.updateSidebarStats();
            this.handleApiError(error, options);
        }

        this._syncAutoRefresh();
    }

    startAutoRefresh() {
        if (this._autoRefreshTimer) {
            return;
        }
        this._autoRefreshTimer = setInterval(async () => {
            try {
                await this.refreshData({ silent: true });
            } catch (error) {
                // 静默刷新失败不影响后续轮询
            }
            this._syncAutoRefresh();
        }, 4000);
    }

    stopAutoRefresh() {
        if (this._autoRefreshTimer) {
            clearInterval(this._autoRefreshTimer);
            this._autoRefreshTimer = null;
        }
    }

    _syncAutoRefresh() {
        const running = !!(this.runtimeStatus && this.runtimeStatus.is_running);
        if (running) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    async loadTaskRecords(taskId, options = {}) {
        if (!taskId) {
            this.historyRecords = [];
            this.renderHistoryEmpty('选择任务后查看执行记录。');
            return;
        }

        try {
            const result = await this.fetchJson(
                `/api/scheduled-tasks/${encodeURIComponent(taskId)}/records`,
                {},
                '加载执行记录失败'
            );
            const records = this.extractCollection(result, 'records');

            this.historyRecords = records.map((record, index) => this.normalizeRecord(record, index));
            this.renderHistory();
        } catch (error) {
            this.historyRecords = [];
            this.renderHistoryEmpty(`执行记录加载失败：${this.escapeHtml(error.message)}`);
            this.handleApiError(error, options);
        }
    }

    async saveTask() {
        const saveButton = document.getElementById('scheduled-task-save-btn');
        const taskId = document.getElementById('scheduled-task-id')?.value?.trim() || '';

        try {
            const payload = this.buildTaskPayload();

            if (saveButton) {
                saveButton.disabled = true;
                saveButton.textContent = taskId ? '保存中...' : '创建中...';
            }

            const result = await this.fetchJson(
                taskId ? `/api/scheduled-tasks/${encodeURIComponent(taskId)}` : '/api/scheduled-tasks',
                {
                    method: taskId ? 'PUT' : 'POST',
                    body: JSON.stringify(payload)
                },
                taskId ? '更新任务失败' : '创建任务失败'
            );

            const savedTask = this.extractSingleTask(result, taskId, payload);
            await this.refreshData({ silent: true });

            if (savedTask?.task_id) {
                await this.selectTask(savedTask.task_id, { silent: true });
            } else if (taskId) {
                await this.selectTask(taskId, { silent: true });
            }

            this.showNotification(taskId ? '定时任务已更新' : '定时任务已创建', 'success');
        } catch (error) {
            this.showNotification(error.message, 'error');
        } finally {
            if (saveButton) {
                saveButton.disabled = false;
                saveButton.textContent = '保存任务';
            }
        }
    }

    async selectTask(taskId, options = {}) {
        const task = this.tasks.find((item) => item.task_id === taskId);
        if (!task) {
            return;
        }

        this.selectedTaskId = taskId;
        this.fillTaskForm(task);
        this.renderTasks();

        await this.loadTaskRecords(taskId, options);
    }

    async toggleTask(task) {
        const nextEnabled = !task.enabled;

        try {
            await this.fetchJson(
                `/api/scheduled-tasks/${encodeURIComponent(task.task_id)}/toggle`,
                {
                    method: 'POST',
                    body: JSON.stringify({ enabled: nextEnabled })
                },
                nextEnabled ? '启用任务失败' : '停用任务失败'
            );

            await this.refreshData({ silent: true });
            if (this.selectedTaskId === task.task_id) {
                await this.selectTask(task.task_id, { silent: true });
            }

            this.showNotification(
                `任务已${nextEnabled ? '启用' : '停用'}`,
                'success'
            );
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    runTaskNow(task) {
        const taskName = task.name || task.task_id;
        window.dialogManager?.showConfirm(
            `确认立即执行任务“${taskName}”吗？该操作会复用现有生成链路，并遵守单任务串行限制。`,
            async () => {
                try {
                    await this.fetchJson(
                        `/api/scheduled-tasks/${encodeURIComponent(task.task_id)}/run-now`,
                        { method: 'POST' },
                        '立即执行失败'
                    );

                    await this.refreshData({ silent: true });
                    await this.loadTaskRecords(task.task_id, { silent: true });
                    this.showNotification(`任务“${taskName}”已开始执行`, 'success');
                } catch (error) {
                    this.showNotification(error.message, 'error');
                }
            }
        );
    }

    deleteTask(task) {
        const taskName = task.name || task.task_id;
        window.dialogManager?.showConfirm(
            `确认删除任务“${taskName}”吗？删除后将无法恢复该任务配置。`,
            async () => {
                try {
                    await this.fetchJson(
                        `/api/scheduled-tasks/${encodeURIComponent(task.task_id)}`,
                        { method: 'DELETE' },
                        '删除任务失败'
                    );

                    if (this.selectedTaskId === task.task_id) {
                        this.resetForm({ keepSelection: false, silent: true });
                    }

                    await this.refreshData({ silent: true });
                    this.showNotification('任务已删除', 'success');
                } catch (error) {
                    this.showNotification(error.message, 'error');
                }
            }
        );
    }

    buildTaskPayload() {
        const taskName = document.getElementById('scheduled-task-name')?.value?.trim() || '';
        const topic = document.getElementById('scheduled-task-topic')?.value?.trim() || '';
        const scheduleType = document.getElementById('scheduled-task-schedule-type')?.value || 'fixed_time';
        const timeOfDay = document.getElementById('scheduled-task-time-of-day')?.value || '';
        const cronExpression = document.getElementById('scheduled-task-cron-expression')?.value?.trim() || '';
        const maxRetries = Number.parseInt(
            document.getElementById('scheduled-task-max-retries')?.value || '3',
            10
        );

        if (!taskName) {
            throw new Error('任务名称不能为空');
        }

        if (!topic) {
            throw new Error('任务话题不能为空；该字段与创意工坊 topic-input 语义一致，且不支持空话题自动热搜');
        }

        if (scheduleType === 'fixed_time' && !timeOfDay) {
            throw new Error('请选择固定时间任务的触发时间');
        }

        if (scheduleType === 'cron' && !cronExpression) {
            throw new Error('请输入 Cron 表达式');
        }

        if (Number.isNaN(maxRetries) || maxRetries < 0) {
            throw new Error('最大重试次数必须是大于等于 0 的整数');
        }

        return {
            name: taskName,
            topic,
            schedule_type: scheduleType,
            time_of_day: scheduleType === 'fixed_time' ? timeOfDay : null,
            cron_expression: scheduleType === 'cron' ? cronExpression : null,
            enabled: Boolean(document.getElementById('scheduled-task-enabled')?.checked),
            auto_publish: Boolean(document.getElementById('scheduled-task-auto-publish')?.checked),
            max_retries: maxRetries
        };
    }

    updateScheduleFieldVisibility() {
        const scheduleType = document.getElementById('scheduled-task-schedule-type')?.value || 'fixed_time';
        const fixedField = document.querySelector('[data-schedule-mode="fixed_time"]');
        const cronField = document.querySelector('[data-schedule-mode="cron"]');
        const timeInput = document.getElementById('scheduled-task-time-of-day');
        const cronInput = document.getElementById('scheduled-task-cron-expression');

        if (fixedField) {
            fixedField.style.display = scheduleType === 'fixed_time' ? 'block' : 'none';
        }
        if (cronField) {
            cronField.style.display = scheduleType === 'cron' ? 'block' : 'none';
        }
        if (timeInput) {
            timeInput.required = scheduleType === 'fixed_time';
        }
        if (cronInput) {
            cronInput.required = scheduleType === 'cron';
        }
    }

    fillTaskForm(task) {
        document.getElementById('scheduled-task-id').value = task.task_id;
        document.getElementById('scheduled-task-name').value = task.name;
        document.getElementById('scheduled-task-topic').value = task.topic;
        document.getElementById('scheduled-task-schedule-type').value = task.schedule_type;
        document.getElementById('scheduled-task-time-of-day').value = task.time_of_day || '09:00';
        document.getElementById('scheduled-task-cron-expression').value = task.cron_expression || '';
        document.getElementById('scheduled-task-max-retries').value = String(task.max_retries);
        document.getElementById('scheduled-task-enabled').checked = task.enabled;
        document.getElementById('scheduled-task-auto-publish').checked = task.auto_publish;

        const formTitle = document.getElementById('scheduled-task-form-title');
        if (formTitle) {
            formTitle.textContent = '编辑任务';
        }

        const selectedBadge = document.getElementById('scheduled-task-selected-badge');
        if (selectedBadge) {
            selectedBadge.textContent = task.name || task.task_id;
        }

        this.updateScheduleFieldVisibility();
    }

    resetForm(options = {}) {
        const { keepSelection = false, silent = false } = options;
        const form = document.getElementById('scheduled-task-form');
        form?.reset();

        document.getElementById('scheduled-task-id').value = '';
        document.getElementById('scheduled-task-time-of-day').value = '09:00';
        document.getElementById('scheduled-task-max-retries').value = '3';
        document.getElementById('scheduled-task-enabled').checked = true;
        document.getElementById('scheduled-task-auto-publish').checked = true;
        document.getElementById('scheduled-task-schedule-type').value = 'fixed_time';
        document.getElementById('scheduled-task-cron-expression').value = '';

        const formTitle = document.getElementById('scheduled-task-form-title');
        if (formTitle) {
            formTitle.textContent = '新建任务';
        }

        const selectedBadge = document.getElementById('scheduled-task-selected-badge');
        if (selectedBadge) {
            selectedBadge.textContent = '未选择任务';
        }

        if (!keepSelection) {
            this.selectedTaskId = '';
            this.historyRecords = [];
            this.renderTasks();
            this.renderHistoryEmpty('选择任务后查看执行记录。');
        }

        this.updateScheduleFieldVisibility();

        if (!silent) {
            this.showNotification('已切换到新建任务表单', 'info');
        }
    }

    applyFilters() {
        this.filteredTasks = this.tasks.filter((task) => {
            const matchesFilter = this.matchesCurrentFilter(task);
            const matchesSearch = !this.currentSearch
                || [task.name, task.topic, task.task_id]
                    .filter(Boolean)
                    .some((value) => value.toLowerCase().includes(this.currentSearch));

            return matchesFilter && matchesSearch;
        });

        this.renderSidebarTree();
        this.renderTasks();
        this.updateSidebarStats();
    }

    matchesCurrentFilter(task) {
        const effectiveStatus = this.getEffectiveStatus(task);

        if (this.currentFilter === 'enabled') {
            return task.enabled;
        }
        if (this.currentFilter === 'disabled') {
            return !task.enabled;
        }
        if (this.currentFilter === 'running') {
            return effectiveStatus === 'running';
        }
        if (this.currentFilter === 'failed') {
            return ['failed', 'retrying', 'skipped'].includes(effectiveStatus);
        }
        return true;
    }

    renderSidebarTree() {
        const tree = document.getElementById('scheduled-task-sidebar-tree');
        if (!tree) {
            return;
        }

        const counts = {
            all: this.tasks.length,
            enabled: this.tasks.filter((task) => task.enabled).length,
            disabled: this.tasks.filter((task) => !task.enabled).length,
            running: this.tasks.filter((task) => this.getEffectiveStatus(task) === 'running').length,
            failed: this.tasks.filter((task) => ['failed', 'retrying', 'skipped'].includes(this.getEffectiveStatus(task))).length
        };

        const filters = [
            {
                key: 'all',
                label: '全部任务',
                icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M7 8h10" /><path d="M7 12h10" /><path d="M7 16h6" /></svg>'
            },
            {
                key: 'enabled',
                label: '已启用',
                icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"><path d="M20 6 9 17l-5-5" /></svg>'
            },
            {
                key: 'disabled',
                label: '已停用',
                icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"><path d="M18 6 6 18" /><path d="M6 6l12 12" /></svg>'
            },
            {
                key: 'running',
                label: '执行中',
                icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>'
            },
            {
                key: 'failed',
                label: '异常任务',
                icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><path d="M12 9v4" /><path d="M12 17h.01" /></svg>'
            }
        ];

        tree.innerHTML = filters.map((filter) => `
            <div class="tree-item ${this.currentFilter === filter.key ? 'active' : ''}" data-filter="${filter.key}">
                <div>
                    <span class="tree-icon">${filter.icon}</span>
                    <span class="tree-name">${filter.label}</span>
                </div>
                <span class="item-count">${counts[filter.key] || 0}</span>
            </div>
        `).join('');
    }

    renderRuntimeStatus() {
        const runtimeGrid = document.getElementById('scheduled-task-runtime-grid');
        if (!runtimeGrid) {
            return;
        }

        const schedulerMeta = this.getStatusMeta(this.runtimeStatus.scheduler_status);
        const currentTaskLabel = this.runtimeStatus.current_task_name || '当前无执行任务';
        const nextRunText = this.runtimeStatus.next_run_at
            ? this.formatDateTime(this.runtimeStatus.next_run_at)
            : '暂无下次触发时间';
        const pendingTasks = this.toNumber(this.runtimeStatus.pending_tasks, 0);
        const updatedAt = this.runtimeStatus.updated_at
            ? this.formatDateTime(this.runtimeStatus.updated_at)
            : this.formatDateTime(new Date().toISOString());

        runtimeGrid.innerHTML = `
            ${this.createRuntimeCard('调度器状态', schedulerMeta.label, schedulerMeta.className, this.runtimeStatus.last_message || '根据运行时接口返回结果更新')}
            ${this.createRuntimeCard('当前执行任务', currentTaskLabel, this.runtimeStatus.is_running ? 'info' : 'neutral', this.runtimeStatus.current_task_id || '暂无任务在运行')}
            ${this.createRuntimeCard('等待中任务', String(pendingTasks), pendingTasks > 0 ? 'warning' : 'neutral', `下次触发：${nextRunText}`)}
            ${this.createRuntimeCard('最近刷新时间', updatedAt, 'neutral', this.runtimeStatus.next_task_name ? `下一任务：${this.runtimeStatus.next_task_name}` : '点击右上角按钮手动刷新')}
        `;
    }

    createRuntimeCard(title, value, statusClass, description) {
        return `
            <article class="scheduled-task-runtime-card ${statusClass}">
                <span class="scheduled-task-runtime-title">${this.escapeHtml(title)}</span>
                <strong class="scheduled-task-runtime-value">${this.escapeHtml(value)}</strong>
                <p class="scheduled-task-runtime-desc">${this.escapeHtml(description || '-')}</p>
            </article>
        `;
    }

    renderTasks() {
        const grid = document.getElementById('scheduled-task-grid');
        const caption = document.getElementById('scheduled-task-list-caption');
        if (!grid) {
            return;
        }

        grid.className = `scheduled-task-grid content-grid ${this.currentLayout === 'list' ? 'list-view' : ''}`;

        if (caption) {
            caption.textContent = `当前展示 ${this.filteredTasks.length} / ${this.tasks.length} 个任务。`;
        }

        if (this.filteredTasks.length === 0) {
            grid.innerHTML = `
                <div class="empty-state scheduled-task-empty-state">
                    <svg viewBox="0 0 24 24" width="56" height="56" fill="none" stroke="currentColor">
                        <rect x="3" y="4" width="18" height="16" rx="2" />
                        <path d="M7 8h10" />
                        <path d="M7 12h10" />
                        <path d="M7 16h6" />
                    </svg>
                    <h3>${this.tasks.length === 0 ? '暂无定时任务' : '没有匹配的任务'}</h3>
                    <p>${this.tasks.length === 0 ? '点击右上角“新建任务”开始配置定时生成计划。' : '请调整筛选条件或搜索关键词。'}</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.filteredTasks.map((task) => this.createTaskCard(task)).join('');
    }

    createTaskCard(task) {
        const status = this.getStatusMeta(this.getEffectiveStatus(task));
        const enabledBadge = task.enabled
            ? '<span class="scheduled-task-chip success">已启用</span>'
            : '<span class="scheduled-task-chip neutral">已停用</span>';
        const publishBadge = task.auto_publish
            ? '<span class="scheduled-task-chip info">自动发布</span>'
            : '<span class="scheduled-task-chip neutral">仅生成</span>';
        const errorBlock = task.last_error
            ? `<p class="scheduled-task-error-text">${this.escapeHtml(this.truncateText(task.last_error, 120))}</p>`
            : '';

        return `
            <article class="content-card scheduled-task-card ${this.selectedTaskId === task.task_id ? 'selected' : ''}" data-task-id="${this.escapeHtml(task.task_id)}">
                <div class="scheduled-task-card-body">
                    <div class="scheduled-task-card-header">
                        <div class="scheduled-task-card-title-group">
                            <h4 class="card-title" title="${this.escapeHtml(task.name)}">${this.escapeHtml(task.name)}</h4>
                            <span class="scheduled-task-status-badge ${status.className}">${this.escapeHtml(status.label)}</span>
                        </div>
                        <span class="scheduled-task-task-id">${this.escapeHtml(task.task_id)}</span>
                    </div>

                    <p class="scheduled-task-topic-text" title="${this.escapeHtml(task.topic)}">${this.escapeHtml(this.truncateText(task.topic, 120))}</p>

                    <div class="scheduled-task-chip-row">
                        ${enabledBadge}
                        ${publishBadge}
                        <span class="scheduled-task-chip neutral">${this.escapeHtml(this.getScheduleLabel(task))}</span>
                    </div>

                    <dl class="scheduled-task-meta-grid">
                        <div>
                            <dt>下次触发</dt>
                            <dd>${this.escapeHtml(this.formatDateTime(task.next_run_at) || '待计算')}</dd>
                        </div>
                        <div>
                            <dt>最近执行</dt>
                            <dd>${this.escapeHtml(this.formatDateTime(task.last_run_at) || '暂无记录')}</dd>
                        </div>
                        <div>
                            <dt>重试配置</dt>
                            <dd>${this.escapeHtml(`${task.current_retry_count}/${task.max_retries}`)}</dd>
                        </div>
                        <div>
                            <dt>更新时间</dt>
                            <dd>${this.escapeHtml(this.formatDateTime(task.updated_at) || '-')}</dd>
                        </div>
                    </dl>

                    ${errorBlock}
                </div>

                <div class="scheduled-task-card-actions">
                    <button type="button" class="scheduled-task-action-btn" data-action="select">编辑</button>
                    <button type="button" class="scheduled-task-action-btn" data-action="run-now">立即执行</button>
                    <button type="button" class="scheduled-task-action-btn" data-action="toggle">${task.enabled ? '停用' : '启用'}</button>
                    <button type="button" class="scheduled-task-action-btn danger" data-action="delete">删除</button>
                </div>
            </article>
        `;
    }

    renderHistory() {
        const historyContainer = document.getElementById('scheduled-task-history');
        const caption = document.getElementById('scheduled-task-history-caption');
        if (!historyContainer) {
            return;
        }

        if (caption) {
            caption.textContent = this.selectedTaskId
                ? `当前显示任务 ${this.selectedTaskId} 的执行记录。`
                : '选择任务后查看运行历史、失败信息与产出记录。';
        }

        if (!this.selectedTaskId) {
            this.renderHistoryEmpty('选择任务后查看执行记录。');
            return;
        }

        if (this.historyRecords.length === 0) {
            this.renderHistoryEmpty('该任务暂无执行记录。');
            return;
        }

        historyContainer.innerHTML = this.historyRecords.map((record) => {
            const status = this.getStatusMeta(record.status);
            const articlePath = record.article_path || '暂无产出路径';
            const detailMessage = record.message || '暂无额外说明';

            return `
                <article class="scheduled-task-history-item">
                    <div class="scheduled-task-history-header">
                        <span class="scheduled-task-status-badge ${status.className}">${this.escapeHtml(status.label)}</span>
                        <span class="scheduled-task-history-time">开始：${this.escapeHtml(this.formatDateTime(record.started_at) || '-')}</span>
                        <span class="scheduled-task-history-time">结束：${this.escapeHtml(this.formatDateTime(record.finished_at) || '进行中')}</span>
                    </div>
                    <div class="scheduled-task-history-body">
                        <p><strong>重试次数：</strong>${this.escapeHtml(String(record.retry_attempt))}</p>
                        <p><strong>发布结果：</strong>${record.published ? '已发布' : '未发布'}</p>
                        <p><strong>产出路径：</strong><span title="${this.escapeHtml(articlePath)}">${this.escapeHtml(this.truncateText(articlePath, 100))}</span></p>
                        <p><strong>执行说明：</strong>${this.escapeHtml(detailMessage)}</p>
                    </div>
                </article>
            `;
        }).join('');
    }

    renderHistoryEmpty(message) {
        const historyContainer = document.getElementById('scheduled-task-history');
        if (!historyContainer) {
            return;
        }

        historyContainer.innerHTML = `
            <div class="scheduled-task-history-empty">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor">
                    <path d="M12 8v4l3 3" />
                    <circle cx="12" cy="12" r="9" />
                </svg>
                <p>${message}</p>
            </div>
        `;
    }

    updateSidebarStats() {
        const runtimeLabel = document.getElementById('scheduled-task-sidebar-runtime');
        const enabledCount = document.getElementById('scheduled-task-sidebar-enabled-count');
        const totalCount = document.getElementById('scheduled-task-sidebar-total-count');

        if (runtimeLabel) {
            runtimeLabel.textContent = this.getStatusMeta(this.runtimeStatus.scheduler_status).label;
        }
        if (enabledCount) {
            enabledCount.textContent = String(this.tasks.filter((task) => task.enabled).length);
        }
        if (totalCount) {
            totalCount.textContent = String(this.tasks.length);
        }
    }

    normalizeTask(task, index) {
        const taskId = String(task.task_id ?? task.id ?? task.taskId ?? `task_${index + 1}`);

        return {
            task_id: taskId,
            name: String(task.name ?? task.title ?? taskId),
            topic: String(task.topic ?? ''),
            schedule_type: String(task.schedule_type ?? task.scheduleType ?? 'fixed_time'),
            time_of_day: task.time_of_day ?? task.timeOfDay ?? '',
            cron_expression: task.cron_expression ?? task.cronExpression ?? '',
            enabled: this.toBoolean(task.enabled, true),
            auto_publish: this.toBoolean(task.auto_publish ?? task.autoPublish, true),
            max_retries: this.toNumber(task.max_retries ?? task.maxRetries, 3),
            current_retry_count: this.toNumber(task.current_retry_count ?? task.currentRetryCount, 0),
            last_run_at: task.last_run_at ?? task.lastRunAt ?? '',
            next_run_at: task.next_run_at ?? task.nextRunAt ?? '',
            last_status: String(task.last_status ?? task.lastStatus ?? 'idle'),
            last_error: String(task.last_error ?? task.lastError ?? ''),
            created_at: task.created_at ?? task.createdAt ?? '',
            updated_at: task.updated_at ?? task.updatedAt ?? ''
        };
    }

    normalizeRuntimeStatus(result) {
        const source = result?.data ?? result ?? {};
        const currentTask = source.current_task ?? source.running_task ?? source.active_task ?? null;

        return {
            scheduler_status: String(
                source.scheduler_status
                ?? source.status
                ?? (source.is_running || source.running ? 'running' : 'idle')
            ),
            is_running: this.toBoolean(source.is_running ?? source.running ?? Boolean(currentTask), false),
            current_task_id: String(source.current_task_id ?? currentTask?.task_id ?? currentTask?.id ?? ''),
            current_task_name: String(source.current_task_name ?? currentTask?.name ?? ''),
            next_task_name: String(source.next_task_name ?? source.next_task ?? ''),
            next_run_at: source.next_run_at ?? source.nextRunAt ?? '',
            pending_tasks: this.toNumber(source.pending_tasks ?? source.queue_size ?? source.pending_count, 0),
            last_message: String(source.message ?? source.last_message ?? ''),
            updated_at: source.updated_at ?? source.updatedAt ?? new Date().toISOString()
        };
    }

    normalizeRecord(record, index) {
        return {
            record_id: String(record.record_id ?? record.id ?? `record_${index + 1}`),
            task_id: String(record.task_id ?? record.taskId ?? this.selectedTaskId ?? ''),
            started_at: record.started_at ?? record.startedAt ?? '',
            finished_at: record.finished_at ?? record.finishedAt ?? '',
            status: String(record.status ?? 'idle'),
            retry_attempt: this.toNumber(record.retry_attempt ?? record.retryAttempt, 0),
            message: String(record.message ?? record.detail ?? ''),
            article_path: String(record.article_path ?? record.articlePath ?? ''),
            published: this.toBoolean(record.published, false)
        };
    }

    extractCollection(result, key) {
        if (Array.isArray(result)) {
            return result;
        }
        if (Array.isArray(result?.data)) {
            return result.data;
        }
        if (Array.isArray(result?.[key])) {
            return result[key];
        }
        if (Array.isArray(result?.data?.[key])) {
            return result.data[key];
        }
        return [];
    }

    extractSingleTask(result, fallbackTaskId, fallbackPayload) {
        const taskSource = result?.data?.task
            ?? result?.task
            ?? result?.data
            ?? result;

        if (!taskSource || Array.isArray(taskSource)) {
            return fallbackTaskId
                ? this.normalizeTask({ task_id: fallbackTaskId, ...fallbackPayload }, 0)
                : null;
        }

        return this.normalizeTask(
            {
                task_id: taskSource.task_id ?? taskSource.id ?? fallbackTaskId,
                ...taskSource,
                ...fallbackPayload
            },
            0
        );
    }

    sortTasks(left, right) {
        const leftRunning = this.getEffectiveStatus(left) === 'running' ? 1 : 0;
        const rightRunning = this.getEffectiveStatus(right) === 'running' ? 1 : 0;
        if (leftRunning !== rightRunning) {
            return rightRunning - leftRunning;
        }

        const leftEnabled = left.enabled ? 1 : 0;
        const rightEnabled = right.enabled ? 1 : 0;
        if (leftEnabled !== rightEnabled) {
            return rightEnabled - leftEnabled;
        }

        const leftNextRun = left.next_run_at ? new Date(left.next_run_at).getTime() : Number.MAX_SAFE_INTEGER;
        const rightNextRun = right.next_run_at ? new Date(right.next_run_at).getTime() : Number.MAX_SAFE_INTEGER;
        if (leftNextRun !== rightNextRun) {
            return leftNextRun - rightNextRun;
        }

        return left.name.localeCompare(right.name, 'zh-CN');
    }

    getEffectiveStatus(task) {
        if (!task.enabled) {
            return 'disabled';
        }
        if (this.isTaskRunning(task)) {
            return 'running';
        }
        return String(task.last_status || 'idle').toLowerCase();
    }

    isTaskRunning(task) {
        if (this.runtimeStatus.current_task_id && task.task_id === this.runtimeStatus.current_task_id) {
            return true;
        }
        if (this.runtimeStatus.is_running && this.runtimeStatus.current_task_name && task.name === this.runtimeStatus.current_task_name) {
            return true;
        }
        return String(task.last_status || '').toLowerCase() === 'running';
    }

    getScheduleLabel(task) {
        if (task.schedule_type === 'cron') {
            return task.cron_expression ? `Cron: ${task.cron_expression}` : 'Cron 任务';
        }
        return task.time_of_day ? `每日 ${task.time_of_day}` : '固定时间';
    }

    getStatusMeta(status) {
        const statusKey = String(status || 'idle').toLowerCase();
        const statusMap = {
            idle: { label: '空闲', className: 'neutral' },
            running: { label: '执行中', className: 'info' },
            success: { label: '成功', className: 'success' },
            completed: { label: '成功', className: 'success' },
            failed: { label: '失败', className: 'error' },
            retrying: { label: '重试中', className: 'warning' },
            skipped: { label: '已跳过', className: 'warning' },
            stopped: { label: '已停止', className: 'warning' },
            disabled: { label: '已停用', className: 'neutral' },
            scheduler_running: { label: '运行中', className: 'success' },
            scheduler_stopped: { label: '已停止', className: 'neutral' },
            scheduler_error: { label: '异常', className: 'error' },
            paused: { label: '已暂停', className: 'warning' },
            ready: { label: '就绪', className: 'success' },
            unknown: { label: '未知', className: 'neutral' }
        };

        if (statusMap[statusKey]) {
            return statusMap[statusKey];
        }

        if (statusKey.includes('fail') || statusKey.includes('error')) {
            return { label: '失败', className: 'error' };
        }
        if (statusKey.includes('run')) {
            return { label: '运行中', className: 'success' };
        }
        if (statusKey.includes('stop')) {
            return { label: '已停止', className: 'neutral' };
        }
        return { label: status || '未知', className: 'neutral' };
    }

    createFallbackRuntimeStatus(message = '') {
        return {
            scheduler_status: message ? 'unknown' : 'idle',
            is_running: false,
            current_task_id: '',
            current_task_name: '',
            next_task_name: '',
            next_run_at: '',
            pending_tasks: 0,
            last_message: message,
            updated_at: new Date().toISOString()
        };
    }

    async fetchJson(url, options = {}, fallbackMessage = '请求失败') {
        const requestOptions = {
            ...options,
            headers: {
                ...(options.headers || {})
            }
        };

        if (requestOptions.body && !(requestOptions.body instanceof FormData)) {
            requestOptions.headers['Content-Type'] = requestOptions.headers['Content-Type'] || 'application/json';
        }

        const response = await fetch(url, requestOptions);
        let result = null;

        try {
            result = await response.json();
        } catch (error) {
            result = null;
        }

        if (!response.ok) {
            const errorMessage = result?.detail || result?.message || result?.error || fallbackMessage;
            throw new Error(errorMessage);
        }

        return result;
    }

    handleApiError(error, options = {}) {
        if (options.silent || this.apiWarningShown) {
            return;
        }

        this.apiWarningShown = true;
        this.showNotification(`定时任务接口暂不可用：${error.message}`, 'warning');
    }

    toBoolean(value, fallback = false) {
        if (typeof value === 'boolean') {
            return value;
        }
        if (typeof value === 'string') {
            return ['true', '1', 'yes', 'on'].includes(value.toLowerCase());
        }
        if (typeof value === 'number') {
            return value > 0;
        }
        return fallback;
    }

    toNumber(value, fallback = 0) {
        const parsed = Number.parseInt(value, 10);
        return Number.isNaN(parsed) ? fallback : parsed;
    }

    formatDateTime(value) {
        if (!value) {
            return '';
        }

        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    truncateText(text, maxLength = 80) {
        if (!text || text.length <= maxLength) {
            return text || '';
        }
        return `${text.slice(0, maxLength)}...`;
    }

    escapeHtml(text) {
        const value = String(text ?? '');
        return value
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    showNotification(message, type = 'info') {
        if (window.app?.showNotification) {
            window.app.showNotification(message, type);
            return;
        }

        window.dialogManager?.showAlert(message, type === 'error' ? 'error' : 'info');
    }
}

window.ScheduledTaskManager = ScheduledTaskManager;
