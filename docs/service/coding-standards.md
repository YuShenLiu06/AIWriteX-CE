# AIWriteX 编码规范

> 最后更新: 2026-05-10

---

## 1. Python 编码规范

### 1.1 基本要求

- 遵循 **PEP 8** 编码规范
- 使用 **type annotations** 注解所有函数签名
- 优先使用 **immutable data structures**

```python
# ✅ 正确示例
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass(frozen=True)
class AgentConfig:
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    llm_config: Dict[str, Any] = field(default_factory=dict)

# ❌ 错误示例
class AgentConfig:
    def __init__(self, name, role, goal, backstory, tools=None):
        self.name = name
        ...
```

### 1.2 格式化工具

| 工具 | 用途 |
|------|------|
| **black** | 代码格式化 |
| **isort** | import排序 |
| **ruff** | 代码检查 (linting) |

---

## 2. 代码组织原则

### 2.1 文件大小

| 指标 | 最大值 | 推荐值 |
|------|--------|--------|
| 单个函数行数 | 50行 | <30行 |
| 单个文件行数 | 800行 | 200-400行 |

### 2.2 目录结构

```
src/ai_write_x/
├── core/          # 核心框架 (工作流/Agent/配置)
├── tools/         # 工具模块 (搜索/发布/模板)
├── adapters/      # 平台适配器
├── creative/      # 创意引擎
├── web/           # Web模块 (FastAPI/Web UI)
├── utils/         # 工具函数
├── config/        # 配置管理
└── license/       # 许可证
```

---

## 3. 命名规范

### 3.1 类命名

```python
# 使用 PascalCase
class UnifiedContentWorkflow
class DimensionalCreativeEngine
class AgentFactory

# 抽象基类添加 Adapter/Base 后缀
class PlatformAdapter(ABC)
class BaseWorkflowFramework(ABC)
```

### 3.2 函数/方法命名

```python
# 使用 snake_case
def get_instance()
def execute_workflow()
def apply_dimensional_creative()

# 私有方法以 _ 开头
def _generate_base_content()
def _save_content()
```

### 3.3 常量命名

```python
# 使用 UPPER_SNAKE_CASE
MAX_ARTICLE_LEN = 2000
DEFAULT_PLATFORM = "wechat"

# 配置键使用小写 + 下划线
api_type = "OpenRouter"
api_key = "OPENROUTER_API_KEY"
```

---

## 4. 日志规范

### 4.1 日志级别

```python
from src.ai_write_x.utils import log

log.print_log("常规操作信息", "info")      # INFO
log.print_log("潜在问题警告", "warning")   # WARN
log.print_log("错误事件详情", "error")     # ERROR
log.print_log("调试详细信息", "internal")   # DEBUG (内部使用)
```

### 4.2 关键日志位置

| 位置 | 日志级别 | 说明 |
|------|---------|------|
| 启动/结束 | INFO | 记录应用生命周期 |
| 用户输入 | INFO | 记录话题/参数 |
| API请求/响应 | INFO | 记录外部调用 |
| 数据处理 | DEBUG | 记录详细流程 |
| 错误捕获 | ERROR | 记录异常堆栈 |

---

## 5. 错误处理

### 5.1 原则

- **总是处理错误**: 每层都要有错误处理
- **提供友好消息**: UI层用用户语言
- **记录详细信息**: 服务端记录完整堆栈
- **永不静默吞没**: 不使用空 except 块

### 5.2 示例

```python
# ✅ 正确示例
try:
    result = self.content_engine.execute_workflow(input_data)
except Exception as e:
    self.monitor.log_error("unified_workflow", str(e), {"topic": topic})
    raise WorkflowExecutionError(f"内容生成失败: {e}") from e

# ❌ 错误示例
try:
    result = self.content_engine.execute_workflow(input_data)
except:
    pass
```

---

## 6. 输入验证

### 6.1 验证时机

- **系统边界**: 所有外部输入都要验证
- **尽早失败**: fail fast with clear message
- **不信任外部数据**: API响应/用户输入/文件内容

### 6.2 配置验证

```python
def validate_config(self):
    """验证配置,仅在 CrewAI 执行时调用"""
    api_keys = api_config.get("api_key", [])
    if not api_keys or not any(api_keys):
        self.error_message = f"未配置API KEY，请打开配置填写{api_type}的api_key"
        return False
```

---

## 7. 禁止事项

| 禁止 | 正确做法 |
|------|---------|
| 使用 `print()` | 使用 `logging` 模块 |
| 硬编码值 | 使用常量或配置 |
| 空 except 块 | 具体异常处理 |
| 深度嵌套 (>4层) | 提取函数 |
| 重复代码 | 抽象为公共函数 |

---

## 8. 单例模式使用场景

| 类 | 模式 | 说明 |
|------|------|------|
| `Config` | 单例 + RLock | 全局配置管理 |
| `WorkflowMonitor` | 单例 | 工作流监控 |
| `GlobalToolRegistry` | 单例 | 全局工具注册表 |