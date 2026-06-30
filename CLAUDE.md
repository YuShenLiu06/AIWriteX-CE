# AIWriteX 项目记忆

> 此文件由 AI 自动生成，记录项目架构、规范和关键入口点。
> 最后更新: 2026-06-30

---

## 项目概述

**AIWriteX** 是一个基于 **CrewAI 多智能体框架**的 AI 写作助手，专门用于微信公众号内容创作、自动热点选题、AI生成文章和自动发布。

| 属性 | 值 |
|------|-----|
| 版本 | V2.4.4 |
| 技术栈 | Python 3.10+, CrewAI, FastAPI, PyWebView |
| 多模型支持 | OpenRouter, DeepSeek, Grok, Claude, Qwen, Gemini, Ollama, SiliconFlow, Kimi, GLM, MiniMax |
| 许可证 | Apache 2.0 |

---

## 目录结构

```
D:/Code/business/AIWriteX/
├── main.py                    # GUI模式入口
├── crew_main.py               # 无UI模式入口 (CrewAI工作流)
├── pyproject.toml            # 项目配置 (hatchling构建)
├── requirements.txt           # 依赖声明
│
├── src/ai_write_x/            # 核心源代码
│   ├── core/                  # 核心框架模块
│   │   ├── agent_factory.py   # Agent工厂类
│   │   ├── base_framework.py  # 工作流基类和数据模型
│   │   ├── content_generation.py  # 内容生成引擎
│   │   ├── monitoring.py      # 工作流监控 (单例模式)
│   │   ├── system_init.py      # 系统初始化
│   │   ├── tool_registry.py    # 全局工具注册表 (单例模式)
│   │   └── unified_workflow.py # 统一内容工作流编排器
│   │
│   ├── tools/                 # 工具模块
│   │   ├── custom_tool.py     # 自定义工具基类 (ReadTemplateTool)
│   │   ├── hotnews.py         # 热搜获取工具
│   │   ├── image_search_tool.py # 图片搜索工具 (BaseTool, 向量+关键词)
│   │   ├── text_knowledge_search_tool.py # 文本知识搜索工具 (BaseTool, 向量+关键词)
│   │   ├── search_template.py # AIForge搜索模板工具
│   │   └── wx_publisher.py    # 微信发布工具
│   │
│   ├── adapters/              # 平台适配器
│   │   └── platform_adapters.py  # 7个平台适配器
│   │
│   ├── creative/              # 创意引擎
│   │   └── dimensional_engine.py  # 维度化创意引擎 (16个维度)
│   │
│   ├── web/                   # Web模块
│   │   ├── app.py            # FastAPI应用
│   │   ├── state.py          # 应用状态管理
│   │   ├── webview_gui.py    # pywebview GUI
│   │   └── api/              # API路由 (articles, config, templates, generate)
│   │
│   ├── utils/                # 工具函数
│   │   ├── comm.py          # 通信工具
│   │   ├── content_parser.py # 内容解析器
│   │   ├── icon_manager.py   # 图标管理
│   │   ├── log.py            # 日志模块
│   │   ├── path_manager.py   # 路径管理
│   │   ├── tray_manager.py   # 系统托盘
│   │   └── utils.py          # 通用工具
│   │
│   ├── config/               # 配置管理
│   │   ├── config.py        # 配置类 (单例模式，threading.RLock)
│   │   └── config.yaml      # 主配置文件
│   │
│   ├── license/              # 许可证模块
│   └── version.py            # 版本信息
│
├── knowledge/               # 知识库
│   └── templates/           # 11个分类的文章模板
│
├── docs/                    # 文档目录
│   └── service/             # 服务文档 (架构、规范、封装)
│
├── output/                  # 输出目录
├── logs/                    # 日志目录
├── image/                   # 图片资源
└── temp/                    # 临时文件
```

---

## 核心架构

### 工作流执行流程

```
入口 (main.py / crew_main.py)
    ↓
UnifiedContentWorkflow.execute()
    ↓
┌─────────────────────────────────────────────────────────┐
│  1. _generate_base_content()    → 内容生成               │
│     CrewAI Sequential Tasks:                             │
│     1a. search_knowledge (Agent: researcher)             │
│         → TextKnowledgeSearchTool 搜索知识库             │
│     1b. write_content  (Agent: writer)                   │
│         context=[search_knowledge]                       │
│         → AIForgeSearchTool + ImageSearchTool            │
│                                                         │
│  2. _apply_dimensional_creative_transformation()       │
│     → 维度化创意变换 (16个创意维度)                      │
│                                                         │
│  3. _transform_content()     → HTML格式转换             │
│     (Template路径 / Design路径)                          │
│                                                         │
│  4. _save_content()          → 保存到 output/          │
│                                                         │
│  5. _publish_content()       → 发布到目标平台           │
└─────────────────────────────────────────────────────────┘
```

### 关键类和数据模型

| 类/数据类 | 文件 | 说明 |
|----------|------|------|
| `AgentConfig` | core/base_framework.py | Agent配置数据类 |
| `TaskConfig` | core/base_framework.py | Task配置数据类 |
| `WorkflowConfig` | core/base_framework.py | 工作流配置数据类 |
| `ContentResult` | core/base_framework.py | 统一内容结果格式 |
| `WorkflowType` | core/base_framework.py | SEQUENTIAL/PARALLEL/HIERARCHICAL/CUSTOM |
| `ContentType` | core/base_framework.py | ARTICLE/SOCIAL_POST/VIDEO_SCRIPT... |
| `UnifiedContentWorkflow` | core/unified_workflow.py | 统一内容工作流编排器 |
| `ContentGenerationEngine` | core/content_generation.py | 纯内容生成引擎 (继承BaseWorkflowFramework) |
| `AgentFactory` | core/agent_factory.py | Agent工厂类，LLM缓存 |
| `GlobalToolRegistry` | core/tool_registry.py | 全局工具注册表 (单例模式) |
| `DimensionalCreativeEngine` | creative/dimensional_engine.py | 16维创意引擎 |
| `TextKnowledgeSearchTool` | tools/text_knowledge_search_tool.py | 文本知识搜索 (BaseTool, 向量+关键词回退) |
| `Config` | config/config.py | 配置管理 (单例模式，threading.RLock) |
| `PlatformType` | adapters/platform_adapters.py | 7个平台枚举 |

---

## 入口点

### GUI模式入口 (main.py)

```python
# main.py
def run():
    from src.ai_write_x.license import check_license_and_start
    check_license_and_start()

# 启动流程:
# 1. 检查许可证
# 2. 初始化 WebViewGUI
# 3. 启动 FastAPI 后端服务器 (端口8000)
# 4. 创建 pywebview 窗口显示 Web UI
```

### 无UI模式入口 (crew_main.py)

```bash
python -m src.ai_write_x.crew_main

# 核心函数:
# - ai_write_x_main()    → 主入口函数
# - ai_write_x_run()     → 执行写作任务
# - run_crew_in_process() → 在独立进程中运行 CrewAI 工作流
```

---

## 平台适配器

| 平台 | 适配器类 | 支持HTML | 支持模板 |
|------|---------|---------|---------|
| 微信公众号 | `WeChatAdapter` | ✅ | ✅ |
| 小红书 | `XiaohongshuAdapter` | ✅ | ❌ |
| 抖音 | `DouyinAdapter` | ✅ | ❌ |
| 今日头条 | `ToutiaoAdapter` | ✅ | ❌ |
| 百家号 | `BaijiahaoAdapter` | ✅ | ❌ |
| 知乎 | `ZhihuAdapter` | ✅ | ❌ |
| 豆瓣 | `DoubanAdapter` | ✅ | ❌ |

---

## 设计模式

| 模式 | 应用位置 |
|------|---------|
| 单例模式 | `Config.get_instance()`, `WorkflowMonitor.get_instance()`, `GlobalToolRegistry.get_instance()` |
| 工厂模式 | `AgentFactory.create_agent()` |
| 适配器模式 | `PlatformAdapter` 基类 + 7个平台实现 |
| 注册表模式 | `GlobalToolRegistry` 全局工具注册 |
| 配置合并策略 | `Config.merge_with_user_config()` 智能合并用户配置 |

---

## 代码规范

### Python 规范

- 遵循 **PEP 8** 编码规范
- 使用 **type annotations** 注解所有函数签名
- 优先使用 **immutable data structures** (`@dataclass(frozen=True)`)
- 格式化工具: **black**, **isort**, **ruff**

### 关键约束

- 单个函数代码行数 **≤50行**
- 文件行数 **≤800行** (200-400行为推荐)
- 禁止使用 `print()`，应使用 `logging` 模块
- 禁止硬编码值，使用常量或配置

### 日志规范

```python
from src.ai_write_x.utils import log

log.print_log("消息内容", "info")      # 常规信息
log.print_log("警告信息", "warning")   # 潜在问题
log.print_log("错误信息", "error")     # 错误事件
```

---

## 配置文件

### config.yaml (主配置)

- `platforms`: 热搜平台权重配置
- `wechat.credentials`: 微信公众号凭据
- `api`: 多平台API配置 (api_type, api_key, model, api_base)
- `dimensional_creative`: 16维创意配置
- `article_format`: html/markdown/text
- `auto_publish`: 自动发布开关

### aiforge.toml (AIForge引擎配置)

- LLM提供商配置 (openrouter, deepseek, grok等)
- 缓存配置
- 安全配置
- 网络域名过滤

---

## 版本管理

### 统一版本源 (Single Source of Truth)

前端 footer 显示的版本号 **不是硬编码**，而是从统一版本定义逐层渲染：

```
footer.html {{ version }}  →  web/app.py:186 get_version_with_prefix()  →  src/ai_write_x/version.py __version__
```

| 文件 | 作用 |
|------|------|
| `src/ai_write_x/version.py` | **唯一真实源** (`__version__`)；`get_version_with_prefix()` 返回 `v{__version__}` |
| `web/app.py:186` | 渲染 `index.html` 时注入 `{"version": get_version_with_prefix()}` |
| `web/templates/components/footer.html` | `<span class="version-text">{{ version }}</span>` |
| `pyproject.toml` | 构建版本，**需与 `version.py` 同步** |

> **修改版本号时**：改 `src/ai_write_x/version.py` 的 `__version__`，并同步 `pyproject.toml` 的 `version`。footer 中的 `v` 前缀由 `get_version_with_prefix()` 自动添加，无需手写。当前版本：`1.1.5`。

### CLI 客户端 (独立版本，勿联动)

`client/` 目录下的 `aiwritex_cli` 是 **独立包**，拥有独立的版本生命周期，**不要**与 Web 应用版本耦合：

| 文件 | 作用 |
|------|------|
| `client/aiwritex_cli/__init__.py` | CLI `__version__` |
| `client/pyproject.toml` | CLI 构建版本 |

---

## 文档位置

项目文档存放于 `docs/service/` 目录下：

| 文档 | 说明 |
|------|------|
| `docs/service/architecture.md` | 架构详解 |
| `docs/service/coding-standards.md` | 编码规范 |
| `docs/service/patterns.md` | 封装模式 |
| `docs/service/entry-points.md` | 关键函数入口 |
| `docs/service/release-standard.md` | 发布书写标准(版本号 / tag / CHANGELOG / Release Notes / 发版时机) |

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| V2.4.4 | 2026-05-12 | 底层架构重构 + 文本知识搜索Agent集成 |
| V2.4.3 | - | - |
| V2.4.2 | - | AI自动配图 + 资源图库 |