# AIWriteX 定时任务 Web 接入说明

> 最后更新: 2026-05-19

---

## 1. 接入目标

定时任务页面需要接入当前 Web UI 的既有结构，而不是引入新的前端路由系统。

当前项目前端是“单页模板聚合 + 视图切换”模式：

- 主模板：`src/ai_write_x/web/templates/index.html`
- 侧边栏：`src/ai_write_x/web/templates/components/sidebar.html`
- 视图目录：`src/ai_write_x/web/templates/components/views/`
- 切换逻辑：`src/ai_write_x/web/static/js/main.js`

因此定时任务页面必须按现有约定接入：

1. 新增一个独立 view 模板。
2. 在侧边栏加入顶级导航。
3. 在 `index.html` 中 include 挂载 view，并引入对应 js/css。
4. 在 `main.js` 中加入 view 初始化与切换支持。

---

## 2. 当前前端结构

### 2.1 现有顶级视图

当前顶级视图包括：

- `creative-workshop`
- `article-manager`
- `template-manager`
- `knowledge-manager`
- `config-manager`

其中 `config-manager` 是一个特殊视图，侧边栏中以“系统设置”顶级项 + 二级菜单形式呈现；其余页面均为普通顶级导航。

### 2.2 定时任务的接入位置

定时任务应作为新的**顶级导航**接入，而不是放到“系统设置”二级菜单中。

原因：

1. 它是独立业务模块，不是系统配置项。
2. 页面内会包含任务列表、执行记录和运行状态，不属于配置面板语义。
3. 与“创意工坊”“文章管理”“模板管理”“知识库管理”同级更符合信息架构。

---

## 3. view 命名契约

当前 `main.js` 的切换逻辑基于以下规则：

```javascript
const view = link.dataset.view;
const targetView = document.getElementById(`${viewName}-view`);
```

因此定时任务页面必须严格遵守以下命名契约：

| 元素 | 命名 |
|------|------|
| sidebar 导航 `data-view` | `scheduled-task-manager` |
| view 根节点 id | `scheduled-task-manager-view` |
| 模板文件 | `scheduled-task-manager.html` |
| 管理器脚本 | `scheduled-task-manager.js` |
| 样式文件 | `scheduled-task-manager.css` |
| 全局管理器对象 | `window.scheduledTaskManager` |

结论：`scheduled-task-manager` 是页面切换的基准名，相关 DOM id、模板文件、脚本文件都应围绕这个基准名保持一致。

---

## 4. sidebar 顶级导航接入

修改文件：`src/ai_write_x/web/templates/components/sidebar.html`

建议新增一个普通顶级导航项，位置放在“知识库管理”之后、“系统设置”之前或之后均可，但应保持与其他业务页面同级。

建议结构：

```html
<li class="nav-item">
    <a href="#" class="nav-link" data-view="scheduled-task-manager">
        <span>定时任务</span>
    </a>
</li>
```

接入要求：

1. 使用 `nav-link`，不要使用 `nav-sublink`。
2. `data-view` 必须为 `scheduled-task-manager`。
3. 该项应参与 `main.js` 现有 `.nav-link:not(.nav-toggle)` 点击绑定。

这样无需额外实现新导航机制，点击后会自动进入 `showView('scheduled-task-manager')` 流程。

---

## 5. index include 挂载方式

修改文件：`src/ai_write_x/web/templates/index.html`

### 5.1 view include

当前所有主视图都通过 `{% include %}` 直接挂载在：

```html
<main class="content-area">
    ...
</main>
```

定时任务页面应遵循相同方式，例如：

```html
{% include 'components/views/scheduled-task-manager.html' %}
```

建议放在已有业务视图附近，保持 include 顺序清晰。

### 5.2 样式接入

当前 `index.html` 在 `<head>` 中集中引入各 view 的样式文件。定时任务页面应新增：

```html
<link rel="stylesheet" href="/static/css/views/scheduled-task-manager.css">
```

### 5.3 脚本接入

当前 `index.html` 在页面底部集中引入各 manager 脚本。定时任务页面应新增：

```html
<script src="/static/js/scheduled-task-manager.js"></script>
```

说明：

- 继续沿用原生脚本加载模式。
- 不引入前端框架或模块打包器。
- 脚本加载位置应与现有 manager 文件保持一致。

---

## 6. main.js 切换机制接入

修改文件：`src/ai_write_x/web/static/js/main.js`

### 6.1 当前切换机制

当前应用由 `AIWriteXApp.showView(viewName)` 控制页面切换，核心逻辑包括：

1. 根据 `data-view` 更新导航高亮。
2. 通过 `${viewName}-view` 定位目标 DOM。
3. 隐藏其他 `.view-content`。
4. 显示目标 view。
5. 调用 `initializeViewManager(viewName)` 初始化页面管理器。

这意味着定时任务页面只要遵守 view 命名契约，就能直接复用现有切换机制。

### 6.2 需要补充的初始化分支

在 `initializeViewManager(viewName)` 中新增：

```javascript
case 'scheduled-task-manager':
    if (!window.scheduledTaskManager) {
        window.scheduledTaskManager = new ScheduledTaskManager();
    }
    break;
```

作用：

- 首次进入页面时初始化管理器。
- 后续切换时复用同一实例，保持与现有 manager 风格一致。

### 6.3 预览按钮处理

当前 `updatePreviewButtonVisibility(viewName)` 只对以下页面显示预览按钮：

- `creative-workshop`
- `article-manager`
- `template-manager`

定时任务页面通常不需要右侧预览面板，因此不应加入该列表。这样切换到定时任务页面时，预览按钮会自动隐藏，符合当前机制。

---

## 7. 定时任务 view 结构建议

新增文件：`src/ai_write_x/web/templates/components/views/scheduled-task-manager.html`

根节点必须为：

```html
<div id="scheduled-task-manager-view" class="view-content" style="display: none;">
```

这与当前 `article-manager.html`、`template-manager.html`、`knowledge-manager.html` 的隐藏式初始化方式一致。

建议页面分为四个区域：

1. 页面头部
   - 标题
   - 简要说明
   - 运行状态摘要

2. 任务列表区
   - 任务名称
   - 执行时间
   - 启用状态
   - 最近执行结果
   - 操作按钮

3. 任务编辑区
   - 新建/编辑表单
   - 必填字段 `topic`
   - 时间配置
   - 重试配置

4. 执行记录区
   - 最近执行时间
   - 状态
   - 错误原因
   - 生成文件路径
   - 是否发布

建议在表单区域明确说明：

- 预设话题必须填写
- 留空自动热搜仅适用于创意工坊
- 自动发布沿用当前全局配置

---

## 8. 前端管理器职责

新增文件：`src/ai_write_x/web/static/js/scheduled-task-manager.js`

建议提供 `ScheduledTaskManager` 类，职责如下：

| 职责 | 说明 |
|------|------|
| 初始化页面 | 绑定事件、加载列表、加载运行时状态 |
| 任务 CRUD | 创建、编辑、删除任务 |
| 启停任务 | 调用 toggle 接口 |
| 立即执行 | 调用 run-now 接口 |
| 记录展示 | 拉取并渲染执行历史 |
| 状态展示 | 展示调度器状态、当前运行任务、全局自动发布状态 |

建议沿用当前项目的原生 `fetch` 调用方式和 `window.app?.showNotification(...)` 提示方式。

---

## 9. 与创意工坊的关系

### 9.1 topic 语义复用

定时任务中的 `topic` 应与创意工坊 `#topic-input` 的语义保持一致：

- 都表示“用户明确指定的话题”
- 都会进入现有内容生成链路
- 都不是新的提示词体系

### 9.2 不复用空值热搜行为

虽然语义与 `topic-input` 一致，但空话题自动热搜不应复制到定时任务中。

原因：

1. 当前热搜补全发生在 `creative-workshop.js` 页面逻辑里。
2. 定时任务需要可重复、可预期的执行输入。
3. 若每次定时都动态热搜，会使任务定义缺乏稳定性，也超出初版范围。

因此前端表单应把 `topic` 设为必填项，并给出明确提示。

---

## 10. 定时任务状态展示与现有状态机制的关系

当前系统已有一套围绕“手动生成”的状态与日志机制：

- `creative-workshop.js` 负责生成按钮状态
- WebSocket `/api/ws/generate/logs` 负责日志流式展示
- `/api/generate/status` 负责轮询运行状态

定时任务页面初版不应重做一套新的全局运行状态系统，而应以“任务管理视图”身份展示以下信息：

1. 调度器是否已启动
2. 当前是否有生成任务运行
3. 某个定时任务最近一次执行结果
4. 某个任务的执行历史

建议处理方式：

- 任务级状态与历史从 `scheduled_tasks` API 获取
- 全局运行状态通过定时任务运行时状态接口间接暴露
- 不要求在定时任务页面复刻创意工坊日志流式面板

这样可以避免把现有“生成日志 UI”与“定时任务管理 UI”混在同一层。

---

## 11. JSON 持久化在 Web 层的体现

前端不直接关心 JSON 文件内容，但文档与页面提示应与后端持久化方案一致。

建议在页面说明或开发注释中明确：

- 任务定义持久化到 `scheduled_tasks.json`
- 执行记录持久化到 `scheduled_task_execution_records.json`
- 具体落位由 `PathManager` 决定

推荐后端最终使用：

- `PathManager.get_config_dir() / "scheduled_tasks.json"`
- `PathManager.get_config_dir() / "scheduled_task_execution_records.json"`

这样前端只面向 API，路径细节统一由后端控制。

---

## 12. 推荐接入顺序

### 12.1 模板层

1. 新增 `scheduled-task-manager.html`
2. 修改 `sidebar.html`
3. 修改 `index.html` include 和资源引入

### 12.2 脚本层

1. 新增 `scheduled-task-manager.js`
2. 修改 `main.js` 初始化分支
3. 视需要补充页面切换后的状态刷新逻辑

### 12.3 样式层

1. 新增 `scheduled-task-manager.css`
2. 复用现有 shared-manager 风格
3. 保持与其他 manager 页面一致的间距、卡片、表单样式

---

## 13. Web 接入结论

定时任务页面首版必须遵守以下前端集成原则：

1. 作为 sidebar 顶级导航接入，不放入系统设置二级菜单。
2. 使用 `scheduled-task-manager` 作为统一 view 基准名。
3. 通过 `index.html` 的 include、css、js 挂载进入现有页面结构。
4. 通过 `main.js` 的既有切换机制完成显示与初始化。
5. 在页面表单中明确要求填写 `topic`，不支持空话题热搜。
6. 在页面说明中明确自动发布沿用全局 Config，不做任务级覆盖。
7. 状态展示以任务管理为主，不重做一套新的全局日志交互系统。
