class TemplateManager {  
    constructor() {  
        this.templates = [];  
        this.categories = [];  
        this.currentTemplate = null;  
        this.currentLayout = 'grid'; // 'grid' or 'list'  
        this.currentCategory = null;  
        this.init();  
    }  
  
    async init() {  
        await this.loadCategories();  
        await this.loadTemplates();  
        this.bindEvents();  
        this.renderCategoryTree();  
        this.renderTemplateGrid();  
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
                <span class="category-name">全部模板</span>  
                <span class="category-count">${allCount}</span>  
            </div>  
            ${this.categories.map(cat => `  
                <div class="category-item ${this.currentCategory === cat.name ? 'active' : ''}"   
                     data-category="${cat.name}">  
                    <span class="category-icon">📂</span>  
                    <span class="category-name">${cat.name}</span>  
                    <span class="category-count">${cat.template_count}</span>  
                </div>  
            `).join('')}  
        `;  
    }  
  
    renderTemplateGrid() {  
        const grid = document.getElementById('template-grid');  
        if (!grid) return;  
          
        grid.className = this.currentLayout === 'grid' ? 'template-grid' : 'template-grid list-view';  
          
        if (this.templates.length === 0) {  
            grid.innerHTML = '<div class="empty-state">暂无模板</div>';  
            return;  
        }  
          
        // 先渲染卡片结构  
        grid.innerHTML = this.templates.map(template => `  
            <div class="template-card" data-template-path="${template.path}">  
                <div class="card-preview">  
                    <iframe sandbox="allow-same-origin allow-scripts"   
                            loading="lazy"  
                            data-template-path="${template.path}"></iframe>  
                </div>    
                <div class="card-content">  
                    <h4 class="card-title">${template.name}</h4>  
                    <div class="card-meta">  
                        <span class="category-badge">${template.category}</span>  
                        <span class="size-info">${template.size}</span>  
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
          
        // 异步加载预览内容  
        this.loadPreviewContents();  
        this.bindCardEvents();  
    }  
      
    async loadPreviewContents() {  
        const iframes = document.querySelectorAll('.card-preview iframe[data-template-path]');  
        
        for (const iframe of iframes) {  
            const templatePath = iframe.dataset.templatePath;  
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
            } catch (error) {  
                console.error('加载模板预览失败:', templatePath, error);  
                iframe.srcdoc = '<div style="padding: 20px; color: red;">加载失败</div>';  
            }  
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
          
        // 更新按钮状态  
        document.querySelectorAll('.view-toggle .view-btn').forEach(btn => {  
            btn.classList.toggle('active', btn.dataset.layout === layout);  
        });  
          
        // 重新渲染  
        this.renderTemplateGrid();  
    }  
  
    async selectCategory(category) {  
        this.currentCategory = category || null;  
        await this.loadTemplates(this.currentCategory);  
        this.renderCategoryTree();  
        this.renderTemplateGrid();  
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
        const name = prompt('输入模板名称:');  
        if (!name) return;  
  
        const category = prompt('输入分类名称:', this.currentCategory || '');  
        if (!category) return;  
  
        try {  
            const response = await fetch('/api/templates/', {  
                method: 'POST',  
                headers: { 'Content-Type': 'application/json' },  
                body: JSON.stringify({  
                    name: name,  
                    category: category,  
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
                alert('创建失败: ' + error.detail);  
            }  
        } catch (error) {  
            alert('创建失败: ' + error.message);  
        }  
    }  
  
    async showCreateCategoryDialog() {  
        const name = prompt('输入分类名称:');  
        if (!name) return;  
  
        try {  
            const response = await fetch('/api/templates/categories', {  
                method: 'POST',  
                headers: { 'Content-Type': 'application/json' },  
                body: JSON.stringify({ name: name })  
            });  
  
            if (response.ok) {  
                await this.loadCategories();  
                this.renderCategoryTree();  
                window.app?.showNotification('分类已创建', 'success');  
            } else {  
                const error = await response.json();  
                alert('创建失败: ' + error.detail);  
            }  
        } catch (error) {  
            alert('创建失败: ' + error.message);  
        }  
    }  
}  
  
// 初始化  
window.templateManager = new TemplateManager();