class AIWriteXConfigManager {  
    constructor() {  
        this.apiEndpoint = '/api/config';  
        this.config = {};  
        this.uiConfig = this.loadUIConfig();  
        this.init();  
    }  
      
    async init() {  
        try {  
            await this.loadConfig();  
            this.populateUI();  
        } catch (error) {  
            console.error('配置管理器初始化失败:', error);  
        }  
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