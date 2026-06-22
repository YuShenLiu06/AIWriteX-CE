# -*- coding: utf-8 -*-
"""
文本知识搜索工具 - CrewAI Tool

供 AI Agent 主动搜索文本知识库，用精炼关键词查找相关参考资料。
优先向量语义检索，回退到关键词双向匹配。
匹配到后返回完整正文供 Agent 参考。
"""

import json
from typing import Optional

from crewai.tools import BaseTool

from src.ai_write_x.core.knowledge_manager import KnowledgeManager
from src.ai_write_x.core.text_knowledge_repository import TextKnowledgeRepository
from src.ai_write_x.utils import log


class TextKnowledgeSearchTool(BaseTool):
    """
    文本知识搜索工具

    供 AI Agent 主动搜索知识库，获取相关参考资料。
    优先使用向量语义检索，回退到关键词双向匹配。
    返回匹配条目的完整正文内容，供 Agent 参考。

    输入参数:
        query: 搜索关键词（必填），建议使用简洁关键词而非完整指令
        limit: 返回数量，默认3

    返回:
        JSON字符串: [{title, summary, tags, category, content}, ...]
    """

    name: str = "text_knowledge_search"
    description: str = (
        "搜索文本知识库，根据关键词找到相关的参考资料和素材。"
        "输入: query(搜索关键词，建议用简洁的词如'创业故事'而非完整句子), limit(可选默认3)"
        "返回: JSON数组 [{title, summary, tags, category, content}]"
    )

    def _run(
        self,
        query: str,
        limit: int = 3,
    ) -> str:
        """
        执行文本知识搜索

        Args:
            query: 搜索关键词
            limit: 返回结果数量限制

        Returns:
            str: JSON格式的知识条目列表
        """
        if not query or not query.strip():
            return json.dumps([], ensure_ascii=False)

        query = query.strip()

        try:
            km = KnowledgeManager.get_instance()

            # 文本知识库未启用时，静默返回空结果
            if not km.is_text_enabled():
                return json.dumps([], ensure_ascii=False)

            results = []

            # 优先使用向量语义检索
            if km.is_initialized:
                vector_results = km.search_texts(query, limit=limit)
                if vector_results:
                    results = vector_results
                    log.print_log(
                        f"文本知识向量检索命中 {len(results)} 条: query='{query}'",
                        "info",
                    )

            # 向量检索无结果，回退到关键词检索
            if not results:
                log.print_log(
                    f"文本知识向量检索无结果，回退到关键词检索: query='{query}'",
                    "info",
                )
                text_repo = TextKnowledgeRepository.get_instance()
                keyword_items = text_repo.search(query, limit=limit)
                if keyword_items:
                    results = [
                        {
                            "title": item.title,
                            "summary": item.summary,
                            "tags": item.tags,
                            "category": item.category,
                            "content": item.content,
                            "score": 1.0,
                        }
                        for item in keyword_items
                    ]
                    log.print_log(
                        f"文本知识关键词检索命中 {len(results)} 条: query='{query}'",
                        "info",
                    )

            # 增加使用计数
            for r in results:
                item_id = r.get("item_id")
                if item_id:
                    text_repo = TextKnowledgeRepository.get_instance()
                    text_repo.increment_usage(item_id)

            if not results:
                log.print_log(f"文本知识检索无结果: query='{query}'", "info")
                return json.dumps([], ensure_ascii=False)

            return json.dumps(results, ensure_ascii=False)

        except Exception as e:
            log.print_log(f"文本知识搜索异常: {e}", "error")
            return json.dumps([], ensure_ascii=False)
