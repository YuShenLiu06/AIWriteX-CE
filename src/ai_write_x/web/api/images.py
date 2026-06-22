# -*- coding: utf-8 -*-
"""
图片管理 REST API

提供图片的上传、列表、搜索、删除和更新功能。
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from ..auth import verify_auth
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from src.ai_write_x.core.image_repository import ImageRepository
from src.ai_write_x.core.knowledge_manager import KnowledgeManager
from src.ai_write_x.utils import log


router = APIRouter(prefix="/api/images", tags=["images"], dependencies=[Depends(verify_auth)])


class ImageUpdate(BaseModel):
    """图片更新请求模型"""
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None


class ImageResponse(BaseModel):
    """图片响应数据模型"""
    id: str
    original_filename: str
    stored_path: str
    description: str
    tags: List[str]
    category: Optional[str]
    usage_count: int
    created_at: str


@router.post("/")
async def upload_image(
    file: UploadFile = File(...),
    description: str = Form(""),
    tags: str = Form(""),
    category: Optional[str] = Form(None)
):
    """
    上传图片到仓库

    - **file**: 图片文件（必填）
    - **description**: 图片描述（供AI检索使用）
    - **tags**: 标签，多个用逗号分隔
    - **category**: 分类
    """
    try:
        repo = ImageRepository.get_instance()

        # 解析标签
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        # 保存上传的文件到临时路径
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename or ".jpg") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # 添加到仓库
        resource = repo.add_image(tmp_path, description, tag_list, category)

        # 清理临时文件
        Path(tmp_path).unlink(missing_ok=True)

        # 刷新知识库
        try:
            km = KnowledgeManager.get_instance()
            km.refresh_images()
        except Exception as e:
            log.print_log(f"刷新知识库失败: {e}", "warning")

        log.print_log(f"图片上传成功: {resource.id}", "info")

        return {
            "status": "success",
            "data": {
                "id": resource.id,
                "original_filename": resource.original_filename,
                "stored_path": resource.stored_path,
                "description": resource.description,
                "tags": resource.tags,
                "category": resource.category,
                "usage_count": resource.usage_count,
            }
        }

    except Exception as e:
        log.print_log(f"图片上传失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_images(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50
):
    """
    获取图片列表

    - **category**: 可选的分类过滤
    - **search**: 可选的搜索词（搜索描述和标签）
    - **limit**: 返回数量限制，默认50
    """
    try:
        repo = ImageRepository.get_instance()

        if search:
            # 搜索模式
            images = repo.search(search, category=category, limit=limit)
        else:
            # 列表模式
            images = repo.get_all()
            if category:
                images = [img for img in images if img.category == category]
            images = images[:limit]

        return {
            "status": "success",
            "data": [
                {
                    "id": img.id,
                    "original_filename": img.original_filename,
                    "stored_path": img.stored_path,
                    "description": img.description,
                    "tags": img.tags,
                    "category": img.category,
                    "usage_count": img.usage_count,
                    "created_at": img.created_at,
                }
                for img in images
            ]
        }

    except Exception as e:
        log.print_log(f"获取图片列表失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{image_id}")
async def get_image(image_id: str):
    """获取单个图片信息"""
    try:
        repo = ImageRepository.get_instance()
        img = repo.get_by_id(image_id)

        if not img:
            raise HTTPException(status_code=404, detail="图片不存在")

        return {
            "status": "success",
            "data": {
                "id": img.id,
                "original_filename": img.original_filename,
                "stored_path": img.stored_path,
                "description": img.description,
                "tags": img.tags,
                "category": img.category,
                "file_size": img.file_size,
                "mime_type": img.mime_type,
                "usage_count": img.usage_count,
                "created_at": img.created_at,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"获取图片失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{image_id}/file")
async def get_image_file(image_id: str):
    """获取图片文件"""
    try:
        repo = ImageRepository.get_instance()
        img = repo.get_by_id(image_id)

        if not img:
            raise HTTPException(status_code=404, detail="图片不存在")

        file_path = Path(img.stored_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="图片文件不存在")

        return FileResponse(
            path=file_path,
            media_type=img.mime_type,
            filename=img.original_filename
        )

    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"获取图片文件失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{image_id}")
async def update_image(image_id: str, update: ImageUpdate):
    """
    更新图片信息

    - **description**: 新的描述
    - **tags**: 新的标签列表
    - **category**: 新的分类
    """
    try:
        repo = ImageRepository.get_instance()

        # 构建更新参数
        kwargs = {}
        if update.description is not None:
            kwargs["description"] = update.description
        if update.tags is not None:
            kwargs["tags"] = update.tags
        if update.category is not None:
            kwargs["category"] = update.category

        if not kwargs:
            raise HTTPException(status_code=400, detail="没有要更新的字段")

        if not repo.update(image_id, **kwargs):
            raise HTTPException(status_code=404, detail="图片不存在")

        # 刷新知识库
        try:
            km = KnowledgeManager.get_instance()
            km.refresh_images()
        except Exception as e:
            log.print_log(f"刷新知识库失败: {e}", "warning")

        log.print_log(f"图片更新成功: {image_id}", "info")
        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"更新图片失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}")
async def delete_image(image_id: str):
    """删除图片"""
    try:
        repo = ImageRepository.get_instance()

        if not repo.delete(image_id):
            raise HTTPException(status_code=404, detail="图片不存在")

        # 刷新知识库
        try:
            km = KnowledgeManager.get_instance()
            km.refresh_images()
        except Exception as e:
            log.print_log(f"刷新知识库失败: {e}", "warning")

        log.print_log(f"图片删除成功: {image_id}", "info")
        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"删除图片失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-knowledge")
async def refresh_knowledge():
    """手动刷新图片知识库（兼容旧接口）"""
    try:
        km = KnowledgeManager.get_instance()
        km.refresh_images()
        log.print_log("图片知识库刷新成功", "info")
        return {"status": "success"}
    except Exception as e:
        log.print_log(f"图片知识库刷新失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))