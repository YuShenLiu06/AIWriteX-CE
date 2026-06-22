"""Configuration commands for AIWriteX CLI."""

from typing import Optional
import typer
from ..config_store import ConfigStore
from ..formatters import print_success, print_error, print_info, print_table, print_json

app = typer.Typer(help="管理 CLI 配置")


@app.command()
def set(key: str, value: str) -> None:
    """设置配置项。"""
    valid_keys = ["base_url", "api_key", "username", "password", "timeout"]
    if key not in valid_keys:
        print_error(f"无效的配置项: {key}")
        print_info(f"有效配置项: {', '.join(valid_keys)}")
        raise typer.Exit(1)

    # 转换 timeout 为整数
    if key == "timeout":
        try:
            value = int(value)
        except ValueError:
            print_error("timeout 必须是整数")
            raise typer.Exit(1)

    if ConfigStore.set(key, value):
        print_success(f"已设置 {key} = {value}")
    else:
        print_error("配置保存失败")
        raise typer.Exit(1)


@app.command()
def get(key: str) -> None:
    """获取配置项。"""
    value = ConfigStore.get(key)
    if value is None:
        print_error(f"配置项不存在: {key}")
        raise typer.Exit(1)
    print_info(f"{key} = {value}")


@app.command()
def list() -> None:
    """列出所有配置。"""
    config = ConfigStore.load()
    rows = [[k, str(v)] for k, v in config.items()]
    print_table(["配置项", "值"], rows, title="当前配置")


@app.command()
def show() -> None:
    """显示完整配置 (JSON 格式)。"""
    config = ConfigStore.load()
    print_json(config)
