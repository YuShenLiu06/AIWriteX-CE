"""Templates commands for AIWriteX CLI."""

from typing import Optional
from pathlib import Path
import typer
from ..client import AIWriteXClient
from ..formatters import print_success, print_error, print_info, print_table

app = typer.Typer(help="管理模板")


@app.command()
def list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="筛选分类"),
) -> None:
    """列出模板。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/templates/", params={"category": category})
        data = response.get("data", [])
        rows = [
            [
                item.get("name", ""),
                item.get("category", ""),
                item.get("size", ""),
                item.get("create_time", ""),
            ]
            for item in data
        ]
        print_table(["名称", "分类", "大小", "创建时间"], rows)
    except Exception as e:
        print_error(f"获取模板列表失败: {e}")
        raise typer.Exit(1)


@app.command()
def categories() -> None:
    """列出所有模板分类。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/templates/categories")
        data = response.get("data", [])
        rows = [[item.get("name", ""), str(item.get("template_count", 0))] for item in data]
        print_table(["分类", "模板数量"], rows)
    except Exception as e:
        print_error(f"获取分类失败: {e}")
        raise typer.Exit(1)


@app.command()
def get(path: str) -> None:
    """获取模板内容。"""
    client = AIWriteXClient()
    try:
        content = client.get_text(f"/api/templates/content/{path}", params={})
        print_info(content)
    except Exception as e:
        print_error(f"获取模板内容失败: {e}")
        raise typer.Exit(1)


@app.command()
def create(
    name: str = typer.Option(..., "--name", "-n", help="模板名称"),
    category: str = typer.Option(..., "--category", "-c", help="模板分类"),
    content: Optional[str] = typer.Option(None, "--content", "-C", help="模板内容"),
    content_file: Optional[str] = typer.Option(None, "--content-file", "-f", help="模板内容文件"),
) -> None:
    """创建模板。"""
    if not content and not content_file:
        print_error("必须提供 --content 或 --content-file")
        raise typer.Exit(1)

    if content_file:
        content = Path(content_file).read_text(encoding="utf-8")

    client = AIWriteXClient()
    try:
        response = client.post_json(
            "/api/templates/",
            json={
                "name": name,
                "category": category,
                "content": content,
            },
        )
        print_success(response.get("message", "模板已创建"))
    except Exception as e:
        print_error(f"创建模板失败: {e}")
        raise typer.Exit(1)


@app.command()
def delete(path: str) -> None:
    """删除模板。"""
    client = AIWriteXClient()
    try:
        response = client.delete_json(f"/api/templates/{path}")
        print_success(response.get("message", "模板已删除"))
    except Exception as e:
        print_error(f"删除模板失败: {e}")
        raise typer.Exit(1)
