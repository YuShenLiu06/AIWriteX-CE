# AIWriteX 架构详解

> 最后更新: 2026-05-12

---

## 1. 系统架构图

```
┌──────────────────────────────────────────────────────────────┐
│                         入口层                                │
│  ┌─────────────┐              ┌─────────────┐                 │
│  │   main.py   │              │ crew_main  │                 │
│  │  (GUI模式)  │              │ (无UI模式)  │                 │
│  └──────┬──────┘              └──────┬─────┘                 │
└─────────┼────────────────────────────┼───────────────────────┘
          │                            │
          ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedContentWorkflow                    │
│                   (统一内容工作流编排器)                       │
└─────────┬────────────────────────────┬───────────────────────┘
          │                            │
          ▼                            ▼
┌─────────────────┐        ┌─────────────────────────────┐
│  内容生成引擎    │        │    维度化创意引擎             │
│ ContentGeneration│        │ DimensionalCreativeEngine   │
│     Engine      │        │       (16个维度)              │
└────────┬────────┘        └─────────────┬────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AgentFactory                            │
│                   (智能体工厂类)                              │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   GlobalToolRegistry                         │
│                   (全局工具注册表)                            │
└────────┬────────────┬────────────┬────────────┬──────────────────┘
         │            │            │            │
         ▼            ▼            ▼            ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐
│AIForgeSearch│ │ReadTemplate │ │ WxPublisher │ │TextKnowledgeSearch│
│    Tool     │ │    Tool     │ │    Tool     │ │      Tool        │
└─────────────┘ └─────────────┘ └─────────────┘ └──────────────────┘
         │            │            │            │
         ▼            ▼            ▼            ▼
┌─────────────┐
│ImageSearch  │
│    Tool     │
└─────────────┘
```

---

## 2. 核心模块

### 2.1 工作流编排 (UnifiedContentWorkflow)

**位置**: `src/ai_write_x/core/unified_workflow.py`

```python
class UnifiedContentWorkflow:
    """统一的内容工作流编排器"""

    def execute(self, topic: str, **kwargs) -> Dict[str, Any]:
        """统一执行流程：输入 -> 内容生成 -> 格式处理 -> 保存 -> 发布"""
```

**执行流程**:
1. `_generate_base_content()` - CrewAI Sequential Tasks:
   - Task 1: `search_knowledge` (Agent: researcher, Tool: TextKnowledgeSearchTool) — 知识库搜索
   - Task 2: `write_content` (Agent: writer, Tools: AIForgeSearchTool + ImageSearchTool, context: [search_knowledge]) — AIForge搜索+写作
2. `_apply_dimensional_creative_transformation()` - 16维创意变换
3. `_transform_content()` - HTML格式转换 (Template或Design路径)
4. `_save_content()` - 保存到output目录
5. `_publish_content()` - 发布到目标平台

### 2.2 内容生成引擎 (ContentGenerationEngine)

**位置**: `src/ai_write_x/core/content_generation.py`

```python
class ContentGenerationEngine(BaseWorkflowFramework):
    """纯内容生成引擎，与平台无关"""
```

继承 `BaseWorkflowFramework`，使用 CrewAI 的 Crew 执行工作流。

### 2.3 维度化创意引擎 (DimensionalCreativeEngine)

**位置**: `src/ai_write_x/creative/dimensional_engine.py`

**16个创意维度**:
- `style` - 文体风格 (诗歌/散文/小说/议论文...)
- `culture` - 文化视角 (东方哲学/西方思辨/日式物哀...)
- `time` - 时空背景 (春秋战国/唐宋盛世/赛博朋克...)
- `personality` - 人格角色 (李白/鲁迅/梦境诗人...)
- `emotion` - 情感调性 (治愈系/悬疑惊悚/热血励志...)
- `format` - 表达格式 (日记体/对话体/书信体...)
- `scene` - 场景环境 (咖啡馆/深夜地铁/海边小屋...)
- `audience` - 目标受众 (Z世代/职场精英/银发族...)
- `theme` - 主题内容 (成长蜕变/时间治愈/梦想追寻...)
- `technique` - 表现技法 (第一人称/全知视角/意识流...)
- `language` - 语言风格 (古典雅致/现代白话/方言土语...)
- `tone` - 语调语气 (严肃庄重/轻松随意/讽刺挖苦...)
- `perspective` - 叙述视角 (第一人称/第二人称/第三人称...)
- `structure` - 文章结构 (时间顺序/空间顺序/层层递进...)
- `rhythm` - 节奏韵律 (快节奏/慢节奏/变化多端...)

### 2.4 平台适配器 (PlatformAdapter)

**位置**: `src/ai_write_x/adapters/platform_adapters.py`

```python
class PlatformAdapter(ABC):
    @abstractmethod
    def format_content(self, content_result: ContentResult, **kwargs) -> str

    @abstractmethod
    def publish_content(self, content_result: ContentResult, **kwargs) -> PublishResult

class WeChatAdapter(PlatformAdapter): ...
class XiaohongshuAdapter(PlatformAdapter): ...
class DouyinAdapter(PlatformAdapter): ...
class ToutiaoAdapter(PlatformAdapter): ...
class BaijiahaoAdapter(PlatformAdapter): ...
class ZhihuAdapter(PlatformAdapter): ...
class DoubanAdapter(PlatformAdapter): ...
```

---

## 3. 配置管理

### 3.1 Config单例

**位置**: `src/ai_write_x/config/config.py`

```python
class Config:
    _instance = None
    _lock = threading.RLock()  # 可重入锁

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
```

### 3.2 配置文件

| 文件 | 用途 |
|------|------|
| `config.yaml` | 主配置 (平台/热搜/API/维度化创意) |
| `aiforge.toml` | AIForge引擎配置 (LLM/缓存/安全) |

---

## 4. 多进程架构

```
主进程 (main.py)
    ├── UI主线程 (PyWebView/pywebview)
    ├── FastAPI服务器 (端口8000)
    └── Web API处理 (articles/config/templates/generate)

子进程 (crew_main.py)
    └── CrewAI工作流执行 (多Agent协作)
```

进程间通信: `multiprocessing.Queue`