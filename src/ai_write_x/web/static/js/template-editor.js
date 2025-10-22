class TemplateEditorDialog {  
    constructor() {  
        this.dialog = null;  
        this.editor = null;  
        this.currentTemplate = null;  
        this.currentLanguage = 'html';  
        this.originalContent = '';  
        this.isDirty = false;  
        this.previewTimer = null;  
        this.isFullscreen = false;  
        this.monacoLoaded = false;  
        this.themeObserver = null;  
    }  
      
    async initialize() {  
        if (this.monacoLoaded) return;  
        await this.preloadMonaco();  
    }  
      
    preloadMonaco() {  
        if (typeof monaco !== 'undefined') {  
            this.monacoLoaded = true;  
            return Promise.resolve();  
        }  
        
        return new Promise((resolve, reject) => {  
            if (typeof require === 'undefined') {  
                reject(new Error('Monaco Editor loader 未加载'));  
                return;  
            }  
            
            require.config({   
                paths: { 'vs': '/static/monaco/vs' }  
            });  
            
            // 只加载 editor.main,它已包含所有基础语言支持  
            require(['vs/editor/editor.main'], () => {  
                this.monacoLoaded = true;  
                resolve();  
            }, reject);  
        });  
    }  
      
    async open(templatePath, templateName) {  
        await this.initialize();  
        
        this.currentTemplate = templatePath;  
        
        const ext = templatePath.toLowerCase().split('.').pop();  
        const languageMap = {  
            'html': 'html',  
            'htm': 'html',  
            'md': 'markdown',  
            'markdown': 'markdown',  
            'txt': 'plaintext'  
        };  
        this.currentLanguage = languageMap[ext] || 'html';  
        
        this.createDialog(templateName);  
        
        // 先添加到 DOM,确保容器存在  
        document.body.appendChild(this.dialog);  
        
        // 等待 DOM 渲染  
        await new Promise(resolve => requestAnimationFrame(resolve));  
        
        // 初始化编辑器  
        await this.initMonacoEditor();  
        
        // 加载模板内容  
        await this.loadTemplate();  
        
        // 绑定事件  
        this.bindEvents();  
        
        // 显示对话框  
        requestAnimationFrame(() => {  
            this.dialog.classList.add('show');  
        });  
    } 
      
    createDialog(templateName) {  
        this.dialog = document.createElement('div');  
        this.dialog.className = 'template-editor-dialog';  
        this.dialog.innerHTML = `  
            <div class="editor-container">  
                <div class="editor-header">  
                    <h2 class="editor-title">  
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">  
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>  
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>  
                        </svg>  
                        <span>编辑模板 - ${templateName}</span>  
                    </h2>  
                    <div class="editor-actions">  
                        <select class="language-selector" id="language-selector">  
                            <option value="html">HTML</option>  
                            <option value="markdown">Markdown</option>  
                            <option value="plaintext">纯文本</option>  
                        </select>  
                          
                        <button class="btn-icon" id="format-code" title="格式化代码 (Shift+Alt+F)">  
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor">  
                                <path d="M4 7h16M4 12h10M4 17h16"/>  
                            </svg>  
                        </button>  
                        <button class="btn-icon" id="toggle-fullscreen" title="全屏 (F11)">  
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor">  
                                <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>  
                            </svg>  
                        </button>  
                        <button class="btn btn-secondary" id="cancel-edit">取消</button>  
                        <button class="btn btn-primary" id="save-template">  
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>  
                                <polyline points="17 21 17 13 7 13 7 21"/>  
                                <polyline points="7 3 7 8 15 8"/>  
                            </svg>  
                            保存 (Ctrl+S)  
                        </button>  
                    </div>  
                </div>  
                  
                <div class="editor-body">  
                    <div class="editor-panel">  
                        <div class="panel-header">  
                            <span id="language-label">HTML 代码</span>  
                            <span class="editor-status" id="editor-status">行: 1, 列: 1</span>  
                        </div>  
                        <div id="monaco-editor-container"></div>  
                    </div>  
                      
                    <div class="resize-handle" id="resize-handle"></div>  
                      
                    <div class="preview-panel">  
                        <div class="panel-header">  
                            <span>实时预览</span>  
                            <button class="btn-icon" id="refresh-preview" title="刷新预览">  
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                                    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>  
                                </svg>  
                            </button>  
                        </div>  
                        <iframe id="preview-iframe" sandbox="allow-same-origin allow-scripts"></iframe>  
                    </div>  
                </div>  
            </div>  
        `;  
    }  
      
    async initMonacoEditor() {  
        const container = this.dialog.querySelector('#monaco-editor-container');  
        const isDarkTheme = document.body.getAttribute('data-theme') === 'dark';  
        
        this.editor = monaco.editor.create(container, {  
            language: this.currentLanguage,  
            theme: isDarkTheme ? 'vs-dark' : 'vs',  
            automaticLayout: true,  
            fontSize: 14,  
            fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",  
            lineNumbers: 'on',  
            minimap: { enabled: true },  
            scrollBeyondLastLine: false,  
            wordWrap: 'on',  
            formatOnPaste: true,  
            formatOnType: true,  
            tabSize: 2,  
            insertSpaces: true,  
            renderWhitespace: 'selection',  
            bracketPairColorization: { enabled: true },  
            guides: {  
                bracketPairs: true,  
                indentation: true  
            }  
        });  
        
        this.themeObserver = new MutationObserver((mutations) => {  
            mutations.forEach((mutation) => {  
                if (mutation.attributeName === 'data-theme') {  
                    const isDark = document.body.getAttribute('data-theme') === 'dark';  
                    monaco.editor.setTheme(isDark ? 'vs-dark' : 'vs');  
                }  
            });  
        });  
        
        this.themeObserver.observe(document.body, {  
            attributes: true,  
            attributeFilter: ['data-theme']  
        });  
        
        this.editor.onDidChangeModelContent(() => { 
            this.isDirty = true;  
            this.updatePreviewDebounced();  
        });  
          
        this.editor.onDidChangeCursorPosition((e) => {  
            const status = this.dialog.querySelector('#editor-status');  
            if (status) {  
                status.textContent = `行: ${e.position.lineNumber}, 列: ${e.position.column}`;  
            }  
        });  
    }  
      
    async loadTemplate() {  
        try {  
            // 确保编辑器已初始化  
            if (!this.editor) {  
                throw new Error('编辑器未初始化');  
            }  
            
            const response = await fetch(`/api/templates/content/${encodeURIComponent(this.currentTemplate)}`);  
            if (!response.ok) throw new Error(`HTTP ${response.status}`);  
            
            const content = await response.text();  
            this.originalContent = content;  
            
            // 使用 setTimeout 确保编辑器完全就绪  
            setTimeout(() => {  
                this.editor.setValue(content);  
                this.isDirty = false;  
                
                const languageSelector = this.dialog.querySelector('#language-selector');  
                if (languageSelector) {  
                    languageSelector.value = this.currentLanguage;  
                }  
                
                this.updateLanguageLabel();  
                this.updatePreview();  
            }, 100);  
        } catch (error) {  
            window.dialogManager?.showAlert('加载模板失败: ' + error.message, 'error');  
        }  
    }  
      
    updatePreviewDebounced() {  
        clearTimeout(this.previewTimer);  
        this.previewTimer = setTimeout(() => {  
            if (this.currentLanguage === 'html') {  
                this.updatePreview();  
            } else if (this.currentLanguage === 'markdown') {  
                this.updateMarkdownPreview();  
            }  
        }, 500);  
    }   
      
    updatePreview() {  
        const content = this.editor.getValue();  
        const iframe = this.dialog.querySelector('#preview-iframe');  
          
        const styledContent = `  
            <style>  
                body {   
                    margin: 0;   
                    padding: 16px;  
                    overflow: auto;  
                }  
            </style>  
            ${content}  
        `;  
          
        iframe.srcdoc = styledContent;  
    }  
      
    updateMarkdownPreview() {  
        const content = this.editor.getValue();  
        const iframe = this.dialog.querySelector('#preview-iframe');  
          
        const htmlContent = this.markdownToHtml(content);  
          
        const styledContent = `  
            <style>  
                body {   
                    margin: 0;   
                    padding: 16px;  
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;  
                    line-height: 1.6;  
                }  
                h1, h2, h3 { margin-top: 24px; }  
                code {   
                    background: #f5f5f5;   
                    padding: 2px 6px;   
                    border-radius: 3px;   
                }  
                pre {   
                    background: #f5f5f5;   
                    padding: 12px;   
                    border-radius: 6px;   
                    overflow-x: auto;   
                }  
            </style>  
            ${htmlContent}  
        `;  
          
        iframe.srcdoc = styledContent;  
    }  
      
    markdownToHtml(markdown) {  
        return markdown  
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')  
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')  
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')  
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')  
            .replace(/\*(.*)\*/gim, '<em>$1</em>')  
            .replace(/\`(.*?)\`/gim, '<code>$1</code>')  
            .replace(/\n/gim, '<br>');  
    }  
      
    bindEvents() {  
        const saveBtn = this.dialog.querySelector('#save-template');  
        if (saveBtn) {  
            saveBtn.addEventListener('click', () => this.saveTemplate());  
        }  
          
        const cancelBtn = this.dialog.querySelector('#cancel-edit');  
        if (cancelBtn) {  
            cancelBtn.addEventListener('click', () => this.close());  
        }  
          
        const formatBtn = this.dialog.querySelector('#format-code');  
        if (formatBtn) {  
            formatBtn.addEventListener('click', () => {  
                this.editor.getAction('editor.action.formatDocument').run();  
            });  
        }  
          
        const fullscreenBtn = this.dialog.querySelector('#toggle-fullscreen');  
        if (fullscreenBtn) {  
            fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());  
        }  
          
        const refreshBtn = this.dialog.querySelector('#refresh-preview');  
        if (refreshBtn) {  
            refreshBtn.addEventListener('click', () => {  
                if (this.currentLanguage === 'html') {  
                    this.updatePreview();  
                } else if (this.currentLanguage === 'markdown') {  
                    this.updateMarkdownPreview();  
                }  
            });  
        }  
          
        const languageSelector = this.dialog.querySelector('#language-selector');  
        if (languageSelector) {  
            languageSelector.value = this.currentLanguage;  
            languageSelector.addEventListener('change', (e) => {  
                this.switchLanguage(e.target.value);  
            });  
        }  
          
        this.initResizeHandle();  
          
        document.addEventListener('keydown', this.handleKeydown.bind(this));  
          
        this.dialog.addEventListener('click', (e) => {  
            if (e.target === this.dialog) {  
                this.close();  
            }  
        });  
    }  
    
    initResizeHandle() {  
        const handle = this.dialog.querySelector('#resize-handle');  
        const editorPanel = this.dialog.querySelector('.editor-panel');  
        const previewPanel = this.dialog.querySelector('.preview-panel');  
        
        if (!handle || !editorPanel || !previewPanel) return;  
        
        let isResizing = false;  
        let startX = 0;  
        let startWidth = 0;  
    
        handle.addEventListener('mousedown', (e) => {  
            isResizing = true;  
            startX = e.clientX;  
            startWidth = editorPanel.offsetWidth;  
            document.body.style.cursor = 'col-resize';  
            e.preventDefault();  
        });  
    
        document.addEventListener('mousemove', (e) => {  
            if (!isResizing) return;  
            
            const delta = e.clientX - startX;  
            const newWidth = startWidth + delta;  
            const containerWidth = this.dialog.querySelector('.editor-body').offsetWidth;  
            const minWidth = 300;  
            const maxWidth = containerWidth - 300;  
            
            if (newWidth >= minWidth && newWidth <= maxWidth) {  
                const percentage = (newWidth / containerWidth) * 100;  
                editorPanel.style.flex = `0 0 ${percentage}%`;  
                previewPanel.style.flex = `1`;  
            }  
        });  
    
        document.addEventListener('mouseup', () => {  
            if (isResizing) {  
                isResizing = false;  
                document.body.style.cursor = '';  
            }  
        });  
    }

    switchLanguage(language) {  
        this.currentLanguage = language;  
          
        const model = this.editor.getModel();  
        monaco.editor.setModelLanguage(model, language);  
          
        this.updateLanguageLabel();  
          
        const previewPanel = this.dialog.querySelector('.preview-panel');  
          
        if (language === 'html') {  
            if (previewPanel) previewPanel.style.display = '';  
            this.updatePreview();  
        } else if (language === 'markdown') {  
            if (previewPanel) previewPanel.style.display = '';  
            this.updateMarkdownPreview();  
        } else {  
            if (previewPanel) previewPanel.style.display = 'none';  
        }  
    }
    
    updateLanguageLabel() {  
        const languageLabel = this.dialog.querySelector('#language-label');  
        const labelMap = {  
            'html': 'HTML 代码',  
            'markdown': 'Markdown 文档',  
            'plaintext': '纯文本'  
        };  
        if (languageLabel) {  
            languageLabel.textContent = labelMap[this.currentLanguage] || '代码';  
        }  
    }
      
    handleKeydown(e) {  
        if (!this.dialog || !this.dialog.classList.contains('show')) return;  
          
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {  
            e.preventDefault();  
            this.saveTemplate();  
        }  
          
        if (e.key === 'Escape') {  
            e.preventDefault();  
            this.close();  
        }  
          
        if (e.key === 'F11') {  
            e.preventDefault();  
            this.toggleFullscreen();  
        }  
    }  
      
    toggleFullscreen() {  
        this.isFullscreen = !this.isFullscreen;  
        this.dialog.classList.toggle('fullscreen', this.isFullscreen);  
          
        const icon = this.dialog.querySelector('#toggle-fullscreen svg');  
        if (this.isFullscreen) {  
            icon.innerHTML = `  
                <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/>  
            `;  
        } else {  
            icon.innerHTML = `  
                <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>  
            `;  
        }  
    }  
      
    async saveTemplate() {  
        const content = this.editor.getValue();  
        const saveBtn = this.dialog.querySelector('#save-template');  
          
        try {  
            saveBtn.disabled = true;  
            saveBtn.textContent = '保存中...';  
              
            const response = await fetch(`/api/templates/content/${encodeURIComponent(this.currentTemplate)}`, {  
                method: 'PUT',  
                headers: { 'Content-Type': 'application/json' },  
                body: JSON.stringify({ content })  
            });  
              
            if (response.ok) {  
                this.originalContent = content;  
                this.isDirty = false;  
                window.app?.showNotification('模板已保存', 'success');  
                  
                if (window.templateManager) {  
                    await window.templateManager.loadTemplates(window.templateManager.currentCategory);  
                    window.templateManager.renderTemplateGrid();  
                }  
            } else {  
                const error = await response.json();  
                window.dialogManager?.showAlert('保存失败: ' + (error.detail || '未知错误'), 'error');  
            }  
        } catch (error) {  
            window.dialogManager?.showAlert('保存失败: ' + error.message, 'error');  
        } finally {  
            saveBtn.disabled = false;  
            saveBtn.innerHTML = `  
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>  
                    <polyline points="17 21 17 13 7 13 7 21"/>  
                    <polyline points="7 3 7 8 15 8"/>  
                </svg>  
                保存 (Ctrl+S)  
            `;  
        }  
    }  
      
    close() {  
        if (this.isDirty) {  
            window.dialogManager.showConfirm(  
                '有未保存的修改,确认关闭?',  
                () => this.destroy()  
            );  
        } else {  
            this.destroy();  
        }  
    }  
      
    destroy() {  
        if (this.themeObserver) {  
            this.themeObserver.disconnect();  
            this.themeObserver = null;  
        }  
        if (this.editor) {  
            this.editor.dispose();  
            this.editor = null;  
        }  
        if (this.dialog && this.dialog.parentNode) {  
            this.dialog.parentNode.removeChild(this.dialog);  
        }  
        this.dialog = null;  
        this.currentTemplate = null;  
        this.isDirty = false;  
    }  
}  
  
document.addEventListener('DOMContentLoaded', () => {  
    window.templateEditorDialog = new TemplateEditorDialog();  
});