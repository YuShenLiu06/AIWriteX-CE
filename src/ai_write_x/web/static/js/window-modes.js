class WindowModeManager {  
    constructor() {  
        this.modes = {  
            STANDARD: { width: 1400, height: 900, name: "标准模式" },  
            MAXIMIZED: { maximized: true, name: "最大化模式" }  
        };  
          
        this.currentMode = this.loadSavedMode();  
        this.init();  
    }  
      
    init() {  
        this.createModeSelector();  
        this.applyMode(this.currentMode);  
    }  
      
    loadSavedMode() {  
        try {  
            return localStorage.getItem('aiwritex_window_mode') || 'STANDARD';  
        } catch (e) {  
            return 'STANDARD';  
        }  
    }  
      
    saveMode(mode) {  
        try {  
            localStorage.setItem('aiwritex_window_mode', mode);  
        } catch (e) {  
            console.warn('无法保存窗口模式设置:', e);  
        }  
    }  
      
    applyMode(mode) {  
        // 修复正则表达式转义问题  
        document.body.className = document.body.className.replace(/window-mode-\\w+/g, '');  
        document.body.classList.add(`window-mode-${mode.toLowerCase()}`);  
        document.body.setAttribute('data-window-mode', mode.toLowerCase());  
          
        // 设置CSS变量  
        const root = document.documentElement;  
        if (mode === 'STANDARD') {  
            root.style.setProperty('--window-width', '1400px');  
            root.style.setProperty('--window-height', '900px');  
            root.style.setProperty('--sidebar-width', '250px');  
            root.style.setProperty('--panel-width', '300px');  
        } else if (mode === 'MAXIMIZED') {  
            root.style.setProperty('--window-width', '100vw');  
            root.style.setProperty('--window-height', '100vh');  
            root.style.setProperty('--sidebar-width', '280px');  
            root.style.setProperty('--panel-width', '350px');  
        }  
          
        this.currentMode = mode;  
    }  
      
    createModeSelector() {  
        try {  
            const configView = document.getElementById('config-manager-view');  
            if (!configView) {  
                console.warn('配置页面未找到，无法创建窗口模式选择器');  
                return;  
            }  
              
            // 查找界面设置区域  
            let interfaceSection = configView.querySelector('.config-section:has(.config-section-title:contains("界面设置"))');  
              
            // 如果没有找到，创建界面设置区域  
            if (!interfaceSection) {  
                interfaceSection = document.createElement('div');  
                interfaceSection.className = 'config-section';  
                interfaceSection.innerHTML = `  
                    <h3 class="config-section-title">界面设置</h3>  
                    <div class="config-grid" id="interface-config-grid">  
                    </div>  
                `;  
                configView.appendChild(interfaceSection);  
            }  
              
            const configGrid = interfaceSection.querySelector('.config-grid') ||   
                              interfaceSection.querySelector('#interface-config-grid');  
              
            if (!configGrid) {  
                console.warn('配置网格未找到');  
                return;  
            }  
              
            // 创建窗口模式选择器  
            const modeSelector = document.createElement('div');  
            modeSelector.className = 'config-item';  
            modeSelector.innerHTML = `  
                <label class="form-label">窗口模式</label>  
                <select id="window-mode-select" class="form-select">  
                    <option value="STANDARD" ${this.currentMode === 'STANDARD' ? 'selected' : ''}>标准模式 (1400x900)</option>  
                    <option value="MAXIMIZED" ${this.currentMode === 'MAXIMIZED' ? 'selected' : ''}>最大化模式</option>  
                </select>  
                <p class="form-help">选择窗口显示模式，重启应用后生效</p>  
            `;  
              
            configGrid.appendChild(modeSelector);  
              
            // 绑定事件  
            const select = document.getElementById('window-mode-select');  
            if (select) {  
                select.addEventListener('change', (e) => {  
                    const newMode = e.target.value;  
                    this.saveMode(newMode);  
                    this.showRestartNotification();  
                });  
            }  
        } catch (error) {  
            console.error('创建窗口模式选择器失败:', error);  
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
    }
}  
  
// 初始化窗口模式管理器  
document.addEventListener('DOMContentLoaded', () => {  
    window.windowModeManager = new WindowModeManager();  
});