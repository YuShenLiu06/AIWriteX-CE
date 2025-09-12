import os
import time
from typing import Dict, Any
from src.ai_write_x.core.creative_modules import (
    StyleTransformModule,
    TimeTravelModule,
    RolePlayModule,
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
            "time_travel": TimeTravelModule(),
            "role_play": RolePlayModule(),
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

    def get_base_content_config(self, **kwargs) -> WorkflowConfig:
        """动态生成基础内容配置，根据平台和需求定制"""

        config = Config.get_instance()
        # 获取目标平台
        publish_platform = kwargs.get("publish_platform", PlatformType.WECHAT.value)

        topic_analyzer_des = """解析话题'{topic}'，确定文章的核心要点和结构。
生成一份包含文章大纲和核心要点的报告。
注意：
1. 关于文章标题的日期处理：
    - 严格检查：'{topic}'中是否已包含具体年份或日期信息
    - 如果包含，则保留该日期信息在文章标题中
    - 如果不包含，则文章标题不能带任何年份或日期信息
    - 禁止自行添加当前年份或任何其他年份到文章标题中
2. 内容中的日期处理：
    - 如果'{topic}'包含日期，在内容中使用该日期
    - 如果不包含，对于需要提及年份的内容，使用"20xx年"格式
"""
        writer_des = f"""基于生成的文章大纲和搜索工具获取的最新信息，撰写一篇高质量的文章。
确保文章内容准确、逻辑清晰、语言流畅，并具有独到的见解。
工具 aiforge_search_tool 使用以下参数：
    topic={{topic}}
    urls={{urls}}
    reference_ratio={{reference_ratio}}。

执行步骤：
1. 使用 aiforge_search_tool 获取关于'{{topic}}'的最新信息
2. 根据获取的结果的类型和内容深度调整写作策略：
    - 如果获取到有效搜索结果：
    * 包含"参考比例"时：融合生成的文章大纲与参考文章结果的内容，并根据比例调整借鉴程度
    * 不包含"参考比例"时：融合生成的文章大纲和与'{{topic}}'相关的搜索结果进行原创写作
    * 用搜索结果中的真实时间替换大纲中的占位符
        - 如果搜索结果有具体日期，直接替换"20xx年"等占位符
        - 如果搜索结果无具体日期，使用"近期"、"最近"、"据最新数据显示"等表述
    - 如果没有获取到有效搜索结果：
    * 基于文章大纲进行原创写作，确保内容的完整性和可读性
    * 将所有日期占位符（如"20xx年"）替换为通用时间表述：
        - "近年来"、"近期"、"最近几年"
        - "当前"、"目前"、"现阶段"
        - "据业界观察"、"根据行业趋势"
3. 最终检查：确保文章中不存在任何未替换的日期占位符

生成的文章要求：
- 标题：当{{platform}}不为空时为"{{platform}}|{{topic}}"，否则为"{{topic}}"
- 总字数：{config.min_article_len}~{config.max_article_len}字（纯文本字数，不包括Markdown语法、空格）
- 文章内容：仅输出最终纯文章内容，禁止包含思考过程、分析说明、字数统计等额外注释、说明"""

        config = Config.get_instance()

        # 基础配置
        agents = [
            AgentConfig(
                role="话题分析专家",
                name="topic_analyzer",
                goal="解析话题，确定文章的核心要点和结构",
                backstory="你是一位内容策略师",
            ),
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
                name="analyze_topic",
                description=topic_analyzer_des,
                agent_name="topic_analyzer",
                expected_output="文章大纲",
            ),
            TaskConfig(
                name="write_content",
                description=writer_des,
                agent_name="writer",
                expected_output="文章标题 + 文章正文（标准Markdown格式）",
                context=["analyze_topic"],
            ),
        ]

        # 动态添加审核（基于配置）
        if config.need_auditor:
            agents.append(
                AgentConfig(
                    role="质量审核专家", name="auditor", goal="质量审核", backstory="质量专家"
                )
            )
            tasks.append(
                TaskConfig(
                    name="audit_content",
                    description="质量审核",
                    agent_name="auditor",
                    expected_output="审核后文章",
                    context=["write_content"],
                )
            )

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
        """应用创意变换，支持组合使用"""

        def create_engine(config):
            """创建内容生成引擎的工厂方法"""
            return ContentGenerationEngine(config)

        config = Config.get_instance()
        creative_mode = config.config.get("creative_mode", "")
        creative_config = config.config.get("creative_config", {})

        if not creative_mode:
            return base_content

        # 支持组合模式
        modes = [mode.strip() for mode in creative_mode.split(",")]
        current_content = base_content

        for mode in modes:
            if mode == "style_transform" and creative_config.get("style_transform", {}).get(
                "enabled"
            ):
                style_config = creative_config["style_transform"]
                module = self.creative_modules.get("style_transform")
                if module:
                    current_content = module.transform(
                        current_content,
                        style_target=style_config.get("style_target", "shakespeare"),
                        engine_factory=create_engine,
                        **kwargs,
                    )

            elif mode == "time_travel" and creative_config.get("time_travel", {}).get("enabled"):
                time_config = creative_config["time_travel"]
                module = self.creative_modules.get("time_travel")
                if module:
                    current_content = module.transform(
                        current_content,
                        time_perspective=time_config.get("time_perspective", "ancient"),
                        engine_factory=create_engine,
                        **kwargs,
                    )

            elif mode == "role_play" and creative_config.get("role_play", {}).get("enabled"):
                role_config = creative_config["role_play"]
                module = self.creative_modules.get("role_play")
                if module:
                    current_content = module.transform(
                        current_content,
                        role_character=role_config.get("role_character", "celebrity"),
                        engine_factory=create_engine,
                        **kwargs,
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
    - 生成的代码**必须**放在Markdown ``` 标签中
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
