// AIWriteX 主JavaScript文件  
  
class AIWriteXApp {  
    constructor() {  
        this.ws = null;  
        this.currentView = 'creative-workshop';  
        this.isGenerating = false;  
        this.config = {};  
          
        this.init();  
    }  
      
    init() {  
        this.setupEventListeners();  
        this.connectWebSocket();  
        this.loadConfig();  
        this.showView(this.currentView);  
    }  
      
    setupEventListeners() {  
        // 导航菜单点击事件  
        document.querySelectorAll('.nav-link').forEach(link => {  
            link.addEventListener('click', (e) => {  
                e.preventDefault();  
                const view = link.dataset.view;  
                this.showView(view);  
            });  
        });  
          
        // 生成按钮事件  
        const generateBtn = document.getElementById('generate-btn');  
        if (generateBtn) {  
            generateBtn.addEventListener('click', () => this.startGeneration());  
        }  
          
        // 停止按钮事件  
        const stopBtn = document.getElementById('stop-btn');  
        if (stopBtn) {  
            stopBtn.addEventListener('click', () => this.stopGeneration());  
        }  
          
        // 配置保存事件  
        const saveConfigBtn = document.getElementById('save-config-btn');  
        if (saveConfigBtn) {  
            saveConfigBtn.addEventListener('click', () => this.saveConfig());  
        }  
          
        // 维度滑块事件  
        document.querySelectorAll('.dimension-slider').forEach(slider => {  
            slider.addEventListener('input', (e) => {  
                this.updateDimensionValue(e.target);  
            });  
        });  
    }  
      
    connectWebSocket() {  
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';  
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;  
          
        this.ws = new WebSocket(wsUrl);  
          
        this.ws.onopen = () => {  
            console.log('WebSocket连接已建立');  
            this.updateConnectionStatus(true);  
        };  
          
        this.ws.onmessage = (event) => {  
            const data = JSON.parse(event.data);  
            this.addLogEntry(data);  
        };  
          
        this.ws.onclose = () => {  
            console.log('WebSocket连接已断开');  
            this.updateConnectionStatus(false);  
            // 3秒后重连  
            setTimeout(() => this.connectWebSocket(), 3000);  
        };  
          
        this.ws.onerror = (error) => {  
            console.error('WebSocket错误:', error);  
            this.updateConnectionStatus(false);  
        };  
          
        // 发送心跳  
        setInterval(() => {  
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {  
                this.ws.send('ping');  
            }  
        }, 30000);  
    }  
      
    updateConnectionStatus(connected) {  
        const indicator = document.querySelector('.status-indicator');  
        if (indicator) {  
            indicator.style.backgroundColor = connected ?   
                'var(--success-color)' : 'var(--error-color)';  
        }  
    }  
      
    addLogEntry(logData) {  
        const logPanel = document.getElementById('log-panel');  
        if (!logPanel) return;  
          
        const entry = document.createElement('div');  
        entry.className = `log-entry ${logData.type}`;  
          
        const timestamp = new Date(logData.timestamp * 1000).toLocaleTimeString();  
        entry.innerHTML = `  
            <span class="log-timestamp">[${timestamp}]</span>  
            <span class="log-message">${this.escapeHtml(logData.message)}</span>  
        `;  
          
        logPanel.appendChild(entry);  
        logPanel.scrollTop = logPanel.scrollHeight;  
          
        // 限制日志条数  
        const entries = logPanel.querySelectorAll('.log-entry');  
        if (entries.length > 1000) {  
            entries[0].remove();  
        }  
    }  
      
    escapeHtml(text) {  
        const div = document.createElement('div');  
        div.textContent = text;  
        return div.innerHTML;  
    }  
      
    showView(viewName) {  
        // 更新导航状态  
        document.querySelectorAll('.nav-link').forEach(link => {  
            link.classList.remove('active');  
            if (link.dataset.view === viewName) {  
                link.classList.add('active');  
            }  
        });  
          
        // 显示对应视图  
        document.querySelectorAll('.view-content').forEach(view => {  
            view.style.display = 'none';  
        });  
          
        const targetView = document.getElementById(`${viewName}-view`);  
        if (targetView) {  
            targetView.style.display = 'block';  
        }  
          
        this.currentView = viewName;  
          
        // 根据视图加载相应数据  
        switch (viewName) {  
            case 'creative-workshop':  
                this.loadDimensionalConfig();  
                break;  
            case 'article-manager':  
                this.loadArticles();  
                break;  
            case 'config-manager':  
                this.loadConfig();  
                break;  
        }  
    }  
      
    async startGeneration() {  
        if (this.isGenerating) return;  
          
        const topic = document.getElementById('topic-input')?.value || '';  
        const platform = document.getElementById('platform-select')?.value || '';  
          
        const requestData = {  
            topic: topic,  
            platform: platform,  
            urls: [],  
            reference_ratio: 0.0,  
            custom_template_category: '',  
            custom_template: ''  
        };  
          
        try {  
            this.setGeneratingState(true);  
              
            const response = await fetch('/api/content/generate', {  
                method: 'POST',  
                headers: {  
                    'Content-Type': 'application/json',  
                },  
                body: JSON.stringify(requestData)  
            });  
              
            if (!response.ok) {  
                throw new Error(`HTTP error! status: ${response.status}`);  
            }  
              
            const result = await response.json();  
            this.showNotification('任务启动成功', 'success');  
              
        } catch (error) {  
            console.error('启动生成任务失败:', error);  
            this.showNotification(`启动失败: ${error.message}`, 'error');  
            this.setGeneratingState(false);  
        }  
    }  
      
    async stopGeneration() {  
        try {  
            const response = await fetch('/api/content/stop', {  
                method: 'POST'  
            });  
              
            if (response.ok) {  
                this.setGeneratingState(false);  
                this.showNotification('任务已停止', 'info');  
            }  
        } catch (error) {  
            console.error('停止任务失败:', error);  
            this.showNotification(`停止失败: ${error.message}`, 'error');  
        }  
    }  
      
    setGeneratingState(isGenerating) {  
        this.isGenerating = isGenerating;  
          
        const generateBtn = document.getElementById('generate-btn');  
        const stopBtn = document.getElementById('stop-btn');  
          
        if (generateBtn) {  
            generateBtn.disabled = isGenerating;  
            generateBtn.textContent = isGenerating ? '生成中...' : '开始创作';  
        }  
          
        if (stopBtn) {  
            stopBtn.disabled = !isGenerating;  
        }  
    }  
      
    async loadConfig() {  
        try {  
            const response = await fetch('/api/config/');  
            if (response.ok) {  
                const result = await response.json();  
                this.config = result.data;  
                this.updateConfigUI();  
            }  
        } catch (error) {  
            console.error('加载配置失败:', error);  
            this.showNotification('加载配置失败', 'error');  
        }  
    }  
      
    async saveConfig() {  
        try {  
            const response = await fetch('/api/config/', {  
                method: 'POST',  
                headers: {  
                    'Content-Type': 'application/json',  
                },  
                body: JSON.stringify({  
                    config_data: this.config  
                })  
            });  
              
            if (response.ok) {  
                this.showNotification('配置保存成功', 'success');  
            } else {  
                throw new Error('保存失败');  
            }  
        } catch (error) {  
            console.error('保存配置失败:', error);  
            this.showNotification('配置保存失败', 'error');  
        }  
    }  
      
    async loadDimensionalConfig() {  
        try {  
            const response = await fetch('/api/config/dimensional_creative');  
            if (response.ok) {  
                const result = await response.json();  
                this.updateDimensionalUI(result.data);  
            }  
        } catch (error) {  
            console.error('加载维度配置失败:', error);  
        }  
    }  
      
    updateDimensionValue(slider) {  
        const value = slider.value;  
        const valueDisplay = slider.parentElement.querySelector('.slider-value');  
        if (valueDisplay) {  
            valueDisplay.textContent = value;  
        }  
          
        // 实时更新配置  
        const dimensionName = slider.dataset.dimension;  
        if (dimensionName && this.config.dimensional_creative) {  
            this.config.dimensional_creative[dimensionName] = parseFloat(value);  
        }  
    }  
      
    updateConfigUI() {  
        // 更新API配置  
        const apiTypeSelect = document.getElementById('api-type-select');  
        if (apiTypeSelect && this.config.api) {  
            apiTypeSelect.value = this.config.api.api_type || '';  
        }  
          
        // 更新微信配置  
        const wechatAppId = document.getElementById('wechat-appid');  
        if (wechatAppId && this.config.wechat && this.config.wechat.credentials[0]) {  
            wechatAppId.value = this.config.wechat.credentials[0].appid || '';  
        }  
          
        // 更新模板配置  
        const useTemplate = document.getElementById('use-template');  
        if (useTemplate && this.config.template) {  
            useTemplate.checked = this.config.template.use_template || false;  
        }  
    }  
      
    updateDimensionalUI(dimensionalConfig) {  
        // 更新维度滑块  
        Object.entries(dimensionalConfig).forEach(([key, value]) => {  
            const slider = document.querySelector(`[data-dimension="${key}"]`);  
            if (slider) {  
                slider.value = value;  
                this.updateDimensionValue(slider);  
            }  
        });  
    }  
      
    async loadArticles() {  
        // 加载文章列表  
        try {  
            const response = await fetch('/api/articles/');  
            if (response.ok) {  
                const articles = await response.json();  
                this.updateArticleGrid(articles);  
            }  
        } catch (error) {  
            console.error('加载文章失败:', error);  
        }  
    }  
      
    updateArticleGrid(articles) {  
        const grid = document.getElementById('article-grid');  
        if (!grid) return;  
          
        grid.innerHTML = '';  
          
        articles.forEach(article => {  
            const card = this.createArticleCard(article);  
            grid.appendChild(card);  
        });  
    }  
      
    createArticleCard(article) {  
        const card = document.createElement('div');  
        card.className = 'article-card';  
        card.innerHTML = `  
            <div class="article-thumbnail">  
                <span>📄</span>  
            </div>  
            <div class="article-content">  
                <h3 class="article-title">${article.title}</h3>  
                <div class="article-meta">  
                    <span>${article.date}</span>  
                    <span>${article.platform}</span>  
                </div>  
                <div class="article-actions">  
                    <button class="action-btn primary" onclick="app.previewArticle('${article.id}')">预览</button>  
                    <button class="action-btn" onclick="app.editArticle('${article.id}')">编辑</button>  
                    <button class="action-btn" onclick="app.deleteArticle('${article.id}')">删除</button>  
                </div>  
            </div>  
        `;  
        return card;  
    }  
      
    showNotification(message, type = 'info') {  
        const notification = document.createElement('div');  
        notification.className = `notification ${type}`;  
        notification.innerHTML = `  
            <div class="notification-content">  
                <span>${message}</span>  
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>  
            </div>  
        `;  
          
        document.body.appendChild(notification);  
          
        // 3秒后自动移除  
        setTimeout(() => {  
            if (notification.parentElement) {  
                notification.remove();  
            }  
        }, 3000);  
    }  
      
    previewArticle(articleId) {  
        // 预览文章  
        console.log('预览文章:', articleId);  
    }  
      
    editArticle(articleId) {  
        // 编辑文章  
        console.log('编辑文章:', articleId);  
    }  
      
    deleteArticle(articleId) {  
        // 删除文章  
        if (confirm('确定要删除这篇文章吗？')) {  
            console.log('删除文章:', articleId);  
        }  
    }  
}  
  
// 初始化应用  
let app;  
document.addEventListener('DOMContentLoaded', () => {  
    app = new AIWriteXApp();  
});