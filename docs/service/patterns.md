# AIWriteX 封装模式

> 最后更新: 2026-05-10

---

## 1. 设计模式总览

| 模式 | 应用位置 | 说明 |
|------|---------|------|
| **单例模式** | Config, WorkflowMonitor, GlobalToolRegistry | 全局唯一实例 |
| **工厂模式** | AgentFactory | 创建Agent实例 |
| **适配器模式** | PlatformAdapter | 统一接口访问多平台 |
| **注册表模式** | GlobalToolRegistry | 运行时工具注册 |
| **策略模式** | _transform_content (Template/Design路径) | 不同转换策略 |

---

## 2. 单例模式

### 2.1 Config配置管理

**位置**: `src/ai_write_x/config/config.py`

```python
class Config:
    _instance = None
    _lock = threading.RLock()  # 可重入锁，支持重入

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def api_key(self):
        with self._lock:
            # 线程安全访问
            return self.config["api"][self.api_type]["api_key"][self.key_index]
```

**特点**:
- `threading.RLock()` 支持同一线程重复获取锁
- 所有属性访问都通过 `with self._lock` 保护
- 配置热加载支持

### 2.2 GlobalToolRegistry全局工具注册表

**位置**: `src/ai_write_x/core/tool_registry.py`

```python
class GlobalToolRegistry:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def register_tool(self, name: str, tool_class):
        """注册工具类"""
        self._tools[name] = tool_class

    def get_tool(self, name: str):
        """获取工具类"""
        return self._tools.get(name)
```

---

## 3. 工厂模式

### 3.1 AgentFactory

**位置**: `src/ai_write_x/core/agent_factory.py`

```python
class AgentFactory:
    def __init__(self):
        self._tool_registry = GlobalToolRegistry.get_instance()
        self._llm_cache: Dict[str, LLM] = {}

    def create_agent(self, config: AgentConfig, custom_llm: LLM | None = None) -> Agent:
        """创建智能体实例"""
        tools = []
        for tool_name in config.tools:
            tool_class = self._tool_registry.get_tool(tool_name)
            if tool_class:
                tools.append(tool_class())

        agent_kwargs = {
            "role": config.role,
            "goal": config.goal,
            "backstory": config.backstory,
            "tools": tools,
            ...
        }

        # LLM优先级：自定义LLM > 配置中的LLM > 全局LLM
        llm = custom_llm or self._get_llm(config.llm_config)
        if llm:
            agent_kwargs["llm"] = llm

        return Agent(**agent_kwargs)

    def _get_llm(self, llm_config: Dict[str, Any] | None = None) -> Optional[LLM]:
        """获取LLM实例，支持缓存"""
        cache_key = f"{config.api_type}_{config.api_model}"
        if cache_key not in self._llm_cache:
            self._llm_cache[cache_key] = LLM(model=config.api_model, api_key=config.api_key)
        return self._llm_cache.get(cache_key)
```

**特点**:
- LLM缓存避免重复创建
- 工具通过GlobalToolRegistry获取
- 支持自定义LLM覆盖

---

## 4. 适配器模式

### 4.1 PlatformAdapter基类

**位置**: `src/ai_write_x/adapters/platform_adapters.py`

```python
class PlatformAdapter(ABC):
    """平台适配器基类"""

    @abstractmethod
    def format_content(self, content_result: ContentResult, **kwargs) -> str:
        """格式化内容"""
        pass

    @abstractmethod
    def publish_content(self, content_result: ContentResult, **kwargs) -> PublishResult:
        """发布内容"""
        pass

    def supports_html(self) -> bool:
        """是否支持HTML格式"""
        return False

    def supports_template(self) -> bool:
        """是否支持模板功能"""
        return False

class WeChatAdapter(PlatformAdapter):
    def supports_html(self) -> bool:
        return True

    def supports_template(self) -> bool:
        return True

    def format_content(self, content_result: ContentResult, **kwargs) -> str:
        """格式化为微信公众号HTML格式"""
        ...
```

### 4.2 UnifiedContentWorkflow中的适配器使用

```python
class UnifiedContentWorkflow:
    def __init__(self):
        self.platform_adapters = {
            PlatformType.WECHAT.value: WeChatAdapter(),
            PlatformType.XIAOHONGSHU.value: XiaohongshuAdapter(),
            ...
        }

    def _transform_content(self, content, publish_platform, **kwargs):
        adapter = self.platform_adapters.get(publish_platform)
        if adapter.supports_html() and config.article_format.upper() == "HTML":
            if config.use_template and adapter.supports_template():
                return self._apply_template_formatting(content, **kwargs)
            else:
                return self._apply_design_formatting(content, publish_platform, **kwargs)
```

---

## 5. 注册表模式

### 5.1 GlobalToolRegistry

```python
class GlobalToolRegistry:
    """全局工具注册表 - 运行时注册和管理工具"""

    def __init__(self):
        self._tools: Dict[str, Type] = {}
        self._initialized = False

    def register_tool(self, name: str, tool_class):
        """注册工具到注册表"""
        self._tools[name] = tool_class

    def get_tool(self, name: str) -> Optional[Type]:
        """获取工具类"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有已注册工具"""
        return list(self._tools.keys())
```

### 5.2 工具注册时机

```python
# 在 BaseWorkflowFramework.__init__ 中
self.tools_registry = GlobalToolRegistry.get_instance()

# 注册工具
self.register_tool("AIForgeSearchTool", AIForgeSearchTool)
self.register_tool("ReadTemplateTool", ReadTemplateTool)
```

---

## 6. 配置智能合并策略

### 6.1 merge_with_user_config

```python
def merge_with_user_config(self, user_config: dict) -> dict:
    """
    智能合并用户配置：以默认配置为基础，保留用户已配置的有效值
    替代复杂的版本迁移逻辑
    """
    merged_config = copy.deepcopy(self.default_config)

    def merge_dict(default_dict, user_dict, path=""):
        for key, user_value in user_dict.items():
            if key not in default_dict:
                continue  # 跳过废弃配置

            default_value = default_dict[key]

            if isinstance(default_value, dict) and isinstance(user_value, dict):
                merge_dict(default_value, user_value, current_path)
            elif self._is_meaningful_value(user_value, default_value):
                default_dict[key] = user_value
                count += 1

    return merged_config
```

### 6.2 _is_meaningful_value

```python
def _is_meaningful_value(self, user_value, default_value) -> bool:
    """判断用户值是否有意义（值得保留）"""
    # 字符串：不保留空字符串
    if isinstance(user_value, str):
        return user_value.strip() != ""
    # 列表：不保留空列表
    if isinstance(user_value, list):
        return bool(user_value) and any(item.strip() for item in user_value if isinstance(item, str))
    # 布尔：只有与默认值不同时才保留
    if isinstance(user_value, bool):
        return user_value != default_value
    ...
```

---

## 7. 数据类定义

### 7.1 base_framework.py中的数据模型

```python
@dataclass
class AgentConfig:
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    llm_config: Dict[str, Any] = field(default_factory=dict)
    allow_delegation: bool = False
    memory: bool = True
    max_rpm: int = 100
    verbose: bool = True
    system_template: Optional[str] = None
    prompt_template: Optional[str] = None
    response_template: Optional[str] = None

@dataclass
class TaskConfig:
    name: str
    description: str
    agent_name: str
    expected_output: str
    context: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    callback: Optional[str] = None
    async_execution: bool = False

@dataclass
class ContentResult:
    """统一的内容结果格式"""
    title: str
    content: str
    summary: str
    content_format: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    content_type: ContentType = ContentType.ARTICLE
```

---

## 8. 工作流配置构建

### 8.1 动态配置生成

```python
class UnifiedContentWorkflow:
    def get_base_content_config(self, **kwargs) -> WorkflowConfig:
        """动态生成基础内容配置，根据平台和需求定制"""
        config = Config.get_instance()
        publish_platform = kwargs.get("publish_platform", PlatformType.WECHAT.value)

        writer_des = f"""基于话题'{{topic}}'和搜索工具获取的最新信息，撰写一篇高质量的文章。
        ...
        文章要求：
        - 标题：当{{platform}}不为空时为"{{platform}}|{{topic}}"，否则为"{{topic}}"
        - 总字数：{config.min_article_len}~{config.max_article_len}字
        ...
        """

        agents = [
            AgentConfig(
                role="内容创作专家",
                name="writer",
                goal="撰写高质量文章",
                backstory="你是一位作家",
                tools=["AIForgeSearchTool"],
            ),
        ]

        tasks = [
            TaskConfig(
                name="write_content",
                description=writer_des,
                agent_name="writer",
                expected_output="文章标题 + 文章正文（标准Markdown格式）",
                context=["analyze_topic"],
            ),
        ]

        return WorkflowConfig(
            name=f"{publish_platform}_content_generation",
            description=f"面向{publish_platform}平台的内容生成工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )
```