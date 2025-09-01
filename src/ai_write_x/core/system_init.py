from .tool_registry import GlobalToolRegistry
from ..tools.custom_tool import AIForgeSearchTool
from ..tools.custom_tool import PublisherTool
from ..tools.custom_tool import ReadTemplateTool


def initialize_global_tools():
    """初始化全局工具注册表"""
    registry = GlobalToolRegistry.get_instance()

    # 注册所有可用工具
    registry.register_tool("AIForgeSearchTool", AIForgeSearchTool)
    registry.register_tool("PublisherTool", PublisherTool)
    registry.register_tool("ReadTemplateTool", ReadTemplateTool)

    print("Global tools registered successfully")
    return registry


# 在应用启动时调用
def setup_aiwritex():
    # 1. 首先初始化工具注册表
    initialize_global_tools()

    # 2. 然后初始化其他组件
    from .unified_workflow import UnifiedContentWorkflow

    workflow = UnifiedContentWorkflow()
    return workflow
