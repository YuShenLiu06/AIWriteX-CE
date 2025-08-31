from typing import Dict, Any
from crewai import Crew, Process, Task, Agent
from .base_framework import BaseWorkflowFramework, WorkflowConfig, WorkflowType, ContentResult
from .agent_factory import AgentFactory
from ..tools.custom_tool import AIForgeSearchTool
from .creative_modules import CreativeModule


class ContentGenerationEngine(BaseWorkflowFramework):
    """纯内容生成引擎，与平台无关"""

    def __init__(self, config: WorkflowConfig):
        super().__init__(config)
        self.agent_factory = AgentFactory()
        self.creative_modules: Dict[str, "CreativeModule"] = {}

        # 注册基础工具
        self.agent_factory.register_tool("AIForgeSearchTool", AIForgeSearchTool)

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
        """执行工作流"""
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

        # 执行工作流
        result = crew.kickoff(inputs=input_data)

        # 解析结果为标准格式
        return self._parse_result(result, input_data)

    def _parse_result(self, raw_result: Any, input_data: Dict[str, Any]) -> ContentResult:
        """解析原始结果为标准内容格式"""
        # 这里需要根据实际的CrewAI输出格式进行解析
        content_str = str(raw_result)

        # 简单的标题提取逻辑（可以根据需要优化）
        lines = content_str.split("\n")
        title = input_data.get("topic", "Untitled")

        # 提取第一行作为标题（如果格式合适）
        if lines and lines[0].strip() and len(lines[0]) < 100:
            title = lines[0].strip().lstrip("#").strip()
            content = "\n".join(lines[1:]).strip()
        else:
            content = content_str

        # 生成摘要（取前200字符）
        summary = content[:200] + "..." if len(content) > 200 else content

        return ContentResult(
            title=title,
            content=content,
            summary=summary,
            content_type=self.config.content_type,
            metadata={
                "workflow_name": self.config.name,
                "input_data": input_data,
                "agent_count": len(self.agents),
                "task_count": len(self.tasks),
            },
        )

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
