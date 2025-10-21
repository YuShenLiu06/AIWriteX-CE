class TemplateManager {  
    constructor() {  
        this.templates = [];  
        this.categories = [];  
        this.currentTemplate = null;  
        this.currentLayout = 'grid';
        this.currentCategory = null;
        this.observer = null;
        this.initialized = false;
        this.init();
    }  
  
    async init() {  
        if (this.initialized) {  
            // 如果已经初始化,只刷新数据,不重新渲染    
            await this.loadCategories();    
            await this.loadTemplates(this.currentCategory);    
            this.renderCategoryTree();  
            
            // 重新激活 Observer  
            if (this.observer) {  
                const cards = document.querySelectorAll('.template-card');  
                cards.forEach(card => {  
                    if (card.querySelector('iframe[data-loaded="true"]')) {  
                        // 已加载的卡片不需要重新观察  
                        return;  
                    }  
                    this.observer.observe(card);  
                });  
            }
            this.updateAddTemplateButtonState();
            return;    
        }  
        
        await this.loadCategories();    
        await this.loadTemplates();    
        this.setupIntersectionObserver();    
        this.bindEvents();    
        this.renderCategoryTree();    
        this.renderTemplateGrid();    
        this.initialized = true;
        this.updateAddTemplateButtonState();
    }
  
    async loadCategories() {  
        const response = await fetch('/api/templates/categories');  
        const result = await response.json();  
        this.categories = result.data;  
    }  
  
    async loadTemplates(category = null) {  
        const url = category   
            ? `/api/templates?category=${encodeURIComponent(category)}`  
            : '/api/templates';  
        const response = await fetch(url);  
        const result = await response.json();  
        this.templates = result.data;  
    }  
  
    bindEvents() {  
        // 新建模板  
        const addTemplateBtn = document.getElementById('add-template');  
        if (addTemplateBtn) {  
            addTemplateBtn.addEventListener('click', () => {  
                this.showCreateTemplateDialog();  
            });  
        }  
          
        // 新建分类  
        const addCategoryBtn = document.getElementById('add-category');  
        if (addCategoryBtn) {  
            addCategoryBtn.addEventListener('click', () => {  
                this.showCreateCategoryDialog();  
            });  
        }  
          
        // 搜索  
        const searchInput = document.getElementById('template-search');  
        if (searchInput) {  
            searchInput.addEventListener('input', (e) => {  
                this.filterTemplates(e.target.value);  
            });  
        }  
          
        // 视图切换 - 使用更具体的选择器避免冲突  
        document.querySelectorAll('.view-toggle .view-btn').forEach(btn => {  
            btn.addEventListener('click', (e) => {  
                e.preventDefault();  
                e.stopPropagation();  
                this.switchLayout(btn.dataset.layout);  
            });  
        });  
          
        // 分类树点击  
        const categoryTree = document.getElementById('category-tree');  
        if (categoryTree) {  
            categoryTree.addEventListener('click', (e) => {  
                const categoryItem = e.target.closest('.category-item');  
                if (categoryItem) {  
                    this.selectCategory(categoryItem.dataset.category);  
                }  
            });  
        }  
    }  
  
    renderCategoryTree() {  
        const tree = document.getElementById('category-tree');  
        if (!tree) return;  
        
        const allCount = this.templates.length;  
        tree.innerHTML = `  
            <div class="category-item ${!this.currentCategory ? 'active' : ''}" data-category="">  
                <span class="category-icon">📁</span>  
                <span class="category-name" title="全部模板">全部模板</span>  
                <span class="category-count">${allCount}</span>  
            </div>  
            ${this.categories.map(cat => `  
                <div class="category-item ${this.currentCategory === cat.name ? 'active' : ''}"   
                    data-category="${cat.name}">  
                    <span class="category-icon">📂</span>  
                    <span class="category-name" title="${cat.name}">${cat.name}</span>  
                    <span class="category-count">${cat.template_count}</span>  
                </div>  
            `).join('')}  
        `;  
        
        // 绑定右键菜单事件  
        tree.querySelectorAll('.category-item[data-category]:not([data-category=""])').forEach(item => {  
            item.addEventListener('contextmenu', (e) => {  
                e.preventDefault();  
                const categoryName = item.dataset.category;  
                this.showCategoryContextMenu(e, categoryName);  
            });  
        });  
    }

    showCategoryContextMenu(e, categoryName) {  
        const existingMenu = document.querySelector('.category-context-menu');  
        if (existingMenu) {  
            existingMenu.remove();  
        }  
        
        // 创建菜单  
        const menu = document.createElement('div');  
        menu.className = 'category-context-menu';  
        menu.style.left = `${e.pageX}px`;  
        menu.style.top = `${e.pageY}px`;  
        
        // 编辑选项  
        const editItem = document.createElement('div');  
        editItem.className = 'context-menu-item';  
        editItem.innerHTML = '<span>✏️</span> 编辑分类';  
        editItem.addEventListener('click', () => {  
            menu.remove();  
            this.editCategory(categoryName);  
        });  
        
        // 删除选项  
        const deleteItem = document.createElement('div');  
        deleteItem.className = 'context-menu-item context-menu-item-danger';  
        deleteItem.innerHTML = '<span>🗑️</span> 删除分类';  
        deleteItem.addEventListener('click', () => {  
            menu.remove();  
            this.deleteCategory(categoryName);  
        });  
        
        menu.appendChild(editItem);  
        menu.appendChild(deleteItem);  
        document.body.appendChild(menu);  
        
        // 点击外部关闭菜单  
        setTimeout(() => {  
            const closeMenu = () => {  
                menu.remove();  
                document.removeEventListener('click', closeMenu);  
            };  
            document.addEventListener('click', closeMenu);  
        }, 0);  
    }

    async editCategory(oldCategoryName) {    
        window.dialogManager.showInput(    
            '编辑分类',    
            '请输入新的分类名称:',    
            oldCategoryName,    
            async (newName) => {    
                if (!newName || newName === oldCategoryName) {    
                    return;    
                }    
                
                // 检查新名称是否已存在    
                if (this.categories.some(cat => cat.name === newName)) {    
                    window.dialogManager.showAlert('分类名称已存在', 'error');    
                    return;    
                }    
                
                try {    
                    const response = await fetch(`/api/templates/categories/${encodeURIComponent(oldCategoryName)}`, {    
                        method: 'PUT',    
                        headers: { 'Content-Type': 'application/json' },    
                        body: JSON.stringify({   
                            old_name: oldCategoryName,  // 添加这一行  
                            new_name: newName   
                        })    
                    });    
    
                    if (response.ok) {    
                        await this.updateConfigIfNeeded(oldCategoryName, newName);    
                        await this.loadCategories();    
                        this.renderCategoryTree();    
                        
                        if (this.currentCategory === oldCategoryName) {    
                            await this.selectCategory(newName);    
                        }    
                        
                        window.app?.showNotification('分类已重命名', 'success');    
                    } else {    
                        const error = await response.json();  
                        const errorMessage = typeof error.detail === 'string'   
                            ? error.detail   
                            : JSON.stringify(error.detail);  
                        window.dialogManager.showAlert('重命名失败: ' + errorMessage, 'error');    
                    }    
                } catch (error) {    
                    window.dialogManager.showAlert('重命名失败: ' + error.message, 'error');    
                }    
            }    
        );    
    }

    async deleteCategory(categoryName) {    
        const category = this.categories.find(cat => cat.name === categoryName);    
        const templateCount = category ? category.template_count : 0;    
        
        const message = templateCount > 0    
            ? `确认删除分类 "${categoryName}" 及其包含的 ${templateCount} 个模板?\n\n此操作不可撤销!`    
            : `确认删除空分类 "${categoryName}"?`;    
        
        window.dialogManager.showConfirm(    
            message,    
            async () => {    
                try {    
                    const response = await fetch(`/api/templates/categories/${encodeURIComponent(categoryName)}?force=true`, {    
                        method: 'DELETE'    
                    });    
    
                    if (response.ok) {    
                        await this.updateConfigIfNeeded(categoryName, null);    
                        await this.loadCategories();    
                        await this.loadTemplates();    
                        this.renderCategoryTree();    
                        this.renderTemplateGrid();    
                        
                        if (this.currentCategory === categoryName) {    
                            await this.selectCategory(null);    
                        }    
                        
                        window.app?.showNotification('分类已删除', 'success');    
                    } else {    
                        const error = await response.json();  
                        const errorMessage = typeof error.detail === 'string'   
                            ? error.detail   
                            : JSON.stringify(error.detail);  
                        window.dialogManager.showAlert('删除失败: ' + errorMessage, 'error');    
                    }    
                } catch (error) {    
                    console.error('删除分类失败:', error);  
                    window.dialogManager.showAlert('删除失败: ' + error.message, 'error');    
                }    
            }    
        );    
    }

    async updateConfigIfNeeded(oldCategoryName, newCategoryName) {  
        try {  
            // 获取当前配置  
            const configResponse = await fetch('/api/config/');  
            if (!configResponse.ok) return;  
            
            const configData = await configResponse.json();  
            const currentCategory = configData.data?.template_category;  
            
            // 如果当前配置的分类就是被修改/删除的分类  
            if (currentCategory === oldCategoryName) {  
                // 更新配置  
                const updateResponse = await fetch('/api/config/', {  
                    method: 'PATCH',  
                    headers: { 'Content-Type': 'application/json' },  
                    body: JSON.stringify({  
                        template_category: newCategoryName || ''  // 删除时设为空字符串  
                    })  
                });  
                
                if (updateResponse.ok) {  
                    // 持久化到磁盘  
                    await fetch('/api/config/', { method: 'POST' });  
                    
                    if (newCategoryName) {  
                        window.app?.showNotification(`配置已自动更新为新分类: ${newCategoryName}`, 'info');  
                    } else {  
                        window.app?.showNotification('配置中的分类设置已清空', 'info');  
                    }  
                }  
            }  
        } catch (error) {  
            console.error('更新配置失败:', error);  
            // 配置更新失败不影响分类操作本身  
        }  
    }

    setupIntersectionObserver() {  
        // 清理旧的observer  
        if (this.observer) {  
            this.observer.disconnect();  
            this.observer = null;  
        }  
    
        // 创建新的observer  
        this.observer = new IntersectionObserver((entries) => {  
            entries.forEach(entry => {  
                if (entry.isIntersecting) {  
                    const card = entry.target;  
                    const iframe = card.querySelector('iframe[data-template-path]');  
                    if (iframe && iframe.dataset.loaded !== 'true') {  
                        this.loadSinglePreview(iframe);  
                        this.observer.unobserve(card);  
                    }  
                }  
            });  
        }, {  
            root: document.querySelector('.template-main'),  
            rootMargin: '200px',  
            threshold: 0.01  
        });  
    }
  
    renderTemplateGrid() {  
        const grid = document.getElementById('template-grid');  
        if (!grid) return;  
          
        grid.className = this.currentLayout === 'grid' ? 'template-grid' : 'template-grid list-view';  
          
        if (this.templates.length === 0) {  
            grid.innerHTML = '<div class="empty-state">暂无模板</div>';  
            return;  
        }
        const formatTime = (timeStr) => {  
            const date = new Date(timeStr);  
            const today = new Date();  
            const diffDays = Math.floor((today - date) / (1000 * 60 * 60 * 24));  
            
            if (diffDays === 0) return '今天';  
            if (diffDays === 1) return '昨天';  
            if (diffDays < 7) return `${diffDays}天前`;  
            return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });  
        }; 

          
        // 渲染卡片结构,但不立即加载iframe内容  
        grid.innerHTML = this.templates.map(template => `  
            <div class="template-card" data-template-path="${template.path}">    
                <div class="card-preview">    
                    <iframe sandbox="allow-same-origin allow-scripts"     
                            loading="lazy"    
                            data-template-path="${template.path}"    
                            data-loaded="false"></iframe>    
                    <div class="preview-loading">加载中...</div>    
                </div>    
                <div class="card-content">    
                    <h4 class="card-title" title="${template.name}">${template.name}</h4>    
                    <div class="card-meta">    
                        <span class="category-badge" title="${template.category}">${template.category}</span>  
                        <span class="meta-divider">•</span>    
                        <span class="size-info">${template.size}</span>    
                        <span class="meta-divider">•</span>    
                        <span class="time-info">${formatTime(template.create_time)}</span>    
                    </div>    
                </div> 
                <div class="card-actions">  
                    <button class="btn-icon" data-action="preview" title="预览">  
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>  
                            <circle cx="12" cy="12" r="3"/>  
                        </svg>  
                    </button>  
                    <button class="btn-icon" data-action="edit" title="编辑">  
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>  
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>  
                        </svg>  
                    </button>  
                    <button class="btn-icon" data-action="copy" title="复制">  
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>  
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>  
                        </svg>  
                    </button>  
                    <button class="btn-icon" data-action="delete" title="删除">  
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                            <polyline points="3 6 5 6 21 6"/>  
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>  
                        </svg>  
                    </button>  
                </div>  
            </div>  
        `).join('');  
          
        this.bindCardEvents();  
          
        // 观察所有卡片,实现懒加载  
        const cards = grid.querySelectorAll('.template-card');  
        cards.forEach(card => this.observer.observe(card));  
    }  
  
    async loadSinglePreview(iframe) {  
        const templatePath = iframe.dataset.templatePath;  
        const loadingEl = iframe.parentElement.querySelector('.preview-loading');  
          
        try {  
            const response = await fetch(`/api/templates/content/${encodeURIComponent(templatePath)}`);  
            if (!response.ok) {  
                throw new Error(`HTTP ${response.status}`);  
            }  
            const html = await response.text();  
            const styledHtml = `  
                <style>  
                    body {   
                        overflow: hidden !important;   
                        margin: 0;  
                    }  
                    ::-webkit-scrollbar { display: none !important; }  
                    * { scrollbar-width: none !important; }  
                </style>  
                ${html}  
            `;  
            iframe.srcdoc = styledHtml;  
            iframe.dataset.loaded = 'true';  
            if (loadingEl) loadingEl.style.display = 'none';  
        } catch (error) {  
            console.error('加载模板预览失败:', templatePath, error);  
            iframe.srcdoc = '<div style="padding: 20px; color: red;">加载失败</div>';  
            if (loadingEl) loadingEl.textContent = '加载失败';  
        }  
    } 
  
    bindCardEvents() {  
        const grid = document.getElementById('template-grid');  
        if (!grid) return;  
          
        grid.querySelectorAll('.template-card').forEach(card => {  
            // 卡片点击预览  
            card.addEventListener('click', (e) => {  
                if (!e.target.closest('.card-actions')) {  
                    const templatePath = card.dataset.templatePath;  
                    const template = this.templates.find(t => t.path === templatePath);  
                    if (template) {  
                        this.previewTemplate(template);  
                    }  
                }  
            });  
              
            // 操作按钮点击  
            card.querySelectorAll('[data-action]').forEach(btn => {  
                btn.addEventListener('click', (e) => {  
                    e.stopPropagation();  
                    const action = btn.dataset.action;  
                    const templatePath = card.dataset.templatePath;  
                    const template = this.templates.find(t => t.path === templatePath);  
                    if (template) {  
                        this.handleCardAction(action, template);  
                    }  
                });  
            });  
        });  
    }  
  
    async handleCardAction(action, template) {  
        switch(action) {  
            case 'preview':  
                this.previewTemplate(template);  
                break;  
            case 'edit':  
                await this.editTemplate(template);  
                break;  
            case 'copy':  
                await this.copyTemplate(template);  
                break;  
            case 'delete':  
                await this.deleteTemplate(template);  
                break;  
        }  
    }  
  
    previewTemplate(template) {  
        // 使用全局preview-panel,参考现有实现  
        fetch(`/api/templates/content/${encodeURIComponent(template.path)}`)  
            .then(res => res.text())  
            .then(html => {  
                if (window.previewPanelManager) {  
                    window.previewPanelManager.show(html);  
                }  
            })  
            .catch(err => {  
                console.error('预览失败:', err);  
                alert('预览失败: ' + err.message);  
            });  
    }  
  
    async editTemplate(template) {  
        // 使用Monaco Editor或简单的文本编辑器  
        const content = await fetch(`/api/templates/content/${encodeURIComponent(template.path)}`)  
            .then(res => res.text());  
          
        // 显示编辑对话框  
        const newContent = prompt('编辑模板内容:', content);  
        if (newContent !== null && newContent !== content) {  
            try {  
                const response = await fetch(`/api/templates/content/${encodeURIComponent(template.path)}`, {  
                    method: 'PUT',  
                    headers: { 'Content-Type': 'application/json' },  
                    body: JSON.stringify({ content: newContent })  
                });  
                  
                if (response.ok) {  
                    window.app?.showNotification('模板已保存', 'success');  
                } else {  
                    const error = await response.json();  
                    alert('保存失败: ' + error.detail);  
                }  
            } catch (error) {  
                alert('保存失败: ' + error.message);  
            }  
        }  
    }  
  
    async copyTemplate(template) {  
        const newName = prompt('输入新模板名称:', template.name + '_copy');  
        if (!newName) return;  
  
        try {  
            const response = await fetch('/api/templates/copy', {  
                method: 'POST',  
                headers: { 'Content-Type': 'application/json' },  
                body: JSON.stringify({  
                    source_path: template.path,  
                    new_name: newName,  
                    target_category: template.category  
                })  
            });  
  
            if (response.ok) {  
                await this.loadTemplates(this.currentCategory);  
                this.renderTemplateGrid();  
                window.app?.showNotification('模板已复制', 'success');  
            } else {  
                const error = await response.json();  
                alert('复制失败: ' + error.detail);  
            }  
        } catch (error) {  
            alert('复制失败: ' + error.message);  
        }  
    }  
  
    async deleteTemplate(template) {  
        if (!confirm(`确认删除模板"${template.name}"?`)) return;  
          
        try {  
            const response = await fetch(`/api/templates/${encodeURIComponent(template.path)}`, {  
                method: 'DELETE'  
            });  
              
            if (response.ok) {  
                await this.loadCategories();  
                await this.loadTemplates(this.currentCategory);  
                this.renderCategoryTree();  
                this.renderTemplateGrid();  
                window.app?.showNotification('模板已删除', 'success');  
            } else {  
                const error = await response.json();  
                alert('删除失败: ' + error.detail);  
            }  
        } catch (error) {  
            alert('删除失败: ' + error.message);  
        }  
    }  
  
    switchLayout(layout) {  
        this.currentLayout = layout;        
        document.querySelectorAll('.view-toggle .view-btn').forEach(btn => {  
            if (btn.dataset.layout === layout) {  
                btn.classList.add('active');  
            } else {  
                btn.classList.remove('active');  
            }  
        });  
        
        // 重新渲染  
        this.renderTemplateGrid();  
    }
  
    async selectCategory(category) {  
        this.currentCategory = category || null;    
        await this.loadTemplates(this.currentCategory);    
        this.renderCategoryTree();    
        this.renderTemplateGrid();  
        
        // 更新新建模板按钮状态  
        this.updateAddTemplateButtonState();  
    }  
  
    updateAddTemplateButtonState() {  
        const addTemplateBtn = document.getElementById('add-template');  
        if (!addTemplateBtn) return;  
        
        // 当选中"全部模板"(currentCategory为null)时禁用按钮  
        if (this.currentCategory === null) {  
            addTemplateBtn.disabled = true;  
            addTemplateBtn.style.opacity = '0.5';  
            addTemplateBtn.style.cursor = 'not-allowed';  
            addTemplateBtn.title = '请先选择一个分类';  
        } else {  
            addTemplateBtn.disabled = false;  
            addTemplateBtn.style.opacity = '1';  
            addTemplateBtn.style.cursor = 'pointer';  
            addTemplateBtn.title = '新建模板';  
        }  
    }

    filterTemplates(searchText) {  
        const filtered = this.templates.filter(template =>   
            template.name.toLowerCase().includes(searchText.toLowerCase())  
        );  
          
        const grid = document.getElementById('template-grid');  
        if (!grid) return;  
          
        // 临时替换templates进行渲染  
        const originalTemplates = this.templates;  
        this.templates = filtered;  
        this.renderTemplateGrid();  
        this.templates = originalTemplates;  
    }  
  
    async showCreateTemplateDialog() {  
        // 如果没有选中分类,不应该执行到这里(按钮已禁用)  
        if (!this.currentCategory) {  
            window.dialogManager.showAlert('请先选择一个分类', 'error');  
            return;  
        }  
        
        window.dialogManager.showInput(  
            '新建模板',  
            '请输入模板名称:',
            '',  
            async (name) => {  
                if (!name) return;  
                
                try {  
                    const response = await fetch('/api/templates/', {  
                        method: 'POST',  
                        headers: { 'Content-Type': 'application/json' },  
                        body: JSON.stringify({  
                            name: name,  
                            category: this.currentCategory,  // 使用当前选中的分类  
                            content: ''  
                        })  
                    });  
    
                    if (response.ok) {  
                        await this.loadCategories();  
                        await this.loadTemplates(this.currentCategory);  
                        this.renderCategoryTree();  
                        this.renderTemplateGrid();  
                        window.app?.showNotification('模板已创建', 'success');  
                    } else {  
                        const error = await response.json();  
                        window.dialogManager.showAlert('创建失败: ' + error.detail, 'error');  
                    }  
                } catch (error) {  
                    window.dialogManager.showAlert('创建失败: ' + error.message, 'error');  
                }  
            }  
        );  
    }
  
    async showCreateCategoryDialog() {  
        window.dialogManager.showInput(  
            '新建分类',  
            '请输入分类名称:',  
            '',  
            async (name) => {  
                if (!name) {  
                    window.dialogManager.showAlert('分类名称不能为空', 'error');  
                    return;  
                }  
                
                try {  
                    const response = await fetch('/api/templates/categories', {  
                        method: 'POST',  
                        headers: { 'Content-Type': 'application/json' },  
                        body: JSON.stringify({ name: name })  
                    });  
    
                    if (response.ok) {  
                        await this.loadCategories();  
                        this.renderCategoryTree();  
                        
                        // 自动切换到新创建的分类  
                        await this.selectCategory(name);  
                        
                        window.app?.showNotification('分类已创建', 'success');  
                    } else {  
                        const error = await response.json();  
                        window.dialogManager.showAlert('创建失败: ' + error.detail, 'error');  
                    }  
                } catch (error) {  
                    window.dialogManager.showAlert('创建失败: ' + error.message, 'error');  
                }  
            }  
        );  
    }  
}  
  
// 初始化  
// window.templateManager = new TemplateManager();