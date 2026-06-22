"""Generate commands for AIWriteX CLI."""

from typing import Optional
import typer
from ..client import AIWriteXClient
from ..formatters import print_success, print_error, print_info, print_status

app = typer.Typer(help="内容生成")


@app.command()
def run(
    topic: str = typer.Option(..., "--topic", "-t", help="文章主题"),
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="生成模式: prompt|rewrite|template"),
    platform: Optional[str] = typer.Option(None, "--platform", "-P", help="目标平台"),
    urls: Optional[str] = typer.Option(None, "--urls", "-u", help="参考 URL，用 | 分隔"),
    ratio: Optional[int] = typer.Option(30, "--ratio", "-r", help="参考比例 0-100"),
    template_category: Optional[str] = typer.Option(None, "--template-category", "-c", help="模板分类"),
    template_name: Optional[str] = typer.Option(None, "--template-name", "-n", help="模板名称"),
) -> None:
    """生成内容。"""
    client = AIWriteXClient()

    # 构建参考配置
    reference = None
    if urls or (template_category and template_name):
        reference = {"reference_ratio": ratio}
        if urls:
            reference["reference_urls"] = urls
        if template_category:
            reference["template_category"] = template_category
        if template_name:
            reference["template_name"] = template_name

    # 根据 mode 验证参数
    if mode == "prompt" and reference:
        print_error("prompt 模式不需要参考参数")
        raise typer.Exit(1)
    if mode == "rewrite" and not urls:
        print_error("rewrite 模式需要 --urls 参数")
        raise typer.Exit(1)
    if mode == "template" and not (template_category and template_name):
        print_error("template 模式需要 --template-category 和 --template-name 参数")
        raise typer.Exit(1)

    try:
        response = client.post_json(
            "/api/generate",
            json={
                "topic": topic,
                "platform": platform or "",
                "reference": reference,
            },
        )
        print_status(response.get("status"), response.get("message", ""))
    except Exception as e:
        print_error(f"生成失败: {e}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """获取生成状态。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/generate/status")
        print_status(response.get("status"))
    except Exception as e:
        print_error(f"获取状态失败: {e}")
        raise typer.Exit(1)


@app.command()
def stop() -> None:
    """停止当前生成任务。"""
    client = AIWriteXClient()
    try:
        response = client.post_json("/api/generate/stop")
        print_status(response.get("status"), response.get("message", ""))
    except Exception as e:
        print_error(f"停止任务失败: {e}")
        raise typer.Exit(1)


@app.command()
def hot_topics() -> None:
    """获取热搜话题。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/hot-topics")
        platform = response.get("platform", "")
        topic = response.get("topic", "")
        print_success(f"平台: {platform}")
        print_info(f"话题: {topic}")
    except Exception as e:
        print_error(f"获取热搜失败: {e}")
        raise typer.Exit(1)
