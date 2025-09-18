import os
import time
from typing import Dict, Any
from src.ai_write_x.core.creative_modules import (
    StyleTransformModule,
    CulturalFusionModule,
    MultiDimensionalCreativeModule,
    # 配置类导入
    RolePlayConfig,
    StyleTransformConfig,
    TimeTravelConfig,
    DynamicTransformConfig,
    GenreFusionConfig,
    CulturalFusionConfig,
    MultiDimensionalConfig,
)
from src.ai_write_x.core.creative_dimensions_engine import (
    get_creative_dimensions_engine,
)
from src.ai_write_x.core.ai_persona_team import (
    get_ai_persona_team,
)
from src.ai_write_x.core.base_framework import (
    WorkflowConfig,
    AgentConfig,
    TaskConfig,
    WorkflowType,
    ContentType,
    ContentResult,
)
from src.ai_write_x.adapters.platform_adapters import (
    WeChatAdapter,
    XiaohongshuAdapter,
    DouyinAdapter,
    ToutiaoAdapter,
    BaijiahaoAdapter,
    ZhihuAdapter,
    DoubanAdapter,
)
from src.ai_write_x.core.monitoring import WorkflowMonitor
from src.ai_write_x.config.config import Config
from src.ai_write_x.core.content_generation import ContentGenerationEngine
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import utils
from src.ai_write_x.adapters.platform_adapters import PlatformType
from src.ai_write_x.utils import log


class UnifiedContentWorkflow:
    """统一的内容工作流编排器"""

    def __init__(self):
        self.content_engine = None
        self.creative_modules = {
            "style_transform": StyleTransformModule(),
            "multi_dimensional": MultiDimensionalCreativeModule(),
            "cultural_fusion": CulturalFusionModule(),
            # TODO: 其他模块需要按照新模式重构
        }
        self.platform_adapters = {
            PlatformType.WECHAT.value: WeChatAdapter(),
            PlatformType.XIAOHONGSHU.value: XiaohongshuAdapter(),
            PlatformType.DOUYIN.value: DouyinAdapter(),
            PlatformType.TOUTIAO.value: ToutiaoAdapter(),
            PlatformType.BAIJIAHAO.value: BaijiahaoAdapter(),
            PlatformType.ZHIHU.value: ZhihuAdapter(),
            PlatformType.DOUBAN.value: DoubanAdapter(),
        }
        self.monitor = WorkflowMonitor.get_instance()
        # 初始化创意引擎和AI人格团队
        self.creative_engine = get_creative_dimensions_engine()
        self.ai_persona_team = get_ai_persona_team()

    def get_base_content_config(self, **kwargs) -> WorkflowConfig:
        """动态生成基础内容配置，根据平台和需求定制"""

        config = Config.get_instance()
        # 获取目标平台
        publish_platform = kwargs.get("publish_platform", PlatformType.WECHAT.value)
        writer_des = f"""基于话题'{{topic}}'和搜索工具获取的最新信息，撰写一篇高质量的文章。

工具 aiforge_search_tool 使用参数：
    topic={{topic}}
    urls={{urls}}
    reference_ratio={{reference_ratio}}

执行步骤：
1. 使用 aiforge_search_tool 获取关于'{{topic}}'的最新信息
2. 根据搜索结果的来源类型调整写作策略：
    - 如果是"参考文章"结果：基于提供的参考内容进行创作，根据参考比例调整借鉴程度
    - 如果是"搜索"结果：基于搜索到的信息进行原创写作
    - 优先使用搜索结果中的真实发布时间和数据
    - 如果没有获取到有效结果：使用通用时间表述进行原创写作
3. 确保文章逻辑清晰、内容完整、语言流畅

文章要求：
- 标题：当{{platform}}不为空时为"{{platform}}|{{topic}}"，否则为"{{topic}}"
- 总字数：{config.min_article_len}~{config.max_article_len}字（纯文本字数）
- 格式：标准Markdown格式
- 内容：仅输出最终文章内容，严禁包含思考过程或额外说明"""

        config = Config.get_instance()

        # 基础配置
        agents = [
            AgentConfig(
                role="内容创作专家",
                name="writer",
                goal="撰写高质量文章",
                backstory="你是一位作家",
                tools=["AIForgeSearchTool"],
            ),
        ]

        tasks = [
            TaskConfig(
                name="write_content",
                description=writer_des,
                agent_name="writer",
                expected_output="文章标题 + 文章正文（标准Markdown格式）",
                context=["analyze_topic"],
            ),
        ]

        return WorkflowConfig(
            name=f"{publish_platform}_content_generation",
            description=f"面向{publish_platform}平台的内容生成工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def _generate_base_content(self, topic: str, **kwargs) -> ContentResult:
        """生成基础内容"""
        # 动态获取配置
        base_config = self.get_base_content_config(**kwargs)

        # 创建内容生成引擎
        self.content_engine = ContentGenerationEngine(base_config)

        # 准备输入数据
        input_data = {
            "topic": topic,
            "platform": kwargs.get("platform", ""),
            "urls": kwargs.get("urls", []),
            "reference_ratio": kwargs.get("reference_ratio", 0.0),
        }

        return self.content_engine.execute_workflow(input_data)

    def execute(self, topic: str, **kwargs) -> Dict[str, Any]:
        """统一执行流程：输入 -> 内容生成 -> 格式处理 -> 保存 -> 发布"""
        start_time = time.time()
        success = False
        config = Config.get_instance()
        publish_platform = config.publish_platform
        # 构建标题：platform|topic 格式
        platform = kwargs.get("platform", "")

        if platform:
            title = f"{platform}|{topic}"
        else:
            title = topic

        try:
            # 1. 生成基础内容（统一Markdown格式）
            base_content = self._generate_base_content(
                topic, publish_platform=publish_platform, **kwargs
            )

            # 2. 可选创意变换
            final_content = self._apply_creative_transformation(base_content, **kwargs)

            # 3. 转换处理（template或design）
            transform_content = self._transform_content(final_content, publish_platform, **kwargs)

            # 4. 保存（非AI参与）
            save_result = self._save_content(transform_content, title)
            if save_result.get("success", False):
                log.print_log(f"文章“{title}”保存成功")

            # 5. 可选发布（非AI参与，开关控制）
            publish_result = None
            if self._should_publish():
                publish_result = self._publish_content(
                    transform_content, publish_platform, **kwargs
                )
                log.print_log(f"发布完成，总结：{publish_result.get('message')}")

            results = {
                "base_content": base_content,
                "final_content": final_content,
                "formatted_content": transform_content.content,
                "save_result": save_result,
                "publish_result": publish_result,
                "success": True,
            }

            success = True
            return results

        except Exception as e:
            self.monitor.log_error("unified_workflow", str(e), {"topic": topic})
            raise
        finally:
            duration = time.time() - start_time
            self.monitor.track_execution("unified_workflow", duration, success, {"topic": topic})

    def _transform_content(
        self, content: ContentResult, publish_platform: str, **kwargs
    ) -> ContentResult:
        """内容转换：template或design路径的AI处理"""
        config = Config.get_instance()
        adapter = self.platform_adapters.get(publish_platform)

        if not adapter:
            raise ValueError(f"不支持的平台: {publish_platform}")

        # AI驱动的内容转换
        if adapter.supports_html() and config.article_format.upper() == "HTML":
            if config.use_template and adapter.supports_template():
                return self._apply_template_formatting(content, **kwargs)
            else:
                return self._apply_design_formatting(content, publish_platform, **kwargs)
        else:
            return content

    def _apply_template_formatting(self, content: ContentResult, **kwargs) -> ContentResult:
        """Template路径：使用AI填充本地模板"""
        # 创建专门的模板处理工作流
        template_config = self._get_template_workflow_config(**kwargs)
        engine = ContentGenerationEngine(template_config)

        input_data = {
            "content": content.content,
            "title": content.title,
            "parse_result": False,
            "content_format": "html",
            **kwargs,
        }

        return engine.execute_workflow(input_data)

    def _apply_design_formatting(
        self, content: ContentResult, publish_platform: str, **kwargs
    ) -> ContentResult:
        """Design路径：使用AI生成HTML设计"""
        # 创建专门的设计工作流
        design_config = self._get_design_workflow_config(publish_platform, **kwargs)
        engine = ContentGenerationEngine(design_config)

        input_data = {
            "content": content.content,
            "title": content.title,
            "platform": publish_platform,
            "parse_result": False,
            "content_format": "html",
            **kwargs,
        }

        return engine.execute_workflow(input_data)

    def _apply_creative_transformation(self, base_content, **kwargs):
        """创意变换，支持引擎缓存"""

        config = Config.get_instance()
        creative_mode = config.config.get("creative_mode", "")
        creative_config = config.config.get("creative_config", {})

        if not creative_mode:
            return base_content

        # 支持组合模式和新的创意模式
        modes = [mode.strip() for mode in creative_mode.split(",")]
        current_content = base_content

        # 缓存引擎实例以减少重复创建开销
        engine_cache = {}

        def get_or_create_engine(mode, mode_config, **extra_params):
            """获取或创建缓存的引擎实例"""
            cache_key = f"{mode}_{hash(str(mode_config))}_{hash(str(extra_params))}"
            if cache_key not in engine_cache:
                module = self.creative_modules.get(mode)
                if module:
                    # 根据模块类型创建相应的配置对象
                    if mode == "multi_dimensional":
                        dimensions = extra_params.get("dimensions", [])
                        config_obj = MultiDimensionalConfig(dimensions=dimensions)
                        workflow_config = module.get_workflow_config(config_obj)
                    elif mode == "cultural_fusion":
                        cultural_perspective = extra_params.get(
                            "cultural_perspective",
                            mode_config.get("cultural_perspective", "eastern_philosophy"),
                        )
                        config_obj = CulturalFusionConfig(cultural_perspective=cultural_perspective)
                        workflow_config = module.get_workflow_config(config_obj)
                    elif mode == "style_transform":
                        style_target = extra_params.get(
                            "style_target", mode_config.get("style_target", "shakespeare")
                        )
                        config_obj = StyleTransformConfig(style_target=style_target)
                        workflow_config = module.get_workflow_config(config_obj)
                    elif mode == "time_travel":
                        time_perspective = extra_params.get(
                            "time_perspective", mode_config.get("time_perspective", "ancient")
                        )
                        config_obj = TimeTravelConfig(time_perspective=time_perspective)
                        workflow_config = module.get_workflow_config(config_obj)
                    elif mode == "role_play":
                        role_character = extra_params.get(
                            "role_character", mode_config.get("role_character", "celebrity")
                        )
                        custom_character = mode_config.get("custom_character", "")
                        config_obj = RolePlayConfig(
                            role_character=role_character, custom_character=custom_character
                        )
                        workflow_config = module.get_workflow_config(config_obj)
                    elif mode == "dynamic_transform":
                        scenario = extra_params.get(
                            "scenario", mode_config.get("scenario", "elevator_pitch")
                        )
                        config_obj = DynamicTransformConfig(scenario=scenario)
                        workflow_config = module.get_workflow_config(config_obj)
                    elif mode == "genre_fusion":
                        genre_combination = extra_params.get(
                            "genre_combination",
                            mode_config.get("genre_combination", ["scifi", "wuxia"]),
                        )
                        config_obj = GenreFusionConfig(genre_combination=genre_combination)
                        workflow_config = module.get_workflow_config(config_obj)
                    else:
                        # 对于未识别的模块，返回 None
                        return None

                    engine_cache[cache_key] = ContentGenerationEngine(workflow_config)
            return engine_cache.get(cache_key)

        for mode in modes:
            mode_config = creative_config.get(mode, {})

            # 处理新的创意模式
            if mode == "multi_dimensional":
                if mode_config.get("enabled", False):
                    # 获取创意维度组合
                    topic = base_content.title
                    if "|" in topic:
                        topic = topic.split("|", 1)[1].strip()

                    # 生成智能创意组合
                    combinations = self.creative_engine.generate_smart_combinations(
                        topic=topic,
                        target_audience=mode_config.get("target_audience", ""),
                        num_combinations=1,
                    )

                    if combinations:
                        dimensions = combinations[0].dimensions
                        module = self.creative_modules.get("multi_dimensional")
                        if module:
                            multi_config = mode_config.copy()
                            multi_config["dimensions"] = dimensions
                            engine = get_or_create_engine(
                                "multi_dimensional", multi_config, dimensions=dimensions
                            )
                            current_content = module.transform(
                                current_content,
                                engine_factory=lambda config: engine,
                                config=MultiDimensionalConfig(dimensions=dimensions),
                            )

            elif mode == "cultural_fusion":
                if mode_config.get("enabled", False):
                    cultural_perspective = mode_config.get(
                        "cultural_perspective", "eastern_philosophy"
                    )
                    module = self.creative_modules.get("cultural_fusion")
                    if module:
                        engine = get_or_create_engine(
                            "cultural_fusion",
                            mode_config,
                            cultural_perspective=cultural_perspective,
                        )
                        current_content = module.transform(
                            current_content,
                            engine_factory=lambda config: engine,
                            config=CulturalFusionConfig(cultural_perspective=cultural_perspective),
                        )

            elif mode == "dynamic_transform":
                if mode_config.get("enabled", False):
                    scenario = mode_config.get("scenario", "elevator_pitch")
                    module = self.creative_modules.get("dynamic_transform")
                    if module:
                        engine = get_or_create_engine(
                            "dynamic_transform", mode_config, scenario=scenario
                        )
                        current_content = module.transform(
                            current_content,
                            engine_factory=lambda config: engine,
                            config=DynamicTransformConfig(scenario=scenario),
                        )

            elif mode == "genre_fusion":
                if mode_config.get("enabled", False):
                    genre_combination = mode_config.get("genre_combination", ["scifi", "wuxia"])
                    module = self.creative_modules.get("genre_fusion")
                    if module:
                        engine = get_or_create_engine(
                            "genre_fusion", mode_config, genre_combination=genre_combination
                        )
                        current_content = module.transform(
                            current_content,
                            engine_factory=lambda config: engine,
                            config=GenreFusionConfig(genre_combination=genre_combination),
                        )

            elif mode == "ai_persona":
                if mode_config.get("enabled", False):
                    # 智能选择合适的AI人格
                    topic = base_content.title
                    if "|" in topic:
                        topic = topic.split("|", 1)[1].strip()

                    ai_persona_module = self.creative_modules.get("ai_persona")
                    if ai_persona_module:
                        persona_type = ai_persona_module.get_suitable_persona_for_topic(topic)
                        engine = get_or_create_engine(
                            "ai_persona", mode_config, persona_type=persona_type
                        )
                        current_content = ai_persona_module.transform(
                            current_content,
                            engine_factory=lambda config: engine,
                            persona_type=persona_type,
                        )

            # 保持原有的创意模式处理逻辑
            elif not mode_config.get("enabled", False):
                continue
            else:
                engine = get_or_create_engine(mode, mode_config)
                if not engine:
                    continue

                # 执行变换
                module = self.creative_modules.get(mode)
                if module:
                    if mode == "style_transform":
                        style_target = mode_config.get("style_target", "shakespeare")
                        engine = get_or_create_engine(
                            "style_transform", mode_config, style_target=style_target
                        )
                        # 创建配置对象
                        config_obj = StyleTransformConfig(style_target=style_target)
                        current_content = module.transform(
                            current_content,
                            engine_factory=lambda config: engine,
                            config=config_obj,
                        )
                    elif mode == "time_travel":
                        time_perspective = mode_config.get("time_perspective", "ancient")
                        engine = get_or_create_engine(
                            "time_travel", mode_config, time_perspective=time_perspective
                        )
                        # 创建配置对象
                        config_obj = TimeTravelConfig(time_perspective=time_perspective)
                        current_content = module.transform(
                            current_content,
                            engine_factory=lambda config: engine,
                            config=config_obj,
                        )
                    elif mode == "role_play":
                        role_character = mode_config.get("role_character", "celebrity")
                        custom_character = mode_config.get("custom_character", "")
                        engine = get_or_create_engine(
                            "role_play", mode_config, role_character=role_character
                        )
                        # 创建配置对象
                        config_obj = RolePlayConfig(
                            role_character=role_character, custom_character=custom_character
                        )
                        current_content = module.transform(
                            current_content,
                            engine_factory=lambda config: engine,
                            config=config_obj,
                        )

        return current_content

    def _get_template_workflow_config(
        self, publish_platform: str = PlatformType.WECHAT.value, **kwargs
    ) -> WorkflowConfig:
        """生成模板处理工作流配置"""
        # 获取配置以获取字数限制
        config = Config.get_instance()

        if publish_platform == PlatformType.WECHAT.value:
            # 微信平台的详细模板填充要求
            task_description = f"""
# HTML内容适配任务
## 任务目标
使用工具 read_template_tool 读取本地HTML模板，将以下文章内容适配填充到HTML模板中：

**文章内容：**
{{content}}

**文章标题：**
{{title}}

## 执行步骤
1. 首先使用 read_template_tool 读取HTML模板
2. 分析模板的结构、样式和布局特点
3. 获取前置任务生成的文章内容
4. 将新内容按照模板结构进行适配填充
5. 确保最终输出是基于原模板的HTML，保持视觉效果和风格不变

## 具体要求
- 分析HTML模板的结构、样式和布局特点
- 识别所有内容占位区域（标题、副标题、正文段落、引用、列表等）
- 将新文章内容按照原模板的结构和布局规则填充：
    * 保持<section>标签的布局结构和内联样式不变
    * 保持原有的视觉层次、色彩方案和排版风格
    * 保持原有的卡片式布局、圆角和阴影效果
    * 保持SVG动画元素和交互特性

- 内容适配原则：
    * 标题替换标题、段落替换段落、列表替换列表
    * 内容总字数{config.min_article_len}~{config.max_article_len}字，不可过度删减前置任务生成的文章内容
    * 当新内容比原模板内容长或短时，合理调整，不破坏布局
    * 保持原有的强调部分（粗体、斜体、高亮等）应用于新内容的相应部分
    * 保持图片位置
    * 不可使用模板中的任何日期作为新文章的日期

- 严格限制：
    * 不添加新的style标签或外部CSS
    * 不改变原有的色彩方案（限制在三种色系内）
    * 不修改模板的整体视觉效果和布局结构"""

            backstory = "你是微信公众号模板处理专家，能够将内容适配到HTML模板中。严格按照以下要求：保持<section>标签的布局结构和内联样式不变、保持原有的视觉层次、色彩方案和排版风格、不可使用模板中的任何日期作为新文章的日期"  # noqa 501
        else:
            # 其他平台的简化模板处理
            task_description = "使用工具 read_template_tool 读取本地模板，将内容适配填充到模板中"
            backstory = "你是模板处理专家，能够将内容适配到模板中"

        agents = [
            AgentConfig(
                role="模板调整与内容填充专家",
                name="templater",
                goal="根据文章内容，适当调整给定的HTML模板，去除原有内容，并填充新内容。",
                backstory=backstory,
                tools=["ReadTemplateTool"],
            )
        ]

        tasks = [
            TaskConfig(
                name="template_content",
                description=task_description,
                agent_name="templater",
                expected_output="填充新内容但保持原有视觉风格的文章（HTML格式）",
            )
        ]

        return WorkflowConfig(
            name="template_formatting",
            description="模板格式化工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def _get_design_workflow_config(self, publish_platform: str, **kwargs) -> WorkflowConfig:
        """生成设计工作流配置"""

        # 微信平台的完整系统模板
        wechat_system_template = """<|start_header_id|>system<|end_header_id|>
# 严格按照以下要求进行微信公众号排版设计：
## 设计目标：
    - 创建一个美观、现代、易读的"**中文**"的移动端网页，具有以下特点：
    - 纯内联样式：不使用任何外部CSS、JavaScript文件，也不使用<style>标签
    - 移动优先：专为移动设备设计，不考虑PC端适配
    - 模块化结构：所有内容都包裹在<section style="xx">标签中
    - 简洁结构：不包含<header>和<footer>标签
    - 视觉吸引力：创造出视觉上令人印象深刻的设计

## 设计风格指导:
    - 色彩方案：使用大胆、酷炫配色、吸引眼球，反映出活力与吸引力，但不能超过三种色系，长久耐看，间隔合理使用，出现层次感。
    - 读者感受：一眼喜欢，很高级，很震惊，易读易懂
    - 排版：符合中文最佳排版实践，利用不同字号、字重和间距创建清晰的视觉层次，风格如《时代周刊》、《VOGUE》
    - 卡片式布局：使用圆角、阴影和边距创建卡片式UI元素
    - 图片处理：大图展示，配合适当的圆角和阴影效果

## 技术要求:
    - 纯 HTML 结构：只使用 HTML 基本标签和内联样式
    - 这不是一个标准HTML结构，只有div和section包裹，但里面可以用任意HTML标签
    - 内联样式：所有样式和字体都通过style属性直接应用在<section>这个HTML元素上，其他都没有style,包括body
    - 模块化：使用<section>标签包裹不同内容模块
    - 简单交互：用HTML原生属性实现微动效
    - 图片处理：非必要不使用配图，若必须配图且又找不到有效图片链接时，使用https://picsum.photos/[宽度]/[高度]?random=1随机一张
    - SVG：生成炫酷SVG动画，目的是方便理解或给用户小惊喜
    - SVG图标：采用Material Design风格的现代简洁图标，支持容器式和内联式两种展示方式
    - 只基于核心主题内容生成，不包含作者，版权，相关URL等信息

## 其他要求：
    - 先思考排版布局，然后再填充文章内容
    - 输出长度：10屏以内 (移动端)
    - 生成的代码**必须**放在`` 标签中
    - 主体内容必须是**中文**，但可以用部分英语装逼
    - 不能使用position: absolute
<|eot_id|>"""

        # 根据平台定制设计要求
        platform_requirements = {
            PlatformType.WECHAT.value: "微信公众号HTML设计要求：使用内联CSS样式，避免外部样式表；采用适合移动端阅读的字体大小和行距；使用微信官方推荐的色彩搭配；确保在微信客户端中显示效果良好",  # noqa 501
            PlatformType.XIAOHONGSHU.value: "小红书平台设计要求：注重视觉美感，使用年轻化的设计风格；适当使用emoji和装饰元素；保持简洁清新的排版",
            PlatformType.ZHIHU.value: "知乎平台设计要求：专业简洁的学术风格；重视内容的逻辑性和可读性；使用适合长文阅读的排版",
        }

        design_requirement = platform_requirements.get(
            publish_platform, "通用HTML设计要求：简洁美观，注重用户体验"
        )

        agents = [
            AgentConfig(
                role="微信排版专家",
                name="designer",
                goal=f"为{publish_platform}平台创建精美的HTML设计和排版",
                backstory="你是HTML设计专家",
                system_template=(
                    wechat_system_template
                    if publish_platform == PlatformType.WECHAT.value
                    else None
                ),
                prompt_template="<|start_header_id|>user<|end_header_id|>{{ .Prompt }}<|eot_id|>",
                response_template="<|start_header_id|>assistant<|end_header_id|>{{ .Response }}<|eot_id|>",  # noqa 501
            )
        ]

        tasks = [
            TaskConfig(
                name="design_content",
                description=f"为{publish_platform}平台设计HTML排版。{design_requirement}。创建精美的HTML格式，包含适当的标题层次、段落间距、颜色搭配和视觉元素，确保内容在{publish_platform}平台上有最佳的展示效果。",  # noqa 501
                agent_name="designer",
                expected_output=f"针对{publish_platform}平台优化的精美HTML内容",
            )
        ]

        return WorkflowConfig(
            name=f"{publish_platform}_design",
            description=f"面向{publish_platform}平台的HTML设计工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
        )

    def _save_content(self, content: ContentResult, title: str) -> Dict[str, Any]:
        """保存内容（非AI参与）"""
        config = Config.get_instance()
        # 确定文件格式和路径
        file_extension = utils.get_file_extension(config.article_format)
        save_path = self._get_save_path(title, file_extension)

        # 保存文件
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content.content)

        return {"success": True, "path": save_path, "title": title, "format": config.article_format}

    def _get_save_path(self, title: str, file_extension: str) -> str:
        """获取保存路径"""

        # 获取文章保存目录
        dir_path = PathManager.get_article_dir()

        # 清理文件名，确保安全
        safe_filename = utils.sanitize_filename(title)

        # 构建完整路径
        save_path = os.path.join(dir_path, f"{safe_filename}.{file_extension}")

        return save_path

    def _publish_content(
        self, content: ContentResult, publish_platform: str, **kwargs
    ) -> Dict[str, Any]:
        """发布内容（非AI参与）"""
        adapter = self.platform_adapters.get(publish_platform)

        if not adapter:
            return {"success": False, "message": f"不支持的平台: {publish_platform}"}

        # 使用平台适配器发布
        publish_result = adapter.publish_content(content, **kwargs)

        return {
            "success": publish_result.success,
            "message": publish_result.message,
            "platform": publish_platform,
        }

    def _should_publish(self) -> bool:
        """判断是否应该发布"""
        config = Config.get_instance()

        # 检查配置中的自动发布设置
        if not config.auto_publish:
            return False

        # 检查是否有有效的微信凭据
        valid_credentials = any(
            cred["appid"] and cred["appsecret"] for cred in config.wechat_credentials
        )

        if not valid_credentials:
            # 自动转为非自动发布并提示
            log.print_log("检测到自动发布已开启，但未配置有效的微信公众号凭据", "warning")
            log.print_log("请在配置中填写 appid 和 appsecret 以启用自动发布功能", "warning")
            log.print_log("当前将跳过发布步骤，仅生成内容", "info")
            return False

        return True

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
