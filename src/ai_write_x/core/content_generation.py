import time
from typing import Dict, Any
from crewai import Crew, Process, Task, Agent
from .base_framework import BaseWorkflowFramework, WorkflowConfig, ContentResult, WorkflowType
from .agent_factory import AgentFactory
from .creative_modules import CreativeModule
from .monitoring import WorkflowMonitor
from ..utils import log


class ContentGenerationEngine(BaseWorkflowFramework):
    """纯内容生成引擎，与平台无关"""

    def __init__(self, config: WorkflowConfig, callback_params: Dict[str, Any] = None):
        super().__init__(config)
        self.callback_params = callback_params or {}
        self.agent_factory = AgentFactory()
        self.creative_modules: Dict[str, "CreativeModule"] = {}
        # 添加监控器
        self.monitor = WorkflowMonitor.get_instance()

    def _create_unified_callback(self, callback_type: str):
        """创建统一的回调处理器"""

        def callback_function(output):
            if callback_type == "saver_callback":
                self._handle_save_callback(output)
            elif callback_type == "publisher_callback":
                self._handle_publish_callback(output)

        return callback_function

    def _handle_save_callback(self, output):
        """处理保存回调"""
        from ..tools.custom_tool import SaveArticleTool

        # 提取必要参数
        save_params = {
            "appid": self.callback_params.get("appid", ""),
            "appsecret": self.callback_params.get("appsecret", ""),
            "author": self.callback_params.get("author", ""),
        }

        SaveArticleTool().run(output.raw, **save_params)

    def _handle_publish_callback(self, output):
        """处理发布回调"""
        target_platform = self.callback_params.get("target_platform", "wechat")

        # 通过平台适配器处理发布
        from ..core.system_init import get_platform_adapter

        adapter = get_platform_adapter(target_platform)

        if adapter:
            publish_result = adapter.publish_content(output.raw, **self.callback_params)
            log.print_log(publish_result.message, "status" if publish_result.success else "error")
        else:
            log.print_log(f"不支持的平台: {target_platform}", "error")

    def setup_agents(self) -> Dict[str, Agent]:
        """设置智能体"""
        agents = {}
        for agent_config in self.config.agents:
            agent = self.agent_factory.create_agent(agent_config)
            agents[agent_config.role] = agent
        return agents

    def setup_tasks(self) -> Dict[str, Task]:
        """设置任务"""
        tasks = {}
        for task_config in self.config.tasks:
            # 动态创建任务
            task = Task(
                description=task_config.description,
                expected_output=task_config.expected_output,
                agent=self.agents[task_config.agent_role],
            )

            # 设置上下文依赖
            if task_config.context:
                task.context = [tasks[ctx] for ctx in task_config.context if ctx in tasks]

            # 设置回调
            if task_config.callback and task_config.callback in self.output_handlers:
                task.callback = self.output_handlers[task_config.callback]

            tasks[task_config.name] = task
        return tasks

    def execute_workflow(self, input_data: Dict[str, Any]) -> ContentResult:
        """执行工作流并记录监控数据"""
        start_time = time.time()
        success = False

        try:
            self.validate_config()
            self.agents = self.setup_agents()
            self.tasks = self.setup_tasks()

            # 根据工作流类型选择执行策略
            process_map = {
                WorkflowType.SEQUENTIAL: Process.sequential,
                WorkflowType.HIERARCHICAL: Process.hierarchical,
                WorkflowType.PARALLEL: Process.sequential,  # CrewAI暂不支持真正的并行
                WorkflowType.CUSTOM: Process.sequential,
            }

            process = process_map.get(self.config.workflow_type, Process.sequential)

            crew = Crew(
                agents=list(self.agents.values()),
                tasks=list(self.tasks.values()),
                process=process,
                verbose=True,
            )

            result = crew.kickoff(inputs=input_data)
            parsed_result = self._parse_result(result, input_data)

            success = True
            return parsed_result

        except Exception as e:
            self.monitor.log_error(self.config.name, str(e), input_data)
            raise
        finally:
            # 记录执行指标
            duration = time.time() - start_time
            self.monitor.track_execution(self.config.name, duration, success)

    def _parse_result(self, raw_result: Any, input_data: Dict[str, Any]) -> ContentResult:
        from ..utils.content_parser import ContentParser

        parser = ContentParser()
        parsed_content = parser.parse(str(raw_result))

        return ContentResult(
            title=parsed_content.title or input_data.get("topic", "Untitled"),
            content=parsed_content.content,
            summary=parsed_content.summary or self._generate_summary(parsed_content.content),
            content_type=self.config.content_type,
            metadata={
                "workflow_name": self.config.name,
                "input_data": input_data,
                "agent_count": len(self.agents),
                "task_count": len(self.tasks),
                "parsing_confidence": parsed_content.confidence,
            },
        )

    def _generate_summary(self, content: str) -> str:
        """生成内容摘要"""
        if not content:
            return ""

        # 取前200字符作为摘要
        summary = content[:200] + "..." if len(content) > 200 else content
        return summary

    def register_creative_module(self, name: str, module: "CreativeModule"):
        """注册创意模块"""
        self.creative_modules[name] = module

    def apply_creative_transform(
        self, base_content: ContentResult, creative_mode: str, **kwargs
    ) -> ContentResult:
        """应用创意变换"""
        if creative_mode not in self.creative_modules:
            raise ValueError(f"Unknown creative mode: {creative_mode}")

        module = self.creative_modules[creative_mode]
        return module.transform(base_content, **kwargs)

    def _create_publisher_callback(self):
        """创建平台无关的发布回调"""

        def callback_function(output):
            # 获取目标平台
            target_platform = self.callback_params.get("target_platform", "wechat")

            # 通过平台适配器处理发布
            from ..core.system_init import get_platform_adapter

            adapter = get_platform_adapter(target_platform)

            if adapter:
                # 将所有参数传递给平台适配器，让适配器决定需要哪些参数
                publish_result = adapter.publish_content(
                    output.raw, **self.callback_params  # 传递所有参数，让适配器自行筛选
                )
                log.print_log(
                    publish_result.message, "status" if publish_result.success else "error"
                )
            else:
                log.print_log(f"不支持的平台: {target_platform}", "error")

        return callback_function

    def _create_saver_callback(self):
        """创建平台无关的保存回调"""

        def callback_function(output):
            from ..tools.custom_tool import ContentSaver

            saver = ContentSaver()
            result = saver.process(output.raw)
            log.print_log(result["message"], "status" if result["success"] else "error")

        return callback_function
