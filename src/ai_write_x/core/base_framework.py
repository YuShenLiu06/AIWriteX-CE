from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from crewai import Agent, Crew, Task, LLM
from dataclasses import dataclass, field
from enum import Enum
import threading
from datetime import datetime


class WorkflowType(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    CUSTOM = "custom"


class ContentType(Enum):
    ARTICLE = "article"
    SOCIAL_POST = "social_post"
    VIDEO_SCRIPT = "video_script"
    PODCAST_SCRIPT = "podcast_script"


@dataclass
class AgentConfig:
    role: str
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    llm_config: Dict[str, Any] = field(default_factory=dict)
    allow_delegation: bool = False
    memory: bool = True
    max_rpm: int = 100
    verbose: bool = True


@dataclass
class TaskConfig:
    name: str
    description: str
    agent_role: str
    expected_output: str
    context: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    callback: Optional[str] = None
    async_execution: bool = False


@dataclass
class WorkflowConfig:
    name: str
    description: str
    workflow_type: WorkflowType
    content_type: ContentType
    agents: List[AgentConfig]
    tasks: List[TaskConfig]
    output_handlers: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentResult:
    """统一的内容结果格式"""

    title: str
    content: str
    summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    content_type: ContentType = ContentType.ARTICLE


class BaseWorkflowFramework(ABC):
    """通用工作流框架基类"""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.tools_registry: Dict[str, Any] = {}
        self.output_handlers: Dict[str, Any] = {}
        self._lock = threading.Lock()

    @abstractmethod
    def setup_agents(self) -> Dict[str, Agent]:
        """设置智能体"""
        pass

    @abstractmethod
    def setup_tasks(self) -> Dict[str, Task]:
        """设置任务"""
        pass

    @abstractmethod
    def execute_workflow(self, input_data: Dict[str, Any]) -> ContentResult:
        """执行工作流"""
        pass

    def register_tool(self, name: str, tool_class):
        """注册工具"""
        with self._lock:
            self.tools_registry[name] = tool_class

    def register_output_handler(self, name: str, handler):
        """注册输出处理器"""
        with self._lock:
            self.output_handlers[name] = handler

    def validate_config(self) -> bool:
        """验证配置有效性"""
        # 验证智能体角色是否在任务中被引用
        agent_roles = {agent.role for agent in self.config.agents}
        task_agent_roles = {task.agent_role for task in self.config.tasks}

        if not task_agent_roles.issubset(agent_roles):
            missing_roles = task_agent_roles - agent_roles
            raise ValueError(f"Missing agent roles: {missing_roles}")

        return True
