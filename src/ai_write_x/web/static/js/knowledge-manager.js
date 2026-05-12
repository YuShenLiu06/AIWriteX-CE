/**
 * 知识库管理器
 * 支持图片知识库和文本知识库的双面板管理
 */

class KnowledgeManager {
    constructor() {
        this.currentKnowledgeType = 'image'; // 'image' | 'text'
        this.currentCategory = 'all';
        this.currentView = 'grid';
        this.images = [];
        this.textItems = [];
        this.categories = [];
        this.currentEditItem = null;
        this.initialized = false;
        this.init();
    }

    async init() {
        if (this.initialized) {
            // 重复初始化时刷新数据
            await Promise.all([
                this.loadImages(),
                this.loadTextKnowledge()
            ]);
            this.loadCategories();
            return;
        }

        // 首次初始化：并行加载所有数据
        await Promise.all([
            this.loadKnowledgeConfig(),
            this.loadCategories(),
            this.loadImages(),
            this.loadTextKnowledge()
        ]);

        this.bindEvents();
        this.initialized = true;
    }

    // ========== 知识库开关配置 ==========
    async loadKnowledgeConfig() {
        try {
            const response = await fetch('/api/config/');
            if (response.ok) {
                const result = await response.json();
                const knowledgeConfig = result.data?.knowledge || {};
                const textEnabled = knowledgeConfig.text_enabled !== false;
                const imageEnabled = knowledgeConfig.image_enabled !== false;

                document.getElementById('km-toggle-text').checked = textEnabled;
                document.getElementById('km-toggle-image').checked = imageEnabled;
            }
        } catch (e) {
            console.error('加载知识库配置失败:', e);
        }
    }

    async toggleKnowledge(type, enabled) {
        try {
            const updateData = {
                knowledge: {
                    [`${type}_enabled`]: enabled
                }
            };
            const response = await fetch('/api/config/', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config_data: updateData })
            });

            if (response.ok) {
                window.app?.showNotification(
                    `${type === 'text' ? '文本' : '图片'}知识库已${enabled ? '启用' : '禁用'}`,
                    'success'
                );
            }
        } catch (e) {
            console.error('更新知识库配置失败:', e);
            window.app?.showNotification('更新配置失败', 'error');
        }
    }

    bindEvents() {
        // 知识库类型切换Tab
        document.querySelectorAll('.km-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.km-tab-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.switchKnowledgeType(e.target.dataset.type);
            });
        });

        // 视图切换
        document.querySelectorAll('#knowledge-manager-view .view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchView(e.target.closest('.view-btn').dataset.layout));
        });

        // 搜索
        const searchInput = document.getElementById('km-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.searchItems(e.target.value));
        }

        // 新增按钮
        const addBtn = document.getElementById('km-add-item-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showAddModal());
        }

        // 知识库开关
        const textToggle = document.getElementById('km-toggle-text');
        if (textToggle) {
            textToggle.addEventListener('change', (e) => this.toggleKnowledge('text', e.target.checked));
        }
        const imageToggle = document.getElementById('km-toggle-image');
        if (imageToggle) {
            imageToggle.addEventListener('change', (e) => this.toggleKnowledge('image', e.target.checked));
        }

        // 新建分类按钮
        const addCategoryBtn = document.getElementById('add-category-btn');
        if (addCategoryBtn) {
            addCategoryBtn.addEventListener('click', () => this.showAddCategoryModal());
        }

        // 分类切换
        document.querySelectorAll('#category-tree .tree-item').forEach(item => {
            item.addEventListener('click', (e) => this.switchCategory(item.dataset.category));
        });

        // 文本Modal事件
        document.getElementById('km-close-text')?.addEventListener('click', () => this.hideTextModal());
        document.getElementById('km-cancel-text')?.addEventListener('click', () => this.hideTextModal());
        document.getElementById('km-confirm-text')?.addEventListener('click', () => this.saveTextItem());

        // 文本预览Modal事件
        document.getElementById('km-close-text-preview')?.addEventListener('click', () => this.hideTextPreviewModal());
        document.getElementById('km-edit-text-from-preview')?.addEventListener('click', () => this.editTextFromPreview());
        document.getElementById('km-delete-text')?.addEventListener('click', () => this.deleteTextFromPreview());

        // 图片上传Modal事件
        document.getElementById('km-close-upload')?.addEventListener('click', () => this.hideUploadModal());
        document.getElementById('km-cancel-upload')?.addEventListener('click', () => this.hideUploadModal());
        document.getElementById('km-confirm-upload')?.addEventListener('click', () => this.uploadImage());

        // 文件上传区域交互
        this._initFileUploadArea();

        // 图片编辑Modal事件
        document.getElementById('km-close-edit')?.addEventListener('click', () => this.hideEditModal());
        document.getElementById('km-cancel-edit')?.addEventListener('click', () => this.hideEditModal());
        document.getElementById('km-confirm-edit')?.addEventListener('click', () => this.saveImageEdit());

        // 图片预览Modal事件
        document.getElementById('km-close-preview')?.addEventListener('click', () => this.hidePreviewModal());
        document.getElementById('km-use-image')?.addEventListener('click', () => this.useImageFromPreview());
        document.getElementById('km-edit-from-preview')?.addEventListener('click', () => this.editFromPreview());
        document.getElementById('km-delete-image')?.addEventListener('click', () => this.deleteImageFromPreview());

        // 点击Modal外部关闭
        ['km-text-modal', 'km-text-preview-modal', 'km-upload-modal', 'km-edit-modal', 'km-preview-modal'].forEach(id => {
            const modal = document.getElementById(id);
            if (modal) {
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        modal.style.display = 'none';
                    }
                });
            }
        });
    }

    // ========== 库类型切换 ==========

    async switchKnowledgeType(type) {
        this.currentKnowledgeType = type;
        const imagePanel = document.getElementById('km-image-panel');
        const textPanel = document.getElementById('km-text-panel');
        const addBtnText = document.getElementById('km-add-btn-text');
        const currentLibrary = document.getElementById('km-current-library');
        const searchInput = document.getElementById('km-search-input');

        if (type === 'image') {
            if (imagePanel) imagePanel.style.display = 'block';
            if (textPanel) textPanel.style.display = 'none';
            if (addBtnText) addBtnText.textContent = '上传图片';
            if (currentLibrary) currentLibrary.textContent = '图片知识库';
            if (searchInput) searchInput.placeholder = '搜索图片描述或标签...';
            this.updateStats();
            this.renderImages();
        } else {
            if (imagePanel) imagePanel.style.display = 'none';
            if (textPanel) textPanel.style.display = 'block';
            if (addBtnText) addBtnText.textContent = '新增文本';
            if (currentLibrary) currentLibrary.textContent = '文本知识库';
            if (searchInput) searchInput.placeholder = '搜索标题、内容或标签...';
            this.updateStats();
            // 切换到文本时确保数据已加载
            if (this.textItems.length === 0) {
                await this.loadTextKnowledge();
            }
            this.renderTextItems();
        }
    }

    // ========== 数据加载 ==========

    async loadCategories() {
        try {
            const response = await fetch('/api/text-knowledge/categories');
            if (response.ok) {
                const result = await response.json();
                this.categories = result.data || [];
                this.renderCategoryTree();
            }
        } catch (error) {
            console.error('加载分类失败:', error);
        }
    }

    renderCategoryTree() {
        const tree = document.getElementById('category-tree');
        if (!tree) return;

        // 保留"全部"和"未分类"，移除其他分类项
        const existingItems = tree.querySelectorAll('.tree-item[data-category]');
        existingItems.forEach(item => {
            if (item.dataset.category !== 'all' && item.dataset.category !== 'uncategorized') {
                item.remove();
            }
        });

        // 添加从数据库加载的分类
        this.categories.forEach(category => {
            const existing = tree.querySelector(`[data-category="${category}"]`);
            if (existing) return;

            const item = document.createElement('div');
            item.className = 'tree-item';
            item.dataset.category = category;
            item.innerHTML = `
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                <span>${category}</span>
            `;
            item.addEventListener('click', () => this.switchCategory(category));
            tree.appendChild(item);
        });
    }

    async loadData() {
        // 同时加载两种数据，不依赖 currentKnowledgeType
        await Promise.all([
            this.loadImages(),
            this.loadTextKnowledge()
        ]);
    }

    async loadImages() {
        try {
            const response = await fetch('/api/images');
            if (response.ok) {
                const result = await response.json();
                this.images = result.data || [];
                this.updateStats();
                this.renderImages();
            }
        } catch (error) {
            console.error('加载图片失败:', error);
            window.app?.showNotification('加载图片失败', 'error');
        }
    }

    async loadTextKnowledge() {
        try {
            const response = await fetch('/api/text-knowledge');
            if (response.ok) {
                const result = await response.json();
                this.textItems = result.data || [];
                this.updateStats();
                this.renderTextItems();
            }
        } catch (error) {
            console.error('加载文本知识失败:', error);
            window.app?.showNotification('加载文本知识失败', 'error');
        }
    }

    updateStats() {
        const totalEl = document.getElementById('km-total-items');
        if (totalEl) {
            const count = this.currentKnowledgeType === 'image' ? this.images.length : this.textItems.length;
            totalEl.textContent = count;
        }
    }

    // ========== 图片知识库渲染 ==========

    renderImages() {
        const grid = document.getElementById('km-image-grid');
        const emptyState = document.getElementById('km-empty-state');

        if (!grid) return;

        let filteredImages = this.images;

        // 按分类筛选
        if (this.currentCategory === 'uncategorized') {
            filteredImages = filteredImages.filter(img => !img.category);
        } else if (this.currentCategory !== 'all') {
            filteredImages = filteredImages.filter(img => img.category === this.currentCategory);
        }

        if (filteredImages.length === 0) {
            grid.innerHTML = '';
            if (emptyState) {
                emptyState.style.display = 'block';
                emptyState.querySelector('h3').textContent = '暂无图片';
                emptyState.querySelector('p').textContent = '点击"上传图片"添加第一张图片到知识库';
            }
            return;
        }

        if (emptyState) emptyState.style.display = 'none';

        grid.innerHTML = filteredImages.map(image => this.createImageCard(image)).join('');

        // 绑定卡片事件
        grid.querySelectorAll('.image-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const imageId = card.dataset.imageId;
                this.showPreviewModal(imageId);
            });
        });

        // 视图切换
        if (this.currentView === 'list') {
            grid.classList.add('list-view');
        } else {
            grid.classList.remove('list-view');
        }
    }

    createImageCard(image) {
        const tags = image.tags || [];
        const tagsHtml = tags.slice(0, 3).map(tag =>
            `<span class="meta-badge">${tag}</span>`
        ).join('');

        const fileSize = this.formatFileSize(image.file_size);

        return `
            <div class="content-card image-card" data-image-id="${image.id}">
                <div class="card-preview">
                    <img src="/api/images/${image.id}/file" alt="${image.description || image.original_filename}">
                </div>
                <div class="card-content">
                    <h4 class="card-title">${image.original_filename}</h4>
                    <div class="card-meta">
                        ${tagsHtml}
                        ${image.category ? `<span class="meta-badge" style="background: var(--secondary-color)">${image.category}</span>` : ''}
                    </div>
                    <div class="card-meta" style="margin-top: 4px;">
                        <span class="size-info">${fileSize}</span>
                        <span class="meta-divider">|</span>
                        <span class="time-info">使用 ${image.usage_count || 0} 次</span>
                    </div>
                </div>
            </div>
        `;
    }

    // ========== 文本知识库渲染 ==========

    renderTextItems() {
        const list = document.getElementById('km-text-list');
        const emptyState = document.getElementById('km-empty-state');

        if (!list) return;

        let filteredItems = this.textItems;

        // 按分类筛选
        if (this.currentCategory === 'uncategorized') {
            filteredItems = filteredItems.filter(item => !item.category);
        } else if (this.currentCategory !== 'all') {
            filteredItems = filteredItems.filter(item => item.category === this.currentCategory);
        }

        if (filteredItems.length === 0) {
            list.innerHTML = '';
            if (emptyState) {
                emptyState.style.display = 'block';
                emptyState.querySelector('h3').textContent = '暂无文本知识';
                emptyState.querySelector('p').textContent = '点击"新增文本"添加第一条知识到知识库';
            }
            return;
        }

        if (emptyState) emptyState.style.display = 'none';

        list.innerHTML = filteredItems.map(item => this.createTextCard(item)).join('');

        // 绑定卡片事件
        list.querySelectorAll('.text-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const itemId = card.dataset.itemId;
                this.showTextPreviewModal(itemId);
            });
        });

        // 视图切换
        if (this.currentView === 'list') {
            list.classList.add('list-view');
        } else {
            list.classList.remove('list-view');
        }
    }

    createTextCard(item) {
        const tags = item.tags || [];
        const tagsHtml = tags.slice(0, 3).map(tag =>
            `<span class="meta-badge">${tag}</span>`
        ).join('');

        return `
            <div class="content-card text-card" data-item-id="${item.id}">
                <div class="card-content">
                    <h4 class="card-title">${item.title}</h4>
                    <p class="card-excerpt">${item.summary || item.content?.substring(0, 100) || ''}</p>
                    <div class="card-meta">
                        ${tagsHtml}
                        ${item.category ? `<span class="meta-badge" style="background: var(--secondary-color)">${item.category}</span>` : ''}
                        ${item.source_type ? `<span class="meta-badge">${this.getSourceTypeLabel(item.source_type)}</span>` : ''}
                    </div>
                    <div class="card-meta" style="margin-top: 4px;">
                        <span class="time-info">使用 ${item.usage_count || 0} 次</span>
                    </div>
                </div>
            </div>
        `;
    }

    getSourceTypeLabel(type) {
        const labels = { manual: '手动录入', imported: '导入', web: '网页', other: '其他' };
        return labels[type] || type;
    }

    // ========== 通用方法 ==========

    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    switchView(view) {
        this.currentView = view;
        document.querySelectorAll('#knowledge-manager-view .view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.layout === view);
        });
        if (this.currentKnowledgeType === 'image') {
            this.renderImages();
        } else {
            this.renderTextItems();
        }
    }

    switchCategory(category) {
        this.currentCategory = category;
        document.querySelectorAll('#category-tree .tree-item').forEach(item => {
            item.classList.toggle('active', item.dataset.category === category);
        });
        if (this.currentKnowledgeType === 'image') {
            this.renderImages();
        } else {
            this.renderTextItems();
        }
    }

    searchItems(query) {
        if (!query.trim()) {
            if (this.currentKnowledgeType === 'image') {
                this.renderImages();
            } else {
                this.renderTextItems();
            }
            return;
        }

        const lowerQuery = query.toLowerCase();

        if (this.currentKnowledgeType === 'image') {
            const filtered = this.images.filter(image => {
                const descMatch = image.description?.toLowerCase().includes(lowerQuery);
                const tagMatch = image.tags?.some(tag => tag.toLowerCase().includes(lowerQuery));
                const nameMatch = image.original_filename?.toLowerCase().includes(lowerQuery);
                return descMatch || tagMatch || nameMatch;
            });
            this.renderFilteredImages(filtered);
        } else {
            const filtered = this.textItems.filter(item => {
                const titleMatch = item.title?.toLowerCase().includes(lowerQuery);
                const contentMatch = item.content?.toLowerCase().includes(lowerQuery);
                const tagMatch = item.tags?.some(tag => tag.toLowerCase().includes(lowerQuery));
                return titleMatch || contentMatch || tagMatch;
            });
            this.renderFilteredTextItems(filtered);
        }
    }

    renderFilteredImages(images) {
        const grid = document.getElementById('km-image-grid');
        const emptyState = document.getElementById('km-empty-state');

        if (images.length === 0) {
            grid.innerHTML = '';
            if (emptyState) {
                emptyState.querySelector('h3').textContent = '未找到图片';
                emptyState.querySelector('p').textContent = '尝试使用其他关键词搜索';
                emptyState.style.display = 'block';
            }
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        grid.innerHTML = images.map(image => this.createImageCard(image)).join('');

        grid.querySelectorAll('.image-card').forEach(card => {
            card.addEventListener('click', () => {
                this.showPreviewModal(card.dataset.imageId);
            });
        });
    }

    renderFilteredTextItems(items) {
        const list = document.getElementById('km-text-list');
        const emptyState = document.getElementById('km-empty-state');

        if (items.length === 0) {
            list.innerHTML = '';
            if (emptyState) {
                emptyState.querySelector('h3').textContent = '未找到文本知识';
                emptyState.querySelector('p').textContent = '尝试使用其他关键词搜索';
                emptyState.style.display = 'block';
            }
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        list.innerHTML = items.map(item => this.createTextCard(item)).join('');

        list.querySelectorAll('.text-card').forEach(card => {
            card.addEventListener('click', () => {
                this.showTextPreviewModal(card.dataset.itemId);
            });
        });
    }

    showAddModal() {
        if (this.currentKnowledgeType === 'image') {
            this.showUploadModal();
        } else {
            this.showTextModal();
        }
    }

    // ========== 分类管理 ==========

    async createCategory(name) {
        // 创建一个占位文本知识来"创建"分类
        // 因为后端分类是从文本知识的 category 字段动态提取的
        const placeholderData = {
            title: `分类: ${name}`,
            content: `这是「${name}」分类的占位条目，用于在分类树中显示该分类`,
            summary: `分类「${name}」的占位摘要`,
            tags: ['_system_category'],
            category: name,
            source_type: 'system'
        };

        try {
            const response = await fetch('/api/text-knowledge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(placeholderData)
            });
            return response.ok;
        } catch (error) {
            console.error('创建分类失败:', error);
            return false;
        }
    }

    showAddCategoryModal() {
        window.dialogManager?.showInput(
            '新建分类',
            '请输入分类名称:',
            '',
            async (name) => {
                if (name && name.trim()) {
                    const categoryName = name.trim();
                    const success = await this.createCategory(categoryName);
                    if (success) {
                        window.app?.showNotification('分类已创建: ' + categoryName, 'success');
                        // 刷新分类和文本知识
                        this.loadCategories();
                        this.loadTextKnowledge();
                    } else {
                        window.app?.showNotification('分类创建失败', 'error');
                    }
                }
            },
            () => {
                // 取消操作
            }
        );
    }

    // ========== 文本知识库CRUD ==========

    showTextModal(item = null) {
        const modal = document.getElementById('km-text-modal');
        const title = document.getElementById('km-text-modal-title');

        if (item) {
            this.currentEditItem = item;
            title.textContent = '编辑文本知识';
            document.getElementById('km-text-id').value = item.id;
            document.getElementById('km-text-title').value = item.title || '';
            document.getElementById('km-text-content').value = item.content || '';
            document.getElementById('km-text-summary').value = item.summary || '';
            document.getElementById('km-text-tags').value = (item.tags || []).join(', ');
            document.getElementById('km-text-category').value = item.category || '';
            document.getElementById('km-text-source-type').value = item.source_type || 'manual';
        } else {
            this.currentEditItem = null;
            title.textContent = '新增文本知识';
            document.getElementById('km-text-id').value = '';
            document.getElementById('km-text-title').value = '';
            document.getElementById('km-text-content').value = '';
            document.getElementById('km-text-summary').value = '';
            document.getElementById('km-text-tags').value = '';
            document.getElementById('km-text-category').value = '';
            document.getElementById('km-text-source-type').value = 'manual';
        }

        if (modal) modal.style.display = 'flex';
    }

    hideTextModal() {
        const modal = document.getElementById('km-text-modal');
        if (modal) modal.style.display = 'none';
        this.currentEditItem = null;
    }

    async saveTextItem() {
        const id = document.getElementById('km-text-id').value;
        const title = document.getElementById('km-text-title').value.trim();
        const content = document.getElementById('km-text-content').value.trim();
        const summary = document.getElementById('km-text-summary').value.trim();
        const tagsInput = document.getElementById('km-text-tags').value;
        const category = document.getElementById('km-text-category').value;
        const sourceType = document.getElementById('km-text-source-type').value;

        if (!title || !content) {
            window.app?.showNotification('标题和内容不能为空', 'warning');
            return;
        }

        const itemData = {
            title,
            content,
            summary,
            tags: tagsInput.split(',').map(t => t.trim()).filter(t => t),
            category: category || null,
            source_type: sourceType
        };

        try {
            let response;
            if (id) {
                response = await fetch(`/api/text-knowledge/${id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(itemData)
                });
            } else {
                response = await fetch('/api/text-knowledge', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(itemData)
                });
            }

            if (response.ok) {
                window.app?.showNotification(id ? '文本知识已更新' : '文本知识已新增', 'success');
                this.hideTextModal();
                this.loadTextKnowledge();
            } else {
                const error = await response.json();
                window.app?.showNotification(error.message || '保存失败', 'error');
            }
        } catch (error) {
            console.error('保存失败:', error);
            window.app?.showNotification('保存失败', 'error');
        }
    }

    showTextPreviewModal(itemId) {
        const item = this.textItems.find(t => t.id === itemId);
        if (!item) return;

        this.currentEditItem = item;

        document.getElementById('km-text-preview-title').textContent = item.title;
        document.getElementById('km-text-preview-title-val').textContent = item.title || '-';
        document.getElementById('km-text-preview-category').textContent = item.category || '未分类';
        document.getElementById('km-text-preview-tags').textContent = (item.tags || []).join(', ') || '-';
        document.getElementById('km-text-preview-source').textContent = this.getSourceTypeLabel(item.source_type);
        document.getElementById('km-text-preview-usage').textContent = item.usage_count || 0;
        document.getElementById('km-text-preview-content').textContent = item.content || '';

        const modal = document.getElementById('km-text-preview-modal');
        if (modal) modal.style.display = 'flex';
    }

    hideTextPreviewModal() {
        const modal = document.getElementById('km-text-preview-modal');
        if (modal) modal.style.display = 'none';
        this.currentEditItem = null;
    }

    editTextFromPreview() {
        if (!this.currentEditItem) return;
        this.hideTextPreviewModal();
        this.showTextModal(this.currentEditItem);
    }

    async deleteTextFromPreview() {
        if (!this.currentEditItem) return;

        const itemId = this.currentEditItem.id;

        if (!confirm('确定要删除这条文本知识吗？')) return;

        try {
            const response = await fetch(`/api/text-knowledge/${itemId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                window.app?.showNotification('文本知识已删除', 'success');
                this.hideTextPreviewModal();
                this.loadTextKnowledge();
            } else {
                window.app?.showNotification('删除失败', 'error');
            }
        } catch (error) {
            console.error('删除失败:', error);
            window.app?.showNotification('删除失败', 'error');
        }
    }

    // ========== 图片知识库CRUD ==========

    showUploadModal() {
        const modal = document.getElementById('km-upload-modal');
        console.log('showUploadModal called, modal element:', modal);
        if (modal) {
            console.log('Setting modal display to flex');
            modal.style.display = 'flex';
            document.getElementById('km-file-input').value = '';
            document.getElementById('km-image-description').value = '';
            document.getElementById('km-image-tags').value = '';
            document.getElementById('km-image-category').value = '';
        } else {
            console.error('km-upload-modal element not found!');
        }
    }

    hideUploadModal() {
        const modal = document.getElementById('km-upload-modal');
        if (modal) modal.style.display = 'none';
        // 清空文件列表
        const fileList = document.getElementById('km-file-list');
        if (fileList) fileList.innerHTML = '';
        const placeholder = document.querySelector('.file-upload-placeholder');
        if (placeholder) placeholder.style.display = 'flex';
    }

    _initFileUploadArea() {
        const area = document.getElementById('km-file-upload-area');
        const fileInput = document.getElementById('km-file-input');
        if (!area || !fileInput) return;

        // 点击上传区域触发文件选择
        area.addEventListener('click', () => fileInput.click());

        // 文件输入变化时更新列表
        fileInput.addEventListener('change', () => {
            this._renderFileList(fileInput.files);
        });

        // 拖拽支持
        area.addEventListener('dragover', (e) => {
            e.preventDefault();
            area.classList.add('dragover');
        });
        area.addEventListener('dragleave', () => {
            area.classList.remove('dragover');
        });
        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('dragover');
            if (e.dataTransfer.files) {
                this._renderFileList(e.dataTransfer.files);
            }
        });
    }

    _renderFileList(files) {
        const fileList = document.getElementById('km-file-list');
        const placeholder = document.querySelector('.file-upload-placeholder');
        if (!fileList) return;

        fileList.innerHTML = '';
        if (files.length === 0) {
            if (placeholder) placeholder.style.display = 'flex';
            return;
        }

        if (placeholder) placeholder.style.display = 'none';

        Array.from(files).forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <span class="file-name">${file.name}</span>
                <button class="file-remove" data-index="${index}">&times;</button>
            `;
            item.querySelector('.file-remove').addEventListener('click', (e) => {
                e.stopPropagation();
                // 移除对应的文件（通过创建新的 FileList）
                const dt = new DataTransfer();
                const input = document.getElementById('km-file-input');
                Array.from(input.files).forEach((f, i) => {
                    if (i !== index) dt.items.add(f);
                });
                input.files = dt.files;
                this._renderFileList(input.files);
            });
            fileList.appendChild(item);
        });
    }

    async uploadImage() {
        const fileInput = document.getElementById('km-file-input');
        const description = document.getElementById('km-image-description').value;
        const tagsInput = document.getElementById('km-image-tags').value;
        const category = document.getElementById('km-image-category').value;

        if (!fileInput.files || fileInput.files.length === 0) {
            window.app?.showNotification('请选择图片', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('description', description);
        formData.append('tags', tagsInput);
        formData.append('category', category);

        try {
            const response = await fetch('/api/images', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                window.app?.showNotification('图片上传成功', 'success');
                this.hideUploadModal();
                this.loadImages();
            } else {
                const error = await response.json();
                window.app?.showNotification(error.message || '上传失败', 'error');
            }
        } catch (error) {
            console.error('上传失败:', error);
            window.app?.showNotification('上传失败', 'error');
        }
    }

    showPreviewModal(imageId) {
        const image = this.images.find(img => img.id === imageId);
        if (!image) return;

        this.currentEditItem = image;

        document.getElementById('km-preview-image').src = `/api/images/${image.id}/file`;
        document.getElementById('km-preview-title').textContent = image.original_filename;
        document.getElementById('km-preview-filename').textContent = image.original_filename;
        document.getElementById('km-preview-description').textContent = image.description || '-';
        document.getElementById('km-preview-tags').textContent = (image.tags || []).join(', ') || '-';
        document.getElementById('km-preview-category').textContent = image.category || '未分类';
        document.getElementById('km-preview-usage').textContent = image.usage_count || 0;

        const modal = document.getElementById('km-preview-modal');
        if (modal) modal.style.display = 'flex';
    }

    hidePreviewModal() {
        const modal = document.getElementById('km-preview-modal');
        if (modal) modal.style.display = 'none';
        this.currentEditItem = null;
    }

    useImageFromPreview() {
        if (!this.currentEditItem) return;
        window.app?.showNotification('图片已复制到剪贴板', 'success');
        this.hidePreviewModal();
    }

    editFromPreview() {
        if (!this.currentEditItem) return;
        this.showEditModal(this.currentEditItem);
    }

    showEditModal(image) {
        this.currentEditItem = image;

        document.getElementById('km-edit-image-id').value = image.id;
        document.getElementById('km-edit-description').value = image.description || '';
        document.getElementById('km-edit-tags').value = (image.tags || []).join(', ');
        document.getElementById('km-edit-category').value = image.category || '';

        const modal = document.getElementById('km-edit-modal');
        if (modal) modal.style.display = 'flex';
    }

    hideEditModal() {
        const modal = document.getElementById('km-edit-modal');
        if (modal) modal.style.display = 'none';
        this.currentEditItem = null;
    }

    async saveImageEdit() {
        if (!this.currentEditItem) return;

        const imageId = document.getElementById('km-edit-image-id').value;
        const description = document.getElementById('km-edit-description').value;
        const tagsInput = document.getElementById('km-edit-tags').value;
        const category = document.getElementById('km-edit-category').value;

        const updateData = {
            description,
            tags: tagsInput.split(',').map(t => t.trim()).filter(t => t),
            category: category || null
        };

        try {
            const response = await fetch(`/api/images/${imageId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });

            if (response.ok) {
                window.app?.showNotification('图片信息已更新', 'success');
                this.hideEditModal();
                this.loadImages();
                if (document.getElementById('km-preview-modal').style.display !== 'none') {
                    const updatedImage = this.images.find(img => img.id === imageId);
                    if (updatedImage) {
                        this.showPreviewModal(imageId);
                    }
                }
            } else {
                window.app?.showNotification('更新失败', 'error');
            }
        } catch (error) {
            console.error('更新失败:', error);
            window.app?.showNotification('更新失败', 'error');
        }
    }

    async deleteImageFromPreview() {
        if (!this.currentEditItem) return;

        const imageId = this.currentEditItem.id;

        if (!confirm('确定要删除这张图片吗？')) return;

        try {
            const response = await fetch(`/api/images/${imageId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                window.app?.showNotification('图片已删除', 'success');
                this.hidePreviewModal();
                this.loadImages();
            } else {
                window.app?.showNotification('删除失败', 'error');
            }
        } catch (error) {
            console.error('删除失败:', error);
            window.app?.showNotification('删除失败', 'error');
        }
    }
}

// 知识库管理器由 main.js 统一初始化，不在这里创建
// window.knowledgeManager = new KnowledgeManager();
