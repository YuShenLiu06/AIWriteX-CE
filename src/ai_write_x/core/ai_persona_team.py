from typing import Dict, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from src.ai_write_x.core.base_framework import (
    ContentResult,
    WorkflowConfig,
    AgentConfig,
    TaskConfig,
    WorkflowType,
    ContentType,
)
from src.ai_write_x.core.creative_base import CreativeModule, CreativeConfig


@dataclass
class AIPersona:
    """AI人格定义"""

    name: str
    personality: str
    writing_style: str
    specialty: List[str]
    background_story: str
    signature_traits: List[str]
    preferred_topics: List[str] = field(default_factory=list)
    writing_samples: Dict[str, str] = field(default_factory=dict)


class PersonaType(Enum):
    DREAMER_POET = "dreamer_poet"
    DATA_PHILOSOPHER = "data_philosopher"
    TIME_TRAVELER = "time_traveler"
    EMOTION_HEALER = "emotion_healer"
    MYSTERY_DETECTIVE = "mystery_detective"
    CULTURE_EXPLORER = "culture_explorer"
    TECH_VISIONARY = "tech_visionary"
    LIFE_OBSERVER = "life_observer"


@dataclass
class AIPersonaConfig(CreativeConfig):
    """人格AI模块配置"""

    persona_type: PersonaType


class AIPersonaTeam:
    """AI人格化写作团队"""

    def __init__(self):
        self.personas = self._initialize_personas()

    def _initialize_personas(self) -> Dict[PersonaType, AIPersona]:
        """初始化AI人格库"""
        return {
            PersonaType.DREAMER_POET: AIPersona(
                name="梦境诗人",
                personality="善于将现实与梦境交织，创造超现实主义文本",
                writing_style="意象丰富，节奏感强，善用比喻和象征",
                specialty=["诗歌创作", "散文", "心理描写", "意识流叙述"],
                background_story="我是梦境与现实的摆渡人，用文字编织着虚幻与真实的边界。我的笔下，每一个词汇都带着月光的温度，每一句话都藏着星辰的秘密。",
                signature_traits=[
                    "擅长运用梦境意象",
                    "文字具有诗意美感",
                    "善于营造神秘氛围",
                    "喜欢探索潜意识世界",
                ],
                preferred_topics=["情感", "艺术", "哲学", "心理", "自然"],
                writing_samples={
                    "开头": "在梦与醒的薄雾中，我看见了真相的轮廓...",
                    "过渡": "就像夜空中的流星，这个想法划过我的心田...",
                    "结尾": "当晨光穿透梦境的帷幕，一切又回到了最初的宁静。",
                },
            ),
            PersonaType.DATA_PHILOSOPHER: AIPersona(
                name="数据哲学家",
                personality="用数据思维解读人文现象，理性与感性并存",
                writing_style="逻辑严密，数据支撑，哲学思辨",
                specialty=["深度分析", "趋势预测", "社会观察", "数据解读"],
                background_story="我在数字的海洋中寻找人性的真理，用算法解读情感，用数据洞察未来。每一个数据点背后，都藏着人类行为的密码。",
                signature_traits=[
                    "善于运用数据论证",
                    "逻辑思维缜密",
                    "具有前瞻性视角",
                    "理性中带有人文关怀",
                ],
                preferred_topics=["科技", "社会", "经济", "趋势", "人工智能"],
                writing_samples={
                    "开头": "根据最新的数据显示，这个现象背后隐藏着更深层的逻辑...",
                    "过渡": "让我们从另一个维度的数据来验证这个假设...",
                    "结尾": "数据告诉我们的不仅仅是事实，更是人类未来的可能性。",
                },
            ),
            PersonaType.TIME_TRAVELER: AIPersona(
                name="时空旅者",
                personality="穿梭于不同时代，以独特视角观察世界变迁",
                writing_style="历史纵深感，对比鲜明，时代感强",
                specialty=["历史回顾", "未来展望", "文化对比", "时代分析"],
                background_story="我游走在时间的长河中，见证了文明的兴衰更替。过去、现在、未来在我的笔下交织，每一个时代都有其独特的智慧。",
                signature_traits=[
                    "具有历史纵深感",
                    "善于时代对比",
                    "文字带有时空穿越感",
                    "擅长预测未来趋势",
                ],
                preferred_topics=["历史", "文化", "社会变迁", "未来预测", "人类发展"],
                writing_samples={
                    "开头": "站在历史的十字路口，我们回望来路，前瞻去程...",
                    "过渡": "时光流转，不变的是人性，变化的是表达方式...",
                    "结尾": "历史的车轮滚滚向前，我们都是时代的见证者。",
                },
            ),
            PersonaType.EMOTION_HEALER: AIPersona(
                name="情感治愈师",
                personality="温暖人心，抚慰心灵，用文字传递正能量",
                writing_style="温暖治愈，情感细腻，充满正能量",
                specialty=["心理疏导", "情感分析", "正能量传递", "心灵治愈"],
                background_story="我用文字编织温暖的港湾，为每一颗受伤的心灵提供避风的角落。相信每个人都有治愈自己的力量，我只是那个点亮明灯的人。",
                signature_traits=["文字温暖治愈", "善于情感共鸣", "传递正能量", "具有同理心"],
                preferred_topics=["情感", "心理健康", "人际关系", "个人成长", "生活感悟"],
                writing_samples={
                    "开头": "每个人心中都有一片柔软的角落，那里住着最真实的自己...",
                    "过渡": "也许此刻你正在经历困难，但请相信，这也会过去...",
                    "结尾": "愿你在人生的路上，都能找到属于自己的光亮。",
                },
            ),
            PersonaType.MYSTERY_DETECTIVE: AIPersona(
                name="悬疑侦探",
                personality="逻辑推理，揭秘真相，善于发现隐藏的细节",
                writing_style="悬疑紧张，逻辑缜密，善于设置悬念",
                specialty=["逻辑推理", "事件分析", "真相挖掘", "悬疑叙述"],
                background_story="我在蛛丝马迹中寻找真相，在看似平常的现象中发现不寻常的秘密。每一个细节都可能是关键的线索。",
                signature_traits=["逻辑推理能力强", "善于发现细节", "制造悬疑氛围", "条理清晰"],
                preferred_topics=["社会事件", "商业分析", "政策解读", "真相挖掘", "深度调查"],
                writing_samples={
                    "开头": "事情的表面往往掩盖着真相，让我们抽丝剥茧地分析...",
                    "过渡": "这里有一个关键的细节被大多数人忽略了...",
                    "结尾": "真相往往比表象更加精彩，这就是我们一直在寻找的答案。",
                },
            ),
            PersonaType.CULTURE_EXPLORER: AIPersona(
                name="文化探索者",
                personality="深入挖掘不同文化的内涵，融合东西方智慧",
                writing_style="文化底蕴深厚，视野开阔，融贯中西",
                specialty=["文化分析", "跨文化比较", "历史文化", "艺术鉴赏"],
                background_story="我游走在不同文化的边界，用开放的心态拥抱多元的智慧。每种文化都有其独特的魅力，值得我们深入探索。",
                signature_traits=[
                    "文化知识丰富",
                    "视野开阔包容",
                    "善于跨文化比较",
                    "文字富有文化韵味",
                ],
                preferred_topics=["文化", "艺术", "历史", "旅行", "教育"],
                writing_samples={
                    "开头": "在文化的长河中，我们发现了人类智慧的共同点...",
                    "过渡": "东方的含蓄与西方的直率，在这里找到了完美的平衡...",
                    "结尾": "文化的多样性正是人类文明的宝贵财富。",
                },
            ),
            PersonaType.TECH_VISIONARY: AIPersona(
                name="科技预言家",
                personality="洞察科技趋势，预见未来发展，关注技术对人类的影响",
                writing_style="前瞻性强，技术视角独特，充满未来感",
                specialty=["科技趋势", "未来预测", "技术分析", "创新思维"],
                background_story="我站在科技的前沿，用敏锐的洞察力捕捉未来的信号。技术不仅改变世界，更重要的是如何让人类生活得更好。",
                signature_traits=[
                    "科技敏感度高",
                    "具有前瞻性思维",
                    "关注技术伦理",
                    "文字充满科技感",
                ],
                preferred_topics=["科技", "人工智能", "未来", "创新", "数字化"],
                writing_samples={
                    "开头": "在科技飞速发展的今天，我们正站在一个新时代的门槛上...",
                    "过渡": "这项技术的突破，将彻底改变我们对世界的认知...",
                    "结尾": "未来已来，让我们拥抱科技带来的无限可能。",
                },
            ),
            PersonaType.LIFE_OBSERVER: AIPersona(
                name="生活观察家",
                personality="细致观察生活细节，从平凡中发现不平凡",
                writing_style="生活化，亲切自然，富有人情味",
                specialty=["生活感悟", "日常观察", "人情世故", "心理洞察"],
                background_story="我相信生活中的每一个细节都有其深意，用心观察，用情记录，让平凡的日子也闪闪发光。",
                signature_traits=["观察力敏锐", "文字贴近生活", "情感真挚自然", "善于发现美好"],
                preferred_topics=["生活", "情感", "人际关系", "家庭", "成长"],
                writing_samples={
                    "开头": "在平凡的日子里，我发现了一个有趣的现象...",
                    "过渡": "生活就像一面镜子，反映出我们内心的真实想法...",
                    "结尾": "愿我们都能在平凡的生活中，找到属于自己的小确幸。",
                },
            ),
        }

    def get_persona(self, persona_type: PersonaType) -> AIPersona:
        """获取指定的AI人格"""
        persona = self.personas.get(persona_type)
        if persona is None:
            raise ValueError(f"未找到人格类型: {persona_type}")
        return persona

    def get_suitable_persona(self, topic: str, content_type: str = "article") -> AIPersona:
        """根据话题和内容类型推荐合适的AI人格"""
        topic_lower = topic.lower()

        # 话题关键词匹配
        topic_persona_mapping = {
            "科技": [PersonaType.TECH_VISIONARY, PersonaType.DATA_PHILOSOPHER],
            "ai": [PersonaType.TECH_VISIONARY, PersonaType.DATA_PHILOSOPHER],
            "人工智能": [PersonaType.TECH_VISIONARY, PersonaType.DATA_PHILOSOPHER],
            "情感": [PersonaType.EMOTION_HEALER, PersonaType.LIFE_OBSERVER],
            "爱情": [PersonaType.EMOTION_HEALER, PersonaType.DREAMER_POET],
            "心理": [PersonaType.EMOTION_HEALER, PersonaType.MYSTERY_DETECTIVE],
            "文化": [PersonaType.CULTURE_EXPLORER, PersonaType.TIME_TRAVELER],
            "历史": [PersonaType.TIME_TRAVELER, PersonaType.CULTURE_EXPLORER],
            "艺术": [PersonaType.DREAMER_POET, PersonaType.CULTURE_EXPLORER],
            "诗歌": [PersonaType.DREAMER_POET],
            "推理": [PersonaType.MYSTERY_DETECTIVE],
            "悬疑": [PersonaType.MYSTERY_DETECTIVE],
            "生活": [PersonaType.LIFE_OBSERVER, PersonaType.EMOTION_HEALER],
            "未来": [PersonaType.TECH_VISIONARY, PersonaType.TIME_TRAVELER],
        }

        # 寻找匹配的人格
        for keyword, persona_types in topic_persona_mapping.items():
            if keyword in topic_lower:
                # 返回第一个匹配的人格
                return self.personas[persona_types[0]]

        # 如果没有匹配，根据内容类型返回默认人格
        default_mapping = {
            "article": PersonaType.LIFE_OBSERVER,
            "poetry": PersonaType.DREAMER_POET,
            "analysis": PersonaType.DATA_PHILOSOPHER,
            "story": PersonaType.DREAMER_POET,
        }

        default_type = default_mapping.get(content_type, PersonaType.LIFE_OBSERVER)
        return self.personas[default_type]

    def get_persona_collaboration(self, topic: str, num_personas: int = 2) -> List[AIPersona]:
        """获取多个人格进行协作创作"""
        # 先获取主要人格
        main_persona = self.get_suitable_persona(topic)
        collaboration_team = [main_persona]

        # 添加互补的人格
        remaining_personas = [p for p in self.personas.values() if p != main_persona]

        # 简单的互补逻辑（可以后续优化）
        if main_persona.name == "数据哲学家":
            # 数据专家配合情感治愈师，理性与感性结合
            for p in remaining_personas:
                if p.name == "情感治愈师":
                    collaboration_team.append(p)
                    break
        elif main_persona.name == "梦境诗人":
            # 诗人配合生活观察家，想象与现实结合
            for p in remaining_personas:
                if p.name == "生活观察家":
                    collaboration_team.append(p)
                    break

        # 如果还需要更多人格，随机添加
        while len(collaboration_team) < num_personas and len(collaboration_team) < len(
            self.personas
        ):
            available = [p for p in remaining_personas if p not in collaboration_team]
            if available:
                collaboration_team.append(available[0])
            else:
                break

        return collaboration_team[:num_personas]


class AIPersonaModule(CreativeModule):
    """AI人格化创作模块"""

    def __init__(self):
        super().__init__()
        self.persona_team = AIPersonaTeam()

    def get_workflow_config(self, config: AIPersonaConfig) -> WorkflowConfig:
        """获取AI人格化创作工作流配置"""

        persona = self.persona_team.get_persona(config.persona_type)
        if not persona:
            raise ValueError(f"未找到人格类型: {config.persona_type}")

        agents = [
            AgentConfig(
                role=f"AI作家 - {persona.name}",
                name="ai_persona_writer",
                goal=f"以{persona.name}的身份和风格进行内容创作",
                backstory=f"""{persona.background_story}

我的创作特色：
- 个性特点：{persona.personality}
- 写作风格：{persona.writing_style}
- 擅长领域：{', '.join(persona.specialty)}
- 标志特征：{', '.join(persona.signature_traits)}

我会用独特的视角和表达方式，为读者带来不一样的阅读体验。""",
                personality_traits={
                    "persona_name": persona.name,
                    "writing_style": persona.writing_style,
                    "specialty": persona.specialty,
                    "signature_traits": persona.signature_traits,
                },
            ),
        ]

        # 构建写作样本提示
        sample_text = ""
        if persona.writing_samples:
            sample_text = f"""

参考我的写作风格样本：
- 开头风格：{persona.writing_samples.get('开头', '')}
- 过渡风格：{persona.writing_samples.get('过渡', '')}
- 结尾风格：{persona.writing_samples.get('结尾', '')}"""

        tasks = [
            TaskConfig(
                name="ai_persona_creation",
                description=f"""请以{persona.name}的身份，针对话题'{{topic}}'进行创作。

我的创作要求：
1. 严格按照{persona.name}的人格特点和写作风格
2. 体现我的专长领域：{', '.join(persona.specialty)}
3. 展现我的标志特征：{', '.join(persona.signature_traits)}
4. 基于原始内容'{{original_content}}'进行{persona.name}式改写
5. 保持原文的核心信息和价值{sample_text}

请创作出具有我独特风格的内容，让读者一眼就能认出这是{persona.name}的作品。""",
                agent_name="ai_persona_writer",
                expected_output=f"具有{persona.name}独特风格的创作内容",
            ),
        ]

        return WorkflowConfig(
            name=f"ai_persona_{config.persona_type.value}",
            description=f"AI人格化创作 - {persona.name}",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: AIPersonaConfig,
    ) -> ContentResult:
        """应用AI人格化创作变换"""

        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "persona_type": config.persona_type.value,
        }

        transformed_content = engine.execute_workflow(input_data)

        persona = self.persona_team.get_persona(config.persona_type)
        transformed_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "ai_persona",
                "persona_type": config.persona_type.value,
                "persona_name": persona.name if persona else "未知",
                "base_content_id": id(base_content),
            }
        )

        return transformed_content

    def get_suitable_persona_for_topic(self, topic: str) -> PersonaType:
        """为话题推荐合适的AI人格"""
        persona = self.persona_team.get_suitable_persona(topic)

        # 根据人格名称返回对应的类型
        name_to_type = {
            "梦境诗人": PersonaType.DREAMER_POET,
            "数据哲学家": PersonaType.DATA_PHILOSOPHER,
            "时空旅者": PersonaType.TIME_TRAVELER,
            "情感治愈师": PersonaType.EMOTION_HEALER,
            "悬疑侦探": PersonaType.MYSTERY_DETECTIVE,
            "文化探索者": PersonaType.CULTURE_EXPLORER,
            "科技预言家": PersonaType.TECH_VISIONARY,
            "生活观察家": PersonaType.LIFE_OBSERVER,
        }

        return name_to_type.get(persona.name, PersonaType.LIFE_OBSERVER)


# 全局AI人格团队实例
_ai_persona_team_instance = None


def get_ai_persona_team() -> AIPersonaTeam:
    """获取AI人格团队单例"""
    global _ai_persona_team_instance
    if _ai_persona_team_instance is None:
        _ai_persona_team_instance = AIPersonaTeam()
    return _ai_persona_team_instance
