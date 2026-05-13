import os
import time
import json
from typing import Dict, Any, List

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
from src.ai_write_x.core.knowledge_manager import KnowledgeManager
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import utils
from src.ai_write_x.adapters.platform_adapters import PlatformType
from src.ai_write_x.utils import log

# 导入维度化创意引擎
from src.ai_write_x.creative.dimensional_engine import DimensionalCreativeEngine


class UnifiedContentWorkflow:
    """统一的内容工作流编排器"""

    def __init__(self):
        self.content_engine = None
        # 移除所有旧创意模块，只保留维度化创意引擎
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
        # 初始化维度化创意引擎
        config = Config.get_instance()
        dimensional_config = config.dimensional_creative_config
        self.creative_engine = DimensionalCreativeEngine(dimensional_config)

    def _search_relevant_images(self, topic: str, category: str = None) -> List[Dict[str, Any]]:
        """
        搜索与话题相关的图片

        Args:
            topic: 文章话题
            category: 可选的分类

        Returns:
            List[Dict]: 匹配的图片列表
        """
        try:
            from src.ai_write_x.tools.image_search_tool import ImageSearchTool

            tool = ImageSearchTool()
            results = tool._run(query=topic, category=category, limit=5)

            if results:
                return json.loads(results)
            return []

        except Exception as e:
            log.print_log(f"图片搜索失败: {e}", "warning")
            return []

    def _insert_images_to_content(self, content: str, images: List[Dict[str, Any]], max_images: int = 3) -> str:
        """
        将图片插入到文章内容中

        Args:
            content: 文章HTML内容
            images: 图片列表
            max_images: 最大插入图片数

        Returns:
            str: 插入图片后的内容
        """
        if not images:
            return content

        # 构建图片HTML标签
        image_tags = []
        for img in images[:max_images]:
            path = img.get("stored_path", "")
            desc = img.get("description", "") or img.get("original_filename", "")
            alt_text = desc.replace('"', "'")

            # 构建完整的图片标签
            img_tag = f'<img src="{path}" alt="{alt_text}" style="max-width:100%;margin:20px 0;" loading="lazy" />'
            image_tags.append(img_tag)

        if not image_tags:
            return content

        # 尝试在第一个</p>后插入
        first_para_end = content.find("</p>")
        if first_para_end != -1:
            insert_pos = first_para_end + 4
            content = content[:insert_pos] + "\n".join(image_tags) + content[insert_pos:]
        else:
            # 如果没有</p>，在</section>后插入
            first_section_end = content.find("</section>")
            if first_section_end != -1:
                insert_pos = first_section_end + len("</section>")
                content = content[:insert_pos] + "\n".join(image_tags) + content[insert_pos:]

        log.print_log(f"[IMAGE_INSERT] 已插入 {len(image_tags)} 张相关图片到HTML内容", "info")
        return content

    def _extract_image_results(self) -> List[Dict[str, Any]]:
        """从 CrewAI 任务输出中提取图片搜索结果"""
        try:
            if not self.content_engine or not self.content_engine.tasks:
                return []

            search_task = self.content_engine.tasks.get("search_images")
            if not search_task or not hasattr(search_task, "output") or not search_task.output:
                return []

            raw = getattr(search_task.output, "raw", str(search_task.output))
            raw = utils.remove_code_blocks(raw)
            images = json.loads(raw)

            if isinstance(images, list):
                valid = [
                    img for img in images
                    if img.get("image_id") and img.get("stored_path")
                ]
                if valid:
                    log.print_log(
                        f"[IMAGE_MATCH] 提取到 {len(valid)} 张匹配图片", "info"
                    )
                return valid
            return []
        except (json.JSONDecodeError, Exception) as e:
            log.print_log(f"[IMAGE_MATCH] 图片结果解析失败: {e}", "warning")
            return []

    def _replace_placeholder_images(
        self, content: ContentResult, images: List[Dict[str, Any]]
    ) -> ContentResult:
        """替换 HTML 中的占位图片为知识库匹配图片"""
        import re

        if not images:
            return content

        html = content.content
        pattern = r'(src=["\'])https://picsum\.photos/[^"\']+(["\'])'
        matches = list(re.finditer(pattern, html))

        if not matches:
            log.print_log("[IMAGE_MATCH] 未找到占位图片", "info")
            return content

        replaced = 0
        for i, match in enumerate(matches):
            if i >= len(images):
                break
            path = images[i].get("stored_path", "")
            if path:
                html = (
                    html[: match.start()]
                    + f'src="{path}"'
                    + html[match.end() :]
                )
                replaced += 1

        log.print_log(
            f"[IMAGE_MATCH] 替换了 {replaced}/{len(matches)} 张占位图片", "info"
        )

        return ContentResult(
            title=content.title,
            content=html,
            summary=content.summary,
            content_format=content.content_format,
            metadata=content.metadata,
        )

    def get_base_content_config(self, **kwargs) -> WorkflowConfig:
        """动态生成基础内容配置，根据平台和需求定制"""

        config = Config.get_instance()
        # 获取目标平台
        publish_platform = kwargs.get("publish_platform", PlatformType.WECHAT.value)

        # Task 2: 写作任务的描述
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
3. 如果前置任务搜索到了知识库中的相关资料，应结合知识库资料进行创作
4. 确保文章逻辑清晰、内容完整、语言流畅

文章要求：
- 标题：当{{platform}}不为空时为"{{platform}}|{{topic}}"，否则为"{{topic}}"
- 总字数：{config.min_article_len}~{config.max_article_len}字（纯文本字数）
- 格式：标准Markdown格式
- 内容：仅输出最终文章内容，严禁包含思考过程或额外说明"""

        config = Config.get_instance()

        knowledge_manager = KnowledgeManager.get_instance()
        knowledge_sources = knowledge_manager.get_all_knowledge_sources()
        embedder = knowledge_manager.get_embedder() if knowledge_sources else {}

        # 根据知识库启用状态，决定是否添加搜索 Agent 和 Task
        text_enabled = knowledge_manager.is_text_enabled()
        image_enabled = knowledge_manager.is_image_enabled()

        agents = []
        tasks = []

        # Agent: 知识研究员（文本知识库启用时添加）
        if text_enabled:
            agents.append(
                AgentConfig(
                    role="知识研究员",
                    name="researcher",
                    goal="根据话题，在知识库中搜索相关的参考资料和素材",
                    backstory=(
                        "你是知识检索专家。你的任务是根据给定的话题，"
                        "使用 text_knowledge_search 工具搜索知识库中的相关资料。"
                        "请从话题中提取最核心的关键词进行搜索（例如话题是'火锅店老板创业故事'，"
                        "就用'创业故事'或'火锅店老板'搜索），不要用完整的话题描述作为搜索词。"
                        "如果搜索到相关资料，完整输出资料内容；如果未找到，说明即可。"
                    ),
                    tools=["TextKnowledgeSearchTool"],
                ),
            )
            tasks.append(
                TaskConfig(
                    name="search_knowledge",
                    description=(
                        "请根据话题 '{topic}'，在知识库中搜索相关的参考资料。\n"
                        "步骤：\n"
                        "1. 从话题中提取 1-3 个核心关键词\n"
                        "2. 使用 text_knowledge_search 工具搜索\n"
                        "3. 如果第一次搜索无结果，尝试换一组关键词再搜索一次\n"
                        "4. 输出找到的相关知识内容（含完整正文），或明确说明未找到"
                    ),
                    agent_name="researcher",
                    expected_output="搜索到的相关知识内容（含完整正文），或'未找到相关知识'",
                ),
            )

        # Agent: 图片匹配专家（图片知识库启用时添加）
        if image_enabled:
            agents.append(
                AgentConfig(
                    role="图片匹配专家",
                    name="image_matcher",
                    goal="根据文章话题，在图片知识库中搜索最匹配的图片",
                    backstory=(
                        "你是图片检索专家。根据给定的话题，"
                        "使用 image_search 工具搜索图片知识库中的相关图片。"
                        "请从话题中提取关键场景、主题和概念作为搜索词，"
                        "每个搜索词应简洁精准（2-4个词），分别搜索不同维度的图片。"
                    ),
                    tools=["ImageSearchTool"],
                ),
            )
            tasks.append(
                TaskConfig(
                    name="search_images",
                    description=(
                        "请根据话题 '{topic}' 搜索图片知识库。\n"
                        "步骤：\n"
                        "1. 分析话题，提取 3-5 个不同维度的搜索关键词\n"
                        "   （主题词、场景词、情感词、物体词）\n"
                        "2. 对每个关键词使用 image_search 工具搜索，limit=2\n"
                        "3. 汇总所有结果，去除重复（相同 image_id），保留最多 8 张\n"
                        "4. 输出 JSON 格式的图片列表\n\n"
                        "输出格式（必须是合法JSON数组）：\n"
                        '[{{"image_id": "...", "stored_path": "...", '
                        '"description": "...", "score": 0.9}}]'
                    ),
                    agent_name="image_matcher",
                    expected_output=(
                        "JSON格式的匹配图片列表，"
                        "包含 image_id, stored_path, description, score"
                    ),
                    context=["search_knowledge"] if text_enabled else [],
                ),
            )

        # Agent: 内容创作专家
        agents.append(
            AgentConfig(
                role="内容创作专家",
                name="writer",
                goal="撰写高质量文章",
                backstory="你是一位作家，能够结合外部搜索结果和知识库内容完成写作。若前置任务搜索到了知识库中的相关资料，应优先参考其内容融入文章。",
                tools=["AIForgeSearchTool", "ImageSearchTool"],
            ),
        )

        # Task: 写作
        write_context = []
        if text_enabled:
            write_context.append("search_knowledge")
        if image_enabled:
            write_context.append("search_images")
        tasks.append(
            TaskConfig(
                name="write_content",
                description=writer_des,
                agent_name="writer",
                expected_output="文章标题 + 文章正文（标准Markdown格式）",
                context=write_context,
            ),
        )

        return WorkflowConfig(
            name=f"{publish_platform}_content_generation",
            description=f"面向{publish_platform}平台的内容生成工作流",
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=agents,
            tasks=tasks,
            knowledge_sources=knowledge_sources,
            embedder=embedder,
            knowledge_config=knowledge_manager.get_knowledge_config(),
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

        result = self.content_engine.execute_workflow(input_data)

        # 提取图片搜索结果
        matched_images = self._extract_image_results()
        if matched_images:
            result.metadata["matched_images"] = matched_images

        return result

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

        # 注意: 图片检索和文本知识检索已移至 CrewAI Task 内部，
        # 图片配图在 HTML 变换后通过 _replace_placeholder_images 处理

        try:
            # 1. 生成基础内容（统一Markdown格式）
            base_content = self._generate_base_content(
                topic, publish_platform=publish_platform, **kwargs
            )
            log.print_log("[PROGRESS:WRITING:END]", "internal")

            # 2. 维度化创意变换
            log.print_log("[PROGRESS:CREATIVE:START]", "internal")
            final_content = self._apply_dimensional_creative_transformation(base_content, **kwargs)
            log.print_log("[PROGRESS:CREATIVE:END]", "internal")

            # 3. 转换处理（template或design）
            log.print_log("[PROGRESS:TRANSFORM:START]", "internal")
            transform_content = self._transform_content(final_content, publish_platform, **kwargs)
            log.print_log("[PROGRESS:TRANSFORM:END]", "internal")

            # 3.5 配图替换：用知识库匹配图片替换占位图
            matched_images = base_content.metadata.get("matched_images", [])
            if matched_images:
                log.print_log("[PROGRESS:IMAGE_MATCH:START]", "internal")
                transform_content = self._replace_placeholder_images(
                    transform_content, matched_images
                )
                log.print_log("[PROGRESS:IMAGE_MATCH:END]", "internal")

            # 4. 保存（非AI参与）
            log.print_log("[PROGRESS:SAVE:START]", "internal")
            save_result = self._save_content(transform_content, title)
            if save_result.get("success", False):
                article_path = save_result.get("path")
                kwargs["article_path"] = article_path
                log.print_log(f"文章《{title}》保存成功！")
            log.print_log("[PROGRESS:SAVE:END]", "internal")

            # 5. 可选发布（非AI参与，开关控制）
            publish_result = None
            if self._should_publish():
                log.print_log("[PROGRESS:PUBLISH:START]", "internal")
                publish_result = self._publish_content(
                    transform_content, publish_platform, **kwargs
                )
                log.print_log(f"发布完成，总结：{publish_result.get('message')}")

                log.print_log("[PROGRESS:PUBLISH:END]", "internal")

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
        log.print_log("[PROGRESS:TEMPLATE:START]", "internal")

        template_config = self._get_template_workflow_config(**kwargs)
        engine = ContentGenerationEngine(template_config)

        input_data = {
            "content": content.content,
            "title": content.title,
            "parse_result": False,
            "content_format": "html",
            **kwargs,
        }

        ret = engine.execute_workflow(input_data)
        log.print_log("[PROGRESS:TEMPLATE:END]", "internal")

        return ret

    def _apply_design_formatting(
        self, content: ContentResult, publish_platform: str, **kwargs
    ) -> ContentResult:
        """Design路径：使用AI生成HTML设计"""
        # 创建专门的设计工作流
        log.print_log("[PROGRESS:DESIGN:START]", "internal")

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

        ret = engine.execute_workflow(input_data)
        log.print_log("[PROGRESS:DESIGN:END]", "internal")

        return ret

    def _apply_dimensional_creative_transformation(
        self, base_content: ContentResult, **kwargs
    ) -> ContentResult:
        """维度化创意变换"""
        config = Config.get_instance()
        dimensional_config = config.dimensional_creative_config

        # 检查是否启用维度化创意
        if not dimensional_config.get("enabled", False):
            return base_content

        # 重新初始化维度化创意引擎以获取最新配置
        self.creative_engine = DimensionalCreativeEngine(dimensional_config)

        # 应用维度化创意变换
        try:
            transformed_content = self.creative_engine.apply_dimensional_creative(
                base_content.content, base_content.title
            )

            # 创建新的ContentResult对象 - 包含所有必需参数
            result = ContentResult(
                title=base_content.title,
                content=transformed_content,
                summary=base_content.summary,  # 添加缺失的summary参数
                content_format=base_content.content_format,  # 添加缺失的content_format参数
                metadata=base_content.metadata.copy(),
            )

            # 添加变换元数据
            result.metadata.update(
                {
                    "transformation_type": "dimensional_creative",
                    "original_content_id": id(base_content),
                    "creative_engine_config": dimensional_config,
                }
            )

            return result

        except Exception as e:
            log.print_log(f"维度化创意变换失败: {str(e)}", "error")
            return base_content

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

        # 将 cover_path 传递给适配器
        kwargs["cover_path"] = utils.get_cover_path(kwargs.get("article_path"))

        # 使用平台适配器发布
        # 适配器内部会自动保存发布记录
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

    def register_platform_adapter(self, name: str, adapter):
        """注册新的平台适配器"""
        self.platform_adapters[name] = adapter
