#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信文章 → HTML 模板转换器 CLI

将微信公众平台文章 URL 转换为自包含的 HTML 模板，
保留文章原始 CSS 样式（inline style + 精简排版CSS），
去除外部 JS/CSS 依赖，下载图片到本地。

用法:
    python wechat_to_template.py "https://mp.weixin.qq.com/s/xxx" -o ./output
    python wechat_to_template.py "https://mp.weixin.qq.com/s/xxx" -o knowledge/templates/情感心理/
    python wechat_to_template.py "本地文件.html" -o ./output -l
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ai_write_x.utils.article_template_converter import ArticleTemplateConverter


def main():
    parser = argparse.ArgumentParser(
        description="将微信公众平台文章转换为自包含 HTML 模板（保留原始 CSS 样式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python wechat_to_template.py "https://mp.weixin.qq.com/s/_mvElzoa6f4xiC393fVl-w"
  python wechat_to_template.py "URL" -o ./output
  python wechat_to_template.py "URL" -o knowledge/templates/情感心理/ --timeout 60
  python wechat_to_template.py "本地文件.html" -o ./output -l  # 从本地 HTML 文件转换
        """,
    )
    parser.add_argument("url", help="微信文章 URL 或本地 HTML 文件路径")
    parser.add_argument("-o", "--output", default="./output", help="输出目录 (默认: ./output)")
    parser.add_argument("-l", "--local", action="store_true", help="将 url 参数视为本地 HTML 文件路径")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时秒数 (默认: 30)")
    parser.add_argument("--retries", type=int, default=3, help="最大重试次数 (默认: 3)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
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
        sys.exit(1)


if __name__ == "__main__":
    main()
