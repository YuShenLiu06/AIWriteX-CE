/**    
 * AIWriteX 主应用类    
 * 职责:应用初始化、视图路由、全局通知    
 */    
class AIWriteXApp {    
    constructor() {
        this.currentView = 'creative-workshop';

        try {
            this.init();
        } catch (error) {
            console.error('应用初始化失败:', error);
        }
        this.setupMobileSidebar();
    }    
        
    init() {    
        this.setupNavigation();    
        this.showView(this.currentView);
        new UpdateChecker();    
    }    
        
    // ========== 导航管理 ==========    
    setupNavigation() {    
        // 主导航菜单点击事件    
        document.querySelectorAll('.nav-link:not(.nav-toggle)').forEach(link => {    
            link.addEventListener('click', (e) => {    
                e.preventDefault();    
                const view = link.dataset.view;    
                this.showView(view);    
            });    
        });    
            
        // 可展开菜单项（知识库管理、系统设置）的点击事件
        document.querySelectorAll('.nav-item-expandable').forEach(navItem => {
            const navToggle = navItem.querySelector('.nav-toggle');
            if (navToggle) {
                navToggle.addEventListener('click', (e) => {
                    e.preventDefault();
                    navItem.classList.toggle('expanded');
                    const view = navToggle.dataset.view;
                    if (view) {
                        this.showView(view);
                    }
                });
            }
        });

        // 二级菜单点击事件
        document.querySelectorAll('.nav-sublink').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const configType = link.dataset.config;
                const knowledgeType = link.dataset.knowledge;
                const navItem = link.closest('.nav-item-expandable');

                if (configType) {
                    navItem?.querySelectorAll('.nav-sublink').forEach(sublink => {
                        sublink.classList.remove('active');
                    });
                    link.classList.add('active');
                    this.showView('config-manager');

                    if (window.configManager) {
                        window.configManager.showConfigPanel(configType);
                    }
                } else if (knowledgeType) {
                    navItem?.querySelectorAll('.nav-sublink').forEach(sublink => {
                        sublink.classList.remove('active');
                    });
                    link.classList.add('active');
                    this.showView('knowledge-manager');

                    if (window.knowledgeManager) {
                        window.knowledgeManager.switchKnowledgeType(knowledgeType);
                    }
                }
            });
        });
    }    
        
    showView(viewName) {  
        // 更新导航状态  
        document.querySelectorAll('.nav-link').forEach(link => {  
            link.classList.remove('active');  
        });  
        
        requestAnimationFrame(() => {  
            document.querySelectorAll('.nav-link').forEach(link => {  
                if (link.dataset.view === viewName) {  
                    link.classList.add('active');  
                }  
            });  
        });  
        
        const targetView = document.getElementById(`${viewName}-view`);  
        
        // 切换视图时关闭预览面板  
        if (window.previewPanelManager) {  
            window.previewPanelManager.reset(); 
        }  
        
        // 隐藏其他视图  
        document.querySelectorAll('.view-content').forEach(view => {  
            if (view !== targetView) {  
                view.classList.remove('active');  
                setTimeout(() => {  
                    view.style.display = 'none';  
                }, 200);  
            }  
        });  
        
        // 显示目标视图  
        if (targetView) {  
            targetView.style.display = 'block';  
            requestAnimationFrame(() => {  
                targetView.classList.add('active');  
            });  
            
            // 延迟初始化各个管理器  
            this.initializeViewManager(viewName);  
        }  
        
        // 处理配置管理视图的特殊逻辑  
        this.handleConfigViewSwitch(viewName);  
        
        // 控制预览按钮的显示/隐藏  
        this.updatePreviewButtonVisibility(viewName);  
        
        this.currentView = viewName;

        // 移动端：导航后关闭侧边栏抽屉
        if (this.closeMobileSidebar) {
            this.closeMobileSidebar();
        }
    }
        
    initializeViewManager(viewName) {    
        switch(viewName) {    
            case 'creative-workshop':    
                if (!window.creativeWorkshopManager) {    
                    window.creativeWorkshopManager = new CreativeWorkshopManager();    
                }    
                break;    
            case 'template-manager':    
                if (!window.templateManager) {    
                    window.templateManager = new TemplateManager();    
                }    
                break;    
case 'article-manager':
                if (!window.articleManager) {
                    window.articleManager = new ArticleManager();
                }
                break;
            case 'knowledge-manager':
                if (!window.knowledgeManager) {
                    window.knowledgeManager = new KnowledgeManager();
                }
                break;
            case 'scheduled-task-manager':
                if (!window.scheduledTaskManager) {
                    window.scheduledTaskManager = new ScheduledTaskManager();
                }
                break;
        }
    }    
        
    handleConfigViewSwitch(viewName) {
        if (viewName === 'config-manager') {
            // 清除所有子菜单的active状态
            document.querySelectorAll('.nav-sublink').forEach(sublink => {
                sublink.classList.remove('active');
            });

            // 激活界面设置子菜单
            const uiConfigSublink = document.querySelector('[data-config="ui"]');
            if (uiConfigSublink) {
                uiConfigSublink.classList.add('active');
            }

            // 显示界面设置面板（带防御性检查）
            if (window.configManager) {
                try {
                    window.configManager.showConfigPanel('ui');
                } catch (error) {
                    console.error('showConfigPanel调用失败:', error);
                    this.fallbackShowConfigPanel('ui');
                }
            } else {
                this.fallbackShowConfigPanel('ui');
            }
        } else {
            // 如果切换到非配置管理视图,仅折叠系统设置菜单
            const configNavItem = document.querySelector('.nav-item-expandable .nav-toggle[data-view="config-manager"]')?.closest('.nav-item-expandable');
            if (configNavItem) {
                configNavItem.classList.remove('expanded');
            }

            // 同时清除系统设置子菜单的 active 状态
            configNavItem?.querySelectorAll('.nav-sublink').forEach(sublink => {
                sublink.classList.remove('active');
            });
        }
    }

    fallbackShowConfigPanel(panelType) {
        const targetPanel = document.getElementById(`config-${panelType}`);
        if (targetPanel) {
            document.querySelectorAll('.config-panel').forEach(panel => {
                panel.classList.remove('active');
                panel.style.display = 'none';
            });
            targetPanel.style.display = 'block';
            targetPanel.classList.add('active');
        }
    }    
        
    updatePreviewButtonVisibility(viewName) {    
        const previewTrigger = document.getElementById('preview-trigger');    
        if (previewTrigger) {    
            const viewsWithPreview = ['creative-workshop', 'article-manager', 'template-manager'];    
            previewTrigger.style.display = viewsWithPreview.includes(viewName) ? 'flex' : 'none';    
        }    
    }    
        
    // ========== 移动端侧边栏抽屉 ==========

    /** 初始化移动端汉堡菜单和侧边栏抽屉交互 */
    setupMobileSidebar() {
        const menuBtn = document.getElementById('mobile-menu-btn');
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        if (!menuBtn || !sidebar) return;

        /** 关闭侧边栏抽屉 */
        this.closeMobileSidebar = () => {
            sidebar.classList.remove('open');
            overlay?.classList.remove('active');
            document.body.style.overflow = '';
        };

        // 汉堡按钮点击 → 切换抽屉
        menuBtn.addEventListener('click', () => {
            const isOpen = sidebar.classList.toggle('open');
            overlay?.classList.toggle('active');
            document.body.style.overflow = isOpen ? 'hidden' : '';
        });

        // 点击遮罩层 → 关闭抽屉
        overlay?.addEventListener('click', () => this.closeMobileSidebar());
    }

    // ========== 全局通知系统 ==========    
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
        
    // ========== 预览面板控制 ==========    
    showPreview(content) {    
        if (window.previewPanelManager) {    
            window.previewPanelManager.show(content);    
        }    
    }    
        
    hidePreview() {    
        if (window.previewPanelManager) {    
            window.previewPanelManager.hide();    
        }    
    }    
}    
    
// 初始化应用    
let app;    
document.addEventListener('DOMContentLoaded', () => {    
    app = new AIWriteXApp();    
    window.app = app;    
});