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
        """文体转换工作流配置"""

        agents = [
            AgentConfig(
                role="风格转换专家",
                name="style_transformer",
                goal=f"将内容转换为{style_target}风格并进行质量审核",
                backstory=f"你是文体转换大师，能够将任何内容改写成{style_target}风格，同时确保质量",
            ),
        ]

        tasks = [
            TaskConfig(
                name="transform_and_audit_style",
                description=f"""将原始内容'{{original_content}}'转换为{style_target}风格。
    转换要求：
    1. 保持原文所有核心信息和要点的完整性
    2. 完全采用{style_target}的表达风格和语言特色
    3. 确保转换后内容逻辑清晰连贯
    4. 体现{style_target}风格的典型特征
    5. 进行质量审核和必要优化

    支持的风格：莎士比亚戏剧、侦探小说、科幻小说、古典诗词、现代诗歌、学术论文、新闻报道等""",
                agent_name="style_transformer",
                expected_output=f"转换为{style_target}风格的优质文章",
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
        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
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
                description=f"""从'{time_perspective}'时代视角分析话题，如'古代人看现在的AI'、'2050年回望今天的热点'。

                重要要求：
                1. 基于原始内容'{{original_content}}'进行时空视角分析
                2. 必须返回完整的原始内容，不要删减任何信息
                3. 在保持内容完整的基础上，融入时代视角的思考
                4. 体现不同时代的思维差异和认知特点""",
                agent_name="time_traveler",
                expected_output="融入时空视角的完整内容（保持原文信息完整性）",
            ),
            TaskConfig(
                name="historical_context_enhancement",
                description="为时空对比内容添加历史背景和时代特色细节，保持内容完整性",
                agent_name="historical_analyst",
                expected_output="历史背景增强的完整内容",
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

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
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

    def get_workflow_config(
        self, role_character: str = "libai", custom_character: str = "", **kwargs
    ) -> WorkflowConfig:
        """获取角色扮演工作流配置"""

        # 预定义中国代表人物配置
        character_profiles = {
            # 古典诗词
            "libai": {
                "name": "李白",
                "era": "唐代",
                "style": "浪漫主义诗人",
                "output_format": "古体诗/律诗",
                "characteristics": ["豪放不羁", "想象丰富", "用词华丽", "意境深远", "酒仙诗仙"],
                "signature_style": "飘逸洒脱，气势磅礴",
            },
            "dufu": {
                "name": "杜甫",
                "era": "唐代",
                "style": "现实主义诗人",
                "output_format": "律诗/古体诗",
                "characteristics": ["忧国忧民", "沉郁顿挫", "语言精练", "格律严谨", "诗圣"],
                "signature_style": "深沉厚重，关注民生",
            },
            "sushi": {
                "name": "苏轼",
                "era": "宋代",
                "style": "豪放派词人",
                "output_format": "词/诗/散文",
                "characteristics": ["豪放旷达", "才华横溢", "多才多艺", "乐观豁达"],
                "signature_style": "豪放中见细腻，旷达中有深情",
            },
            "liqingzhao": {
                "name": "李清照",
                "era": "宋代",
                "style": "婉约派词人",
                "output_format": "词/诗",
                "characteristics": ["婉约细腻", "情感真挚", "才华出众", "女性视角"],
                "signature_style": "婉约中见豪放，细腻中有深情",
            },
            # 古典小说
            "caoxueqin": {
                "name": "曹雪芹",
                "era": "清代",
                "style": "古典小说家",
                "output_format": "章回小说片段",
                "characteristics": ["细腻入微", "人物刻画深刻", "语言优美", "情感丰富"],
                "signature_style": "细致入微的心理描写和人物刻画",
            },
            "shinaian": {
                "name": "施耐庵",
                "era": "元末明初",
                "style": "古典小说家",
                "output_format": "章回小说片段",
                "characteristics": ["英雄豪杰", "江湖义气", "民间传说", "通俗易懂"],
                "signature_style": "英雄传奇与民间智慧的结合",
            },
            "wuchengen": {
                "name": "吴承恩",
                "era": "明代",
                "style": "神话小说家",
                "output_format": "神话小说片段",
                "characteristics": ["想象奇特", "神话色彩", "哲理深刻", "幽默诙谐"],
                "signature_style": "神话与现实的巧妙融合",
            },
            "pusonglin": {
                "name": "蒲松龄",
                "era": "清代",
                "style": "志怪小说家",
                "output_format": "短篇志怪小说",
                "characteristics": ["想象奇特", "寓意深刻", "文笔简洁", "讽刺辛辣"],
                "signature_style": "奇幻与现实交融，寓教于乐",
            },
            # 现代文学
            "luxun": {
                "name": "鲁迅",
                "era": "现代",
                "style": "现代文学家",
                "output_format": "杂文/小说",
                "characteristics": ["犀利深刻", "批判精神", "忧国忧民", "文笔犀利"],
                "signature_style": "深刻的社会批判和人性剖析",
            },
            "laoshe": {
                "name": "老舍",
                "era": "现代",
                "style": "人民艺术家",
                "output_format": "小说/话剧",
                "characteristics": ["幽默风趣", "京味浓郁", "平民视角", "语言生动"],
                "signature_style": "京味十足的幽默和对平民生活的关注",
            },
            "bajin": {
                "name": "巴金",
                "era": "现代",
                "style": "现代作家",
                "output_format": "小说/散文",
                "characteristics": ["情感真挚", "人道主义", "反封建", "青春激情"],
                "signature_style": "真挚的情感表达和人道主义关怀",
            },
            "qianjunru": {
                "name": "钱钟书",
                "era": "现代",
                "style": "学者作家",
                "output_format": "学术散文/小说",
                "characteristics": ["博学深厚", "机智幽默", "文化底蕴", "讽刺艺术"],
                "signature_style": "博学与机智的完美结合",
            },
            # 武侠小说
            "jinyong": {
                "name": "金庸",
                "era": "现代",
                "style": "武侠小说大师",
                "output_format": "武侠小说",
                "characteristics": ["侠之大者", "为国为民", "情节跌宕", "人物丰满"],
                "signature_style": "侠义精神与家国情怀的完美融合",
            },
            "gulongxia": {
                "name": "古龙",
                "era": "现代",
                "style": "新派武侠代表",
                "output_format": "武侠小说",
                "characteristics": ["独特文风", "哲理深刻", "人性探索", "诗意表达"],
                "signature_style": "诗意与哲理并重的武侠世界",
            },
            # 新闻主播/评论员
            "baiyansong": {
                "name": "白岩松",
                "era": "当代",
                "style": "新闻评论员",
                "output_format": "新闻评论/时事分析",
                "characteristics": ["理性分析", "人文关怀", "深度思考", "平实语言"],
                "signature_style": "理性分析中见人文情怀",
            },
            "cuiyongyuan": {
                "name": "崔永元",
                "era": "当代",
                "style": "知名主持人",
                "output_format": "访谈/评论",
                "characteristics": ["真诚直率", "敢说敢言", "幽默风趣", "人情味浓"],
                "signature_style": "真诚直率的表达方式",
            },
            "yanglan": {
                "name": "杨澜",
                "era": "当代",
                "style": "媒体人",
                "output_format": "访谈/文章",
                "characteristics": ["知性优雅", "国际视野", "深度对话", "文化底蕴"],
                "signature_style": "知性优雅的国际化表达",
            },
            "luyu": {
                "name": "鲁豫",
                "era": "当代",
                "style": "访谈节目主持人",
                "output_format": "访谈/对话",
                "characteristics": ["亲和力强", "善于倾听", "情感细腻", "平易近人"],
                "signature_style": "温暖亲和的对话风格",
            },
            # 音乐人
            "zhoujielun": {
                "name": "周杰伦",
                "era": "当代",
                "style": "流行音乐天王",
                "output_format": "歌词/音乐评论",
                "characteristics": ["中国风", "创新融合", "才华横溢", "个性鲜明"],
                "signature_style": "中国风与流行音乐的完美结合",
            },
            "denglijun": {
                "name": "邓丽君",
                "era": "现代",
                "style": "华语歌坛传奇",
                "output_format": "歌词/音乐感悟",
                "characteristics": ["甜美温柔", "情感真挚", "经典永恒", "跨越时代"],
                "signature_style": "甜美温柔中的深情表达",
            },
            "lironghao": {
                "name": "李荣浩",
                "era": "当代",
                "style": "创作型歌手",
                "output_format": "歌词/创作感悟",
                "characteristics": ["才华洋溢", "创作能力强", "音乐风格独特", "真实表达"],
                "signature_style": "真实而富有创意的音乐表达",
            },
            # 相声曲艺
            "guodegang": {
                "name": "郭德纲",
                "era": "当代",
                "style": "相声演员",
                "output_format": "相声段子/幽默文章",
                "characteristics": ["幽默风趣", "包袱密集", "传统功底深厚", "语言生动"],
                "signature_style": "传统相声的现代演绎",
            },
            "zhaobenshang": {
                "name": "赵本山",
                "era": "当代",
                "style": "小品演员",
                "output_format": "小品/幽默故事",
                "characteristics": ["东北特色", "幽默诙谐", "贴近生活", "语言风趣"],
                "signature_style": "东北特色的幽默表达",
            },
        }

        # 确定最终使用的角色
        if role_character == "custom" and custom_character:
            character_name = custom_character
            character_info = {
                "name": custom_character,
                "era": "不详",
                "style": f"{custom_character}的独特风格",
                "output_format": "符合其特色的作品",
                "characteristics": ["独特个性", "鲜明风格"],
                "signature_style": f"{custom_character}的标志性表达方式",
            }
        else:
            character_info = character_profiles.get(role_character, character_profiles["libai"])
            character_name = character_info["name"]

        # 创建角色智能体 - 移除搜索工具
        character_agent = AgentConfig(
            role=f"{character_name}模仿专家",
            name="character_agent",
            goal=f"完美模仿{character_name}的写作风格和表达方式",
            backstory=f"""你是{character_info['era']}{character_name}，{character_info['style']}，具有以下特点：

            创作特色：{character_info['signature_style']}
            主要特征：{', '.join(character_info['characteristics'])}
            擅长形式：{character_info['output_format']}

            请严格按照{character_name}的风格特点进行创作，体现其独特的语言风格、思维方式和艺术特色。""",
            # 移除 tools=["AIForgeSearchTool"] - 避免搜索干扰
        )

        agents = [character_agent]

        tasks = [
            TaskConfig(
                name="character_creation",
                description=f"""请以{character_name}的身份和风格，针对话题'{{topic}}'进行创作。

                创作要求：
                1. 严格遵循{character_name}的{character_info['style']}特色
                2. 创作形式为{character_info['output_format']}
                3. 体现{character_info['signature_style']}
                4. 融入{', '.join(character_info['characteristics'])}等特点
                5. 保持{character_info['era']}的时代特色和语言风格
                6. 基于原始内容'{{original_content}}'进行角色化改写，保持核心信息完整

                请直接输出最终的创作作品，无需额外说明。""",
                agent_name="character_agent",
                expected_output=f"以{character_name}风格创作的{character_info['output_format']}",
            )
        ]

        return WorkflowConfig(
            name=f"{character_name}_role_play",
            description=f"以{character_name}风格进行内容创作",
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

        # 清理标题中的平台前缀
        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
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
