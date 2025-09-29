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
            // 优先从配置管理器获取  
            if (this.configManager && this.configManager.getUIConfig) {  
                const uiConfig = this.configManager.getUIConfig();  
                if (uiConfig.windowMode) {  
                    return uiConfig.windowMode;  
                }  
            }  
              
            // 回退到 localStorage  
            const saved = localStorage.getItem('aiwritex_window_mode');  
            const result = saved || 'STANDARD';  
            return result;  
        } catch (e) {  
            console.error('加载窗口模式失败:', e);  
            return 'STANDARD';  
        }  
    }  
      
    async saveMode(mode) {  
        try {  
            // 保存到配置管理器  
            if (this.configManager && this.configManager.saveUIConfig) {  
                await this.configManager.saveUIConfig({ windowMode: mode });  
            }  
              
            // 同时保存到 localStorage 作为备份  
            localStorage.setItem('aiwritex_window_mode', mode);  
            // 立即验证保存结果  
            const saved = localStorage.getItem('aiwritex_window_mode');  
              
            // 显示当前 localStorage 状态  
            for (let i = 0; i < localStorage.length; i++) {  
                const key = localStorage.key(i);  
            }  
            return true;  
        } catch (e) {  
            return false;  
        }  
    }  
      
    applyMode(mode) {  
        document.body.className = document.body.className.replace(/window-mode-\w+/g, '');            
        // 添加新的窗口模式类  
        document.body.classList.add(`window-mode-${mode.toLowerCase()}`);            
        // 设置 data 属性  
        document.body.setAttribute('data-window-mode', mode.toLowerCase());            
        // 设置CSS变量  
        const root = document.documentElement;  
        if (mode === 'STANDARD') {  
            root.style.setProperty('--window-width', '1400px');  
            root.style.setProperty('--window-height', '900px');  
            root.style.setProperty('--sidebar-width', '180px');  
            root.style.setProperty('--panel-width', '240px');  
        } else if (mode === 'MAXIMIZED') {  
            root.style.setProperty('--window-width', '100vw');  
            root.style.setProperty('--window-height', '100vh');  
            root.style.setProperty('--sidebar-width', '220px');  
            root.style.setProperty('--panel-width', '280px');  
        }  
        this.currentMode = mode;
    }  
      
    bindModeSelector() {            
        try {  
            const selector = document.getElementById('window-mode-select');                
            if (!selector) {  
                return;  
            }  
              
            // 设置选择器当前值  
            selector.value = this.currentMode;  
              
            // 绑定事件  
            selector.addEventListener('change', async (e) => {  
                const newMode = e.target.value;  
                await this.saveMode(newMode);  
                this.showRestartNotification();  
            });                
        } catch (error) {  
            
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
          
        // 3秒后自动消失  
        setTimeout(() => {  
            if (notification.parentElement) {  
                notification.remove();  
            }  
        }, 3000);  
    }  
}  
  
// 初始化窗口模式管理器  
document.addEventListener('DOMContentLoaded', () => {  
    window.windowModeManager = new WindowModeManager();  
});  
  
// 页面卸载时的调试  
window.addEventListener('beforeunload', () => {  
    if (window.windowModeManager) {  
        window.windowModeManager.debugLocalStorage();  
    }  
});