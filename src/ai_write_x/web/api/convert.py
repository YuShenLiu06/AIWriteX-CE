# -*- coding: utf-8 -*-
"""
微信文章转换器 API

将微信公众号文章 URL 或本地 HTML 转换为自包含 HTML 模板
"""

import re
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator

from src.ai_write_x.utils.article_template_converter import ArticleTemplateConverter
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import log
from ..auth import verify_auth


# ==================== 全局任务状态管理 ====================

@dataclass
class ConvertTaskStatus:
    """转换任务状态"""
    status: str = "idle"  # idle, running, completed, failed
    html_path: Optional[str] = None
    image_count: int = 0
    error: Optional[str] = None
    task_id: Optional[str] = None


# 模块级全局状态（复用 generate.py 的模式）
_convert_task = ConvertTaskStatus()
_convert_lock = threading.Lock()
_current_task_id: Optional[str] = None


def get_convert_status() -> ConvertTaskStatus:
    """获取当前转换状态（线程安全）"""
    with _convert_lock:
        if _current_task_id:
            return ConvertTaskStatus(
                status=_convert_task.status,
                html_path=_convert_task.html_path,
                image_count=_convert_task.image_count,
                error=_convert_task.error,
                task_id=_current_task_id,
            )
        return ConvertTaskStatus(status="idle", task_id=None)


def update_convert_status(**kwargs):
    """更新转换状态（线程安全）"""
    global _convert_task
    with _convert_lock:
        for key, value in kwargs.items():
            if hasattr(_convert_task, key):
                setattr(_convert_task, key, value)


# ==================== Pydantic 请求模型 ====================

class ConvertRequest(BaseModel):
    """微信文章转换请求"""
    url: Optional[str] = Field(None, description="微信公众号文章URL")
    output_type: str = Field("article", description="输出类型: template|article")
    category: Optional[str] = Field(None, description="模板分类（output_type=template时必填）")
    name: Optional[str] = Field(None, description="输出文件名（不含扩展名）")
    html: Optional[str] = Field(None, description="HTML字符串（与URL二选一）")
    timeout: int = Field(30, description="请求超时秒数")
    retries: int = Field(3, description="最大重试次数")

    @validator('url', 'html')
    def validate_source(cls, v, values):
        """校验：url 与 html 至少传一个"""
        if not values.get('url') and not v and not values.get('html'):
            raise ValueError('url 与 html 必须至少提供一个')
        return v

    @validator('output_type')
    def validate_output_type(cls, v):
        """校验输出类型"""
        if v not in ('template', 'article'):
            raise ValueError('output_type 必须是 template 或 article')
        return v

    @validator('category')
    def validate_category(cls, v, values):
        """template 模式下 category 必填"""
        if values.get('output_type') == 'template' and not v:
            raise ValueError('output_type=template 时 category 必填')
        return v


# ==================== 辅助函数 ====================

def determine_output_dir(output_type: str, category: Optional[str]) -> Path:
    """确定输出目录"""
    if output_type == "template":
        if not category:
            raise ValueError("模板模式需要指定分类")
        template_dir = PathManager.get_template_dir()
        output_dir = template_dir / category
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    else:
        return PathManager.get_article_dir()


def generate_filename(name: Optional[str], title: str) -> str:
    """生成安全的文件名"""
    if name:
        # 清理用户提供的文件名
        safe_name = re.sub(r'[<>:"/\\|?*]', "", name).strip()[:50]
        if safe_name:
            return safe_name
    # 使用标题生成文件名
    safe_title = re.sub(r'[<>:"/\\|?*]', "", title).strip()[:50]
    return safe_title or "article"


def migrate_images_to_global_dir(html_path: Path, source_image_dir: Path) -> int:
    """
    将图片从临时目录迁移到全局图片目录，并更新 HTML 路径

    Args:
        html_path: 生成的 HTML 文件路径
        source_image_dir: 源图片目录 (output_dir/image/)

    Returns:
        迁移的图片数量
    """
    if not source_image_dir.exists():
        return 0

    global_image_dir = PathManager.get_image_dir()
    global_image_dir.mkdir(parents=True, exist_ok=True)

    # 读取 HTML 内容
    html_content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")

    migrated_count = 0
    image_map = {}  # 旧路径到新文件名的映射

    # 扫描所有 img 标签
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src.startswith("image/"):
            continue

        # 提取原始文件名
        old_filename = src.replace("image/", "", 1)
        source_path = source_image_dir / old_filename

        if not source_path.exists():
            continue

        # 生成目标文件名
        new_filename = f"{uuid.uuid4().hex}{source_path.suffix}"
        target_path = global_image_dir / new_filename

        # 迁移文件
        try:
            shutil.copy2(source_path, target_path)
            # 更新 HTML 中的引用
            img["src"] = f"/images/{new_filename}"
            image_map[str(source_path)] = str(target_path)
            migrated_count += 1
        except Exception as e:
            log.print_log(f"图片迁移失败: {source_path} -> {target_path}, 错误: {e}", "warning")

    # 写回更新后的 HTML
    if migrated_count > 0:
        html_path.write_text(str(soup), encoding="utf-8")
        log.print_log(f"图片迁移完成: {migrated_count} 张", "info")

    return migrated_count


# ==================== 后台转换函数 ====================

def run_conversion_task(
    task_id: str,
    url_or_html: str,
    output_dir: Path,
    is_local_file: bool,
    timeout: int,
    retries: int,
    output_filename: Optional[str] = None,
):
    """
    后台线程执行转换任务

    Args:
        task_id: 任务 ID
        url_or_html: URL 或 HTML 字符串
        output_dir: 输出目录
        is_local_file: 是否为本地文件
        timeout: 超时时间
        retries: 重试次数
        output_filename: 输出文件名（不含扩展名）
    """
    try:
        log.print_log(f"开始转换任务: {task_id}", "info")

        # 创建转换器
        converter = ArticleTemplateConverter(timeout=timeout, max_retries=retries)

        # 执行转换
        html_path = converter.convert(
            url_or_html=url_or_html,
            output_dir=str(output_dir),
            is_local_file=is_local_file,
        )

        log.print_log(f"转换完成: {html_path}", "info")

        # 图片路径适配：迁移图片到全局目录
        html_file_path = Path(html_path)
        source_image_dir = output_dir / "image"
        image_count = migrate_images_to_global_dir(html_file_path, source_image_dir)

        # 如果指定了输出文件名，进行重命名
        if output_filename:
            new_path = html_file_path.parent / f"{output_filename}.html"
            html_file_path.rename(new_path)
            html_path = str(new_path)

        # 更新状态
        update_convert_status(
            status="completed",
            html_path=html_path,
            image_count=image_count,
            error=None,
        )

        log.print_log(f"任务 {task_id} 完成", "info")

    except Exception as e:
        error_msg = str(e)
        log.print_log(f"转换失败: {error_msg}", "error")
        update_convert_status(status="failed", error=error_msg)


# ==================== API 路由 ====================

router = APIRouter(prefix="/api/convert", tags=["convert"], dependencies=[Depends(verify_auth)])


@router.post("/wechat")
async def convert_wechat_article(request: ConvertRequest, background_tasks: BackgroundTasks):
    """
    异步启动微信文章转换

    接受 URL 或 HTML 字符串，在后台线程执行转换
    """
    global _current_task_id

    with _convert_lock:
        if _convert_task.status == "running":
            raise HTTPException(status_code=409, detail="转换任务正在运行中")

        # 检查 URL 与 HTML 至少传一个
        if not request.url and not request.html:
            raise HTTPException(status_code=400, detail="url 与 html 必须至少提供一个")

    # 生成任务 ID
    task_id = uuid.uuid4().hex

    # 确定输出目录
    try:
        output_dir = determine_output_dir(request.output_type, request.category)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 确定输入源
    url_or_html = request.html or request.url
    is_local_file = bool(request.html)

    # 重置状态
    update_convert_status(status="running", html_path=None, image_count=0, error=None)
    _current_task_id = task_id

    # 启动后台线程
    thread = threading.Thread(
        target=run_conversion_task,
        name=f"convert-{task_id[:8]}",
        kwargs={
            "task_id": task_id,
            "url_or_html": url_or_html,
            "output_dir": output_dir,
            "is_local_file": is_local_file,
            "timeout": request.timeout,
            "retries": request.retries,
            "output_filename": request.name,
        },
        daemon=True,
    )
    thread.start()

    log.print_log(f"转换任务已启动: {task_id}", "info")

    return {
        "task_id": task_id,
        "status": "started",
        "output_type": request.output_type,
        "output_dir": str(output_dir),
    }


@router.get("/status")
async def get_conversion_status():
    """
    获取当前转换状态

    返回: running | completed | failed | idle
    """
    status = get_convert_status()

    result = {
        "status": status.status,
        "task_id": status.task_id,
    }

    if status.status == "completed":
        result["html_path"] = status.html_path
        result["image_count"] = status.image_count
    elif status.status == "failed":
        result["error"] = status.error
    elif status.status == "running":
        # 检查是否还有活跃的转换线程
        active_threads = [
            t for t in threading.enumerate()
            if t.name and t.name.startswith("convert-")
        ]
        if not active_threads and _convert_task.status == "running":
            # 线程已结束但状态未更新，可能是异常退出
            update_convert_status(status="failed", error="任务异常退出")

    return result
