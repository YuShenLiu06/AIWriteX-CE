from src.ai_write_x.core.base_framework import ContentResult, WorkflowConfig
from src.ai_write_x.core.base_framework import (
    AgentConfig,
    TaskConfig,
    WorkflowType,
    ContentType,
)
from src.ai_write_x.core.creative_base import CreativeModule


class StyleTransformModule(CreativeModule):
    """文章变身术模块"""

    def get_workflow_config(self, style_target: str = "shakespeare", **kwargs) -> WorkflowConfig:
        """获取文体转换工作流配置"""

        agents = [
            AgentConfig(
                role="内容分析专家",
                name="content_analyzer",
                goal="分析原始内容的核心信息和结构",
                backstory="你是内容分析专家，擅长提取文章精髓和核心观点",
            ),
            AgentConfig(
                role="风格转换专家",
                name="style_transformer",
                goal=f"将内容转换为{style_target}风格",
                backstory=f"你是文体转换大师，能够将任何内容改写成{style_target}风格，保持原意的同时完全改变表达方式",
                tools=["AIForgeSearchTool"],
            ),
            AgentConfig(
                role="风格审核专家",
                name="style_auditor",
                goal="确保转换后的内容既保持原文核心信息，又完美体现目标文体特色",
                backstory="你是文体质量审核专家，能够判断文体转换是否成功，确保内容质量和风格一致性",
            ),
        ]

        tasks = [
            TaskConfig(
                name="analyze_content_structure",
                description="分析原始内容的核心信息、逻辑结构和关键要点，为文体转换做准备",
                agent_name="content_analyzer",
                expected_output="内容结构分析报告（包含核心观点、逻辑框架、关键信息点）",
            ),
            TaskConfig(
                name="transform_style",
                description=f"根据选定的文体风格'{style_target}'，将内容进行创意转换。支持的风格包括：莎士比亚戏剧、侦探小说、科幻小说、古典诗词、现代诗歌、学术论文、新闻报道等",  # noqa 501
                agent_name="style_transformer",
                expected_output="转换后的文章（保持原文核心信息，完全采用目标文体风格）",
                context=["analyze_content_structure"],
            ),
            TaskConfig(
                name="audit_style_quality",
                description="审核文体转换质量，确保既保持原文核心信息完整性，又完美体现目标文体特色",
                agent_name="style_auditor",
                expected_output="最终优化后的文体转换文章",
                context=["transform_style"],
            ),
        ]

        return WorkflowConfig(
            name="style_transform",
            description="文章变身术 - 将同一话题转换为不同文体风格",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        style_target: str = "shakespeare",
        engine_factory=None,
        **kwargs,
    ) -> ContentResult:
        """应用文体转换"""
        # 创建专门的内容生成引擎来执行转换
        if engine_factory is None:
            raise ValueError("engine_factory is required")

        config = self.get_workflow_config(style_target=style_target, **kwargs)
        engine = engine_factory(config)

        # 准备输入数据
        input_data = {
            "topic": base_content.title,
            "original_content": base_content.content,
            "style_target": style_target,
        }

        # 执行转换工作流
        transformed_content = engine.execute_workflow(input_data)

        # 更新元数据
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "style_transform",
                "style_target": style_target,
                "base_content_id": id(base_content),
            }
        )

        return transformed_content


class TimeTravelModule(CreativeModule):
    """时空穿越写作模块"""

    def get_workflow_config(self, time_perspective: str = "ancient", **kwargs) -> WorkflowConfig:
        """获取时空穿越工作流配置"""

        agents = [
            AgentConfig(
                role="时空穿越者",
                name="time_traveler",
                goal="从不同时代视角分析现代话题",
                backstory="你是时空穿越者，能够站在古代、现代、未来的不同时间点，以不同时代的思维方式和知识背景来理解和分析话题",
                tools=["AIForgeSearchTool"],
            ),
            AgentConfig(
                role="历史学家",
                name="historical_analyst",
                goal="提供历史背景和时代特色分析",
                backstory="你是历史学家，深谙各个时代的文化特色、思维方式和表达习惯",
            ),
            AgentConfig(
                role="时空合成者",
                name="temporal_synthesizer",
                goal="综合不同时代视角，创造时空对比内容",
                backstory="你擅长将不同时代的观点融合，创造出具有时空穿越感的独特内容",
            ),
        ]

        tasks = [
            TaskConfig(
                name="time_perspective_analysis",
                description=f"从'{time_perspective}'时代视角分析话题，如'古代人看现在的AI'、'2050年回望今天的热点'",
                agent_name="time_traveler",
                expected_output="时空视角分析（体现不同时代的思维差异和认知特点）",
            ),
            TaskConfig(
                name="historical_context_enhancement",
                description="为时空对比内容添加历史背景和时代特色细节",
                agent_name="historical_analyst",
                expected_output="历史背景增强的内容",
                context=["time_perspective_analysis"],
            ),
            TaskConfig(
                name="temporal_synthesis",
                description="综合时空视角和历史背景，生成最终的时空穿越文章",
                agent_name="temporal_synthesizer",
                expected_output="完整的时空穿越主题文章",
                context=["time_perspective_analysis", "historical_context_enhancement"],
            ),
        ]

        return WorkflowConfig(
            name="time_travel_writing",
            description="时空穿越写作 - 从不同时代视角分析现代话题",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory=None,
        time_perspective: str = "ancient",
        **kwargs,
    ) -> ContentResult:
        """应用时空穿越变换"""
        if engine_factory is None:
            raise ValueError("engine_factory is required")

        config = self.get_workflow_config(time_perspective=time_perspective, **kwargs)
        engine = engine_factory(config)

        input_data = {
            "topic": base_content.title,
            "original_content": base_content.content,
            "time_perspective": time_perspective,
        }

        transformed_content = engine.execute_workflow(input_data)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "time_travel",
                "time_perspective": time_perspective,
                "base_content_id": id(base_content),
            }
        )

        return transformed_content


class RolePlayModule(CreativeModule):
    """角色扮演内容生成模块"""

    def get_workflow_config(self, role_character: str = "celebrity", **kwargs) -> WorkflowConfig:
        """获取角色扮演工作流配置"""

        # 根据角色类型选择不同的智能体配置
        role_configs = {
            "celebrity": AgentConfig(
                role="名人模仿家",
                name="celebrity_agent",
                goal="以知名人物的视角和语调写作",
                backstory="你能模仿各种名人的思维方式、说话风格和观点表达习惯，让读者感受到名人的独特魅力",
            ),
            "expert": AgentConfig(
                role="行业专家",
                name="expert_agent",
                goal="以行业专家身份进行专业分析",
                backstory="你是各领域的专业专家，能够提供深度的专业见解和权威观点",
            ),
            "ordinary": AgentConfig(
                role="普通人",
                name="ordinary_agent",
                goal="以普通人角度感受和表达",
                backstory="你代表普通大众的视角，用接地气的方式表达观点，让内容更贴近读者生活",
            ),
        }

        agents = [
            role_configs.get(role_character, role_configs["celebrity"]),
            AgentConfig(
                role="角色协调员‌",
                name="role_coordinator",
                goal="协调角色扮演内容，确保角色特色鲜明",
                backstory="你是角色扮演协调专家，能够确保内容完美体现选定角色的特色",
            ),
        ]

        tasks = [
            TaskConfig(
                name="role_based_analysis",
                description=f"以'{role_character}'的身份和视角分析话题，体现该角色的独特观点和表达方式",
                agent_name=f"{role_character}_agent",
                expected_output="角色化的内容分析（体现角色特色和观点）",
            ),
            TaskConfig(
                name="role_content_coordination",
                description="协调和优化角色扮演内容，确保角色特色鲜明且内容连贯",
                agent_name="role_coordinator",
                expected_output="最终的角色扮演文章",
                context=["role_based_analysis"],
            ),
        ]

        return WorkflowConfig(
            name="role_play_writing",
            description="角色扮演内容生成 - 以不同角色身份创作内容",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory=None,
        role_character: str = "celebrity",
        **kwargs,
    ) -> ContentResult:
        """应用角色扮演变换"""
        if engine_factory is None:
            raise ValueError("engine_factory is required")

        config = self.get_workflow_config(role_character=role_character, **kwargs)
        engine = engine_factory(config)

        input_data = {
            "topic": base_content.title,
            "original_content": base_content.content,
            "role_character": role_character,
        }

        transformed_content = engine.execute_workflow(input_data)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "role_play",
                "role_character": role_character,
                "base_content_id": id(base_content),
            }
        )

        return transformed_content
