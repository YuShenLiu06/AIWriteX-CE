# -*- coding: utf-8 -*-
"""
文本知识管理 REST API

提供文本知识的新增、列表、更新、删除和检索功能。
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.ai_write_x.core.knowledge_manager import KnowledgeManager
from src.ai_write_x.core.text_knowledge_repository import TextKnowledgeRepository
from src.ai_write_x.utils import log


router = APIRouter(prefix="/api/text-knowledge", tags=["text-knowledge"])


class TextKnowledgeCreate(BaseModel):
    """文本知识创建请求模型"""

    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    summary: str = ""
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    source_type: str = "manual"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextKnowledgeUpdate(BaseModel):
    """文本知识更新请求模型"""

    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    source_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def _serialize_item(item) -> Dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "content": item.content,
        "summary": item.summary,
        "tags": item.tags,
        "category": item.category,
        "source_type": item.source_type,
        "metadata": item.metadata,
        "usage_count": item.usage_count,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.post("/")
async def create_text_knowledge(payload: TextKnowledgeCreate):
    """创建文本知识条目"""
    log.print_log(f"准备创建文本知识: title={payload.title}", "info")
    try:
        repo = TextKnowledgeRepository.get_instance()
        item = repo.add_item(
            title=payload.title,
            content=payload.content,
            summary=payload.summary,
            tags=payload.tags,
            category=payload.category,
            source_type=payload.source_type,
            metadata=payload.metadata,
        )
        log.print_log(f"文本知识创建成功: {item.id}", "info")

        # 刷新知识库（不影响主流程）
        try:
            km = KnowledgeManager.get_instance()
            log.print_log("开始刷新知识库...", "info")
            km.refresh_texts()
            log.print_log("知识库刷新完成", "info")
        except Exception as refresh_err:
            log.print_log(f"刷新知识库失败(不影响返回): {refresh_err}", "warning")

        return {"status": "success", "data": _serialize_item(item)}
    except Exception as e:
        log.print_log(f"创建文本知识失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_text_knowledge(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
):
    """获取文本知识列表"""
    try:
        repo = TextKnowledgeRepository.get_instance()
        if search:
            items = repo.search(search, category=category, limit=limit)
        else:
            items = repo.get_all()
            if category:
                items = [item for item in items if item.category == category]
            items = items[:limit]
        return {"status": "success", "data": [_serialize_item(item) for item in items]}
    except Exception as e:
        log.print_log(f"获取文本知识列表失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def list_text_categories():
    """获取文本知识库的所有分类列表"""
    try:
        repo = TextKnowledgeRepository.get_instance()
        items = repo.get_all()
        categories = set()
        for item in items:
            if item.category:
                categories.add(item.category)
        return {"status": "success", "data": sorted(list(categories))}
    except Exception as e:
        log.print_log(f"获取文本知识分类失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{item_id}")
async def get_text_knowledge(item_id: str):
    """获取单个文本知识条目"""
    try:
        repo = TextKnowledgeRepository.get_instance()
        item = repo.get_by_id(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="文本知识不存在")
        return {"status": "success", "data": _serialize_item(item)}
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"获取文本知识失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{item_id}")
async def update_text_knowledge(item_id: str, payload: TextKnowledgeUpdate):
    """更新文本知识条目"""
    try:
        kwargs = payload.model_dump(exclude_none=True)
        if not kwargs:
            raise HTTPException(status_code=400, detail="没有要更新的字段")

        repo = TextKnowledgeRepository.get_instance()
        if not repo.update(item_id, **kwargs):
            raise HTTPException(status_code=404, detail="文本知识不存在")

        # 刷新知识库（不影响主流程）
        try:
            KnowledgeManager.get_instance().refresh_texts()
        except Exception as refresh_err:
            log.print_log(f"刷新知识库失败(不影响返回): {refresh_err}", "warning")

        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"更新文本知识失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}")
async def delete_text_knowledge(item_id: str):
    """删除文本知识条目"""
    try:
        repo = TextKnowledgeRepository.get_instance()
        if not repo.delete(item_id):
            raise HTTPException(status_code=404, detail="文本知识不存在")

        # 刷新知识库（不影响主流程）
        try:
            KnowledgeManager.get_instance().refresh_texts()
        except Exception as refresh_err:
            log.print_log(f"刷新知识库失败(不影响返回): {refresh_err}", "warning")

        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        log.print_log(f"删除文本知识失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-knowledge")
async def refresh_text_knowledge():
    """手动刷新文本知识库"""
    try:
        KnowledgeManager.get_instance().refresh_texts()
        return {"status": "success"}
    except Exception as e:
        log.print_log(f"刷新文本知识库失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))
