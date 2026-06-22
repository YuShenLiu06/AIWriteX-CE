"""System commands for AIWriteX CLI."""

import time
import typer
from ..client import AIWriteXClient
from ..formatters import print_success, print_error, print_info, print_json

app = typer.Typer(help="系统管理")


@app.command()
def health() -> None:
    """健康检查。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/health")
        status = response.get("status", "unknown")
        if status == "healthy":
            print_success("服务器健康")
            print_info(f"时间戳: {response.get('timestamp', '')}")
        else:
            print_error(f"服务器状态: {status}")
    except Exception as e:
        print_error(f"健康检查失败: {e}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """获取服务器版本信息。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/config/")
        print_json(response)
    except Exception as e:
        print_error(f"获取版本信息失败: {e}")
        raise typer.Exit(1)
