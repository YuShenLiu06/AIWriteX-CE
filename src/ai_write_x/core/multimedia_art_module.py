from dataclasses import dataclass
from enum import Enum
import random
from typing import List, Callable, Any
from src.ai_write_x.core.base_framework import (
    ContentResult,
    WorkflowConfig,
    AgentConfig,
    TaskConfig,
    WorkflowType,
    ContentType,
    MultimediaAsset,
)
from src.ai_write_x.core.creative_base import CreativeModule, CreativeConfig


class MediaType(Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    VOICE = "voice"


@dataclass
class MediaGenerationConfig:
    """媒体生成配置"""

    type: MediaType
    style: str
    quality: str = "standard"
    size: str = "1024x1024"
    duration: int = 30  # 音频/视频时长（秒）
    voice_type: str = "female"  # 语音类型
    language: str = "zh"  # 语言


@dataclass
class MultimediaArtConfig(CreativeConfig):
    """多媒体艺术模块配置"""

    media_types: List[MediaType]
    image_style: str = "artistic"
    audio_style: str = "ambient"
    generate_assets: bool = False


class MultimediaArtModule(CreativeModule):
    """多模态艺术协作模块 - 整合文字、图像、音频、视频创作"""

    def __init__(self):
        super().__init__()
        self.image_styles = {
            "realistic": "写实摄影风格",
            "artistic": "艺术绘画风格",
            "minimalist": "极简主义风格",
            "vintage": "复古怀旧风格",
            "modern": "现代设计风格",
            "fantasy": "奇幻艺术风格",
            "abstract": "抽象艺术风格",
            "chinese_painting": "中国画风格",
        }

        self.audio_styles = {
            "ambient": "环境音乐",
            "classical": "古典音乐",
            "electronic": "电子音乐",
            "nature": "自然音效",
            "meditation": "冥想音乐",
            "cinematic": "电影配乐",
        }

    def get_workflow_config(self, config: MultimediaArtConfig) -> WorkflowConfig:
        """获取多媒体创作工作流配置"""

        agents = [
            AgentConfig(
                role="多媒体创意总监",
                name="multimedia_director",
                goal="协调文字、图像、音频等多种媒体形式的创作",
                backstory="""你是多媒体创意总监，擅长将文字内容转化为丰富的多媒体体验。

你的能力包括：
- 理解文字内容的核心情感和视觉元素
- 设计配套的图像描述和音效需求
- 创造沉浸式的多媒体叙事体验
- 确保各种媒体形式的协调统一""",
            ),
            AgentConfig(
                role="视觉艺术专家",
                name="visual_artist",
                goal="为内容创作配套的视觉元素描述",
                backstory=f"""你是视觉艺术专家，专精{self.image_styles.get(config.image_style, '艺术创作')}。

你能够：
- 分析文字内容的视觉化潜力
- 创作详细的图像生成提示词
- 设计符合内容主题的视觉风格
- 确保视觉元素与文字完美匹配""",
            ),
        ]

        # 根据需要添加音频专家
        if MediaType.AUDIO in config.media_types:
            agents.append(
                AgentConfig(
                    role="音频设计师",
                    name="audio_designer",
                    goal="为内容设计配套的音频元素",
                    backstory=f"""你是音频设计师，专精{self.audio_styles.get(config.audio_style, '音频创作')}。

你的专长：
- 根据文字内容的情感氛围设计音效
- 创作背景音乐的风格描述
- 设计音频与文字的同步节奏
- 营造沉浸式的听觉体验""",
                )
            )

        tasks = [
            TaskConfig(
                name="multimedia_planning",
                description=f"""基于原始内容'{{original_content}}'，规划多媒体创作方案。

规划要求：
1. 分析内容的核心主题和情感基调
2. 识别适合视觉化的关键场景和元素
3. 设计多媒体叙事结构
4. 确定各媒体形式的风格统一性

媒体类型：{[mt.value for mt in config.media_types]}
图像风格：{config.image_style} - {self.image_styles.get(config.image_style, '')}
audio_info = (
                f'音频风格：{config.audio_style} - {self.audio_styles.get(config.audio_style, "")}'
                if MediaType.AUDIO in config.media_types else ''
            )

输出多媒体创作的整体规划方案。""",
                agent_name="multimedia_director",
                expected_output="多媒体创作的整体规划和协调方案",
            ),
            TaskConfig(
                name="visual_creation",
                description=f"""基于内容和整体规划，创作视觉元素。

视觉创作要求：
1. 提取内容中的关键视觉元素
2. 创作详细的图像生成提示词（英文）
3. 设计{config.image_style}风格的视觉表现
4. 确保图像与文字内容的情感匹配

输出格式：
- 主要配图描述：[详细的英文提示词]
- 辅助配图描述：[可选的补充图像描述]
- 视觉风格说明：[整体视觉设计理念]""",
                agent_name="visual_artist",
                expected_output="详细的图像生成描述和视觉设计方案",
                context=["multimedia_planning"],
            ),
        ]

        # 添加音频创作任务
        if MediaType.AUDIO in config.media_types:
            tasks.append(
                TaskConfig(
                    name="audio_creation",
                    description=f"""基于内容和整体规划，设计音频元素。

音频设计要求：
1. 分析内容的情感节奏和氛围需求
2. 设计{config.audio_style}风格的背景音乐
3. 规划音效和文字的配合时机
4. 创作音频的情感曲线描述

输出格式：
- 背景音乐风格：[具体的音乐风格描述]
- 音效设计：[关键节点的音效需求]
- 情感曲线：[音频的情感变化描述]""",
                    agent_name="audio_designer",
                    expected_output="详细的音频设计方案和情感配乐描述",
                    context=["multimedia_planning"],
                )
            )

        return WorkflowConfig(
            name="multimedia_art_creation",
            description="多模态艺术协作创作工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.MULTIMEDIA,
            agents=agents,
            tasks=tasks,
        )

    def transform(
        self,
        base_content: ContentResult,
        engine_factory: Callable[[WorkflowConfig], Any],
        config: MultimediaArtConfig,
    ) -> ContentResult:
        """应用多媒体艺术变换"""

        workflow_config = self.get_workflow_config(config)
        engine = engine_factory(workflow_config)

        clean_topic = base_content.title
        if "|" in clean_topic:
            clean_topic = clean_topic.split("|", 1)[1].strip()

        input_data = {
            "topic": clean_topic,
            "original_content": base_content.content,
            "media_types": [mt.value for mt in config.media_types],
            "image_style": config.image_style,
            "audio_style": config.audio_style,
        }

        # 执行多媒体创作工作流
        multimedia_result = engine.execute_workflow(input_data)

        # 创建增强的内容结果
        enhanced_content = ContentResult(
            title=base_content.title,
            content=base_content.content + "\n\n" + multimedia_result.content,
            summary=base_content.summary,
            content_format="multimedia",
            content_type=ContentType.MULTIMEDIA,
            metadata=base_content.metadata.copy(),
        )

        # 如果需要实际生成媒体资源
        if config.generate_assets:
            multimedia_assets = self._generate_multimedia_assets(
                multimedia_result.content,
                config.media_types,
                config.image_style,
                config.audio_style,
            )
            enhanced_content.multimedia_assets = multimedia_assets

        enhanced_content.metadata.update(
            {
                "original_title": base_content.title,
                "transformation_type": "multimedia_art",
                "media_types": [mt.value for mt in config.media_types],
                "image_style": config.image_style,
                "audio_style": config.audio_style,
                "assets_generated": config.generate_assets,
                "base_content_id": id(base_content),
            }
        )

        return enhanced_content

    def _generate_multimedia_assets(
        self,
        multimedia_content: str,
        media_types: List[MediaType],
        image_style: str,
        audio_style: str,
    ) -> List[MultimediaAsset]:
        """生成实际的多媒体资源"""
        assets = []

        try:
            # 生成图像资源
            if MediaType.IMAGE in media_types:
                image_assets = self._generate_images(multimedia_content, image_style)
                assets.extend(image_assets)

            # 生成音频资源
            if MediaType.AUDIO in media_types:
                audio_assets = self._generate_audio(multimedia_content, audio_style)
                assets.extend(audio_assets)

            # 其他媒体类型的生成逻辑...

        except Exception as e:
            # 多媒体资源生成失败 - 使用内置警告处理
            print(f"警告：多媒体资源生成失败: {e}")

        return assets

    def _generate_images(self, content: str, style: str) -> List[MultimediaAsset]:
        """生成图像资源"""
        assets = []
        # 暂时使用默认配置，后续可以集成实际配置系统
        # config = Config.get_instance()

        try:
            # 暂时使用占位图，后续可以集成实际图像生成API
            # if config.img_api_type == "ali" and config.img_api_key:
            #     assets.append(self._generate_ali_image(content, style))
            # else:
            assets.append(self._generate_placeholder_image(style))

        except Exception as e:
            # 图像生成失败 - 使用内置警告处理
            print(f"警告：图像生成失败: {e}")
            # 回退到占位图
            assets.append(self._generate_placeholder_image(style))

        return assets

    def _generate_ali_image(self, content: str, style: str) -> MultimediaAsset:
        """使用阿里云生成图像"""
        # 这里需要实现阿里云图像生成的具体逻辑
        # 暂时返回占位符
        return self._generate_placeholder_image(style)

    def _generate_placeholder_image(self, style: str) -> MultimediaAsset:
        """生成占位图像"""
        # 根据风格选择不同的随机图片
        style_seeds = {
            "realistic": random.randint(1, 100),
            "artistic": random.randint(101, 200),
            "minimalist": random.randint(201, 300),
            "vintage": random.randint(301, 400),
            "modern": random.randint(401, 500),
            "fantasy": random.randint(501, 600),
            "abstract": random.randint(601, 700),
            "chinese_painting": random.randint(701, 800),
        }

        seed = style_seeds.get(style, random.randint(1, 800))
        url = f"https://picsum.photos/1024/768?random={seed}"

        return MultimediaAsset(
            type="image",
            url=url,
            description=f"{self.image_styles.get(style, style)}风格配图",
            metadata={"style": style, "size": "1024x768", "source": "picsum"},
        )

    def _generate_audio(self, content: str, style: str) -> List[MultimediaAsset]:
        """生成音频资源"""
        # 音频生成的占位实现
        # 实际项目中需要集成音频生成API
        return [
            MultimediaAsset(
                type="audio",
                url="placeholder_audio.mp3",
                description=f"{self.audio_styles.get(style, style)}风格背景音乐",
                metadata={"style": style, "duration": 180, "format": "mp3"},  # 3分钟
            )
        ]


# 全局多媒体艺术模块实例
_multimedia_art_instance = None


def get_multimedia_art_module() -> MultimediaArtModule:
    """获取多媒体艺术模块单例"""
    global _multimedia_art_instance
    if _multimedia_art_instance is None:
        _multimedia_art_instance = MultimediaArtModule()
    return _multimedia_art_instance
