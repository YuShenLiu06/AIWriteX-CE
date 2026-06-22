"""Articles commands for AIWriteX CLI."""

from typing import Optional
import typer
from ..client import AIWriteXClient
from ..formatters import print_success, print_error, print_info, print_table, print_status

app = typer.Typer(help="管理文章")


@app.command()
def list() -> None:
    """列出所有文章。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/articles/")
        data = response.get("data", [])
        rows = [
            [
                item.get("title", item.get("name", "")),
                item.get("format", ""),
                item.get("size", ""),
                item.get("create_time", ""),
                item.get("status", ""),
            ]
            for item in data
        ]
        print_table(["标题", "格式", "大小", "创建时间", "状态"], rows)
    except Exception as e:
        print_error(f"获取文章列表失败: {e}")
        raise typer.Exit(1)


@app.command()
def get(path: str) -> None:
    """获取文章内容。"""
    client = AIWriteXClient()
    try:
        content = client.get_text("/api/articles/content", params={"path": path})
        print_info(content)
    except Exception as e:
        print_error(f"获取文章内容失败: {e}")
        raise typer.Exit(1)


@app.command()
def delete(path: str) -> None:
    """删除文章。"""
    client = AIWriteXClient()
    try:
        response = client.delete_json(f"/api/articles/{path}")
        print_status(response.get("status"), response.get("message", "文章已删除"))
    except Exception as e:
        print_error(f"删除文章失败: {e}")
        raise typer.Exit(1)


@app.command()
def publish(
    article_paths: str = typer.Option(..., "--article-paths", "-p", help="文章路径，用逗号分隔"),
    account_indices: str = typer.Option(..., "--account-indices", "-a", help="账号索引，用逗号分隔"),
    platform: str = typer.Option("wechat", "--platform", "-P", help="发布平台"),
) -> None:
    """发布文章到平台。"""
    client = AIWriteXClient()
    try:
        paths = [p.strip() for p in article_paths.split(",")]
        indices = [int(i.strip()) for i in account_indices.split(",")]
        response = client.post_json(
            "/api/articles/publish",
            json={
                "article_paths": paths,
                "account_indices": indices,
                "platform": platform,
            },
        )
        print_status(response.get("status"), response.get("message", ""))
        if response.get("success_count"):
            print_success(f"成功发布 {response.get('success_count')} 篇")
        if response.get("fail_count"):
            print_error(f"失败 {response.get('fail_count')} 篇")
        for err in response.get("error_details", []):
            print_error(err)
    except Exception as e:
        print_error(f"发布文章失败: {e}")
        raise typer.Exit(1)
