from typing import Dict, Any, List
from .content_generation import ContentGenerationEngine
from .creative_modules import StyleTransformModule, TimeTravelModule, RolePlayModule
from .base_framework import WorkflowConfig, AgentConfig, TaskConfig, WorkflowType, ContentType
from ..adapters.platform_adapters import (
    WeChatAdapter,
    XiaohongshuAdapter,
    DouyinAdapter,
    ToutiaoAdapter,
    BaijiahaoAdapter,
    ZhihuAdapter,
    DoubanAdapter,
)


class UnifiedContentWorkflow:
    """统一的内容工作流编排器"""

    def __init__(self):
        self.content_engine = None
        self.creative_modules = {
            "style_transform": StyleTransformModule(),
            "time_travel": TimeTravelModule(),
            "role_play": RolePlayModule(),
        }
        self.platform_adapters = {
            "wechat": WeChatAdapter(),
            "xiaohongshu": XiaohongshuAdapter(),
            "douyin": DouyinAdapter(),
            "toutiao": ToutiaoAdapter(),
            "baijiahao": BaijiahaoAdapter(),
            "zhihu": ZhihuAdapter(),
            "douban": DoubanAdapter(),
        }

    def get_base_content_config(self) -> WorkflowConfig:
        """获取基础内容生成配置（复用现有的微信创作流程）"""
        agents = [
            AgentConfig(
                role="researcher",
                goal="解析话题，确定文章的核心要点和结构",
                backstory="你是一位内容策略师，擅长从复杂的话题中提炼出关键信息",
            ),
            AgentConfig(
                role="writer",
                goal="根据给定的热门话题和最新搜索数据，撰写高质量文章",
                backstory="你是一位才华横溢的作家，擅长各种文风",
                tools=["AIForgeSearchTool"],
            ),
            AgentConfig(
                role="auditor",
                goal="对生成的文章进行全面质量审核",
                backstory="你是内容质量专家，能够发现文章中的错误和不足",
            ),
        ]

        tasks = [
            TaskConfig(
                name="analyze_topic",
                description="解析话题'{topic}'，确定文章的核心要点和结构",
                agent_role="researcher",
                expected_output="文章大纲和核心要点",
            ),
            TaskConfig(
                name="write_content",
                description="基于分析结果和搜索工具获取的信息，撰写高质量文章",
                agent_role="writer",
                expected_output="完整的文章内容（Markdown格式）",
                context=["analyze_topic"],
            ),
            TaskConfig(
                name="audit_content",
                description="对生成的文章进行质量审核和优化",
                agent_role="auditor",
                expected_output="审核优化后的最终文章",
                context=["write_content"],
            ),
        ]

        return WorkflowConfig(
            name="base_content_generation",
            description="基础内容生成工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def execute(
        self,
        topic: str,
        creative_mode: str = None,
        target_platforms: List[str] = ["wechat"],
        **kwargs,
    ) -> Dict[str, Any]:
        """执行完整的内容生成和发布流程"""

        # 1. 生成基础内容（创意核心）
        base_config = self.get_base_content_config()
        self.content_engine = ContentGenerationEngine(base_config)

        input_data = {
            "topic": topic,
            "platform": kwargs.get("platform", ""),
            "urls": kwargs.get("urls", []),
            "reference_ratio": kwargs.get("reference_ratio", 0.0),
        }

        base_content = self.content_engine.execute_workflow(input_data)

        # 2. 应用创意变换（如果指定）
        final_content = base_content
        if creative_mode and creative_mode in self.creative_modules:
            creative_module = self.creative_modules[creative_mode]
            final_content = creative_module.transform(base_content, **kwargs)

        # 3. 多平台适配和发布
        results = {"base_content": base_content, "final_content": final_content, "platforms": {}}

        for platform in target_platforms:
            if platform in self.platform_adapters:
                adapter = self.platform_adapters[platform]

                # 格式化内容
                formatted_content = adapter.format_content(final_content)

                # 发布内容（如果需要）
                publish_result = False
                if kwargs.get("auto_publish", False):
                    publish_result = adapter.publish_content(formatted_content, **kwargs)

                results["platforms"][platform] = {
                    "formatted_content": formatted_content,
                    "published": publish_result,
                    "adapter": adapter.get_platform_name(),
                }
            else:
                print(f"Warning: Platform {platform} not supported")

        return results

    def register_creative_module(self, name: str, module):
        """注册新的创意模块"""
        self.creative_modules[name] = module

    def register_platform_adapter(self, name: str, adapter):
        """注册新的平台适配器"""
        self.platform_adapters[name] = adapter
