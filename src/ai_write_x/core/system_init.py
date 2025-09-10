from src.ai_write_x.core.tool_registry import GlobalToolRegistry
from src.ai_write_x.tools.custom_tool import AIForgeSearchTool
from src.ai_write_x.tools.custom_tool import ReadTemplateTool
from src.ai_write_x.core.unified_workflow import UnifiedContentWorkflow
from src.ai_write_x.core.creative_modules import (
    StyleTransformModule,
    TimeTravelModule,
    RolePlayModule,
)
from src.ai_write_x.adapters.platform_adapters import (
    WeChatAdapter,
    XiaohongshuAdapter,
    DouyinAdapter,
    ZhihuAdapter,
    ToutiaoAdapter,
    BaijiahaoAdapter,
    DoubanAdapter,
)
from src.ai_write_x.utils import log


def initialize_global_tools():
    """初始化全局工具注册表"""
    registry = GlobalToolRegistry.get_instance()

    # 注册所有可用工具
    registry.register_tool("AIForgeSearchTool", AIForgeSearchTool)
    registry.register_tool("ReadTemplateTool", ReadTemplateTool)

    return registry


def get_platform_adapter(platform_name: str):
    """获取指定平台的适配器"""

    # 创建临时工作流实例来获取适配器
    workflow = UnifiedContentWorkflow()
    return workflow.platform_adapters.get(platform_name)


# 在应用启动时调用
def setup_aiwritex():
    """完整的系统初始化"""
    # 1. 初始化工具注册表
    initialize_global_tools()

    # 2. 创建统一工作流
    workflow = UnifiedContentWorkflow()

    # 3. 注册所有创意模块
    workflow.register_creative_module("style_transform", StyleTransformModule())
    workflow.register_creative_module("time_travel", TimeTravelModule())
    workflow.register_creative_module("role_play", RolePlayModule())

    # 4. 注册所有平台适配器
    workflow.register_platform_adapter("wechat", WeChatAdapter())
    workflow.register_platform_adapter("xiaohongshu", XiaohongshuAdapter())
    workflow.register_platform_adapter("douyin", DouyinAdapter())
    workflow.register_platform_adapter("zhihu", ZhihuAdapter())
    workflow.register_platform_adapter("toutiao", ToutiaoAdapter())
    workflow.register_platform_adapter("baijiahao", BaijiahaoAdapter())
    workflow.register_platform_adapter("douban", DoubanAdapter())

    log.print_log("AIWriteX 初始化完成")
    return workflow
