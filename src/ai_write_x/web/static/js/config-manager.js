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
                    success ? '已恢复默认设置(仅当前运行有效，永久有效需点“保存设置”)' : '恢复默认设置失败',  
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

        // ========== 热搜平台设置事件绑定 ==========  

        // 保存平台配置按钮  
        const savePlatformsConfigBtn = document.getElementById('save-platforms-config');  
        if (savePlatformsConfigBtn) {  
            savePlatformsConfigBtn.addEventListener('click', async () => {  
                const success = await this.saveConfig();  
                window.app?.showNotification(  
                    success ? '平台配置已保存' : '保存平台配置失败',  
                    success ? 'success' : 'error'  
                );  
            });  
        }  
        
        // 恢复默认平台配置按钮  
        const resetPlatformsConfigBtn = document.getElementById('reset-platforms-config');  
        if (resetPlatformsConfigBtn) {  
            resetPlatformsConfigBtn.addEventListener('click', async () => {  
                // 获取默认配置  
                const response = await fetch(`${this.apiEndpoint}/default`);  
                if (response.ok) {  
                    const result = await response.json();  
                    const defaultPlatforms = result.data.platforms;  
                    
                    // 更新配置  
                    await this.updateConfig({ platforms: defaultPlatforms });  
                    
                    // 刷新UI  
                    this.populatePlatformsUI();  
                    
                    window.app?.showNotification('已恢复默认平台配置(仅当前运行有效，永久有效需点“保存设置”)', 'info');  
                } else {  
                    window.app?.showNotification('恢复默认配置失败', 'error');  
                }  
            });  
        }

        // ========== 微信公众号设置事件绑定 ==========  

        // 添加凭证按钮  
        const addWeChatCredentialBtn = document.getElementById('add-wechat-credential');  
        if (addWeChatCredentialBtn) {  
            addWeChatCredentialBtn.addEventListener('click', () => {  
                this.addWeChatCredential();  
            });  
        }  
        
        // 保存微信配置按钮  
        const saveWeChatConfigBtn = document.getElementById('save-wechat-config');  
        if (saveWeChatConfigBtn) {  
            saveWeChatConfigBtn.addEventListener('click', async () => {  
                await this.saveWeChatConfig();  
            });  
        }  
        
        // 恢复默认微信配置按钮  
        const resetWeChatConfigBtn = document.getElementById('reset-wechat-config');  
        if (resetWeChatConfigBtn) {  
            resetWeChatConfigBtn.addEventListener('click', async () => {  
                const response = await fetch(`${this.apiEndpoint}/default`);  
                if (response.ok) {  
                    const result = await response.json();  
                    const defaultCredentials = result.data.wechat.credentials;  
                    
                    await this.updateConfig({   
                        wechat: { credentials: defaultCredentials }   
                    });  
                    
                    this.populateWeChatUI();  
                    
                    window.app?.showNotification('已恢复默认微信配置(仅当前运行有效，永久有效需点“保存设置”)', 'info');  
                } else {  
                    window.app?.showNotification('恢复默认配置失败', 'error');  
                }  
            });  
        }

        // ========== 微信公众号输入框事件绑定 ==========  
        // 注意:由于凭证是动态生成的,需要使用事件委托  
        
        const wechatContainer = document.getElementById('wechat-credentials-container');  
        if (wechatContainer) {  
            // 使用事件委托处理所有输入框的blur事件  
            wechatContainer.addEventListener('blur', async (e) => {  
                if (e.target.matches('input[id^="wechat-"]')) {  
                    const id = e.target.id;  
                    const match = id.match(/wechat-\w+-(\d+)/);  
                    if (match) {  
                        const index = parseInt(match[1]);  
                        await this.updateWeChatCredential(index);  
                    }  
                }  
            }, true);  
            
            // 处理复选框的change事件  
            wechatContainer.addEventListener('change', async (e) => {  
                if (e.target.matches('input[type="checkbox"][id^="wechat-"]')) {  
                    const id = e.target.id;  
                    const match = id.match(/wechat-(\w+)-(\d+)/);  
                    if (match) {  
                        const [, field, indexStr] = match;  
                        const index = parseInt(indexStr);  
                        
                        if (field === 'call-sendall') {  
                            this.updateSendallOptions(index, e.target.checked);  
                        } else if (field === 'sendall') {  
                            const tagIdInput = document.getElementById(`wechat-tag-id-${index}`);  
                            if (tagIdInput) {  
                                tagIdInput.disabled = e.target.checked;  
                            }  
                            await this.updateWeChatCredential(index);  
                        }  
                    }  
                }  
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
        
        // ========== 填充热搜平台配置 ==========  
        this.populatePlatformsUI();

        // ========== 填充微信公众号配置 ==========  
        this.populateWeChatUI();
    }

    // 填充热搜平台UI  
    populatePlatformsUI() {  
        const platformListBody = document.getElementById('platform-list-body');  
        if (!platformListBody || !this.config.platforms) return;  
        
        // 清空现有内容  
        platformListBody.innerHTML = '';  
        
        // 生成平台行  
        this.config.platforms.forEach((platform, index) => {  
            const row = document.createElement('tr');  
            row.dataset.platformIndex = index;  
            
            // 启用复选框列 - 使用统一的checkbox-label样式  
            const enabledCell = document.createElement('td');  
            const checkboxLabel = document.createElement('label');  
            checkboxLabel.className = 'checkbox-label';  
            checkboxLabel.style.justifyContent = 'center';  
            checkboxLabel.style.margin = '0';  
            
            const enabledCheckbox = document.createElement('input');  
            enabledCheckbox.type = 'checkbox';  
            enabledCheckbox.checked = platform.enabled !== false;  
            enabledCheckbox.addEventListener('change', async (e) => {  
                await this.updatePlatformEnabled(index, e.target.checked);  
            });  
            
            const checkboxCustom = document.createElement('span');  
            checkboxCustom.className = 'checkbox-custom';  
            
            checkboxLabel.appendChild(enabledCheckbox);  
            checkboxLabel.appendChild(checkboxCustom);  
            enabledCell.appendChild(checkboxLabel);  
            
            // 平台名称列  
            const nameCell = document.createElement('td');  
            nameCell.className = 'platform-name';  
            nameCell.textContent = platform.name;  
            
            // 权重输入框列  
            const weightCell = document.createElement('td');  
            const weightInput = document.createElement('input');  
            weightInput.type = 'number';  
            weightInput.className = 'platform-weight-input';  
            weightInput.value = platform.weight;  
            weightInput.min = '0';  
            weightInput.max = '1';  
            weightInput.step = '0.01';  
            weightInput.disabled = platform.enabled === false;  
            weightInput.addEventListener('change', async (e) => {  
                await this.updatePlatformWeight(index, parseFloat(e.target.value));  
            });  
            weightCell.appendChild(weightInput);  
            
            // 说明列  
            const descCell = document.createElement('td');  
            descCell.className = 'platform-description';  
            descCell.textContent = this.getPlatformDescription(platform.name);  
            
            // 组装行  
            row.appendChild(enabledCell);  
            row.appendChild(nameCell);  
            row.appendChild(weightCell);  
            row.appendChild(descCell);  
            
            platformListBody.appendChild(row);  
        });  
    }
    
    // 填充微信公众号UI  
    populateWeChatUI() {  
        const container = document.getElementById('wechat-credentials-container');  
        if (!container) return;  
        
        const credentials = this.config.wechat?.credentials || [];  
        
        // 清空现有内容  
        container.innerHTML = '';  
        
        // 生成凭证卡片  
        credentials.forEach((credential, index) => {  
            const card = this.createWeChatCredentialCard(credential, index);  
            container.appendChild(card);  
        });  
    }  
    
    // 创建表单组辅助方法  
    createFormGroup(label, type, id, value, placeholder, required = false) {  
        const group = document.createElement('div');  
        group.className = 'form-group';  
        
        const labelEl = document.createElement('label');  
        labelEl.setAttribute('for', id);  
        labelEl.textContent = label;  
        if (required) {  
            const requiredSpan = document.createElement('span');  
            requiredSpan.className = 'required';  
            requiredSpan.textContent = ' *';  
            labelEl.appendChild(requiredSpan);  
        }  
        
        const input = document.createElement('input');  
        input.type = type;  
        input.id = id;  
        input.className = 'form-control';  // 确保所有输入框都有这个类  
        input.value = value || '';  
        if (placeholder) {  
            input.placeholder = placeholder;  
            input.title = placeholder;  
        }  
        
        // 为输入框添加blur事件  
        input.addEventListener('blur', async () => {  
            const match = id.match(/wechat-\w+-(\d+)/);  
            if (match) {  
                const index = parseInt(match[1]);  
                await this.updateWeChatCredential(index);  
            }  
        });  
        
        group.appendChild(labelEl);  
        group.appendChild(input);  
        
        return group;  
    }  
    
    // 更新群发选项联动逻辑  
    updateSendallOptions(index, callSendallEnabled) {  
        const sendallCheckbox = document.getElementById(`wechat-sendall-${index}`);  
        const tagIdInput = document.getElementById(`wechat-tag-id-${index}`);  
        
        if (sendallCheckbox) {  
            sendallCheckbox.disabled = !callSendallEnabled;  
        }  
        
        if (tagIdInput) {  
            const sendallChecked = sendallCheckbox?.checked !== false;  
            tagIdInput.disabled = !callSendallEnabled || sendallChecked;  
        }  
        
        // 更新配置  
        this.updateWeChatCredential(index);  
    } 
    
    // 更新单个凭证配置  
    async updateWeChatCredential(index) {  
        const credentials = [...(this.config.wechat?.credentials || [])];  
        
        const credential = {  
            appid: document.getElementById(`wechat-appid-${index}`)?.value || '',  
            appsecret: document.getElementById(`wechat-appsecret-${index}`)?.value || '',  
            author: document.getElementById(`wechat-author-${index}`)?.value || '',  
            call_sendall: document.getElementById(`wechat-call-sendall-${index}`)?.checked || false,  
            sendall: document.getElementById(`wechat-sendall-${index}`)?.checked !== false,  
            tag_id: parseInt(document.getElementById(`wechat-tag-id-${index}`)?.value || 0)  
        };  
        
        credentials[index] = credential;  
        
        await this.updateConfig({   
            wechat: { credentials }   
        });  
    }  
    
    // 添加新凭证  
    addWeChatCredential() {  
        const credentials = [...(this.config.wechat?.credentials || [])];  
        
        // 添加默认凭证  
        credentials.push({  
            appid: '',  
            appsecret: '',  
            author: '',  
            call_sendall: false,  
            sendall: true,  
            tag_id: 0  
        });  
        
        // 更新配置  
        this.updateConfig({   
            wechat: { credentials }   
        }).then(() => {  
            // 刷新UI  
            this.populateWeChatUI();  
            
            window.app?.showNotification(  
                '已添加新凭证,请填写后保存',  
                'info'  
            );  
        });  
    }  
    
    // 删除凭证  
    deleteWeChatCredential(index) {  
        if (index === 0) {  
            window.app?.showNotification(  
                '第一个凭证不能删除',  
                'warning'  
            );  
            return;  
        }  
        
        const credentials = [...(this.config.wechat?.credentials || [])];  
        credentials.splice(index, 1);  
        
        this.updateConfig({   
            wechat: { credentials }   
        }).then(() => {  
            this.populateWeChatUI();  
            
            window.app?.showNotification(  
                '凭证已删除(未保存,点击保存按钮持久化)',  
                'info'  
            );  
        });  
    }  
    
    // 保存微信配置  
    async saveWeChatConfig() {  
        // 验证必填字段  
        const credentials = this.config.wechat?.credentials || [];  
        
        for (let i = 0; i < credentials.length; i++) {  
            const cred = credentials[i];  
            
            // 如果启用了自动发布,检查必填字段  
            if (this.config.auto_publish) {  
                if (!cred.appid || !cred.appsecret || !cred.author) {  
                    window.app?.showNotification(  
                        `凭证 ${i + 1} 缺少必填字段(AppID/AppSecret/作者)`,  
                        'error'  
                    );  
                    return;  
                }  
            }  
        }  
        
        // 调用通用保存方法  
        const success = await this.saveConfig();  
        
        if (success) {  
            const saveBtn = document.getElementById('save-wechat-config');  
            if (saveBtn) {  
                saveBtn.classList.remove('has-changes');  
                saveBtn.innerHTML = '<i class="icon-save"></i> 保存配置';  
            }  
        }  
        
        window.app?.showNotification(  
            success ? '微信配置已保存' : '保存微信配置失败',  
            success ? 'success' : 'error'  
        );  
    }

    // 创建微信凭证卡片  
    createWeChatCredentialCard(credential, index) {  
        const card = document.createElement('div');  
        card.className = 'wechat-credential-card';  
        card.dataset.credentialIndex = index;  
        
        // 标题栏  
        const header = document.createElement('div');  
        header.className = 'credential-header';  
        
        const title = document.createElement('div');  
        title.className = 'credential-title';  
        title.textContent = `凭证 ${index + 1}`;  
        
        const deleteBtn = document.createElement('button');  
        deleteBtn.className = 'credential-delete-btn';  
        deleteBtn.textContent = '删除';  
        deleteBtn.disabled = index === 0; // 第一个凭证不能删除  
        deleteBtn.addEventListener('click', () => {  
            this.deleteWeChatCredential(index);  
        });  
        
        header.appendChild(title);  
        header.appendChild(deleteBtn);  
        
        // 表单内容  
        const form = document.createElement('div');  
        form.className = 'credential-form';  
        
        // 行1: AppID、AppSecret、作者在同一行  
        const row1 = document.createElement('div');  
        row1.className = 'form-row';  
        
        const appidGroup = this.createFormGroup(  
            'AppID',  
            'text',  
            `wechat-appid-${index}`,  
            credential.appid || '',  
            '微信公众号AppID',  
            true  
        );  
        appidGroup.classList.add('form-group-third');  
        
        const appsecretGroup = this.createFormGroup(  
            'AppSecret',  
            'password',  
            `wechat-appsecret-${index}`,  
            credential.appsecret || '',  
            '微信公众号AppSecret',  
            true  
        );  
        appsecretGroup.classList.add('form-group-third');  
        
        const authorGroup = this.createFormGroup(  
            '作者',  
            'text',  
            `wechat-author-${index}`,  
            credential.author || '',  
            '文章作者名称'  
        );  
        authorGroup.classList.add('form-group-third');  
        
        row1.appendChild(appidGroup);  
        row1.appendChild(appsecretGroup);  
        row1.appendChild(authorGroup);  
        
        // 行2: 群发选项  
        const row2 = document.createElement('div');  
        row2.className = 'form-row';  
        
        const sendallOptionsDiv = document.createElement('div');  
        sendallOptionsDiv.className = 'sendall-options';  
        
        // 启用群发复选框  
        const callSendallGroup = document.createElement('div');  
        callSendallGroup.className = 'form-group';  
        
        const callSendallLabel = document.createElement('label');  
        callSendallLabel.className = 'checkbox-label';  
        callSendallLabel.title = '1. 启用群发,群发才有效\n2. 否则不启用,需要网页后台群发';  
        
        const callSendallCheckbox = document.createElement('input');  
        callSendallCheckbox.type = 'checkbox';  
        callSendallCheckbox.id = `wechat-call-sendall-${index}`;  
        callSendallCheckbox.checked = credential.call_sendall || false;  
        callSendallCheckbox.addEventListener('change', (e) => {  
            this.updateSendallOptions(index, e.target.checked);  
        });  
        
        const callSendallCustom = document.createElement('span');  
        callSendallCustom.className = 'checkbox-custom';  
        
        const callSendallText = document.createTextNode('启用群发');  
        
        callSendallLabel.appendChild(callSendallCheckbox);  
        callSendallLabel.appendChild(callSendallCustom);  
        callSendallLabel.appendChild(callSendallText);  
        callSendallGroup.appendChild(callSendallLabel);  
        
        const callSendallHelp = document.createElement('small');  
        callSendallHelp.className = 'form-help';  
        callSendallHelp.textContent = '仅对已认证公众号有效';  
        callSendallGroup.appendChild(callSendallHelp);  
        
        // 群发复选框  
        const sendallGroup = document.createElement('div');  
        sendallGroup.className = 'form-group';  
        
        const sendallLabel = document.createElement('label');  
        sendallLabel.className = 'checkbox-label';  
        sendallLabel.title = '1. 认证号群发数量有限,群发可控\n2. 非认证号,此选项无效(不支持群发)';  
        
        // 群发复选框  
        const sendallCheckbox = document.createElement('input');  
        sendallCheckbox.type = 'checkbox';  
        sendallCheckbox.id = `wechat-sendall-${index}`;  
        sendallCheckbox.checked = credential.sendall !== false;  
        sendallCheckbox.disabled = !credential.call_sendall;
        sendallCheckbox.addEventListener('change', async (e) => {  
            const tagIdInput = document.getElementById(`wechat-tag-id-${index}`);  
            if (tagIdInput) {  
                tagIdInput.disabled = e.target.checked;  
            }  
            await this.updateWeChatCredential(index);  
        });  
        
        const sendallCustom = document.createElement('span');  
        sendallCustom.className = 'checkbox-custom';  
        
        const sendallText = document.createTextNode('群发');  
        
        sendallLabel.appendChild(sendallCheckbox);  
        sendallLabel.appendChild(sendallCustom);  
        sendallLabel.appendChild(sendallText);  
        sendallGroup.appendChild(sendallLabel);  
        
        const sendallHelp = document.createElement('small');  
        sendallHelp.className = 'form-help';  
        sendallHelp.textContent = '发送给所有关注者';  
        sendallGroup.appendChild(sendallHelp);  
        
        // 标签组ID部分  
        const tagIdGroup = this.createFormGroup(  
            '标签组ID',  
            'number',  
            `wechat-tag-id-${index}`,  
            credential.tag_id || 0,  
            '群发的标签组ID'  
        );  
        const tagIdInput = tagIdGroup.querySelector('input');  
        tagIdInput.classList.add('tag-id-input');  // 添加特定宽度类  
        // form-control类已经在createFormGroup中添加,确保高度一致  
        tagIdInput.disabled = !credential.call_sendall || credential.sendall !== false;  
        tagIdInput.addEventListener('change', async () => {  
            await this.updateWeChatCredential(index);  
        }); 
        
        sendallOptionsDiv.appendChild(callSendallGroup);  
        sendallOptionsDiv.appendChild(sendallGroup);  
        sendallOptionsDiv.appendChild(tagIdGroup);  
        
        row2.appendChild(sendallOptionsDiv);  
        
        // 组装表单  
        form.appendChild(row1);  
        form.appendChild(row2);  
        
        // 组装卡片  
        card.appendChild(header);  
        card.appendChild(form);  
        
        return card;  
    }  

    // 更新平台启用状态  
    async updatePlatformEnabled(index, enabled) {  
        const platforms = [...this.config.platforms];  
        platforms[index] = { ...platforms[index], enabled };  
        
        await this.updateConfig({ platforms });  
        
        // 更新权重输入框的禁用状态  
        const row = document.querySelector(`tr[data-platform-index="${index}"]`);  
        if (row) {  
            const weightInput = row.querySelector('.platform-weight-input');  
            if (weightInput) {  
                weightInput.disabled = !enabled;  
            }  
        }  
    }  
    
    // 更新平台权重  
    async updatePlatformWeight(index, weight) {  
        const platforms = [...this.config.platforms];  
        platforms[index] = { ...platforms[index], weight };  
        
        await this.updateConfig({ platforms });  
    }  
    
    // 获取平台描述  
    getPlatformDescription(platformName) {  
        const descriptions = {  
            '微博': '社交媒体热搜话题',  
            '抖音': '短视频平台热点',  
            '小红书': '生活方式分享平台',  
            '今日头条': '新闻资讯聚合',  
            '百度热点': '搜索引擎热搜',  
            '哔哩哔哩': '视频弹幕网站',  
            '快手': '短视频社交平台',  
            '虎扑': '体育社区论坛',  
            '豆瓣小组': '文化兴趣社区',  
            '澎湃新闻': '专业新闻媒体',  
            '知乎热榜': '问答社区热榜'  
        };  
        return descriptions[platformName] || '热搜话题来源';  
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
                body: JSON.stringify({ config_data: updates })  
            });      
                
            if (!response.ok) {      
                throw new Error(`HTTP ${response.status}`);      
            }      
                
            // 同步更新前端内存      
            this.deepMerge(this.config, updates);  
            
            const saveBtn = document.getElementById('save-wechat-config');    
            if (saveBtn && !saveBtn.classList.contains('has-changes')) {    
                saveBtn.classList.add('has-changes');    
                saveBtn.innerHTML = '💾 保存配置 <span style="color: var(--warning-color);">(有未保存更改)</span>';    
            }  
                
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