class ThemeManager {  
    constructor() {  
        this.themes = {  
            LIGHT: { name: "亮色模式", value: "light" },  
            DARK: { name: "暗色模式", value: "dark" }  
        };  
          
        this.waitForConfigManager();  
    }  
      
    init() {  
        this.currentTheme = this.loadSavedTheme();  
        this.applyTheme(this.currentTheme, false); 
        this.bindThemeSelector();  
        this.bindSystemThemeChange();  
    }  
      
    waitForConfigManager() {  
        if (window.configManager) {  
            this.configManager = window.configManager;  
            this.init();  
        } else {  
            setTimeout(() => this.waitForConfigManager(), 50);  
        }  
    }  
      
    loadSavedTheme() {  
        try {  
            // 优先从配置管理器获取  
            if (this.configManager && this.configManager.getUIConfig) {  
                const uiConfig = this.configManager.getUIConfig();  
                if (uiConfig.theme) {  
                    return uiConfig.theme;  
                }  
            }  
              
            // 回退到 localStorage  
            const saved = localStorage.getItem('aiwritex_theme');  
            if (saved && this.themes[saved.toUpperCase()]) {  
                return saved;  
            }  
              
            // 检测系统主题偏好  
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';  
        } catch (e) {  
            return 'light';  
        }  
    }  
      
    async saveTheme(theme) {  
        try {  
            // 保存到配置管理器  
            if (this.configManager && this.configManager.saveUIConfig) {  
                await this.configManager.saveUIConfig({ theme: theme });  
            }  
              
            // 同时保存到 localStorage 作为备份  
            localStorage.setItem('aiwritex_theme', theme);  
            return true;  
        } catch (e) {  
            return false;  
        }  
    }  
      
    async applyTheme(theme, shouldSave = true) {              
        // 只有在需要保存时才保存（用户主动切换时）  
        if (shouldSave) {  
            await this.saveTheme(theme);  
        }  
            
        // 应用主题样式    
        document.documentElement.setAttribute('data-theme', theme);  
        this.currentTheme = theme;  
            
        // 更新选择器状态    
        this.updateThemeSelector();  
    }
      
    bindThemeSelector() {  
        try {  
            const selector = document.getElementById('theme-selector');  
            if (!selector) {  
                return;  
            }  
              
            // 设置当前值  
            selector.value = this.currentTheme;  
              
            // 绑定事件  
            selector.addEventListener('change', async (e) => {  
                const newTheme = e.target.value;  
                await this.applyTheme(newTheme);  
            });                
        } catch (error) {  
        }  
    }  
      
    updateThemeSelector() {  
        const selector = document.getElementById('theme-selector');  
        if (selector) {  
            selector.value = this.currentTheme;  
        }  
    }  
      
    bindSystemThemeChange() {  
        // 监听系统主题变化  
        if (window.matchMedia) {  
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');  
            mediaQuery.addEventListener('change', async (e) => {  
                // 只有在用户没有手动设置主题时才跟随系统  
                const savedTheme = localStorage.getItem('aiwritex_theme');  
                if (!savedTheme) {  
                    await this.applyTheme(e.matches ? 'dark' : 'light');  
                }  
            });  
        }  
    }  
      
    // 切换主题的快捷方法  
    async toggleTheme() {  
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';  
        await this.applyTheme(newTheme);  
    }  
}  
  
// 初始化主题管理器  
document.addEventListener('DOMContentLoaded', () => {  
    window.themeManager = new ThemeManager();  
});