"""Main entry point for AIWriteX CLI."""

import typer
from rich.console import Console

from . import __version__
from .commands import config_cmd, articles, generate, templates, knowledge, tasks, system, convert
from .client import AIWriteXClient
from .errors import AIWriteXError
from .formatters import print_error

console = Console()

# Create main app
app = typer.Typer(
    name="aiwritex",
    help="AIWriteX CLI - Lightweight client for AIWriteX server",
    add_completion=True,
    no_args_is_help=True,
)

# Register command groups
app.add_typer(config_cmd.app, name="config")
app.add_typer(articles.app, name="articles")
app.add_typer(generate.app, name="generate")
app.add_typer(templates.app, name="templates")
app.add_typer(knowledge.app, name="knowledge")
app.add_typer(tasks.app, name="tasks")
app.add_typer(convert.app, name="convert")
app.add_typer(system.app, name="system")


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="显示版本信息"),
    base_url: str = typer.Option(None, "--base-url", help="服务器地址"),
    api_key: str = typer.Option(None, "--api-key", help="API 密钥"),
    timeout: int = typer.Option(None, "--timeout", help="请求超时时间"),
) -> None:
    """AIWriteX CLI - 轻量级命令行客户端。

    使用 `aiwritex <命令> --help` 查看具体命令帮助。
    """
    if version:
        console.print(f"AIWriteX CLI v{__version__}")
        raise typer.Exit()


@app.command()
def test_connection() -> None:
    """测试与服务器连接。"""
    try:
        client = AIWriteXClient()
        response = client.get_json("/health")
        if response.get("status") == "healthy":
            console.print("[green]✓[/green] 连接成功")
        else:
            console.print(f"[yellow]![/yellow] 服务器状态: {response.get('status')}")
    except AIWriteXError as e:
        print_error(f"连接失败: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
