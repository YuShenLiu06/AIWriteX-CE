import time
from typing import Dict, Any
from crewai import Crew, Process, Task, Agent
from .base_framework import BaseWorkflowFramework, WorkflowConfig, ContentResult, WorkflowType
from .agent_factory import AgentFactory
from .creative_modules import CreativeModule
from .monitoring import WorkflowMonitor


class ContentGenerationEngine(BaseWorkflowFramework):
    """纯内容生成引擎，与平台无关"""

    def __init__(self, config: WorkflowConfig):
        super().__init__(config)
        self.agent_factory = AgentFactory()
        self.creative_modules: Dict[str, "CreativeModule"] = {}
        # 添加监控器
        self.monitor = WorkflowMonitor.get_instance()

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
