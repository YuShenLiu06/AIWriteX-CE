class WindowModeManager {    
    constructor() {    
        this.modes = {    
            STANDARD: { width: 1400, height: 900, name: "标准模式" },    
            MAXIMIZED: { maximized: true, name: "最大化模式" }    
        };              
        this.waitForConfigManager();    
    }    
        
    init() {    
        this.currentMode = this.loadSavedMode();    
        this.bindModeSelector();    
        this.applyMode(this.currentMode);    
    }    
        
    waitForConfigManager() {    
        if (window.configManager) {    
            this.configManager = window.configManager;    
            this.init();    
        } else {    
            setTimeout(() => this.waitForConfigManager(), 50);    
        }    
    }    
        
    loadSavedMode() {              
        try {    
            // 必须从配置管理器获取，无回退  
            if (this.configManager && this.configManager.getUIConfig) {    
                const uiConfig = this.configManager.getUIConfig();    
                return uiConfig.windowMode || 'STANDARD';    
            }    
            return 'STANDARD';    
        } catch (e) {    
            console.error('加载窗口模式失败:', e);    
            return 'STANDARD';    
        }    
    }    
        
    async saveMode(mode) {    
        try {    
            // 只保存到配置管理器，无备份  
            if (this.configManager && this.configManager.saveUIConfig) {    
                return await this.configManager.saveUIConfig({ windowMode: mode });    
            }    
            return false;    
        } catch (e) {    
            console.error('保存窗口模式失败:', e);    
            return false;    
        }    
    }    
            
    applyMode(mode) {  
        document.body.className = document.body.className.replace(/window-mode-\\w+/g, '');  
        document.body.classList.add(`window-mode-${mode.toLowerCase()}`);  
        document.body.setAttribute('data-window-mode', mode.toLowerCase());  
        
        const root = document.documentElement;  
        if (mode === 'STANDARD') {  
            root.style.setProperty('--window-width', '1400px');  
            root.style.setProperty('--window-height', '900px');  
            root.style.setProperty('--sidebar-width', '200px');   
            root.style.setProperty('--panel-width', '260px');    
        } else if (mode === 'MAXIMIZED') {  
            root.style.setProperty('--window-width', '100vw');  
            root.style.setProperty('--window-height', '100vh');  
            root.style.setProperty('--sidebar-width', '240px'); 
            root.style.setProperty('--panel-width', '300px');  
        }  
        this.currentMode = mode;  
    } 
        
    bindModeSelector() {              
        try {    
            const selector = document.getElementById('window-mode-select');                  
            if (!selector) return;    
                
            selector.value = this.currentMode;    
                
            selector.addEventListener('change', async (e) => {    
                const newMode = e.target.value;    
                const success = await this.saveMode(newMode);    
                if (success) {    
                    this.showRestartNotification();    
                } else {    
                    console.error('保存窗口模式失败');    
                }    
            });                  
        } catch (error) {    
            console.error('绑定窗口模式选择器失败:', error);    
        }  
    }    
        
    showRestartNotification() {    
        const notification = document.createElement('div');    
        notification.className = 'restart-notification';    
        notification.innerHTML = `    
            <div class="notification-content">    
                <span>窗口模式已保存，请重启应用生效</span>    
                <button onclick="this.parentElement.parentElement.remove()">确定</button>    
            </div>    
        `;    
        document.body.appendChild(notification);    
            
        setTimeout(() => {    
            if (notification.parentElement) {    
                notification.remove();    
            }    
        }, 3000);    
    }    
}    
    
document.addEventListener('DOMContentLoaded', () => {    
    window.windowModeManager = new WindowModeManager();    
});