# AIWriteX 移动端适配审计报告

> 审计日期: 2026-06-22
> 审计分支: feature/frontend-mobile-compatible
> 审计工具: ecc:chrome-devtools（Chrome DevTools MCP，iPhone 14 Pro 视口模拟 390×844 @3x，touch）
> 审计范围: 暂存区已有移动端适配（mobile.css + header.html + main.js 抽屉逻辑）的实测验证

---

## 一、环境与启动方式

### 后端启动问题
- `.venv` 虚拟环境的 `pydantic-core` C 扩展损坏（`cannot import name '__version__'`），导致 `fastapi` 无法导入。
- **修复**: 执行 `uv pip install "pydantic-core==2.46.4" --python .venv/Scripts/python.exe`（需与已安装的 pydantic 版本严格匹配，误装 2.47.0 会触发 `SystemError`）。

### 推荐的前端独立启动方式
前端可脱离 `python main.py`（pywebview GUI）单独启动，便于在浏览器/DevTools 中调试：

```bash
.venv/Scripts/python.exe -m uvicorn src.ai_write_x.web.app:app --host 127.0.0.1 --port 8888 --log-level warning
```

服务地址: `http://127.0.0.1:8888`，健康检查: `/health`。

---

## 二、暂存区适配成果（已生效）

实测确认以下暂存区改动在移动端工作正常：

| 模块 | 状态 | 实测证据 |
|------|------|---------|
| 汉堡菜单按钮 | ✅ | `display:flex`, 44×44px，触摸达标 |
| 侧边栏抽屉 | ✅ | 默认 `left:-260px` 隐藏；点击后 `.open`+overlay.active+body.overflow=hidden 全部正确响应 |
| 创意工坊 | ✅ | 无横向溢出(scrollW=clientW=390)、借鉴/日志面板折叠正常(h=0)、网格单列 |
| 网格布局 | ✅ | `grid-template-columns:1fr`，无横向溢出 |
| 配置面板折叠 | ✅ | `.collapsed` 面板 `max-height:0` 正确 |
| 触摸目标 | ✅ | 全局可见按钮无 <40px，达标 |
| 表单防 iOS 放大 | ✅ | input/textarea `font-size:16px` |

---

## 三、发现问题清单（按严重度）

### 🔴 P0 - 知识库管理：侧边栏遮挡重叠、分类树不可见

**现象**: 知识库管理视图（图片/文本知识库）的 `.manager-sidebar` 区域，分类树（`.sidebar-tree`）只有上半部分可见，且与下方统计区重叠遮挡。

**实测数据**（限定 `#knowledge-manager-view`，视口 390×844）:

| 元素 | offsetWidth | offsetHeight | scrollHeight | 关键 CSS |
|------|-------------|--------------|--------------|---------|
| `.manager-sidebar` | 370 | **180** | **222** | `max-height:180px; overflow:auto` |
| `.sidebar-header`(分类标题+加号) | 332 | 57 | — | — |
| `.sidebar-tree`(分类树) | 332 | **8** | 28 | `flex:1 1 0%`（未重置）|
| `.sidebar-stats`(统计) | 332 | 109 | — | — |

**根因**:
1. `mobile.css` 给 `.manager-sidebar` 设了 `max-height:180px`，但知识库侧边栏含三段内容（header 57 + tree + stats 109 ≈ 222px），超过 180px 被截断。
2. `shared-manager.css` 桌面端规则 `.sidebar-tree { flex:1 }`（占满剩余高度）**未被 mobile.css 重置**。在 180px 容器中，header(57)+stats(109) 占 166px，`.sidebar-tree` 被 `flex:1` 压缩到仅 **8px**，分类项（每项 ~16px+padding）只能露出 8px。
3. `.sidebar-tree`(top:149) 与 `.sidebar-stats`(top:157) 几乎重叠，视觉上分类被统计区遮盖。

> 注: 文章/模板/定时任务管理器因 sidebar 只有 tree（无 stats），`flex:1` 让 tree 占满 180px 未暴露此问题，但属于同一隐患。

---

### 🔴 P0 - 系统设置「向量嵌入设置」面板：横向溢出

**现象**: 系统设置 → 向量嵌入设置（knowledge-embedder）面板横向溢出约 55px，可横向滚动，破坏布局。其余 9 个配置面板均正常。

**实测数据**:

| 元素 | 宽度 | 父容器宽 | flex | min-width |
|------|------|---------|------|-----------|
| `#embedder-api-key-group`(.form-group-half) | **400px** | form-row **308px** | `1 1 0%` | auto |
| `.editable-select` | 400px | — | `0 1 auto` | 0 |
| `.select-display` | 400px | — | `0 1 auto`(basis:auto) | 0 |
| `.config-panel`(active) | clientW=382 | — | — | scrollW=**437** |

**根因**: `.editable-select` 自定义下拉组件的 `.select-display` 为 `flex:0 1 auto`（flex-basis:auto 按内容尺寸），长选项文本（如 "VoyageAI（推荐 Claude 用户）"、API Key）撑开后无法收缩，突破父容器。`.form-group-half` 虽在 `@media(max-width:800px)` 设了 `min-width:auto`，但内部 editable-select 链未约束 `max-width:100%`。

---

### 🟡 P2 - 控制台错误：UpdateChecker 未定义（pre-existing）

**现象**: 控制台报错 `应用初始化失败: ReferenceError: UpdateChecker is not defined`。

**根因**: `main.js:20` 调用 `new UpdateChecker()`，`update-checker.js` 文件存在但 `index.html` 未通过 `<script>` 引入。

**影响**: `init()` 内 `setupNavigation()` 与 `showView()` 已先执行，**不阻塞核心功能**；错误被构造函数 try-catch 捕获，`setupMobileSidebar()` 仍正常运行。非移动端适配引入，属历史遗留，建议顺手修复。

---

### 🟢 P3 - 模板管理：列表超长（可选优化）

**现象**: 模板管理视图 `scrollHeight=11458px`（模板数量多，单列堆叠）。

**影响**: 功能正常，可纵向滚动，但浏览效率低。可后续考虑移动端紧凑列表/分组，非阻塞。

---

## 四、修复方案

所有 CSS 修复统一在 `mobile.css`（最后加载，覆盖桌面端，避免污染桌面样式）；JS/HTML 修复在对应文件。

### 修复 1: 知识库/通用 manager-sidebar（P0）

`mobile.css` 的 `@media(max-width:768px)` 块内，重写 manager 侧边栏规则：

```css
/* 侧边栏：按内容自然展开，不硬截断 */
.manager-sidebar {
    width: 100%;
    height: auto;
    max-height: none;          /* 移除 180px 截断 */
    border-right: none;
    border-bottom: 1px solid var(--border-color);
    min-height: unset;
    flex: 0 0 auto;            /* 按内容高度，不占满 */
}
.manager-sidebar > .sidebar-header,
.manager-sidebar .sidebar-stats {
    flex: 0 0 auto;
}
/* 分类树：横向 chips 滚动，必须重置桌面端 flex:1 防压缩 */
.sidebar-tree {
    flex: 0 0 auto !important;
    flex-wrap: nowrap;
    gap: 8px;
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 8px;
    min-height: 44px;          /* 保证 chips 可见可触摸 */
}
```

### 修复 2: editable-select 溢出（P0）

`mobile.css` 的 `@media(max-width:768px)` 块内追加：

```css
/* 约束自定义下拉组件宽度，防止长文本撑破容器 */
.editable-select,
.select-display,
.select-input,
.form-group-half,
.form-group-quarter,
.form-group-third {
    max-width: 100%;
    min-width: 0;
    box-sizing: border-box;
}
.select-display {
    width: 100%;
}
```

### 修复 3: 引入 UpdateChecker（P2）

`index.html` 在 `main.js` 之前增加：
```html
<script src="/static/js/update-checker.js"></script>
```

---

## 五、第一轮修复验证（reload 后回归）

| 修复项 | 验证结果 |
|--------|---------|
| 知识库 manager-sidebar 遮挡 | ✅ treeH 8px→49px，overlap:false，分类全可见，无溢出 |
| embedder 面板 editable-select 溢出 | ✅ panelOverflow:false（group/selectDisplay 400→308px；select-display 加 overflow:hidden 截断长 API Key） |
| UpdateChecker 未引入 | ✅ 已定义，原 ReferenceError 消失 |

## 六、第二轮审查与修复（多 Agent 辅助）

派 2 个 Agent 并行审查（文章/模板管理、定时任务/配置/模态框）。Agent A（文章/模板）因模型 529 过载未产出，由主流程 Grep 补审（固定宽度均有 max-width:90vw/95vw 兜底，实测无溢出）。Agent B 产出 12 项发现，整合修复：

| Agent B 发现 | 严重度 | 修复 | 验证 |
|-------------|--------|------|------|
| .custom-input-dialog/.custom-alert-dialog min-width:400px 溢出 | P0 | mobile.css 加 92vw 约束 | ✅ |
| .provider-toggle-btn 触摸目标 ~30px | P0 | min-height:44px | ✅ 44px |
| .scheduled-task-action-btn 触摸目标 ~28px | P0 | min-height:44px | ✅ 44px |
| .scheduled-task-meta-grid 固定2列挤压 | P1 | grid-template-columns:1fr | ✅ 无溢出 |
| .platform-table 列宽530px横滚、表头错位 | P1 | 移动端转卡片式 block 布局 | ✅ display:block, 无溢出 |
| 模态框/关闭按钮/卡片操作 | — | 已确认 mobile.css 覆盖 | ✅ 模态 351×675 fitsViewport:true，关闭按钮 44×44 |

## 七、最终全视图回归（iPhone 14 Pro 390×844）

- 6 个主视图 + 10 个配置面板横向溢出复检：**全部 false（无溢出）**
- 知识库图片/文本切换、上传模态触发实测：均正常适配视口

## 八、pre-existing 功能问题（非移动端适配引入，建议单独排查）

1. **404 资源加载失败（41 次）**：文章管理卡片预览资源（预览 iframe/缩略图）批量 404，疑似文章 HTML 预览未生成或路径问题。桌面端同样存在，与移动端无关。
2. **「加载知识库配置失败: Cannot set properties of null (setting 'checked')」**：config-manager.js 加载配置时某 checkbox 元素为 null。`knowledge-enabled` 相关访问（populateEmbedderUI:1259、updateKnowledgeEmbedderStatus:1445、bindKnowledgeEmbedderStatus:1467、embedderInputs 循环:935）均已做 null 保护，报错来自其他 checkbox id，需沿 try-catch 调用链进一步定位。不影响布局，仅影响部分配置项的初始勾选状态。
3. **grapesjs 编辑器（image-designer.js）**：作为全屏对话框（height:85vh inline style）触发，未受 mobile.css 适配，390px 下左右面板会挤压画布。属独立组件（非 config 里的 image-design-config 纯表单面板），建议后续单独适配。

---

## 九、第二轮修复：管理器卡片被裁剪、无法滑动（2026-06-22 追加）

### 问题（用户反馈）
> 文章、模板页面的具体详情卡片仅仅只能展现两张，没有配套相关的滑动查看相关配置。

### 根因
桌面端管理器（文章/模板/知识库/定时任务）采用「固定视口高 + `.manager-main` 内部独立滚动」模式。移动端 `mobile.css` 已将 `.manager-layout` 改为 `height:auto`（配合抽屉布局），但存在两处断裂：

1. `.manager-layout { height:auto }` 后，内部 `.manager-main { flex:1; overflow-y:auto; max-height:calc(100%-2px) }` 的滚动依赖固定高度父链，在 height:auto 下**滚动失效**，内容把 `.manager-layout` 撑到全部卡片高度（模板视图 ~11350px）。
2. 外层 `.app-main { overflow:hidden }`（main.css:45）+ `.app-container` grid `1fr` 固定行高（main.css:30）+ `#article-manager-view.view-content { overflow:hidden; height:100% }`（main.css:74-79）把超出视口的内容**硬裁剪**。

结果：卡片被裁剪到只剩视口内约 2 张，且无任何滚动条出现。

### 修复（mobile.css @media 768px）
改用「整页滚动」方案——`.app-main` 成为唯一滚动容器，内部视图与布局链全部 `visible` 自然铺开：

```css
.app-main { overflow-y: auto; overflow-x: hidden; }
#article-manager-view.view-content,
#template-manager-view.view-content,
#knowledge-manager-view.view-content,
#scheduled-task-manager-view.view-content {
    overflow: visible !important;
    height: auto !important;
    min-height: calc(100vh - var(--header-height) - var(--footer-height));
}
.manager-layout { /* 原有 height:auto; min-height 保留 */ overflow: visible !important; }
.main-wrapper   { overflow: visible !important; }
.manager-main   { overflow: visible !important; max-height: none !important; }
```

> 仅覆盖 4 个管理器视图（不含 config/creative-workshop），最小影响面。

### 验证（iPhone 14 Pro 390×844 @3x touch）

| 视图 | 卡片数 | .app-main scrollH/clientH | overflowY | 滚动后可见卡片 | 结果 |
|------|--------|--------------------------|-----------|---------------|------|
| 文章管理 | 20 | 6431 / 758 | auto | 第 9/10/11/12 张 | ✅ 可滑动 |
| 模板管理 | 36 | 11350 / 758 | auto | 第 15/16/17 张 | ✅ 可滑动 |
| 创意工坊 | — | 758 / 758（内容不超屏） | auto | — | ✅ 无回归 |
| 全局横向溢出 | — | docScrollW=390=clientW | — | — | ✅ 无溢出 |

回归截图：`docs/reports/screenshots/article-manager-mobile-scroll.jpeg`、`template-manager-mobile-scroll.jpeg`
