from abc import ABC, abstractmethod
from typing import Any, Callable
from dataclasses import dataclass
from src.ai_write_x.core.base_framework import ContentResult, WorkflowConfig


@dataclass
class CreativeConfig:
    """创意模块配置基类"""

    pass


class CreativeModule(ABC):
    """
    创意模块基类 - 使用配置对象模式

    这是最佳的现代设计方案：
    1. 每个模块定义自己的配置类，继承自 CreativeConfig
    2. 基类使用 Union 类型接受所有可能的配置类型
    3. 子类可以指定具体的配置类型，获得完整的类型安全
    4. 完全避免了 **kwargs 的问题
    """

    @abstractmethod
    def get_workflow_config(self, config: Any) -> WorkflowConfig:
        """
        获取创意模块的工作流配置

        Args:
            config: 模块特定的配置对象

        Returns:
            WorkflowConfig: 工作流配置
        """
        pass

    @abstractmethod
    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: Any,
    ) -> ContentResult:
        """
        应用创意变换

        Args:
            base_content: 基础内容
            engine_factory: 内容生成引擎工厂函数
            config: 模块特定的配置对象

        Returns:
            ContentResult: 变换后的内容
        """
        pass
