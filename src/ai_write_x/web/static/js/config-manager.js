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
            await this.loadConfig();  
            this.populateUI();
            this.showConfigPanel(this.currentPanel);   
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
    
    saveUIConfig(updates) {  
        try {  
            const currentConfig = this.loadUIConfig();  
            const newConfig = { ...currentConfig, ...updates };  
            localStorage.setItem('aiwritex_ui_config', JSON.stringify(newConfig));  
            this.uiConfig = newConfig;  
            return true;  
        } catch (e) {  
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

        // 填充界面配置  
        const themeSelector = document.getElementById('theme-selector');  
        if (themeSelector) {  
            themeSelector.value = this.getTheme();  
            themeSelector.addEventListener('change', (e) => {  
                this.setTheme(e.target.value);  
                // 触发主题管理器更新  
                if (window.themeManager) {  
                    window.themeManager.applyTheme(e.target.value);  
                }  
            });  
        }  
        
        const windowModeSelector = document.getElementById('window-mode-selector');  
        if (windowModeSelector) {  
            windowModeSelector.value = this.getWindowMode();  
            windowModeSelector.addEventListener('change', (e) => {  
                this.setWindowMode(e.target.value);  
                // 触发窗口模式管理器更新  
                if (window.windowModeManager) {  
                    window.windowModeManager.applyMode(e.target.value);  
                }  
            });  
        } 

        const saveUIConfigBtn = document.getElementById('save-ui-config');  
        if (saveUIConfigBtn) {  
            saveUIConfigBtn.addEventListener('click', () => {  
                // UI配置已经通过change事件自动保存，这里可以显示成功提示  
                console.log('界面配置已保存');  
            });  
        }  
        
        const resetUIConfigBtn = document.getElementById('reset-ui-config');  
        if (resetUIConfigBtn) {  
            resetUIConfigBtn.addEventListener('click', () => {  
                // 重置为默认配置  
                this.saveUIConfig({ theme: 'light', windowMode: 'STANDARD' });  
                // 更新UI显示  
                const themeSelector = document.getElementById('theme-selector');  
                const windowModeSelector = document.getElementById('window-mode-selector');  
                if (themeSelector) themeSelector.value = 'light';  
                if (windowModeSelector) windowModeSelector.value = 'STANDARD';  
                
                // 应用主题和窗口模式  
                if (window.themeManager) window.themeManager.applyTheme('light');  
                if (window.windowModeManager) window.windowModeManager.applyMode('STANDARD');  
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