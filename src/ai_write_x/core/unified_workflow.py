import time
from typing import Dict, Any, List
from .creative_modules import StyleTransformModule, TimeTravelModule, RolePlayModule
from .base_framework import (
    WorkflowConfig,
    AgentConfig,
    TaskConfig,
    WorkflowType,
    ContentType,
    ContentResult,
)
from ..adapters.platform_adapters import (
    WeChatAdapter,
    XiaohongshuAdapter,
    DouyinAdapter,
    ToutiaoAdapter,
    BaijiahaoAdapter,
    ZhihuAdapter,
    DoubanAdapter,
)
from .monitoring import WorkflowMonitor
from ..config.config import Config


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
        self.monitor = WorkflowMonitor.get_instance()

    def get_base_content_config(self, target_platform: str = "wechat", **kwargs) -> WorkflowConfig:
        """动态生成基础内容配置，根据平台和需求定制"""
        config = Config.get_instance()

        # 获取平台适配器能力
        from ..core.system_init import get_platform_adapter

        adapter = get_platform_adapter(target_platform)

        # 基础配置
        agents = [
            AgentConfig(
                role="researcher",
                goal="解析话题，确定文章的核心要点和结构",
                backstory="你是一位内容策略师",
            ),
            AgentConfig(
                role="writer",
                goal="撰写高质量文章",
                backstory="你是一位作家",
                tools=["AIForgeSearchTool"],
            ),
        ]

        tasks = [
            TaskConfig(
                name="analyze_topic",
                description="解析话题'{topic}'",
                agent_role="researcher",
                expected_output="文章大纲",
            ),
            TaskConfig(
                name="write_content",
                description="撰写文章。平台：{platform}，参考链接：{urls}，借鉴比例：{reference_ratio}",
                agent_role="writer",
                expected_output="完整文章",
                context=["analyze_topic"],
            ),
        ]

        # 动态添加审核（基于配置）
        if config.need_auditor:
            agents.append(AgentConfig(role="auditor", goal="质量审核", backstory="质量专家"))
            tasks.append(
                TaskConfig(
                    name="audit_content",
                    description="质量审核",
                    agent_role="auditor",
                    expected_output="审核后文章",
                    context=["write_content"],
                )
            )

        # 动态添加格式处理（基于平台能力和配置）
        last_task_context = ["audit_content"] if config.need_auditor else ["write_content"]

        if adapter and adapter.supports_html() and config.article_format.upper() == "HTML":
            if config.use_template and adapter.supports_template():
                # 模板处理路径
                agents.append(
                    AgentConfig(
                        role="templater",
                        goal="模板处理",
                        backstory="模板专家",
                        tools=["ReadTemplateTool"],
                    )
                )
                tasks.append(
                    TaskConfig(
                        name="template_content",
                        description="使用模板格式化内容",
                        agent_role="templater",
                        expected_output="模板HTML",
                        context=last_task_context,
                        callback="publisher_callback",
                    )
                )
            else:
                # 设计器处理路径
                agents.append(AgentConfig(role="designer", goal="HTML设计", backstory="设计专家"))
                tasks.append(
                    TaskConfig(
                        name="design_content",
                        description="HTML设计",
                        agent_role="designer",
                        expected_output="设计HTML",
                        context=last_task_context,
                        callback="publisher_callback",
                    )
                )
        else:
            # 保存路径（非HTML或不支持HTML的平台）
            agents.append(AgentConfig(role="saver", goal="保存文章", backstory="保存专家"))
            tasks.append(
                TaskConfig(
                    name="save_article",
                    description="保存文章",
                    agent_role="saver",
                    expected_output="保存结果",
                    context=last_task_context,
                    callback="saver_callback",
                )
            )

        return WorkflowConfig(
            name=f"{target_platform}_content_generation",
            description=f"面向{target_platform}平台的内容生成工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def _generate_base_content(self, topic: str, **kwargs) -> ContentResult:
        """生成基础内容 - 传递平台信息"""
        from .content_generation import ContentGenerationEngine

        # 获取目标平台
        target_platform = kwargs.get("target_platform", "wechat")

        # 动态获取配置
        base_config = self.get_base_content_config(target_platform=target_platform, **kwargs)

        # 准备回调参数（包含平台信息）
        callback_params = dict(kwargs)  # 复制所有参数
        callback_params["target_platform"] = target_platform

        # 创建内容生成引擎
        self.content_engine = ContentGenerationEngine(base_config, callback_params)

        # 准备输入数据
        config = Config.get_instance()
        input_data = {
            "topic": topic,
            "platform": kwargs.get("platform", ""),
            "urls": kwargs.get("urls", []),
            "reference_ratio": kwargs.get("reference_ratio", 0.0),
            "min_article_len": config.min_article_len,
            "max_article_len": config.max_article_len,
        }

        return self.content_engine.execute_workflow(input_data)

    def execute(
        self, topic: str, creative_mode: str = None, target_platforms: List[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """执行统一内容工作流并监控"""
        start_time = time.time()
        success = False
        results = {}

        try:
            # 1. 生成基础内容
            base_content = self._generate_base_content(topic, **kwargs)

            # 2. 应用创意变换
            if creative_mode and creative_mode in self.creative_modules:
                final_content = self.creative_modules[creative_mode].transform(
                    base_content, **kwargs
                )
            else:
                final_content = base_content

            # 3. 平台适配和发布
            platform_results = {}
            for platform in target_platforms or []:
                if platform in self.platform_adapters:
                    adapter = self.platform_adapters[platform]
                    formatted_content = adapter.format_content(final_content)
                    platform_results[platform] = {
                        "formatted_content": formatted_content,
                        "published": False,
                    }

            results = {
                "base_content": base_content,
                "final_content": final_content,
                "platform_results": platform_results,
            }

            success = True
            return results

        except Exception as e:
            self.monitor.log_error(
                "unified_workflow", str(e), {"topic": topic, "creative_mode": creative_mode}
            )
            raise
        finally:
            duration = time.time() - start_time
            self.monitor.track_execution("unified_workflow", duration, success, {"topic": topic})

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "workflow_metrics": self.monitor.get_metrics(),
            "recent_executions": self.monitor.get_recent_logs(limit=20),
            "system_status": "healthy" if self._check_system_health() else "degraded",
        }

    def _check_system_health(self) -> bool:
        """检查系统健康状态"""
        metrics = self.monitor.get_metrics()
        for workflow_name, workflow_metrics in metrics.items():
            if workflow_metrics.get("success_rate", 0) < 0.8:  # 成功率低于80%
                return False
        return True

    def register_creative_module(self, name: str, module):
        """注册新的创意模块"""
        self.creative_modules[name] = module

    def register_platform_adapter(self, name: str, adapter):
        """注册新的平台适配器"""
        self.platform_adapters[name] = adapter
