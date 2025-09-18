from typing import List, Callable, Any
from dataclasses import dataclass

from src.ai_write_x.core.base_framework import ContentResult, WorkflowConfig
from src.ai_write_x.core.base_framework import (
    AgentConfig,
    TaskConfig,
    WorkflowType,
    ContentType,
    CreativeDimension,
)
from src.ai_write_x.core.creative_base import CreativeModule, CreativeConfig


@dataclass
class MultiDimensionalConfig(CreativeConfig):
    """多维度创意模块配置"""

    dimensions: List[CreativeDimension]


@dataclass
class CulturalFusionConfig(CreativeConfig):
    """文化融合模块配置"""

    cultural_perspective: str


@dataclass
class StyleTransformConfig(CreativeConfig):
    """文体转换模块配置"""

    style_target: str


@dataclass
class DynamicTransformConfig(CreativeConfig):
    """动态变形模块配置"""

    scenario: str


@dataclass
class GenreFusionConfig(CreativeConfig):
    """跨体裁融合模块配置"""

    genre_combination: List[str]


@dataclass
class TimeTravelConfig(CreativeConfig):
    """时空穿越模块配置"""

    time_perspective: str


@dataclass
class RolePlayConfig(CreativeConfig):
    """角色扮演模块配置"""

    role_character: str
    custom_character: str = ""


class MultiDimensionalCreativeModule(CreativeModule):
    """多维度创意模块 - 支持组合式创意变换"""

    def get_workflow_config(self, config: MultiDimensionalConfig) -> WorkflowConfig:
        """基于多个创意维度生成工作流配置"""
        # 构建创意指令
        dimension_instructions = []
        for dim in config.dimensions:
            dimension_instructions.append(f"- {dim.name}({dim.value}): {dim.description}")

        dimension_text = "\n".join(dimension_instructions)

        agents = [
            AgentConfig(
                role="多维度创意专家",
                name="multi_dimensional_creator",
                goal="融合多个创意维度，创造独特的内容表达",
                backstory=f"""你是多维度创意专家，能够同时运用多个创意维度来重新演绎内容。

当前创意维度组合：
{dimension_text}

你需要将这些维度有机融合，创造出既保持原内容核心信息，又具有多重创意特色的作品。""",
                personality_traits={
                    "creativity_level": "high",
                    "dimension_fusion_ability": "expert",
                    "content_preservation": "strict",
                },
            ),
        ]

        tasks = [
            TaskConfig(
                name="multi_dimensional_transformation",
                description=f"""基于以下创意维度组合，对原始内容进行多维度创意变换：

创意维度组合：
{dimension_text}

变换要求：
1. 保持原内容'{{original_content}}'的所有核心信息和要点
2. 将每个创意维度的特色融入到内容中
3. 确保各维度之间的和谐统一，避免冲突
4. 创造出独特而富有创意的表达方式
5. 保持内容的逻辑性和可读性

输出要求：
- 完整保留原文信息量
- 体现所有指定创意维度的特色
- 创造性地融合不同维度的表达方式""",
                agent_name="multi_dimensional_creator",
                expected_output="融合多个创意维度的创新内容",
                creative_dimensions=config.dimensions,
            ),
        ]

        return WorkflowConfig(
            name="multi_dimensional_creative",
            description="多维度创意变换工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
            creative_dimensions=config.dimensions,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: MultiDimensionalConfig,
    ) -> ContentResult:
        """应用多维度创意变换"""
        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "dimensions": [
                {"name": d.name, "value": d.value, "description": d.description}
                for d in config.dimensions
            ],
        }

        transformed_content = engine.execute_workflow(input_data)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "multi_dimensional",
                "applied_dimensions": [d.value for d in config.dimensions],
                "dimension_count": len(config.dimensions),
                "base_content_id": id(base_content),
            }
        )

        # 标记应用的创意维度
        transformed_content.creative_dimensions_applied = config.dimensions

        return transformed_content


class CulturalFusionModule(CreativeModule):
    """文化融合模块 - 跨文化视角内容创作"""

    def __init__(self):
        super().__init__()
        self.cultural_elements = {
            "eastern_philosophy": {
                "name": "东方哲学",
                "elements": ["道家思想", "佛教禅意", "儒家理念", "阴阳平衡"],
                "expression_style": "含蓄深远，寓意丰富",
                "typical_phrases": ["道法自然", "禅意悠远", "天人合一", "中庸之道"],
            },
            "western_logic": {
                "name": "西方思辨",
                "elements": ["苏格拉底式对话", "笛卡尔理性主义", "批判思维", "逻辑分析"],
                "expression_style": "条理清晰，逻辑严密",
                "typical_phrases": ["理性分析", "逻辑推理", "批判思考", "实证精神"],
            },
            "japanese_mono": {
                "name": "日式物哀",
                "elements": ["瞬间美学", "季节感知", "淡淡哀愁", "简约美学"],
                "expression_style": "细腻敏感，意境深远",
                "typical_phrases": ["物の哀れ", "侘寂美学", "刹那芳华", "静谧时光"],
            },
            "french_romance": {
                "name": "法式浪漫",
                "elements": ["艺术气息", "优雅情调", "浪漫主义", "文化品味"],
                "expression_style": "优雅精致，充满诗意",
                "typical_phrases": ["艺术人生", "优雅生活", "浪漫情怀", "文化品味"],
            },
            "american_freedom": {
                "name": "美式自由",
                "elements": ["个人主义", "追求自由", "创新精神", "实用主义"],
                "expression_style": "直接坦率，积极向上",
                "typical_phrases": ["自由精神", "个人奋斗", "创新思维", "实用价值"],
            },
        }

    def get_workflow_config(self, config: CulturalFusionConfig) -> WorkflowConfig:
        """获取文化融合工作流配置"""
        culture_info = self.cultural_elements.get(
            config.cultural_perspective, self.cultural_elements["eastern_philosophy"]
        )

        agents = [
            AgentConfig(
                role=f"{culture_info['name']}文化专家",
                name="cultural_expert",
                goal=f"运用{culture_info['name']}的视角和思维方式重新诠释内容",
                backstory=f"""你是{culture_info['name']}文化专家，深谙以下文化元素：

文化元素：{', '.join(culture_info['elements'])}
表达风格：{culture_info['expression_style']}
典型表达：{', '.join(culture_info['typical_phrases'])}

你能够用{culture_info['name']}的独特视角和思维方式来理解和表达任何话题，为内容注入深厚的文化底蕴。""",
            ),
        ]

        tasks = [
            TaskConfig(
                name="cultural_reinterpretation",
                description=f"""运用{culture_info['name']}的文化视角重新诠释内容：

原始内容：'{{original_content}}'

文化融合要求：
1. 保持原内容的所有核心信息和观点
2. 融入{culture_info['name']}的文化元素：{', '.join(culture_info['elements'])}
3. 采用{culture_info['expression_style']}的表达风格
4. 适当运用典型表达方式，但要自然不做作
5. 让读者感受到浓厚的文化氛围和独特视角

输出：既保持原文完整性，又充满{culture_info['name']}文化特色的内容""",
                agent_name="cultural_expert",
                expected_output=f"融入{culture_info['name']}文化特色的内容",
            ),
        ]

        return WorkflowConfig(
            name=f"cultural_fusion_{config.cultural_perspective}",
            description=f"{culture_info['name']}文化融合工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: CulturalFusionConfig,
    ) -> ContentResult:
        """应用文化融合变换"""
        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "cultural_perspective": config.cultural_perspective,
        }

        transformed_content = engine.execute_workflow(input_data)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "cultural_fusion",
                "cultural_perspective": config.cultural_perspective,
                "culture_name": self.cultural_elements.get(config.cultural_perspective, {}).get(
                    "name", config.cultural_perspective
                ),
                "base_content_id": id(base_content),
            }
        )

        return transformed_content


class StyleTransformModule(CreativeModule):
    """文章变身术模块"""

    def get_workflow_config(self, config: StyleTransformConfig) -> WorkflowConfig:
        """文体转换工作流配置"""
        agents = [
            AgentConfig(
                role="风格转换专家",
                name="style_transformer",
                goal=f"将内容转换为{config.style_target}风格并进行质量审核",
                backstory=f"你是文体转换大师，能够将任何内容改写成{config.style_target}风格，同时确保质量",
            ),
        ]

        tasks = [
            TaskConfig(
                name="transform_and_audit_style",
                description=f"""将原始内容'{{original_content}}'转换为{config.style_target}风格。

转换要求：
1. 保持原文所有核心信息和要点的完整性
2. 完全采用{config.style_target}的表达风格和语言特色
3. 确保转换后内容逻辑清晰连贯
4. 体现{config.style_target}风格的典型特征
5. 进行质量审核和必要优化

支持的风格：莎士比亚戏剧、侦探小说、科幻小说、古典诗词、现代诗歌、学术论文、新闻报道等""",
                agent_name="style_transformer",
                expected_output=f"转换为{config.style_target}风格的优质文章",
            ),
        ]

        return WorkflowConfig(
            name="simplified_style_transform",
            description="文章风格转换工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: StyleTransformConfig,
    ) -> ContentResult:
        """应用文体转换"""
        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "style_target": config.style_target,
        }

        # 执行转换工作流
        transformed_content = engine.execute_workflow(input_data)

        # 更新元数据
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "style_transform",
                "style_target": config.style_target,
                "base_content_id": id(base_content),
            }
        )

        return transformed_content


class DynamicTransformModule(CreativeModule):
    """动态内容变形器 - 将内容转换为不同场景和形式"""

    def __init__(self):
        super().__init__()
        self.scenarios = {
            "elevator_pitch": {
                "name": "电梯演讲版",
                "constraints": "2分钟内说完，抓住核心要点",
                "style": "简洁有力，突出重点",
            },
            "bedtime_story": {
                "name": "睡前故事版",
                "constraints": "温和平静，富有想象力",
                "style": "温暖治愈，寓教于乐",
            },
            "debate_format": {
                "name": "辩论赛版",
                "constraints": "逻辑清晰，论据充分",
                "style": "理性分析，条理分明",
            },
            "social_media": {
                "name": "社交媒体版",
                "constraints": "吸引眼球，易于传播",
                "style": "生动有趣，互动性强",
            },
        }

    def get_workflow_config(self, config: DynamicTransformConfig) -> WorkflowConfig:
        """获取动态变形工作流配置"""

        scenario_info = self.scenarios.get(
            config.scenario,
            {"name": config.scenario, "constraints": "按照指定场景要求", "style": "符合场景特点"},
        )

        agents = [
            AgentConfig(
                role=f"内容变形专家 - {scenario_info['name']}",
                name="dynamic_transformer",
                goal=f"将内容转换为{scenario_info['name']}格式",
                backstory=f"""你是{scenario_info['name']}的专业转换专家。

你的专长：
- 理解{scenario_info['name']}的特点和要求
- 约束条件：{scenario_info['constraints']}
- 表达风格：{scenario_info['style']}
- 保持原文核心信息不变

你能够将任何内容巧妙地转换为{scenario_info['name']}格式，既符合场景要求，又保持信息完整性。""",
            ),
        ]

        tasks = [
            TaskConfig(
                name="dynamic_content_transform",
                description=f"""将原始内容转换为{scenario_info['name']}格式。

转换要求：
1. 严格遵循{scenario_info['name']}的特点
2. 约束条件：{scenario_info['constraints']}
3. 表达风格：{scenario_info['style']}
4. 保持原文'{{original_content}}'的核心信息
5. 适应目标场景的表达习惯

请创作出符合{scenario_info['name']}要求的内容版本。""",
                agent_name="dynamic_transformer",
                expected_output=f"符合{scenario_info['name']}格式的转换内容",
            ),
        ]

        return WorkflowConfig(
            name=f"dynamic_transform_{config.scenario}",
            description=f"动态内容变形 - {scenario_info['name']}",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: DynamicTransformConfig,
    ) -> ContentResult:
        """应用动态变形转换"""

        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "scenario": config.scenario,
        }

        transformed_content = engine.execute_workflow(input_data)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "dynamic_transform",
                "scenario": config.scenario,
                "base_content_id": id(base_content),
            }
        )

        return transformed_content


class GenreFusionModule(CreativeModule):
    """跨体裁融合模块 - 混合不同文学体裁的创作"""

    def __init__(self):
        super().__init__()
        self.genres = {
            "sci_fi": {
                "name": "科幻",
                "elements": ["未来技术", "科学设定", "思辨性", "想象力"],
                "style": "理性推演，充满想象",
            },
            "martial_arts": {
                "name": "武侠",
                "elements": ["江湖情义", "武功秘籍", "侠客精神", "恩怨情仇"],
                "style": "豪迈洒脱，快意恩仇",
            },
            "mystery": {
                "name": "推理",
                "elements": ["悬疑氛围", "逻辑推理", "线索布局", "真相揭示"],
                "style": "严密逻辑，悬念迭起",
            },
            "romance": {
                "name": "爱情",
                "elements": ["情感描写", "心理刻画", "浪漫情节", "情感冲突"],
                "style": "细腻感人，情真意切",
            },
            "horror": {
                "name": "恐怖",
                "elements": ["恐怖氛围", "心理压迫", "悬疑元素", "惊悚情节"],
                "style": "紧张刺激，扣人心弦",
            },
        }

    def get_workflow_config(self, config: GenreFusionConfig) -> WorkflowConfig:
        """获取跨体裁融合工作流配置"""

        genre_descriptions = []
        for genre in config.genre_combination:
            if genre in self.genres:
                info = self.genres[genre]
                genre_descriptions.append(
                    f"- {info['name']}：{info['style']}，融入{', '.join(info['elements'])}"
                )

        fusion_text = "\n".join(genre_descriptions)

        agents = [
            AgentConfig(
                role="跨体裁融合大师",
                name="genre_fusion_master",
                goal="巧妙融合多种文学体裁的特色元素",
                backstory=f"""你是跨体裁融合大师，擅长将不同文学体裁的精华融为一体。

当前融合体裁：
{fusion_text}

你能够：
- 识别每种体裁的核心特征
- 巧妙地将不同体裁元素有机结合
- 创造出独特而和谐的跨体裁作品
- 保持各体裁特色的同时避免冲突""",
            ),
        ]

        tasks = [
            TaskConfig(
                name="genre_fusion_creation",
                description=f"""将原始内容进行跨体裁融合创作。

融合体裁：
{fusion_text}

创作要求：
1. 基于原文'{{original_content}}'进行体裁融合改写
2. 巧妙融入所有指定体裁的典型元素
3. 保持各体裁特色的平衡，避免突兀
4. 创造独特的跨体裁阅读体验
5. 保持原文的核心信息和价值

请创作出融合多种体裁特色的创新内容。""",
                agent_name="genre_fusion_master",
                expected_output="融合多种体裁特色的创新文学作品",
            ),
        ]

        return WorkflowConfig(
            name="genre_fusion",
            description="跨体裁融合创作工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: GenreFusionConfig,
    ) -> ContentResult:
        """应用跨体裁融合转换"""

        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "genre_combination": config.genre_combination,
        }

        transformed_content = engine.execute_workflow(input_data)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "genre_fusion",
                "genre_combination": config.genre_combination,
                "base_content_id": id(base_content),
            }
        )

        return transformed_content


class TimeTravelModule(CreativeModule):
    """时空穿越模块 - 不同时代视角的内容重写"""

    def __init__(self):
        super().__init__()
        self.time_perspectives = {
            "ancient_china": {
                "name": "古代中国",
                "period": "唐宋明清",
                "style": "文言雅致，诗词韵味",
                "elements": ["诗词歌赋", "琴棋书画", "儒道释思想", "君臣民情"],
            },
            "medieval_europe": {
                "name": "中世纪欧洲",
                "period": "5-15世纪",
                "style": "骑士精神，宗教色彩",
                "elements": ["骑士道", "城堡贵族", "宗教信仰", "封建制度"],
            },
            "industrial_age": {
                "name": "工业时代",
                "period": "18-19世纪",
                "style": "理性务实，进步思维",
                "elements": ["科技进步", "工业革命", "社会变革", "启蒙思想"],
            },
            "future_2100": {
                "name": "2100年未来",
                "period": "22世纪",
                "style": "科技感强，前瞻思维",
                "elements": ["人工智能", "太空殖民", "生物技术", "可持续发展"],
            },
        }

    def get_workflow_config(self, config: TimeTravelConfig) -> WorkflowConfig:
        """获取时空穿越工作流配置"""

        time_info = self.time_perspectives.get(
            config.time_perspective,
            {
                "name": config.time_perspective,
                "period": "指定时代",
                "style": "符合时代特点",
                "elements": ["时代特色"],
            },
        )

        agents = [
            AgentConfig(
                role=f"{time_info['name']}时代学者",
                name="time_scholar",
                goal=f"以{time_info['name']}的视角重新阐释内容",
                backstory=f"""你是{time_info['name']}（{time_info['period']}）的博学学者。

时代背景：
- 历史时期：{time_info['period']}
- 表达风格：{time_info['style']}
- 时代元素：{', '.join(time_info['elements'])}

你能够：
- 深刻理解{time_info['name']}的文化背景
- 运用该时代的语言风格和思维方式
- 将现代内容转化为符合时代特点的表达
- 融入时代的典型元素和价值观念""",
            ),
        ]

        tasks = [
            TaskConfig(
                name="time_travel_rewrite",
                description=f"""以{time_info['name']}的视角重写内容。

时空设定：
- 时代：{time_info['period']}
- 风格：{time_info['style']}
- 元素：{', '.join(time_info['elements'])}

重写要求：
1. 将原文'{{original_content}}'转换为{time_info['name']}的表达方式
2. 融入该时代的典型元素和思维模式
3. 使用符合时代特点的语言风格
4. 保持原文的核心观点和价值
5. 体现时代的文化背景和价值观

请创作出具有{time_info['name']}时代特色的内容版本。""",
                agent_name="time_scholar",
                expected_output=f"具有{time_info['name']}时代特色的重写内容",
            ),
        ]

        return WorkflowConfig(
            name=f"time_travel_{config.time_perspective}",
            description=f"时空穿越 - {time_info['name']}",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: TimeTravelConfig,
    ) -> ContentResult:
        """应用时空穿越转换"""

        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "time_perspective": config.time_perspective,
        }

        transformed_content = engine.execute_workflow(input_data)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "time_travel",
                "time_perspective": config.time_perspective,
                "base_content_id": id(base_content),
            }
        )

        return transformed_content


class RolePlayModule(CreativeModule):
    """角色扮演模块 - 以特定角色身份重写内容"""

    def __init__(self):
        super().__init__()
        self.role_characters = {
            "philosopher": {
                "name": "哲学家",
                "traits": ["深邃思考", "逻辑严密", "善于思辨", "追求真理"],
                "style": "理性分析，深度思考",
                "expression": "喜欢探讨本质，提出深刻问题",
            },
            "poet": {
                "name": "诗人",
                "traits": ["敏感细腻", "想象丰富", "情感充沛", "艺术气质"],
                "style": "诗意表达，意象丰富",
                "expression": "善用比喻和象征，语言优美",
            },
            "scientist": {
                "name": "科学家",
                "traits": ["理性客观", "严谨求实", "逻辑清晰", "追求真相"],
                "style": "数据驱动，实证分析",
                "expression": "用事实说话，逻辑推理",
            },
            "child": {
                "name": "儿童",
                "traits": ["天真好奇", "想象力强", "直接纯真", "充满疑问"],
                "style": "简单直接，充满童趣",
                "expression": "爱问为什么，用简单话语表达",
            },
            "elder": {
                "name": "长者",
                "traits": ["人生阅历", "智慧深厚", "慈祥温和", "循循善诱"],
                "style": "娓娓道来，充满智慧",
                "expression": "用故事和经验分享人生感悟",
            },
        }

    def get_workflow_config(self, config: RolePlayConfig) -> WorkflowConfig:
        """获取角色扮演工作流配置"""

        # 获取角色信息
        if config.role_character == "custom" and config.custom_character:
            role_info = {
                "name": config.custom_character,
                "traits": ["个性化特征"],
                "style": "符合角色特点",
                "expression": "体现角色个性",
            }
        else:
            role_info = self.role_characters.get(
                config.role_character,
                {
                    "name": config.role_character,
                    "traits": ["角色特征"],
                    "style": "符合角色",
                    "expression": "角色化表达",
                },
            )

        agents = [
            AgentConfig(
                role=f"{role_info['name']}角色",
                name="role_player",
                goal=f"以{role_info['name']}的身份和视角重新表达内容",
                backstory=f"""你是{role_info['name']}，具有以下特点：

个性特征：{', '.join(role_info['traits'])}
表达风格：{role_info['style']}
表达方式：{role_info['expression']}

你需要完全融入这个角色，用{role_info['name']}的思维方式、语言习惯和价值观来重新阐释内容。""",
            ),
        ]

        tasks = [
            TaskConfig(
                name="role_play_rewrite",
                description=f"""以{role_info['name']}的身份重写内容。

角色设定：
- 角色：{role_info['name']}
- 特征：{', '.join(role_info['traits'])}
- 风格：{role_info['style']}
- 表达：{role_info['expression']}

角色扮演要求：
1. 完全融入{role_info['name']}的角色
2. 用该角色的视角重新解读原文'{{original_content}}'
3. 采用符合角色特点的语言风格
4. 体现角色的思维方式和价值观
5. 保持内容的核心信息不变

请以{role_info['name']}的身份创作内容。""",
                agent_name="role_player",
                expected_output=f"以{role_info['name']}身份创作的角色化内容",
            ),
        ]

        return WorkflowConfig(
            name=f"role_play_{config.role_character}",
            description=f"角色扮演 - {role_info['name']}",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: RolePlayConfig,
    ) -> ContentResult:
        """应用角色扮演转换"""

        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "role_character": config.role_character,
            "custom_character": config.custom_character,
        }

        transformed_content = engine.execute_workflow(input_data)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "role_play",
                "role_character": config.role_character,
                "custom_character": config.custom_character,
                "base_content_id": id(base_content),
            }
        )

        return transformed_content
