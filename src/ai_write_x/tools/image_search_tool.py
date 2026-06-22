# -*- coding: utf-8 -*-
"""
图片搜索工具 - CrewAI Tool

供 AI Agent 调用以搜索图片库，根据文章主题找到相关图片。
支持向量语义检索和关键词回退检索。
"""

import json
from typing import Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.ai_write_x.core.image_repository import ImageRepository
from src.ai_write_x.core.knowledge_manager import KnowledgeManager
from src.ai_write_x.utils import log


class ImageSearchToolSchema(BaseModel):
    query: str = Field(description="搜索词（必填）")
    category: Optional[str] = Field(default=None, description="可选的分类过滤")
    limit: int = Field(default=3, description="返回数量，默认3")


class ImageSearchTool(BaseTool):
    """
    图片搜索工具

    供 AI Agent 在编写文章时搜索相关图片。
    优先使用向量语义检索，回退到关键词匹配。

    输入参数:
        query: 搜索词（必填）
        category: 可选的分类过滤
        limit: 返回数量，默认3

    返回:
        JSON字符串: [{image_id, stored_path, description, score}, ...]
    """

    name: str = "image_search"
    description: str = (
        "搜索图片库，根据文章主题找到相关图片路径。"
        "输入: query(搜索词，必填), category(可选), limit(可选默认3)"
        "返回: JSON数组 [{image_id, stored_path, description, score}]"
    )
    args_schema: type[BaseModel] = ImageSearchToolSchema

    def _run(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 3
    ) -> str:
        """
        执行图片搜索

        Args:
            query: 搜索查询词
            category: 可选的分类过滤
            limit: 返回结果数量限制

        Returns:
            str: JSON格式的图片列表
        """
        if not query or not query.strip():
            return json.dumps([], ensure_ascii=False)

        query = query.strip()

        try:
            km = KnowledgeManager.get_instance()

            if not km.is_image_enabled():
                return json.dumps([], ensure_ascii=False)

            results = []

            # 优先向量检索（仅当知识库已初始化时）
            if km.is_initialized:
                results = km.search_images(query, limit=limit)
                if results:
                    log.print_log(
                        f"图片向量检索命中 {len(results)} 条: query='{query}'",
                        "info",
                    )

            # 向量无结果 → 关键词回退
            if not results:
                log.print_log(
                    f"图片向量检索无结果，回退到关键词检索: query='{query}'",
                    "info",
                )
                repo = ImageRepository.get_instance()
                images = repo.search(query, limit=limit)
                results = [
                    {
                        "image_id": img.id,
                        "stored_path": img.stored_path,
                        "original_filename": img.original_filename,
                        "description": img.description,
                        "score": 1.0,
                    }
                    for img in images
                ]
                if results:
                    log.print_log(
                        f"图片关键词检索命中 {len(results)} 条: query='{query}'",
                        "info",
                    )

            # 使用计数
            if results:
                repo = ImageRepository.get_instance()
                for r in results:
                    if r.get("image_id"):
                        repo.increment_usage(r["image_id"])
            else:
                log.print_log(f"图片检索无结果: query='{query}'", "info")

            return json.dumps(results, ensure_ascii=False)

        except Exception as e:
            log.print_log(f"图片搜索异常: {e}", "error")
            return json.dumps([], ensure_ascii=False)


class ImageSearchToolV2Schema(BaseModel):
    query: str = Field(description="搜索词")
    category: Optional[str] = Field(default=None, description="可选的分类过滤")
    limit: int = Field(default=5, description="返回数量，默认5")
    min_score: float = Field(default=0.1, description="最低相关度分数")


class ImageSearchTool_v2(BaseTool):
    """
    图片搜索工具 v2 - 支持更灵活的搜索参数

    与 v1 的区别:
        - 支持 min_score 过滤低相关度结果
        - 返回结果包含更多元数据
    """

    name: str = "image_search_v2"
    description: str = (
        "搜索图片库找到相关图片（高级版）。"
        "输入: query(搜索词), category(可选), limit(默认5), min_score(默认0.1)"
        "返回: JSON数组 [{image_id, stored_path, description, score, tags, category}]"
    )
    args_schema: type[BaseModel] = ImageSearchToolV2Schema

    def _run(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.1
    ) -> str:
        """执行图片搜索（高级版）"""
        if not query or not query.strip():
            return json.dumps([], ensure_ascii=False)

        query = query.strip()

        try:
            km = KnowledgeManager.get_instance()
            results = km.search_images(query, limit=limit)

            if not results:
                repo = ImageRepository.get_instance()
                images = repo.search(query, category=category, limit=limit)
                results = [
                    {
                        "image_id": img.id,
                        "stored_path": img.stored_path,
                        "original_filename": img.original_filename,
                        "description": img.description,
                        "tags": img.tags,
                        "category": img.category,
                        "score": 1.0
                    }
                    for img in images
                ]

            # 按 min_score 过滤
            filtered = [r for r in results if r.get("score", 0) >= min_score]

            # 增加使用计数
            for r in filtered:
                if r.get("image_id"):
                    repo = ImageRepository.get_instance()
                    repo.increment_usage(r["image_id"])

            return json.dumps(filtered, ensure_ascii=False)

        except Exception as e:
            log.print_log(f"图片搜索异常(v2): {e}", "error")
            return json.dumps([], ensure_ascii=False)
