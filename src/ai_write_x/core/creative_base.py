from abc import ABC, abstractmethod
from src.ai_write_x.core.base_framework import ContentResult, WorkflowConfig


class CreativeModule(ABC):
    """创意模块基类"""

    @abstractmethod
    def get_workflow_config(self, **kwargs) -> WorkflowConfig:
        """获取创意模块的工作流配置"""
        pass

    @abstractmethod
    def transform(self, base_content: ContentResult, **kwargs) -> ContentResult:
        """应用创意变换"""
        pass
