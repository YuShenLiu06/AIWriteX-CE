class AIWriteXConfigManager {    
    constructor() {    
        this.apiEndpoint = '/api/config';    
        this.config = {};    
        this.uiConfig = this.loadUIConfig();    
          
        this.currentPanel = 'ui';  
        this.init();   
    }    
        
    async init() {    
        try {    
            // 1. 从后端加载 UI 配置    
            const uiResponse = await fetch('/api/config/ui-config');    
            if (uiResponse.ok) {    
                const uiConfig = await uiResponse.json();    
                localStorage.setItem('aiwritex_ui_config', JSON.stringify(uiConfig));    
                this.uiConfig = uiConfig;    
            }    
            
            // 2. 加载业务配置    
            await this.loadConfig();    
            
            // 2.5. 加载动态选项数据(新增)  
            await this.loadDynamicOptions();  
            
            // 3. 绑定事件监听器(只绑定一次)    
            this.bindEventListeners();    
            
            // 4. 填充UI(只负责填充值,不绑定事件)    
            this.populateUI();    
            this.showConfigPanel(this.currentPanel);    
            
            // 5. 通知主题管理器和窗口模式管理器    
            if (window.themeManager) {    
                window.themeManager.onConfigLoaded();    
            }    
            if (window.windowModeManager) {    
                window.windowModeManager.onConfigLoaded();    
            }    
            
            // 6. 最后绑定导航事件(确保DOM已加载)    
            this.bindConfigNavigation();    
        } catch (error) {    
            console.error('配置管理器初始化失败:', error);    
        }    
    }  
    
    bindEventListeners() {          
        // 主题选择器  
        const themeSelector = document.getElementById('theme-selector');  
        if (themeSelector) {  
            themeSelector.addEventListener('change', (e) => {  
                this.uiConfig.theme = e.target.value;  
                if (window.themeManager) {  
                    window.themeManager.applyTheme(e.target.value, false);  
                }  
            });  
        }  
        
        // 窗口模式选择器  
        const windowModeSelector = document.getElementById('window-mode-selector');  
        if (windowModeSelector) {  
            windowModeSelector.addEventListener('change', (e) => {  
                this.uiConfig.windowMode = e.target.value;  
                if (window.windowModeManager) {  
                    window.windowModeManager.applyMode(e.target.value);  
                }  
            });  
        }  
        
        // 保存按钮  
        const saveUIConfigBtn = document.getElementById('save-ui-config');  
        if (saveUIConfigBtn) {  
            saveUIConfigBtn.addEventListener('click', async () => {  
                const success = await this.saveUIConfig(this.uiConfig);  
                if (success) {  
                    window.app?.showNotification('界面设置已保存', 'success');  
                } else {  
                    window.app?.showNotification('保存界面设置失败', 'error');  
                }  
            });  
        }  
        
        // 恢复默认按钮  
        const resetUIConfigBtn = document.getElementById('reset-ui-config');  
        if (resetUIConfigBtn) {  
            resetUIConfigBtn.addEventListener('click', async () => {  
                const oldWindowMode = this.uiConfig.windowMode;  
                this.uiConfig = { theme: 'light', windowMode: 'STANDARD' };  
                
                // 更新UI显示  
                const themeSelector = document.getElementById('theme-selector');  
                const windowModeSelector = document.getElementById('window-mode-selector');  
                if (themeSelector) themeSelector.value = 'light';  
                if (windowModeSelector) windowModeSelector.value = 'STANDARD';  
                
                if (window.themeManager) window.themeManager.applyTheme('light', false);  
                if (window.windowModeManager) window.windowModeManager.applyMode('STANDARD');  
                
                const success = await this.saveUIConfig(this.uiConfig);  
                if (success && oldWindowMode !== 'STANDARD') {  
                    window.windowModeManager?.showRestartNotification();  
                }  
            });  
        }  
        
        // 基础设置保存按钮  
        const saveBaseConfigBtn = document.getElementById('save-base-config');  
        if (saveBaseConfigBtn) {  
            saveBaseConfigBtn.addEventListener('click', async () => {  
                const success = await this.saveConfig();  
                window.app?.showNotification(  
                    success ? '基础设置已保存' : '保存基础设置失败',  
                    success ? 'success' : 'error'  
                );  
            });  
        }  
        
        // 基础设置恢复默认按钮  
        const resetBaseConfigBtn = document.getElementById('reset-base-config');  
        if (resetBaseConfigBtn) {  
            resetBaseConfigBtn.addEventListener('click', async () => {  
                const success = await this.resetToDefault();  
                window.app?.showNotification(  
                    success ? '已恢复默认设置(未保存,点击保存按钮持久化)' : '恢复默认设置失败',  
                    success ? 'info' : 'error'  
                );  
            });  
        }

        // 文章格式  
        const articleFormatSelect = document.getElementById('article-format');  
        if (articleFormatSelect) {  
            articleFormatSelect.addEventListener('change', async (e) => {  
                await this.updateConfig({ article_format: e.target.value });  
                
                // 联动禁用逻辑  
                const formatPublishCheckbox = document.getElementById('format-publish');  
                if (formatPublishCheckbox) {  
                    formatPublishCheckbox.disabled = e.target.value === 'html';  
                }  
            });  
        }  
        
        // 自动发布  
        const autoPublishCheckbox = document.getElementById('auto-publish');  
        if (autoPublishCheckbox) {  
            autoPublishCheckbox.addEventListener('change', async (e) => {  
                await this.updateConfig({ auto_publish: e.target.checked });  
            });  
        }  
        
        // 格式化发布  
        const formatPublishCheckbox = document.getElementById('format-publish');  
        if (formatPublishCheckbox) {  
            formatPublishCheckbox.addEventListener('change', async (e) => {  
                await this.updateConfig({ format_publish: e.target.checked });  
            });  
        }  
        
        // 使用模板  
        const useTemplateCheckbox = document.getElementById('use-template');  
        if (useTemplateCheckbox) {  
            useTemplateCheckbox.addEventListener('change', async (e) => {  
                await this.updateConfig({ use_template: e.target.checked });  
                
                // 联动禁用逻辑  
                const templateCategorySelect = document.getElementById('template-category');  
                const templateSelect = document.getElementById('template');  
                if (templateCategorySelect) templateCategorySelect.disabled = !e.target.checked;  
                if (templateSelect) templateSelect.disabled = !e.target.checked;  
            });  
        }  
        
        // 模板分类(修改为级联加载)  
        const templateCategorySelect = document.getElementById('template-category');    
        if (templateCategorySelect) {    
            templateCategorySelect.addEventListener('change', async (e) => {    
                const category = e.target.value;  
                
                // 更新配置  
                await this.updateConfig({ template_category: category });    
                
                // 级联加载模板列表  
                const templateSelect = document.getElementById('template');  
                if (templateSelect) {  
                    // 清空现有选项  
                    templateSelect.innerHTML = '';  
                    
                    // 添加"随机模板"选项  
                    const randomOption = document.createElement('option');  
                    randomOption.value = '';  
                    randomOption.textContent = '随机模板';  
                    templateSelect.appendChild(randomOption);  
                    
                    // 加载新分类的模板  
                    if (category) {  
                        const templates = await this.loadTemplatesByCategory(category);  
                        templates.forEach(template => {  
                            const option = document.createElement('option');  
                            option.value = template;  
                            option.textContent = template;  
                            templateSelect.appendChild(option);  
                        });  
                    }  
                    
                    // 重置为"随机模板"  
                    templateSelect.value = '';  
                }  
            });    
        }  
        
        // 模板选择  
        const templateSelect = document.getElementById('template');  
        if (templateSelect) {  
            templateSelect.addEventListener('change', async (e) => {  
                await this.updateConfig({ template: e.target.value });  
            });  
        }  
        
        // 压缩模板  
        const useCompressCheckbox = document.getElementById('use-compress');  
        if (useCompressCheckbox) {  
            useCompressCheckbox.addEventListener('change', async (e) => {  
                await this.updateConfig({ use_compress: e.target.checked });  
            });  
        }  
        
        // 最大搜索结果  
        const maxSearchResultsInput = document.getElementById('max-search-results');  
        if (maxSearchResultsInput) {  
            maxSearchResultsInput.addEventListener('change', async (e) => {  
                await this.updateConfig({ aiforge_search_max_results: parseInt(e.target.value) });  
            });  
        }  
        
        // 最小搜索结果  
        const minSearchResultsInput = document.getElementById('min-search-results');  
        if (minSearchResultsInput) {  
            minSearchResultsInput.addEventListener('change', async (e) => {  
                await this.updateConfig({ aiforge_search_min_results: parseInt(e.target.value) });  
            });  
        }  
        
        // 最小文章字数  
        const minArticleLenInput = document.getElementById('min-article-len');  
        if (minArticleLenInput) {  
            minArticleLenInput.addEventListener('change', async (e) => {  
                await this.updateConfig({ min_article_len: parseInt(e.target.value) });  
            });  
        }  
        
        // 最大文章字数  
        const maxArticleLenInput = document.getElementById('max-article-len');  
        if (maxArticleLenInput) {  
            maxArticleLenInput.addEventListener('change', async (e) => {  
                await this.updateConfig({ max_article_len: parseInt(e.target.value) });  
            });  
        }  
    }  
    
    populateUI() {  
        // ========== 填充发布平台 ==========  
        const publishPlatformSelect = document.getElementById('publish-platform');  
        if (publishPlatformSelect && this.config.publish_platform) {  
            publishPlatformSelect.value = this.config.publish_platform;  
        }  
        
        // ========== 填充文章格式 ==========  
        const articleFormatSelect = document.getElementById('article-format');  
        if (articleFormatSelect && this.config.article_format) {  
            articleFormatSelect.value = this.config.article_format;  
        }  
        
        // ========== 填充自动发布 ==========  
        const autoPublishCheckbox = document.getElementById('auto-publish');  
        if (autoPublishCheckbox && this.config.auto_publish !== undefined) {  
            autoPublishCheckbox.checked = this.config.auto_publish;  
        }  
        
        // ========== 填充格式化发布 ==========  
        const formatPublishCheckbox = document.getElementById('format-publish');  
        if (formatPublishCheckbox && this.config.format_publish !== undefined) {  
            formatPublishCheckbox.checked = this.config.format_publish;  
            formatPublishCheckbox.disabled = this.config.article_format === 'html';  
        }  
        
        // ========== 填充使用模板 ==========  
        const useTemplateCheckbox = document.getElementById('use-template');  
        if (useTemplateCheckbox && this.config.use_template !== undefined) {  
            useTemplateCheckbox.checked = this.config.use_template;  
        }  
        
        // ========== 填充模板分类 ==========    
        const templateCategorySelect = document.getElementById('template-category');    
        if (templateCategorySelect) {    
            templateCategorySelect.value = this.config.template_category || '';    
            templateCategorySelect.disabled = !this.config.use_template;  
            
            // 触发级联加载模板列表  
            if (this.config.template_category) {  
                this.loadTemplatesByCategory(this.config.template_category).then(templates => {  
                    const templateSelect = document.getElementById('template');  
                    if (templateSelect) {  
                        // 清空现有选项  
                        templateSelect.innerHTML = '';  
                        
                        // 添加"随机模板"选项  
                        const randomOption = document.createElement('option');  
                        randomOption.value = '';  
                        randomOption.textContent = '随机模板';  
                        templateSelect.appendChild(randomOption);  
                        
                        // 添加模板选项  
                        templates.forEach(template => {  
                            const option = document.createElement('option');  
                            option.value = template;  
                            option.textContent = template;  
                            templateSelect.appendChild(option);  
                        });  
                        
                        // 设置当前选中的模板  
                        templateSelect.value = this.config.template || '';  
                        templateSelect.disabled = !this.config.use_template;  
                    }  
                });  
            }  
        }  
        
        const useCompressCheckbox = document.getElementById('use-compress');  
        if (useCompressCheckbox && this.config.use_compress !== undefined) {  
            useCompressCheckbox.checked = this.config.use_compress;  
        }
        
        // ========== 填充模板选择 ==========  
        const templateSelect = document.getElementById('template');  
        if (templateSelect) {  
            templateSelect.value = this.config.template || '';  
            // 关键:根据use_template设置禁用状态  
            templateSelect.disabled = !this.config.use_template;  
            console.log('设置template:', templateSelect.value);  
            console.log('template禁用状态:', templateSelect.disabled);  
        }    
        
        // ========== 6. 填充搜索数量配置 ==========  
        const maxSearchResultsInput = document.getElementById('max-search-results');  
        if (maxSearchResultsInput && this.config.aiforge_search_max_results !== undefined) {  
            maxSearchResultsInput.value = this.config.aiforge_search_max_results;  
        }  
        
        const minSearchResultsInput = document.getElementById('min-search-results');  
        if (minSearchResultsInput && this.config.aiforge_search_min_results !== undefined) {  
            minSearchResultsInput.value = this.config.aiforge_search_min_results;  
        }  
        
        // ========== 7. 填充文章长度配置 ==========  
        const minArticleLenInput = document.getElementById('min-article-len');  
        if (minArticleLenInput && this.config.min_article_len !== undefined) {  
            minArticleLenInput.value = this.config.min_article_len;  
        }  
        
        const maxArticleLenInput = document.getElementById('max-article-len');  
        if (maxArticleLenInput && this.config.max_article_len !== undefined) {  
            maxArticleLenInput.value = this.config.max_article_len;  
        }  
        
        // ========== 8. 填充界面配置 ==========  
        const themeSelector = document.getElementById('theme-selector');  
        if (themeSelector) {  
            themeSelector.value = this.getTheme();  
        }  
        
        const windowModeSelector = document.getElementById('window-mode-selector');  
        if (windowModeSelector) {  
            windowModeSelector.value = this.getWindowMode();  
        }  
    }

  
    bindConfigNavigation() {  
        const links = document.querySelectorAll('.nav-sublink');          
        links.forEach((link, index) => {  
            link.addEventListener('click', (e) => {  
                e.preventDefault();  
                const configType = link.dataset.config;  
                this.showConfigPanel(configType);  
            });  
        });  
    }    
        
    showConfigPanel(panelType) {  
        const configContent = document.querySelector('.config-content');  
        const targetPanel = document.getElementById(`config-${panelType}`);  
        
        // 关键:在任何DOM操作之前立即重置滚动位置  
        if (configContent) {  
            configContent.scrollTop = 0;  
        }  
        
        // 隐藏所有配置面板  
        document.querySelectorAll('.config-panel').forEach(panel => {  
            if (panel !== targetPanel) {  
                panel.classList.remove('active');  
                panel.style.display = 'none';  
            }  
        });  
        
        // 显示目标面板  
        if (targetPanel) {  
            targetPanel.style.display = 'block';  
            targetPanel.offsetHeight; // 强制重排  
            targetPanel.classList.add('active');  
        }  
        
        // 更新导航状态  
        document.querySelectorAll('.config-nav-item').forEach(item => {  
            item.classList.remove('active');  
        });  
        
        const activeNavItem = document.querySelector(`[data-config="${panelType}"]`)?.parentElement;  
        if (activeNavItem) {  
            activeNavItem.classList.add('active');  
        }  
        
        this.currentPanel = panelType;  
        
        this.populateUI();  
    }  
  
    // ========== UI配置管理(localStorage) ==========  
      
    loadUIConfig() {    
        try {    
            const saved = localStorage.getItem('aiwritex_ui_config');    
            const defaultConfig = {    
                theme: 'light',    
                windowMode: 'STANDARD'    
            };    
              
            if (saved) {    
                return { ...defaultConfig, ...JSON.parse(saved) };    
            }    
            return defaultConfig;    
        } catch (e) {    
            return { theme: 'light', windowMode: 'STANDARD' };    
        }    
    }    
      
    async saveUIConfig(updates) {    
        try {    
            const newConfig = updates.theme !== undefined && updates.windowMode !== undefined     
                ? updates     
                : { ...this.uiConfig, ...updates };    
              
            // 1. 保存到 localStorage    
            localStorage.setItem('aiwritex_ui_config', JSON.stringify(newConfig));    
            this.uiConfig = newConfig;    
              
            // 2. 同步到后端文件(持久化)    
            const response = await fetch('/api/config/ui-config', {    
                method: 'POST',    
                headers: { 'Content-Type': 'application/json' },    
                body: JSON.stringify(newConfig)    
            });    
              
            if (!response.ok) {    
                throw new Error('保存失败');    
            }    
              
            return true;    
        } catch (e) {    
            console.error('保存 UI 配置失败:', e);    
            return false;    
        }    
    }  
  
    getUIConfig() {    
        return this.uiConfig;    
    }  
  
    getTheme() {    
        return this.uiConfig.theme;    
    }    
        
    setTheme(theme) {    
        return this.saveUIConfig({ theme: theme });    
    }    
        
    getWindowMode() {    
        return this.uiConfig.windowMode;    
    }    
        
    setWindowMode(mode) {    
        return this.saveUIConfig({ windowMode: mode });    
    }    
        
    // ========== 业务配置管理(后端API) ==========  
      
    async loadConfig() {    
        try {    
            const response = await fetch(this.apiEndpoint);    
            if (!response.ok) {    
                throw new Error(`HTTP ${response.status}`);    
            }    
                
            const result = await response.json();    
            this.config = result.data;    
                
            return true;    
        } catch (error) {    
            console.error('加载配置失败:', error);  
            return false;    
        }    
    }

    // 加载动态选项数据  
    async loadDynamicOptions() {  
        try {  
            // 加载发布平台列表  
            const platformsResponse = await fetch('/api/config/platforms');  
            if (platformsResponse.ok) {  
                const result = await platformsResponse.json();  
                this.platforms = result.data;  
                this.populatePlatformOptions();  
            }  
            
            // 加载模板分类列表  
            const categoriesResponse = await fetch('/api/config/template-categories');  
            if (categoriesResponse.ok) {  
                const result = await categoriesResponse.json();  
                this.templateCategories = result.data;  
                this.populateTemplateCategoryOptions();  
            }  
        } catch (error) {  
            console.error('加载动态选项失败:', error);  
        }  
    }  
    
    // 填充发布平台选项  
    populatePlatformOptions() {  
        const publishPlatformSelect = document.getElementById('publish-platform');  
        if (!publishPlatformSelect || !this.platforms) return;  
        
        // 清空现有选项  
        publishPlatformSelect.innerHTML = '';  
        
        // 添加平台选项  
        this.platforms.forEach(platform => {  
            const option = document.createElement('option');  
            option.value = platform.value;  
            option.textContent = platform.label;  
            publishPlatformSelect.appendChild(option);  
        });  
        
        // 禁用选择器(只支持微信)  
        publishPlatformSelect.disabled = true;  
    }  
    
    // 填充模板分类选项  
    populateTemplateCategoryOptions() {  
        const templateCategorySelect = document.getElementById('template-category');  
        if (!templateCategorySelect || !this.templateCategories) return;  
        
        // 清空现有选项  
        templateCategorySelect.innerHTML = '';  
        
        // 添加"随机分类"选项  
        const randomOption = document.createElement('option');  
        randomOption.value = '';  
        randomOption.textContent = '随机分类';  
        templateCategorySelect.appendChild(randomOption);  
        
        // 添加分类选项  
        this.templateCategories.forEach(category => {  
            const option = document.createElement('option');  
            option.value = category;  
            option.textContent = category;  
            templateCategorySelect.appendChild(option);  
        });  
    }  
    
    // 加载指定分类的模板列表  
    async loadTemplatesByCategory(category) {  
        try {  
            if (!category || category === '随机分类') {  
                return [];  
            }  
            
            const response = await fetch(`/api/config/templates/${encodeURIComponent(category)}`);  
            if (!response.ok) {  
                throw new Error(`HTTP ${response.status}`);  
            }  
            
            const result = await response.json();  
            return result.data || [];  
        } catch (error) {  
            console.error('加载模板列表失败:', error);  
            return [];  
        }  
    }    
    // 更新配置(仅内存,不保存文件)  
    async updateConfig(updates) {    
        try {    
            const response = await fetch(this.apiEndpoint, {    
                method: 'PATCH',    
                headers: { 'Content-Type': 'application/json' },    
                body: JSON.stringify({ config_data: updates })  // ✅ 包装在config_data中  
            });    
                
            if (!response.ok) {    
                throw new Error(`HTTP ${response.status}`);    
            }    
                
            // 同步更新前端内存    
            this.deepMerge(this.config, updates);    
                
            return true;    
        } catch (error) {    
            console.error('更新配置失败:', error);    
            return false;    
        }    
    }  
      
    // 保存配置到文件  
    async saveConfig() {  
        try {  
            const response = await fetch(this.apiEndpoint, {  
                method: 'POST',  
                headers: { 'Content-Type': 'application/json' }  
            });  
              
            if (!response.ok) {  
                throw new Error(`HTTP ${response.status}`);  
            }  
              
            const result = await response.json();  
            return result.status === 'success';  
        } catch (error) {  
            console.error('保存配置失败:', error);  
            return false;  
        }  
    }  
      
    // 恢复默认配置(仅更新内存,不保存)  
    async resetToDefault() {  
        try {  
            const response = await fetch(`${this.apiEndpoint}/default`);  
            if (!response.ok) {  
                throw new Error('获取默认配置失败');  
            }  
              
            const result = await response.json();  
              
            // 更新后端内存  
            await this.updateConfig(result.data);  
              
            // 更新前端内存  
            this.config = result.data;  
              
            // 刷新UI  
            this.populateUI();  
              
            return true;  
        } catch (error) {  
            console.error('恢复默认配置失败:', error);  
            return false;  
        }  
    }  
      
    // 深度合并辅助方法  
    deepMerge(target, source) {  
        for (const key in source) {  
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {  
                if (!target[key]) target[key] = {};  
                this.deepMerge(target[key], source[key]);  
            } else {  
                target[key] = source[key];  
            }  
        }  
    }
        
    // 获取当前配置    
    getConfig() {    
        return this.config;    
    }    
        
    // 更新特定配置项(仅内存)  
    async updateConfigItem(key, value) {    
        const updateData = {};    
        updateData[key] = value;    
            
        try {    
            await this.updateConfig(updateData);    
            return true;    
        } catch (error) {    
            console.error(`更新配置项 ${key} 失败:`, error);    
            return false;    
        }    
    }    
}    
    
// 全局配置管理器实例    
let configManager;    
    
// 初始化配置管理器    
document.addEventListener('DOMContentLoaded', async () => {    
    configManager = new AIWriteXConfigManager();    
    window.configManager = configManager;    
});