"""Knowledge commands for AIWriteX CLI."""

from typing import Optional
from pathlib import Path
import typer
from ..client import AIWriteXClient
from ..formatters import print_success, print_error, print_info, print_table, print_json

app = typer.Typer(help="知识库管理")


# Text knowledge commands
@app.command("text-list")
def text_list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="筛选分类"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="搜索关键词"),
    limit: int = typer.Option(50, "--limit", "-l", help="返回数量限制"),
) -> None:
    """列出文本知识。"""
    client = AIWriteXClient()
    try:
        response = client.get_json(
            "/api/text-knowledge/",
            params={"category": category, "search": search, "limit": limit},
        )
        data = response.get("data", [])
        rows = [
            [
                item.get("id", ""),
                item.get("title", ""),
                item.get("category", "-"),
                ",".join(item.get("tags", [])),
            ]
            for item in data
        ]
        print_table(["ID", "标题", "分类", "标签"], rows)
    except Exception as e:
        print_error(f"获取文本知识失败: {e}")
        raise typer.Exit(1)


@app.command("text-create")
def text_create(
    title: str = typer.Option(..., "--title", "-t", help="知识标题"),
    content: str = typer.Option(..., "--content", "-c", help="知识内容"),
    summary: Optional[str] = typer.Option("", "--summary", "-s", help="内容摘要"),
    tags: Optional[str] = typer.Option("", "--tags", help="标签，用逗号分隔"),
    category: Optional[str] = typer.Option(None, "--category", "-C", help="知识分类"),
) -> None:
    """创建文本知识。"""
    client = AIWriteXClient()
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        response = client.post_json(
            "/api/text-knowledge/",
            json={
                "title": title,
                "content": content,
                "summary": summary,
                "tags": tag_list,
                "category": category,
            },
        )
        print_success(response.get("message", "文本知识已创建"))
    except Exception as e:
        print_error(f"创建文本知识失败: {e}")
        raise typer.Exit(1)


@app.command("text-get")
def text_get(item_id: str) -> None:
    """获取单个文本知识。"""
    client = AIWriteXClient()
    try:
        response = client.get_json(f"/api/text-knowledge/{item_id}")
        print_json(response.get("data", {}))
    except Exception as e:
        print_error(f"获取文本知识失败: {e}")
        raise typer.Exit(1)


@app.command("text-delete")
def text_delete(item_id: str) -> None:
    """删除文本知识。"""
    client = AIWriteXClient()
    try:
        response = client.delete_json(f"/api/text-knowledge/{item_id}")
        print_success(response.get("message", "文本知识已删除"))
    except Exception as e:
        print_error(f"删除文本知识失败: {e}")
        raise typer.Exit(1)


# Image knowledge commands
@app.command("image-list")
def image_list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="筛选分类"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="搜索关键词"),
    limit: int = typer.Option(50, "--limit", "-l", help="返回数量限制"),
) -> None:
    """列出图片知识。"""
    client = AIWriteXClient()
    try:
        response = client.get_json(
            "/api/images/",
            params={"category": category, "search": search, "limit": limit},
        )
        data = response.get("data", [])
        rows = [
            [
                item.get("id", ""),
                item.get("original_filename", ""),
                item.get("category", "-"),
                item.get("description", ""),
            ]
            for item in data
        ]
        print_table(["ID", "文件名", "分类", "描述"], rows)
    except Exception as e:
        print_error(f"获取图片列表失败: {e}")
        raise typer.Exit(1)


@app.command("image-upload")
def image_upload(
    file: str = typer.Option(..., "--file", "-f", help="图片文件路径"),
    description: Optional[str] = typer.Option("", "--description", "-d", help="图片描述"),
    tags: Optional[str] = typer.Option("", "--tags", help="标签，用逗号分隔"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="图片分类"),
) -> None:
    """上传图片。"""
    client = AIWriteXClient()
    try:
        file_path = Path(file)
        if not file_path.exists():
            print_error(f"文件不存在: {file}")
            raise typer.Exit(1)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "image/jpeg")}
            data = {"description": description, "tags": ",".join(tag_list)}
            if category:
                data["category"] = category

            response = client.post_file("/api/images/", files=files, data=data)

        print_success(f"图片上传成功: {response.get('data', {}).get('id', '')}")
    except Exception as e:
        print_error(f"上传图片失败: {e}")
        raise typer.Exit(1)


@app.command("image-delete")
def image_delete(image_id: str) -> None:
    """删除图片。"""
    client = AIWriteXClient()
    try:
        response = client.delete_json(f"/api/images/{image_id}")
        print_success(response.get("message", "图片已删除"))
    except Exception as e:
        print_error(f"删除图片失败: {e}")
        raise typer.Exit(1)


# Stats and refresh
@app.command("stats")
def knowledge_stats() -> None:
    """获取知识库统计。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/knowledge/stats")
        print_json(response.get("data", {}))
    except Exception as e:
        print_error(f"获取统计失败: {e}")
        raise typer.Exit(1)


@app.command("refresh")
def knowledge_refresh() -> None:
    """刷新知识库。"""
    client = AIWriteXClient()
    try:
        response = client.post_json("/api/knowledge/refresh")
        print_success(response.get("message", "知识库已刷新"))
    except Exception as e:
        print_error(f"刷新知识库失败: {e}")
        raise typer.Exit(1)
