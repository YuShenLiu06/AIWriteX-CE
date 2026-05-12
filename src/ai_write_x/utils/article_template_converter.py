# -*- coding: utf-8 -*-
"""
微信文章 → HTML 模板转换器

将微信公众平台文章 URL 转换为自包含的 HTML 模板，
提取文章原始 CSS 样式（inline style + 精简排版CSS），
去除外部 JS/CSS 依赖和冗余标记，下载图片到本地。
"""

import re
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 内容清洗器：提取干净的文章内容
# ---------------------------------------------------------------------------

def is_layout_only_section(elem) -> bool:
    """判断 section 是否仅为布局包装（无实际样式贡献）"""
    if elem.name != "section":
        return False
    style = elem.get("style", "")
    # 没有 class/id 引用
    if elem.get("class") or elem.get("id"):
        return False
    # 纯布局样式
    if "margin:0px" in style and "padding:0px" in style:
        return True
    return False


def has_meaningful_content(elem) -> bool:
    """判断元素是否有实际内容"""
    if elem.name in ("img", "video", "audio"):
        return True
    text = elem.get_text(strip=True)
    if text and len(text) > 3:
        return True
    return False


def is_trivial_wrapper(elem) -> bool:
    """判断元素是否是无意义的内联包装"""
    style = elem.get("style", "")
    # 纯重置样式
    if style == "margin:0px;padding:0px;box-sizing:border-box":
        return True
    if style == "padding:0px;margin:0px;box-sizing:border-box":
        return True
    return False


def simplify_inline_style(style: str) -> str:
    """精简 inline style（委托给 _clean_style）"""
    return _clean_style(style)


def _clean_style(style: str) -> str:
    """清理 style：移除无意义的默认值，规范化格式"""
    if not style:
        return ""
    decls = [d.strip() for d in style.split(";") if d.strip()]
    kept = []
    seen = set()
    for d in decls:
        prop = d.split(":")[0].strip().lower()
        val = d.split(":", 1)[1].strip()
        # 跳过无意义默认值
        if prop == "visibility" and val == "visible":
            continue
        if prop == "display":
            continue
        if prop == "box-sizing" and val == "border-box":
            continue
        if prop == "font-style" and val == "normal":
            continue
        if prop == "font-weight" and val == "400":
            continue
        if prop == "font-variant" and val == "normal":
            continue
        if prop == "white-space" and val == "normal":
            continue
        if prop in ("margin", "padding") and val in ("0px", "0", "0px 0px 0px", "0 0 0"):
            continue
        if prop not in seen:
            kept.append(d)
            seen.add(prop)
    return "; ".join(kept) if kept else ""


def clean_wechat_content(content_area) -> Tuple[str, str]:
    """
    清洗 WeChat 文章内容：
    - 移除无意义的 layout wrapper
    - 保留 inline style 中的关键样式
    - 移除 WeChat 组件（商品推荐等）
    """
    # 深拷贝避免修改原始
    soup = BeautifulSoup(content_area.decode_contents() if hasattr(content_area, 'decode_contents') else str(content_area), "html.parser")

    # 移除 WeChat 商品/广告组件
    for tag_name in ["mp-common-product", "mp-common-product-iframe-wrp",
                     "template", "button", "dialog", "overlay"]:
        for elem in soup.find_all(tag_name):
            elem.decompose()
    # 移除含特定 class 的 section（如商品推荐 wrapper）
    for section in soup.find_all("section"):
        cls_list = section.get("class", [])
        cls_str = " ".join(cls_list) if cls_list else ""
        if "product" in cls_str.lower() or "ad" in cls_str.lower():
            section.decompose()

    # 处理图片：data-src 有远程 URL（用于下载），src 保留 base64 或原值
    for img in soup.find_all("img"):
        data_src = img.get("data-src") or ""
        src = img.get("src") or ""
        # 有 data-src 的远程图片 - 优先使用 data-src
        # 无 data-src 的 base64 图片 - 保留
        # 无 data-src 且非 base64 的 mmbiz 图片（无 wx_fmt） - 小图标，移除
        if not data_src and not src.startswith("data:") and "wx_fmt=" not in src:
            img.decompose()
            continue
        # 对于有 data-src 的图片，将 data-src 放到 data-origin（后续下载用），保留 src
        if data_src and data_src not in src:
            img["data-origin"] = data_src
        # 精简图片的 style
        if img.get("style"):
            img["style"] = simplify_inline_style(img["style"])

    # 移除纯布局 section（递归处理）
    changed = True
    while changed:
        changed = False
        for section in soup.find_all("section"):
            if is_layout_only_section(section) and not has_meaningful_content(section):
                section.unwrap()
                changed = True

    # 精简所有元素的 style
    for elem in soup.find_all(True):
        style = elem.get("style")
        if style:
            elem["style"] = simplify_inline_style(style)

    # 移除空的文本节点和空白
    for text in soup.find_all(string=lambda s: isinstance(s, NavigableString)):
        if text.strip() == "":
            text.extract()

    return str(soup), ""


@dataclass
class ArticleContent:
    """文章内容数据结构"""
    title: str = ""
    source_url: str = ""
    content_html: str = ""
    typography_css: str = ""
    images: List[Tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心转换器
# ---------------------------------------------------------------------------

class ArticleTemplateConverter:
    """微信文章 → 自包含 HTML 模板转换器"""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch_and_parse(self, url_or_html: str, is_local_file: bool = False) -> ArticleContent:
        if is_local_file:
            with open(url_or_html, "r", encoding="utf-8") as f:
                raw_html = f.read()
            source_url = "local_file"
        else:
            raw_html = self._fetch_with_retry(url_or_html)
            source_url = url_or_html
        return self._parse_html(raw_html, source_url)

    def _fetch_with_retry(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://mp.weixin.qq.com/",
        }
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                response.encoding = "utf-8"
                logger.info(f"页面抓取成功: {url}")
                return response.text
            except requests.RequestException as e:
                wait_time = 2 ** attempt
                logger.warning(f"抓取失败 (尝试 {attempt + 1}/{self.max_retries}): {e}, {wait_time}s 后重试")
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    raise

    def _parse_html(self, html: str, source_url: str) -> ArticleContent:
        soup = BeautifulSoup(html, "html.parser")

        # 移除脚本和样式标签（内容区样式已通过 inline style 处理）
        for tag in soup(["script", "style"]):
            tag.decompose()

        # 移除非 data URI 的外部 link
        for link in soup.find_all("link"):
            href = link.get("href", "")
            if not href.startswith("data:"):
                link.decompose()

        # 提取标题
        title = self._extract_title(soup)

        # #js_content 内容区域
        content_area = soup.select_one("#js_content")
        if not content_area:
            content_area = soup.select_one("article") or soup.select_one("main") or soup.body()

        # 清洗内容 HTML（保留内联样式，不做 class 压缩）
        content_html, _ = clean_wechat_content(content_area)

        return ArticleContent(
            title=title,
            source_url=source_url,
            content_html=content_html,
            typography_css="",
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        meta = soup.select_one('meta[property="og:title"]')
        if meta and meta.get("content"):
            return meta["content"].strip()
        title_tag = soup.select_one("title")
        if title_tag:
            return title_tag.get_text().strip()
        h1_tag = soup.select_one("h1")
        if h1_tag:
            return h1_tag.get_text().strip()
        return "无标题文章"

    def download_images(self, content: ArticleContent, output_dir: str) -> ArticleContent:
        """下载 content_html 中的远程图片到本地"""
        output_path = Path(output_dir)
        image_dir = output_path / "image"
        image_dir.mkdir(parents=True, exist_ok=True)

        soup = BeautifulSoup(content.content_html, "html.parser")
        local_map: dict = {}

        for img in soup.find_all("img"):
            # 优先使用 data-origin（清洗后的远程 URL）
            src = img.get("data-origin") or img.get("data-src") or img.get("src") or ""

            # 跳过 base64 和微信小图标
            if src.startswith("data:") or ("mmbiz.qpic.cn" in src and "wx_fmt=" not in src):
                continue

            # 标准化 URL
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin("https://mp.weixin.qq.com", src)

            if not src or not src.startswith("http"):
                continue

            if src in local_map:
                actual_path = local_map[src]
            else:
                ext = self._guess_ext(src)
                idx = len(local_map) + 1
                save_path = image_dir / f"{idx}{ext}"
                if self._download_single_image(src, str(save_path)):
                    local_map[src] = str(save_path)
                    logger.info(f"图片下载成功: {save_path}")
                else:
                    logger.warning(f"图片下载失败: {src}")
                    continue

            # 替换 src 为本地相对路径
            img_name = Path(local_map[src]).name
            img["src"] = f"image/{img_name}"
            img["data-src"] = ""

        content.content_html = str(soup)
        content.images = [(url, path) for url, path in local_map.items()]
        return content

    def _guess_ext(self, url: str) -> str:
        if "wx_fmt=jpeg" in url or "wx_fmt=jpg" in url:
            return ".jpg"
        if "wx_fmt=png" in url:
            return ".png"
        if "wx_fmt=webp" in url:
            return ".webp"
        if "wx_fmt=gif" in url:
            return ".gif"
        return ".jpg"

    def _download_single_image(self, url: str, save_path: str) -> bool:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://mp.weixin.qq.com/",
        }
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout, stream=True)
                response.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            except Exception:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        return False

    def apply_template(self, content: ArticleContent) -> str:
        """输出纯 body 内容（内联样式，微信兼容）"""
        return content.content_html

    def convert(
        self,
        url_or_html: str,
        output_dir: str,
        is_local_file: bool = False,
    ) -> str:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Step 1: 抓取并解析
        logger.info("正在解析文章...")
        content = self.fetch_and_parse(url_or_html, is_local_file=is_local_file)
        logger.info(f"标题: {content.title}")
        logger.info(f"精简 CSS: {len(content.typography_css):,} chars ({len(content.typography_css)/1024:.1f} KB)")

        # Step 2: 下载图片
        if content.content_html:
            logger.info("正在处理并下载图片...")
            content = self.download_images(content, str(output_path))
            logger.info(f"下载图片数: {len(content.images)}")

        # Step 3: 生成 HTML
        logger.info("正在生成 HTML 模板...")
        html_content = self.apply_template(content)

        # 保存
        safe_title = re.sub(r'[<>:"/\\|?*]', "", content.title).strip()[:50] or "article"
        html_path = output_path / f"{safe_title}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"模板已生成: {html_path}")
        logger.info(f"HTML 大小: {len(html_content):,} ({len(html_content)/1024:.1f} KB)")
        return str(html_path)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="将微信公众平台文章转换为自包含 HTML 模板（保留原始 CSS 样式）"
    )
    parser.add_argument("url", help="微信文章 URL 或本地 HTML 文件路径")
    parser.add_argument("-o", "--output", default="./output", help="输出目录 (默认: ./output)")
    parser.add_argument("-l", "--local", action="store_true", help="将 URL 参数视为本地 HTML 文件路径")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时秒数 (默认: 30)")
    parser.add_argument("--retries", type=int, default=3, help="最大重试次数 (默认: 3)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    converter = ArticleTemplateConverter(timeout=args.timeout, max_retries=args.retries)

    try:
        output_path = converter.convert(args.url, args.output, is_local_file=args.local)
        print(f"\n✓ 转换完成")
        print(f"  输出目录: {args.output}")
        print(f"  HTML文件: {Path(output_path).name}")
    except Exception as e:
        print(f"\n✗ 转换失败: {e}")
        raise


if __name__ == "__main__":
    main()
