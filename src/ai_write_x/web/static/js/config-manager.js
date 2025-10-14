class AIWriteXConfigManager {  
    constructor() {  
        this.apiEndpoint = '/api/config';  
        this.config = {};  
        this.uiConfig = this.loadUIConfig();  
        
        this.currentPanel = 'ui';  
        this.bindConfigNavigation();  

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
            this.populateUI();  
            this.showConfigPanel(this.currentPanel);  
            
            // 3. 通知主题管理器和窗口模式管理器  
            if (window.themeManager) {  
                window.themeManager.onConfigLoaded();  
            }  
            if (window.windowModeManager) {  
                window.windowModeManager.onConfigLoaded();  
            }  
        } catch (error) {  
            console.error('配置管理器初始化失败:', error);  
        }  
    } 

    bindConfigNavigation() {  
        document.querySelectorAll('.config-nav-link').forEach(link => {  
            link.addEventListener('click', (e) => {  
                e.preventDefault();  
                const configType = link.dataset.config;  
                this.showConfigPanel(configType);  
            });  
        });  
    }  
      
    showConfigPanel(panelType) {  
        // 隐藏所有配置面板  
        document.querySelectorAll('.config-panel').forEach(panel => {  
            panel.classList.remove('active');  
        });  
          
        // 显示目标面板  
        const targetPanel = document.getElementById(`config-${panelType}`);  
        if (targetPanel) {  
            targetPanel.classList.add('active');  
        }  
          
        // 更新导航状态  
        document.querySelectorAll('.config-nav-item').forEach(item => {  
            item.classList.remove('active');  
        });  
          
        const activeNavItem = document.querySelector(`[data-config="${panelType}"]`).parentElement;  
        activeNavItem.classList.add('active');  
          
        this.currentPanel = panelType;  
    }  

    // UI配置管理（localStorage）  
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
            // 如果传入的是完整配置,直接使用;否则合并  
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

    // 主题相关方法  
    getTheme() {  
        return this.uiConfig.theme;  
    }  
      
    setTheme(theme) {  
        return this.saveUIConfig({ theme: theme });  
    }  
      
    // 窗口模式相关方法  
    getWindowMode() {  
        return this.uiConfig.windowMode;  
    }  
      
    setWindowMode(mode) {  
        return this.saveUIConfig({ windowMode: mode });  
    }  
      
    // 后端配置管理（API）  
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
            return false;  
        }  
    }  
      
    async saveConfig(updates) {  
        try {  
            const response = await fetch(this.apiEndpoint, {  
                method: 'POST',  
                headers: {  
                    'Content-Type': 'application/json',  
                },  
                body: JSON.stringify(updates)  
            });  
              
            if (!response.ok) {  
                throw new Error(`HTTP ${response.status}`);  
            }  
              
            const result = await response.json();  
            if (result.success) {  
                // 更新本地配置  
                this.config = { ...this.config, ...updates };  
                return true;  
            } else {  
                throw new Error(result.message || '保存失败');  
            }  
        } catch (error) {  
            return false;  
        }  
    }  
      
    populateUI() {  
        // 填充API配置  
        if (this.config.api) {  
            const apiTypeSelect = document.querySelector('select[name="api_type"]');  
            if (apiTypeSelect) {  
                apiTypeSelect.value = this.config.api.api_type || 'OpenRouter';  
            }  
        }  
        
        // 填充微信配置  
        if (this.config.wechat && this.config.wechat.credentials) {  
            this.config.wechat.credentials.forEach((cred, index) => {  
                const appidInput = document.querySelector(`input[name="wechat_appid_${index}"]`);  
                const secretInput = document.querySelector(`input[name="wechat_secret_${index}"]`);  
                
                if (appidInput) appidInput.value = cred.appid || '';  
                if (secretInput) secretInput.value = cred.appsecret || '';  
            });  
        }  
    
        // 填充界面配置 - 主题选择器  
        const themeSelector = document.getElementById('theme-selector');  
        if (themeSelector) {  
            themeSelector.value = this.getTheme();  
            themeSelector.addEventListener('change', (e) => {  
                // 只更新内存中的配置,不保存  
                this.uiConfig.theme = e.target.value;  
                // 触发主题管理器应用主题(不保存)  
                if (window.themeManager) {  
                    window.themeManager.applyTheme(e.target.value, false);  
                }  
            });  
        }  
        
        // 填充界面配置 - 窗口模式选择器  
        const windowModeSelector = document.getElementById('window-mode-selector');  
        if (windowModeSelector) {  
            windowModeSelector.value = this.getWindowMode();  
            windowModeSelector.addEventListener('change', (e) => {  
                // 只更新内存中的配置,不保存  
                this.uiConfig.windowMode = e.target.value;  
                // 触发窗口模式管理器应用模式(不保存)  
                if (window.windowModeManager) {  
                    window.windowModeManager.applyMode(e.target.value);  
                }  
            });  
        }  
    
        // 保存按钮 - 显示保存结果提示  
        const saveUIConfigBtn = document.getElementById('save-ui-config');  
        if (saveUIConfigBtn) {  
            saveUIConfigBtn.addEventListener('click', async () => {                  
                const success = await this.saveUIConfig(this.uiConfig);  
            
                if (success) {  
                    if (window.app && window.app.showNotification) {  
                        window.app.showNotification('界面设置已保存', 'success');  
                    }
                } else {  
                    if (window.app && window.app.showNotification) {  
                        window.app.showNotification('保存界面设置失败', 'error');  
                    }
                }  
            });  
        }
        
        // 恢复默认按钮 - 只在窗口模式改变时显示重启提示  
        const resetUIConfigBtn = document.getElementById('reset-ui-config');  
        if (resetUIConfigBtn) {  
            resetUIConfigBtn.addEventListener('click', async () => {  
                // 记录旧的窗口模式  
                const oldWindowMode = this.uiConfig.windowMode;  
                
                // 重置为默认配置  
                this.uiConfig = { theme: 'light', windowMode: 'STANDARD' };  
                
                // 更新UI显示  
                const themeSelector = document.getElementById('theme-selector');  
                const windowModeSelector = document.getElementById('window-mode-selector');  
                if (themeSelector) themeSelector.value = 'light';  
                if (windowModeSelector) windowModeSelector.value = 'STANDARD';  
                
                // 应用主题和窗口模式(不保存)  
                if (window.themeManager) window.themeManager.applyTheme('light', false);  
                if (window.windowModeManager) window.windowModeManager.applyMode('STANDARD');  
                
                // 保存到后端  
                const success = await this.saveUIConfig(this.uiConfig);  
                
                if (success) {  
                    // 只在窗口模式与默认不同时显示重启提示  
                    if (oldWindowMode !== 'STANDARD') {  
                        if (window.windowModeManager) {  
                            window.windowModeManager.showRestartNotification();  
                        }  
                    }  
                } else {  
                    // 保存失败时显示错误提示  
                    if (window.app && window.app.showNotification) {  
                        window.app.showNotification('恢复默认设置失败', 'error');  
                    }  
                }  
            });  
        } 
    }
      
    // 获取当前配置  
    getConfig() {  
        return this.config;  
    }  
      
    // 更新特定配置项  
    async updateConfigItem(key, value) {  
        const updateData = {};  
        updateData[key] = value;  
          
        try {  
            await this.saveConfig(updateData);  
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

// 模板使用状态切换  
document.getElementById('use-template').addEventListener('change', (e) => {  
    const isEnabled = e.target.checked;  
    document.getElementById('template-category').disabled = !isEnabled;  
    document.getElementById('template').disabled = !isEnabled;  
});  
  
// 文章格式变化处理  
document.getElementById('article-format').addEventListener('change', (e) => {  
    const formatPublishCheckbox = document.getElementById('format-publish');  
    formatPublishCheckbox.disabled = e.target.value === 'html';  
});