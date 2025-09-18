from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random
from src.ai_write_x.core.base_framework import CreativeDimension, ContentResult
from src.ai_write_x.utils import log


class DimensionType(Enum):
    STYLE = "style"
    ERA = "era"
    PERSPECTIVE = "perspective"
    EMOTION = "emotion"
    AUDIENCE = "audience"
    SCENE = "scene"
    FORMAT = "format"
    THEME = "theme"
    CULTURE = "culture"
    PERSONALITY = "personality"


@dataclass
class CreativeDimensionGroup:
    """创意维度组合"""

    dimensions: List[CreativeDimension]
    compatibility_score: float
    description: str
    recommended_for: List[str] = field(default_factory=list)


class CreativeDimensionsEngine:
    """多维度创意引擎 - 实现无限创意可能"""

    def __init__(self):
        self.dimension_library = self._initialize_dimension_library()
        self.compatibility_matrix = self._build_compatibility_matrix()

    def _initialize_dimension_library(self) -> Dict[DimensionType, List[CreativeDimension]]:
        """初始化创意维度库"""
        return {
            DimensionType.STYLE: [
                CreativeDimension("shakespeare", "莎士比亚", 1.0, "诗意优美，语言华丽"),
                CreativeDimension("hemingway", "海明威", 1.0, "简洁有力，硬汉风格"),
                CreativeDimension("murakami", "村上春树", 1.0, "奇幻现实，孤独美学"),
                CreativeDimension("dongye", "东野圭吾", 1.0, "悬疑推理，人性剖析"),
                CreativeDimension("sanmao", "三毛", 1.0, "自由洒脱，浪漫情怀"),
                CreativeDimension("yuhua", "余华", 1.0, "深刻现实，批判精神"),
            ],
            DimensionType.ERA: [
                CreativeDimension("ancient_china", "春秋战国", 1.0, "礼崩乐坏，百家争鸣"),
                CreativeDimension("tang_song", "唐宋盛世", 1.0, "文化繁荣，诗词鼎盛"),
                CreativeDimension("republic", "民国风云", 1.0, "新旧交替，风起云涌"),
                CreativeDimension("eighties", "80年代", 1.0, "改革开放，青春热血"),
                CreativeDimension("cyberpunk", "赛博朋克2077", 1.0, "科技未来，霓虹反乌托邦"),
                CreativeDimension("medieval", "中世纪", 1.0, "骑士精神，神秘主义"),
            ],
            DimensionType.PERSPECTIVE: [
                CreativeDimension("first_person", "第一人称", 1.0, "亲身体验，情感直接"),
                CreativeDimension("omniscient", "全知视角", 1.0, "上帝视角，洞察全局"),
                CreativeDimension("multiple", "多重叙述", 1.0, "多角度展现，复杂立体"),
                CreativeDimension("stream", "意识流", 1.0, "内心独白，思维跳跃"),
                CreativeDimension("flashback", "倒叙", 1.0, "时空交错，悬念重生"),
            ],
            DimensionType.EMOTION: [
                CreativeDimension("healing", "治愈系", 1.0, "温暖人心，抚慰心灵"),
                CreativeDimension("suspense", "悬疑惊悚", 1.0, "紧张刺激，扣人心弦"),
                CreativeDimension("inspiring", "热血励志", 1.0, "激情澎湃，正能量满满"),
                CreativeDimension("philosophical", "深度哲思", 1.0, "思辨深刻，启发智慧"),
                CreativeDimension("humorous", "幽默诙谐", 1.0, "轻松愉快，妙趣横生"),
                CreativeDimension("melancholy", "忧郁怀旧", 1.0, "淡淡忧伤，回忆如潮"),
            ],
            DimensionType.AUDIENCE: [
                CreativeDimension("gen_z", "Z世代", 1.0, "年轻时尚，网络原生"),
                CreativeDimension("professionals", "职场精英", 1.0, "理性务实，效率导向"),
                CreativeDimension("seniors", "银发族", 1.0, "阅历丰富，情感细腻"),
                CreativeDimension("students", "学生党", 1.0, "青春活力，求知欲强"),
                CreativeDimension("parents", "宝妈群体", 1.0, "关爱家庭，实用贴心"),
            ],
            DimensionType.SCENE: [
                CreativeDimension("coffee_shop", "咖啡馆", 1.0, "温馨惬意，都市情调"),
                CreativeDimension("midnight_subway", "深夜地铁", 1.0, "孤独思考，城市夜色"),
                CreativeDimension("rainy_bookstore", "雨夜书店", 1.0, "文艺浪漫，知识殿堂"),
                CreativeDimension("seaside_cabin", "海边小屋", 1.0, "自然宁静，心灵栖息"),
                CreativeDimension("bustling_city", "繁华都市", 1.0, "节奏快速，机遇挑战"),
            ],
            DimensionType.FORMAT: [
                CreativeDimension("diary", "日记体", 1.0, "私密真实，情感流露"),
                CreativeDimension("dialogue", "对话体", 1.0, "生动活泼，互动性强"),
                CreativeDimension("poetry", "诗歌散文", 1.0, "韵律优美，意境深远"),
                CreativeDimension("script", "剧本形式", 1.0, "戏剧冲突，画面感强"),
                CreativeDimension("letter", "书信体", 1.0, "情真意切，时光穿越"),
            ],
            DimensionType.THEME: [
                CreativeDimension("growth", "成长蜕变", 1.0, "青春成长，自我发现"),
                CreativeDimension("time_healing", "时间治愈", 1.0, "岁月如歌，伤痛愈合"),
                CreativeDimension("dream_pursuit", "梦想追寻", 1.0, "理想主义，不懈奋斗"),
                CreativeDimension("human_nature", "人性探索", 1.0, "心理深度，道德思辨"),
                CreativeDimension("tech_reflection", "科技反思", 1.0, "技术进步，人文关怀"),
            ],
            DimensionType.CULTURE: [
                CreativeDimension("eastern_philosophy", "东方哲学", 1.0, "道家思想，禅宗智慧"),
                CreativeDimension("western_logic", "西方思辨", 1.0, "理性分析，逻辑严密"),
                CreativeDimension("japanese_mono", "日式物哀", 1.0, "瞬间美学，淡淡哀愁"),
                CreativeDimension("french_romance", "法式浪漫", 1.0, "优雅情调，艺术气息"),
                CreativeDimension("american_freedom", "美式自由", 1.0, "个人主义，追求自由"),
            ],
            DimensionType.PERSONALITY: [
                CreativeDimension("dreamer_poet", "梦境诗人", 1.0, "善于将现实与梦境交织"),
                CreativeDimension("data_philosopher", "数据哲学家", 1.0, "用数据思维解读人文"),
                CreativeDimension("time_traveler", "时空旅者", 1.0, "穿梭时代，独特视角"),
                CreativeDimension("emotion_healer", "情感治愈师", 1.0, "温暖人心，抚慰心灵"),
                CreativeDimension("mystery_detective", "悬疑侦探", 1.0, "逻辑推理，揭秘真相"),
            ],
        }

    def _build_compatibility_matrix(self) -> Dict[Tuple[str, str], float]:
        """构建维度兼容性矩阵"""
        matrix = {}

        # 高兼容性组合示例
        high_compatibility = [
            ("shakespeare", "ancient_china", 0.9),
            ("murakami", "coffee_shop", 0.9),
            ("dongye", "suspense", 0.95),
            ("healing", "seaside_cabin", 0.9),
            ("cyberpunk", "tech_reflection", 0.95),
            ("french_romance", "poetry", 0.9),
        ]

        # 中等兼容性组合
        medium_compatibility = [
            ("hemingway", "bustling_city", 0.7),
            ("yuhua", "human_nature", 0.8),
            ("gen_z", "humorous", 0.7),
        ]

        # 低兼容性组合（需要谨慎使用）
        low_compatibility = [
            ("shakespeare", "cyberpunk", 0.3),
            ("healing", "suspense", 0.2),
        ]

        for dim1, dim2, score in high_compatibility + medium_compatibility + low_compatibility:
            matrix[(dim1, dim2)] = score
            matrix[(dim2, dim1)] = score  # 对称性

        return matrix

    def calculate_compatibility_score(self, dimensions: List[CreativeDimension]) -> float:
        """计算维度组合的兼容性得分"""
        if len(dimensions) <= 1:
            return 1.0

        total_score = 0.0
        pair_count = 0

        for i in range(len(dimensions)):
            for j in range(i + 1, len(dimensions)):
                dim1, dim2 = dimensions[i].value, dimensions[j].value
                score = self.compatibility_matrix.get((dim1, dim2), 0.5)  # 默认中等兼容性
                total_score += score
                pair_count += 1

        return total_score / pair_count if pair_count > 0 else 1.0

    def generate_smart_combinations(
        self,
        topic: str,
        target_audience: str = "",
        content_type: str = "article",
        num_combinations: int = 5,
    ) -> List[CreativeDimensionGroup]:
        """智能生成创意维度组合"""

        combinations = []

        # 基于话题的智能推荐
        topic_keywords = topic.lower()

        # 根据关键词匹配合适的维度
        recommended_dimensions = []

        # 情感关键词匹配
        if any(word in topic_keywords for word in ["爱情", "感情", "恋爱"]):
            recommended_dimensions.extend(self.dimension_library[DimensionType.EMOTION][:2])
        elif any(word in topic_keywords for word in ["科技", "AI", "人工智能"]):
            recommended_dimensions.extend(
                [
                    dim
                    for dim in self.dimension_library[DimensionType.THEME]
                    if dim.value == "tech_reflection"
                ]
            )
        elif any(word in topic_keywords for word in ["历史", "古代", "传统"]):
            recommended_dimensions.extend(self.dimension_library[DimensionType.ERA][:3])

        # 生成多种组合策略
        strategies = [
            self._generate_emotional_dominant_combination,
            self._generate_cultural_fusion_combination,
            self._generate_format_innovative_combination,
            self._generate_audience_targeted_combination,
            self._generate_balanced_combination,
        ]

        for strategy in strategies[:num_combinations]:
            try:
                combination = strategy(topic, target_audience, recommended_dimensions)
                if combination:
                    combinations.append(combination)
            except Exception as e:
                log.print_log(f"创意组合生成失败: {e}", "warning")
                continue

        # 如果生成的组合不足，补充随机组合
        while len(combinations) < num_combinations:
            random_combination = self._generate_random_combination()
            if random_combination:
                combinations.append(random_combination)

        return combinations

    def _generate_emotional_dominant_combination(
        self, topic: str, target_audience: str, recommended_dims: List[CreativeDimension]
    ) -> CreativeDimensionGroup:
        """生成情感主导型组合"""

        # 选择一个主导情感维度
        emotional_dim = random.choice(self.dimension_library[DimensionType.EMOTION])

        # 选择兼容的其他维度
        compatible_dims = [emotional_dim]

        # 添加场景维度
        scene_dim = random.choice(self.dimension_library[DimensionType.SCENE])
        compatible_dims.append(scene_dim)

        # 添加风格维度
        style_dim = random.choice(self.dimension_library[DimensionType.STYLE])
        compatible_dims.append(style_dim)

        compatibility_score = self.calculate_compatibility_score(compatible_dims)

        return CreativeDimensionGroup(
            dimensions=compatible_dims,
            compatibility_score=compatibility_score,
            description=f"以{emotional_dim.description}为主导的情感化创作",
            recommended_for=["情感类话题", "个人成长", "心理健康"],
        )

    def _generate_cultural_fusion_combination(
        self, topic: str, target_audience: str, recommended_dims: List[CreativeDimension]
    ) -> CreativeDimensionGroup:
        """生成文化融合型组合"""

        # 选择文化维度
        culture_dim = random.choice(self.dimension_library[DimensionType.CULTURE])

        # 选择相应的时代背景
        era_dim = random.choice(self.dimension_library[DimensionType.ERA])

        # 选择合适的格式
        format_dim = random.choice(self.dimension_library[DimensionType.FORMAT])

        compatible_dims = [culture_dim, era_dim, format_dim]
        compatibility_score = self.calculate_compatibility_score(compatible_dims)

        return CreativeDimensionGroup(
            dimensions=compatible_dims,
            compatibility_score=compatibility_score,
            description=f"融合{culture_dim.description}的跨文化创作",
            recommended_for=["文化类话题", "历史内容", "教育科普"],
        )

    def _generate_format_innovative_combination(
        self, topic: str, target_audience: str, recommended_dims: List[CreativeDimension]
    ) -> CreativeDimensionGroup:
        """生成格式创新型组合"""

        # 选择创新格式
        format_dim = random.choice(self.dimension_library[DimensionType.FORMAT])

        # 选择人格维度
        personality_dim = random.choice(self.dimension_library[DimensionType.PERSONALITY])

        # 选择视角
        perspective_dim = random.choice(self.dimension_library[DimensionType.PERSPECTIVE])

        compatible_dims = [format_dim, personality_dim, perspective_dim]
        compatibility_score = self.calculate_compatibility_score(compatible_dims)

        return CreativeDimensionGroup(
            dimensions=compatible_dims,
            compatibility_score=compatibility_score,
            description=f"以{format_dim.description}为载体的创新表达",
            recommended_for=["创意内容", "营销文案", "品牌故事"],
        )

    def _generate_audience_targeted_combination(
        self, topic: str, target_audience: str, recommended_dims: List[CreativeDimension]
    ) -> CreativeDimensionGroup:
        """生成受众导向型组合"""

        # 根据目标受众选择合适的维度
        audience_dim = None
        if target_audience:
            for dim in self.dimension_library[DimensionType.AUDIENCE]:
                if target_audience.lower() in dim.value.lower():
                    audience_dim = dim
                    break

        if not audience_dim:
            audience_dim = random.choice(self.dimension_library[DimensionType.AUDIENCE])

        # 选择适合该受众的主题
        theme_dim = random.choice(self.dimension_library[DimensionType.THEME])

        # 选择适合的情感调性
        emotion_dim = random.choice(self.dimension_library[DimensionType.EMOTION])

        compatible_dims = [audience_dim, theme_dim, emotion_dim]
        compatibility_score = self.calculate_compatibility_score(compatible_dims)

        return CreativeDimensionGroup(
            dimensions=compatible_dims,
            compatibility_score=compatibility_score,
            description=f"针对{audience_dim.description}的定制化内容",
            recommended_for=["目标营销", "用户运营", "社群内容"],
        )

    def _generate_balanced_combination(
        self, topic: str, target_audience: str, recommended_dims: List[CreativeDimension]
    ) -> CreativeDimensionGroup:
        """生成平衡型组合"""

        # 从不同维度类型中各选一个，确保多样性
        selected_dims = []

        # 每种类型随机选择一个
        for dim_type in [DimensionType.STYLE, DimensionType.EMOTION, DimensionType.THEME]:
            dim = random.choice(self.dimension_library[dim_type])
            selected_dims.append(dim)

        compatibility_score = self.calculate_compatibility_score(selected_dims)

        return CreativeDimensionGroup(
            dimensions=selected_dims,
            compatibility_score=compatibility_score,
            description="多维度平衡的综合性创作风格",
            recommended_for=["通用内容", "品牌传播", "知识分享"],
        )

    def _generate_random_combination(self) -> CreativeDimensionGroup:
        """生成随机组合作为补充"""

        # 随机选择2-4个维度
        num_dims = random.randint(2, 4)
        all_dims = []
        for dim_list in self.dimension_library.values():
            all_dims.extend(dim_list)

        selected_dims = random.sample(all_dims, min(num_dims, len(all_dims)))
        compatibility_score = self.calculate_compatibility_score(selected_dims)

        return CreativeDimensionGroup(
            dimensions=selected_dims,
            compatibility_score=compatibility_score,
            description="探索性的随机创意组合",
            recommended_for=["实验性内容", "创意挑战"],
        )

    def apply_dimensions_to_content(
        self, content: ContentResult, dimensions: List[CreativeDimension]
    ) -> ContentResult:
        """将创意维度应用到内容上"""

        # 更新内容的创意维度标记
        content.creative_dimensions_applied = dimensions

        # 更新元数据
        content.metadata.update(
            {
                "creative_dimensions": [
                    {"name": dim.name, "value": dim.value, "description": dim.description}
                    for dim in dimensions
                ],
                "creativity_level": self.calculate_compatibility_score(dimensions),
            }
        )

        return content

    def get_dimension_suggestions(
        self, topic: str, existing_dims: List[CreativeDimension] | None = None
    ) -> List[CreativeDimension]:
        """基于话题和已有维度，推荐补充维度"""

        if not existing_dims:
            existing_dims = []

        existing_types = {self._get_dimension_type(dim) for dim in existing_dims}

        suggestions = []

        # 推荐缺失的维度类型
        for dim_type in DimensionType:
            if dim_type not in existing_types:
                # 基于话题推荐最合适的维度
                best_dim = self._get_best_dimension_for_topic(topic, dim_type)
                if best_dim:
                    suggestions.append(best_dim)

        return suggestions[:3]  # 最多推荐3个

    def _get_dimension_type(self, dimension: CreativeDimension) -> DimensionType:
        """获取维度所属类型"""
        for dim_type, dims in self.dimension_library.items():
            if any(d.value == dimension.value for d in dims):
                return dim_type
        return DimensionType.STYLE  # 默认返回风格类型

    def _get_best_dimension_for_topic(
        self, topic: str, dim_type: DimensionType
    ) -> Optional[CreativeDimension]:
        """为特定话题和维度类型推荐最佳维度"""

        topic_lower = topic.lower()
        dims = self.dimension_library.get(dim_type, [])

        if not dims:
            return None

        # 基于关键词匹配推荐
        keyword_matches = {
            "科技": ["tech_reflection", "cyberpunk", "data_philosopher"],
            "爱情": ["healing", "french_romance", "emotion_healer"],
            "历史": ["ancient_china", "tang_song", "eastern_philosophy"],
            "悬疑": ["dongye", "suspense", "mystery_detective"],
            "治愈": ["healing", "seaside_cabin", "emotion_healer"],
        }

        for keyword, values in keyword_matches.items():
            if keyword in topic_lower:
                for dim in dims:
                    if dim.value in values:
                        return dim

        # 如果没有匹配，返回随机一个
        return random.choice(dims)


# 全局创意引擎实例
_creative_engine_instance = None


def get_creative_dimensions_engine() -> CreativeDimensionsEngine:
    """获取创意维度引擎单例"""
    global _creative_engine_instance
    if _creative_engine_instance is None:
        _creative_engine_instance = CreativeDimensionsEngine()
    return _creative_engine_instance
