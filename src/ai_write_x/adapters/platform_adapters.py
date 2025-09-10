from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from src.ai_write_x.utils import utils
from src.ai_write_x.config.config import Config
from src.ai_write_x.tools.custom_tool import ReadTemplateTool


class PlatformType(Enum):
    """统一的平台类型定义"""

    WECHAT = "wechat"
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    TOUTIAO = "toutiao"
    BAIJIAHAO = "baijiahao"
    ZHIHU = "zhihu"
    DOUBAN = "douban"

    @classmethod
    def get_all_platforms(cls):
        """获取所有支持的平台"""
        return [platform.value for platform in cls]

    @classmethod
    def is_valid_platform(cls, platform_name: str) -> bool:
        """验证平台名称是否有效"""
        return platform_name in cls.get_all_platforms()


@dataclass
class PublishResult:
    success: bool
    message: str
    platform_id: Optional[str] = None
    error_code: Optional[str] = None


class PlatformAdapter(ABC):
    """平台适配器基类"""

    @abstractmethod
    def format_content(self, content: str, title: str = "", summary: str = "") -> str:
        """格式化内容 - 直接处理文件内容"""
        pass

    @abstractmethod
    def publish_content(self, formatted_content: str, **kwargs) -> PublishResult:
        """发布内容"""
        pass

    def supports_html(self) -> bool:
        """是否支持HTML格式"""
        return True

    def supports_template(self) -> bool:
        """是否支持模板功能"""
        return True

    def get_platform_name(self) -> str:
        """获取平台名称"""
        return self.__class__.__name__.replace("Adapter", "").lower()

    def _extract_digest_from_content(self, content: str) -> str:
        """从内容中提取摘要"""

        # 根据文件格式提取摘要
        if content.startswith("# ") or "##" in content:
            # Markdown格式
            _, digest = utils.extract_markdown_content(content)
        else:
            # 纯文本格式
            _, digest = utils.extract_text_content(content)

        return digest or content[:200] + "..." if len(content) > 200 else content


class WeChatAdapter(PlatformAdapter):
    """微信公众号适配器"""

    def format_content(self, content: str, title: str = "", summary: str = "") -> str:
        """格式化为微信公众号HTML格式"""

        config = Config.get_instance()

        # 提取标题（如果未提供）
        if not title:
            title = utils.extract_title_from_content(content)

        # 检查是否需要使用模板
        if config.use_template:
            return self._apply_template_format(content, title)
        else:
            return self._apply_design_format(content, title)

    def _apply_template_format(self, content: str, title: str) -> str:
        """应用HTML模板格式化"""

        # 读取模板
        template_tool = ReadTemplateTool()
        template_html = template_tool.run()  # 使用默认模板选择逻辑

        # 简化的模板填充
        formatted_html = template_html.replace("{{title}}", title)

        # 将markdown内容转换为HTML并填充
        html_content = utils.get_format_article(".md", content)
        formatted_html = formatted_html.replace("{{content}}", html_content)

        return formatted_html

    def _apply_design_format(self, content: str, title: str) -> str:
        """应用设计器格式化"""

        # 将markdown转换为HTML
        html_content = utils.get_format_article(".md", content)

        # 应用微信公众号样式
        formatted_html = f"""
        <section style="max-width: 100%; margin: 0 auto; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <h1 style="font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #333; text-align: center;">{title}</h1>
            <div style="line-height: 1.8; color: #555; font-size: 16px;">
                {html_content}
            </div>
            <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 8px; text-align: center; color: #666;">
                <p style="margin: 0; font-size: 14px;">— END —</p>
            </div>
        </section>
        """  # noqa 501

        return formatted_html

    def publish_content(self, formatted_content: str, **kwargs) -> PublishResult:
        """发布到微信公众号"""
        # 提取微信发布所需参数
        appid = kwargs.get("appid", "")
        appsecret = kwargs.get("appsecret", "")
        author = kwargs.get("author", "")

        # 验证必需参数
        if not all([appid, appsecret]):
            return PublishResult(
                success=False,
                message="微信发布缺少必需参数: appid, appsecret",
                platform_id="wechat",
                error_code="MISSING_CREDENTIALS",
            )

        # 提取标题和摘要
        title = utils.extract_title_from_content(formatted_content)
        digest = self._extract_digest_from_content(formatted_content)

        # 调用微信发布API
        from ..tools.wx_publisher import pub2wx

        try:
            result, _, success = pub2wx(title, digest, formatted_content, appid, appsecret, author)
            return PublishResult(success=success, message=result, platform_id="wechat")
        except Exception as e:
            return PublishResult(
                success=False,
                message=f"微信发布异常: {str(e)}",
                platform_id="wechat",
                error_code="PUBLISH_ERROR",
            )


class XiaohongshuAdapter(PlatformAdapter):
    """小红书适配器"""

    def format_content(self, content: str, title: str = "", summary: str = "") -> str:
        """格式化为小红书特有格式"""
        if not title:
            title = utils.extract_title_from_content(content)

        # 小红书特色：emoji、标签、分段
        formatted = f"✨ {title} ✨\n\n"

        # 添加引人注目的开头
        formatted += "🔥 今天分享一个超有用的内容！\n\n"

        # 处理正文内容，每段添加emoji
        paragraphs = content.split("\n\n")
        emoji_list = ["💡", "🌟", "✨", "🎯", "💫", "🔥", "👀", "💪"]

        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip() and not paragraph.startswith("#"):
                emoji = emoji_list[i % len(emoji_list)]
                formatted += f"{emoji} {paragraph.strip()}\n\n"

        # 添加互动引导
        formatted += "💬 你们觉得呢？评论区聊聊～\n\n"

        # 添加相关标签
        formatted += "#AI写作 #内容创作 #自媒体运营 #干货分享 #效率工具 #科技前沿"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> PublishResult:
        """小红书发布（待开发）"""
        return PublishResult(
            success=False,
            message="小红书发布功能待开发 - 需要接入小红书开放平台API",
            platform_id="xiaohongshu",
            error_code="NOT_IMPLEMENTED",
        )


class DouyinAdapter(PlatformAdapter):
    """抖音适配器"""

    def format_content(self, content: str, title: str = "", summary: str = "") -> str:
        """格式化为短视频脚本格式"""
        if not title:
            title = utils.extract_title_from_content(content)

        script = f"🎬 【视频脚本】{title}\n\n"

        # 开场白
        script += "【开场】（3秒）\n"
        script += "大家好！今天我们来聊一个超有意思的话题...\n\n"

        # 将内容分解为短视频脚本段落（适合60秒短视频）
        paragraphs = [
            p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")
        ][:3]

        for i, paragraph in enumerate(paragraphs, 1):
            script += f"【第{i}部分】（15-20秒）\n"
            # 简化段落内容，适合口语化表达
            simplified = paragraph[:100] + "..." if len(paragraph) > 100 else paragraph
            script += f"{simplified}\n\n"

        # 结尾引导
        script += "【结尾】（5秒）\n"
        script += "如果觉得有用，记得点赞关注哦！我们下期见～\n\n"

        # 添加标签建议
        script += "📝 建议标签：#知识分享 #干货 #学习 #科技"

        return script

    def publish_content(self, formatted_content: str, **kwargs) -> PublishResult:
        """抖音发布（待开发）"""
        return PublishResult(
            success=False,
            message="抖音发布功能待开发 - 需要接入抖音开放平台API",
            platform_id="douyin",
            error_code="NOT_IMPLEMENTED",
        )


class ToutiaoAdapter(PlatformAdapter):
    """今日头条适配器"""

    def format_content(self, content: str, title: str = "", summary: str = "") -> str:
        """格式化为今日头条格式"""
        if not title:
            title = utils.extract_title_from_content(content)

        if not summary:
            summary = self._extract_digest_from_content(content)

        # 今日头条偏好清晰的结构和较长的标题
        formatted = f"# {title}\n\n"

        # 添加导读
        formatted += f"**📖 导读**\n\n{summary}\n\n"
        formatted += "---\n\n"

        # 处理正文内容，添加小标题结构
        paragraphs = [
            p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")
        ]

        section_titles = ["核心观点", "深度分析", "实践应用", "未来展望", "总结思考"]

        for i, paragraph in enumerate(paragraphs):
            # 每隔几段添加小标题
            if i > 0 and i % 2 == 0 and i // 2 < len(section_titles):
                formatted += f"## 🎯 {section_titles[i // 2]}\n\n"

            formatted += f"{paragraph}\n\n"

        # 添加结尾互动
        formatted += "---\n\n"
        formatted += "**💭 你的看法**\n\n"
        formatted += (
            "对于这个话题，你有什么不同的见解？欢迎在评论区分享你的观点，让我们一起讨论！\n\n"
        )
        formatted += "*如果觉得内容有价值，请点赞支持一下～*"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> PublishResult:
        """今日头条发布（待开发）"""
        return PublishResult(
            success=False,
            message="今日头条发布功能待开发 - 需要接入头条号开放平台API",
            platform_id="toutiao",
            error_code="NOT_IMPLEMENTED",
        )


class BaijiahaoAdapter(PlatformAdapter):
    """百家号适配器"""

    def format_content(self, content: str, title: str = "", summary: str = "") -> str:
        """格式化为百家号格式"""
        if not title:
            title = utils.extract_title_from_content(content)

        # 百家号注重原创性和专业性
        formatted = f"# {title}\n\n"

        # 添加原创声明
        formatted += "**📝 原创声明**\n\n"
        formatted += (
            "*本文为原创内容，未经授权禁止转载。如需转载请联系作者获得授权并注明出处。*\n\n"
        )
        formatted += "---\n\n"

        # 处理正文，添加专业化结构
        paragraphs = [
            p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")
        ]

        # 添加目录（如果内容较长）
        if len(paragraphs) > 4:
            formatted += "**📋 本文目录**\n\n"
            for i in range(min(5, len(paragraphs))):
                formatted += f"{i+1}. 核心要点分析\n"
            formatted += "\n---\n\n"

        # 分段处理，每3段添加小标题
        section_count = 1
        for i, paragraph in enumerate(paragraphs):
            if i > 0 and i % 3 == 0:
                formatted += f"## 📊 {section_count}. 深度解析\n\n"
                section_count += 1

            formatted += f"{paragraph}\n\n"
        # 添加专业结尾
        formatted += "---\n\n"
        formatted += "**🎯 总结**\n\n"

        # 生成总结段落
        if summary:
            formatted += f"{summary}\n\n"
        else:
            # 从内容中提取关键点作为总结
            key_points = self._extract_key_points(paragraphs)
            formatted += (
                f"通过以上分析，我们可以看出{key_points}。这些观点为我们提供了新的思考角度。\n\n"
            )

        # 添加专业版权声明
        formatted += "---\n\n"
        formatted += "**📄 版权声明**\n\n"
        formatted += (
            "*本文观点仅代表作者个人立场，不代表平台观点。如有不同见解，欢迎理性讨论。*\n\n"
        )
        formatted += "*原创不易，如果本文对您有帮助，请点赞支持。转载请联系作者授权。*"

        return formatted

    def _extract_key_points(self, paragraphs: list) -> str:
        """从段落中提取关键点"""
        if not paragraphs:
            return "相关话题具有重要意义"

        # 简单的关键点提取逻辑
        first_paragraph = paragraphs[0] if paragraphs else ""
        if len(first_paragraph) > 50:
            return first_paragraph[:50] + "等核心要点"
        return "该话题的多个重要方面"

    def publish_content(self, formatted_content: str, **kwargs) -> PublishResult:
        """百家号发布（待开发）"""
        return PublishResult(
            success=False,
            message="百家号发布功能待开发 - 需要接入百度百家号API",
            platform_id="baijiahao",
            error_code="NOT_IMPLEMENTED",
        )


class ZhihuAdapter(PlatformAdapter):
    """知乎适配器"""

    def format_content(self, content: str, title: str = "", summary: str = "") -> str:
        """格式化为知乎格式"""
        if not title:
            title = utils.extract_title_from_content(content)

        if not summary:
            summary = self._extract_digest_from_content(content)

        # 知乎偏好问答式和深度分析
        formatted = f"# {title}\n\n"

        # 添加TL;DR摘要
        formatted += f"**TL;DR：** {summary}\n\n"
        formatted += "---\n\n"

        # 处理正文，添加逻辑结构
        paragraphs = [
            p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")
        ]

        # 添加目录结构（如果内容较长）
        if len(paragraphs) > 3:
            formatted += "**📚 本文目录：**\n\n"
            section_titles = ["核心观点", "深度分析", "实践应用", "总结思考"]
            for i in range(min(len(section_titles), len(paragraphs))):
                formatted += f"- {section_titles[i]}\n"
            formatted += "\n---\n\n"

        # 分段处理，添加逻辑标题
        section_titles = ["🎯 核心观点", "🔍 深度分析", "💡 实践应用", "🤔 总结思考"]

        for i, paragraph in enumerate(paragraphs):
            # 根据位置添加合适的小标题
            if i < len(section_titles):
                formatted += f"## {section_titles[i]}\n\n"
            elif i > 0 and i % 2 == 0:
                formatted += "## 📖 进一步思考\n\n"

            formatted += f"{paragraph}\n\n"

        # 添加知乎特色的互动引导
        formatted += "---\n\n"
        formatted += "**💬 讨论时间**\n\n"
        formatted += "你怎么看这个问题？欢迎在评论区分享你的想法和经验，我们一起深入讨论！\n\n"
        formatted += "*觉得有价值的话，请点赞支持一下，让更多人看到这个内容～*\n\n"
        formatted += "**🔔 关注我，获取更多深度内容分析**"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> PublishResult:
        """知乎发布（待开发）"""
        return PublishResult(
            success=False,
            message="知乎发布功能待开发 - 需要接入知乎API或使用浏览器自动化",
            platform_id="zhihu",
            error_code="NOT_IMPLEMENTED",
        )


class DoubanAdapter(PlatformAdapter):
    """豆瓣适配器"""

    def format_content(self, content: str, title: str = "", summary: str = "") -> str:
        """格式化为豆瓣格式"""
        if not title:
            title = utils.extract_title_from_content(content)

        # 豆瓣偏好文艺性和个人化表达
        formatted = f"# {title}\n\n"

        # 添加情感化开头
        formatted += "*写在前面：最近在思考这个话题，想和大家分享一些个人的感悟和思考*\n\n"
        formatted += "---\n\n"

        # 处理正文，保持文艺风格
        paragraphs = [
            p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")
        ]

        connectors = [
            "说到这里，",
            "想起来，",
            "不禁让我想到，",
            "或许，",
            "突然觉得，",
            "有时候想想，",
        ]

        for i, paragraph in enumerate(paragraphs):
            # 添加文艺化的连接词（除了第一段）
            if i > 0:
                import random

                connector = random.choice(connectors)
                formatted += f"{connector}"

            formatted += f"{paragraph}\n\n"

        # 添加豆瓣特色的个人化结尾
        formatted += "---\n\n"
        formatted += "*写在最后：*\n\n"
        formatted += (
            "以上只是个人的一些浅见和感悟，每个人的经历和思考都不同，所以观点也会有差异。\n\n"
        )
        formatted += "如果你也有类似的想法，或者有不同的见解，都欢迎在评论区和我交流讨论。\n\n"
        formatted += "🌟 *如果觉得有共鸣，不妨点个赞让我知道～*\n\n"
        formatted += "📚 *更多思考和分享，欢迎关注我的豆瓣*"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> PublishResult:
        """豆瓣发布（待开发）"""
        return PublishResult(
            success=False,
            message="豆瓣发布功能待开发 - 需要使用浏览器自动化工具",
            platform_id="douban",
            error_code="NOT_IMPLEMENTED",
        )
