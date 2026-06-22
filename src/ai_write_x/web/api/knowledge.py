# -*- coding: utf-8 -*-
"""
统一知识库 REST API

提供知识库统计与统一刷新能力。
"""

from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_auth

from src.ai_write_x.core.knowledge_manager import KnowledgeManager
from src.ai_write_x.utils import log


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"], dependencies=[Depends(verify_auth)])


@router.get("/stats")
async def get_knowledge_stats():
    """获取知识库统计信息"""
    try:
        stats = KnowledgeManager.get_instance().get_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        log.print_log(f"获取知识库统计失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_knowledge():
    """统一刷新全部知识库"""
    try:
        KnowledgeManager.get_instance().refresh()
        return {"status": "success"}
    except Exception as e:
        log.print_log(f"统一刷新知识库失败: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))
