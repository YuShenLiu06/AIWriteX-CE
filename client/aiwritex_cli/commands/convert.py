"""Convert commands for AIWriteX CLI."""

import time
from typing import Optional
import typer
from ..client import AIWriteXClient
from ..formatters import print_success, print_error, print_info, print_json

app = typer.Typer(help="内容转换")


@app.command()
def wechat(
    url: str = typer.Option(..., "--url", "-u", help="微信公众号文章 URL"),
    output_type: str = typer.Option("template", "--output-type", "-o", help="输出类型: template|article"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="模板分类 (output_type=template 时)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="模板名称 (output_type=template 时)"),
    timeout: int = typer.Option(30, "--timeout", help="等待超时秒数"),
    retries: int = typer.Option(3, "--retries", "-r", help="重试次数"),
    html_file: Optional[str] = typer.Option(None, "--html-file", "-f", help="保存 HTML 到文件"),
    async_mode: bool = typer.Option(False, "--async", help="异步模式，立即返回 task_id"),
) -> None:
    """转换微信公众号文章。"""
    client = AIWriteXClient()
    try:
        response = client.post_json(
            "/api/convert/wechat",
            json={
                "url": url,
                "output_type": output_type,
                "category": category or "",
                "name": name or "",
            },
        )
        task_id = response.get("data", {}).get("task_id")

        if async_mode:
            print_info(f"任务已提交: {task_id}")
            return

        # 轮询等待完成
        print_info("正在转换...")
        start_time = time.time()
        poll_interval = 2

        while True:
            if time.time() - start_time > timeout:
                print_error("转换超时")
                raise typer.Exit(1)

            time.sleep(poll_interval)

            status_response = client.get_json("/api/convert/status", params={"task_id": task_id})
            status = status_response.get("data", {}).get("status")

            if status == "completed":
                print_success("转换完成")
                result = status_response.get("data", {})
                if html_file:
                    import pathlib
                    pathlib.Path(html_file).write_text(result.get("html", ""), encoding="utf-8")
                    print_info(f"HTML 已保存到: {html_file}")
                else:
                    print_json(result)
                return
            elif status == "failed":
                error = status_response.get("data", {}).get("error", "未知错误")
                print_error(f"转换失败: {error}")
                raise typer.Exit(1)
            elif status in ("pending", "running"):
                print_info("转换中...")
            else:
                print_error(f"未知状态: {status}")
                raise typer.Exit(1)

    except Exception as e:
        print_error(f"转换失败: {e}")
        raise typer.Exit(1)
