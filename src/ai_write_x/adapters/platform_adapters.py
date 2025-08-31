from abc import ABC, abstractmethod
from ..core.base_framework import ContentResult


class PlatformAdapter(ABC):
    """平台适配器基类"""

    @abstractmethod
    def format_content(self, content: ContentResult) -> str:
        """将通用内容格式化为平台特定格式"""
        pass

    @abstractmethod
    def publish_content(self, formatted_content: str, **kwargs) -> bool:
        """发布到特定平台"""
        pass

    def get_platform_name(self) -> str:
        """获取平台名称"""
        return self.__class__.__name__.replace("Adapter", "").lower()


class WeChatAdapter(PlatformAdapter):
    """微信公众号适配器 - 复用现有的designer/templater逻辑"""

    def __init__(self):
        # 复用现有的工具
        from ..tools.custom_tool import PublisherTool, ReadTemplateTool

        self.publisher_tool = PublisherTool()
        self.template_tool = ReadTemplateTool()

    def format_content(
        self, content: ContentResult, use_template: bool = False, template_path: str = None
    ) -> str:
        """格式化为微信公众号HTML格式"""
        if use_template and template_path:
            # 使用模板格式化（对应现有的templater智能体功能）
            return self._apply_template(content, template_path)
        else:
            # 使用设计器格式化（对应现有的designer智能体功能）
            return self._apply_design(content)

    def _apply_template(self, content: ContentResult, template_path: str) -> str:
        """应用HTML模板"""
        # 这里复用现有的templater智能体逻辑
        # 基于src/ai_write_x/config/tasks.yaml:87-124的template_content任务
        template_html = self.template_tool.run(template_path)

        # 简化的模板填充逻辑
        formatted_html = template_html.replace("{{title}}", content.title)
        formatted_html = formatted_html.replace("{{content}}", content.content)

        return formatted_html

    def _apply_design(self, content: ContentResult) -> str:
        """应用设计器格式化"""
        # 这里复用现有的designer智能体逻辑
        # 基于src/ai_write_x/config/agents.yaml:47-93的designer配置

        # 简化的HTML设计逻辑，基于现有的设计要求
        html_content = f"""
        <section style="max-width: 100%; margin: 0 auto; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <h1 style="font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #333;">{content.title}</h1>
            <div style="line-height: 1.6; color: #555;">
                {self._markdown_to_html(content.content)}
            </div>
        </section>
        """  # noqa 501

        return html_content

    def _markdown_to_html(self, markdown_content: str) -> str:
        """使用现有的 markdown 转换功能"""
        from ..utils.utils import get_format_article

        return get_format_article(".md", markdown_content)

    def publish_content(
        self,
        formatted_content: str,
        appid: str = "",
        appsecret: str = "",
        author: str = "",
        **kwargs,
    ) -> bool:
        """发布到微信公众号"""
        # 复用现有的发布逻辑
        from ..tools.wx_publisher import pub2wx
        from ..utils import utils

        try:
            # 提取标题和摘要
            title = utils.extract_main_title(formatted_content)
            if not title:
                print("无法提取文章标题")
                return False

            # 生成摘要
            _, digest = utils.extract_markdown_content(formatted_content)

            # 调用现有的微信发布功能
            result, _, _ = pub2wx(title, digest, formatted_content, appid, appsecret, author)

            return "成功" in result

        except Exception as e:
            print(f"发布失败: {e}")
            return False


class XiaohongshuAdapter(PlatformAdapter):
    """小红书适配器"""

    def format_content(self, content: ContentResult) -> str:
        """格式化为小红书特有格式"""
        # 小红书特色：大量emoji、标签、分段
        formatted = f"✨ {content.title} ✨\n\n"

        # 添加内容，每段后加emoji
        paragraphs = content.content.split("\n\n")
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                formatted += f"{paragraph.strip()} 💫\n\n"

        # 添加相关标签
        formatted += "\n#AI写作 #内容创作 #自媒体 #干货分享"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> bool:
        """小红书发布（暂时返回False，需要接入小红书API）"""
        print("小红书发布功能待开发")
        return False


class DouyinAdapter(PlatformAdapter):
    """抖音适配器"""

    def format_content(self, content: ContentResult) -> str:
        """格式化为短视频脚本格式"""
        script = f"【标题】{content.title}\n\n"
        script += "【开场】\n大家好，今天我们来聊聊...\n\n"

        # 将内容分解为短视频脚本段落
        paragraphs = content.content.split("\n\n")[:3]  # 只取前3段，适合短视频

        for i, paragraph in enumerate(paragraphs, 1):
            if paragraph.strip():
                script += f"【第{i}部分】\n{paragraph.strip()}\n\n"

        script += "【结尾】\n如果觉得有用，记得点赞关注哦！"

        return script

    def publish_content(self, formatted_content: str, **kwargs) -> bool:
        """抖音发布（暂时返回False，需要接入抖音开放平台API）"""
        print("抖音发布功能待开发")
        return False


class ToutiaoAdapter(PlatformAdapter):
    """今日头条适配器"""

    def format_content(self, content: ContentResult) -> str:
        """格式化为今日头条格式"""
        # 今日头条偏好较长标题和清晰的段落结构
        formatted = f"# {content.title}\n\n"

        # 添加引言段落
        formatted += f"**导读：** {content.summary}\n\n"

        # 处理正文内容，确保段落清晰
        paragraphs = content.content.split("\n\n")
        for paragraph in paragraphs:
            if paragraph.strip():
                formatted += f"{paragraph.strip()}\n\n"

        # 添加结尾互动
        formatted += "\n---\n**你对此有什么看法？欢迎在评论区分享你的观点！**"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> bool:
        """今日头条发布（需要接入今日头条开放平台API）"""
        print("今日头条发布功能待开发 - 需要接入头条号开放平台API")
        return False


class BaijiahaoAdapter(PlatformAdapter):
    """百家号适配器"""

    def format_content(self, content: ContentResult) -> str:
        """格式化为百家号格式"""
        # 百家号注重原创性和专业性
        formatted = f"# {content.title}\n\n"

        # 添加作者声明
        formatted += "*本文为原创内容，转载请注明出处*\n\n"

        # 处理正文，添加小标题结构
        paragraphs = content.content.split("\n\n")
        section_count = 1

        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                # 每3段添加一个小标题
                if i > 0 and i % 3 == 0:
                    formatted += f"## {section_count}. 深度解析\n\n"
                    section_count += 1

                formatted += f"{paragraph.strip()}\n\n"

        # 添加版权声明
        formatted += "\n---\n*声明：本文观点仅代表作者本人，不代表平台立场*"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> bool:
        """百家号发布（需要接入百度百家号API）"""
        print("百家号发布功能待开发 - 需要接入百度百家号API")
        return False


class ZhihuAdapter(PlatformAdapter):
    """知乎适配器"""

    def format_content(self, content: ContentResult) -> str:
        """格式化为知乎格式"""
        # 知乎偏好问答式和深度分析
        formatted = f"# {content.title}\n\n"

        # 添加TL;DR摘要
        formatted += f"**TL;DR：** {content.summary}\n\n"
        formatted += "---\n\n"

        # 处理正文，添加逻辑结构
        paragraphs = content.content.split("\n\n")

        # 添加目录结构
        if len(paragraphs) > 3:
            formatted += "**本文目录：**\n"
            for i in range(min(5, len(paragraphs))):
                formatted += f"- 第{i+1}部分：核心观点分析\n"
            formatted += "\n---\n\n"

        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                # 添加分段标题
                if i == 0:
                    formatted += "## 核心观点\n\n"
                elif i == len(paragraphs) // 2:
                    formatted += "## 深度分析\n\n"
                elif i == len(paragraphs) - 1:
                    formatted += "## 总结思考\n\n"

                formatted += f"{paragraph.strip()}\n\n"

        # 添加互动引导
        formatted += "\n---\n**你怎么看？欢迎在评论区分享你的想法，我们一起讨论！**\n\n"
        formatted += "*如果觉得有用，请点赞支持一下～*"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> bool:
        """知乎发布（需要接入知乎API或使用自动化工具）"""
        print("知乎发布功能待开发 - 需要接入知乎API或使用浏览器自动化")
        return False


class DoubanAdapter(PlatformAdapter):
    """豆瓣适配器"""

    def format_content(self, content: ContentResult) -> str:
        """格式化为豆瓣格式"""
        # 豆瓣偏好文艺性和个人化表达
        formatted = f"# {content.title}\n\n"

        # 添加情感化开头
        formatted += "*写在前面：最近在思考这个话题，想和大家分享一些想法*\n\n"

        # 处理正文，保持文艺风格
        paragraphs = content.content.split("\n\n")

        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                # 添加一些文艺化的连接词
                if i > 0:
                    connectors = ["说到这里，", "想起来，", "不禁让我想到，", "或许，"]
                    import random

                    connector = random.choice(connectors)
                    formatted += f"{connector}"

                formatted += f"{paragraph.strip()}\n\n"

        # 添加个人化结尾
        formatted += "\n---\n*以上只是个人的一些浅见，欢迎大家在评论区交流讨论*\n\n"
        formatted += "🌟 *如果你也有类似的想法，不妨点个赞让我知道*"

        return formatted

    def publish_content(self, formatted_content: str, **kwargs) -> bool:
        """豆瓣发布（需要使用自动化工具）"""
        print("豆瓣发布功能待开发 - 需要使用浏览器自动化工具")
        return False
