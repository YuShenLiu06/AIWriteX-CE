# -*- coding: utf-8 -*-
"""
文本知识仓库模块 - 纯文件存储，遵循项目架构

提供普通文本知识条目的存储、索引和检索能力。
单例模式，使用 JSON 文件作为索引。
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager


@dataclass
class TextKnowledgeItem:
    """文本知识条目数据结构"""

    id: str
    title: str
    content: str
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    source_type: str = "manual"
    metadata: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class TextKnowledgeRepository:
    """文本知识仓库 - 单例模式，JSON索引文件"""

    _instance = None

    def __init__(self):
        self._storage_dir = PathManager.get_app_data_dir() / "knowledge" / "texts"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._storage_dir / "text_knowledge_index.json"
        self._items: Dict[str, TextKnowledgeItem] = {}
        self._load_index()

    @classmethod
    def get_instance(cls) -> "TextKnowledgeRepository":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_index(self) -> None:
        """加载索引文件"""
        if not self._index_file.exists():
            return

        try:
            with open(self._index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._items = {key: TextKnowledgeItem(**value) for key, value in data.items()}
            log.print_log(f"文本知识索引加载成功，共 {len(self._items)} 条记录", "info")
        except Exception as e:
            log.print_log(f"加载文本知识索引失败: {e}", "warning")
            self._items = {}

    def _save_index(self) -> None:
        """保存索引文件"""
        try:
            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(
                    {key: asdict(value) for key, value in self._items.items()},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            log.print_log(f"保存文本知识索引失败: {e}", "error")

    def add_item(
        self,
        title: str,
        content: str,
        summary: str = "",
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        source_type: str = "manual",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TextKnowledgeItem:
        """添加文本知识条目"""
        item_id = str(uuid.uuid4())
        timestamp = self._get_timestamp()
        item = TextKnowledgeItem(
            id=item_id,
            title=title.strip(),
            content=content.strip(),
            summary=(summary or self._build_summary(content)).strip(),
            tags=tags or [],
            category=category,
            source_type=source_type,
            metadata=metadata or {},
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._items[item_id] = item
        self._save_index()
        log.print_log(f"文本知识添加成功: {item_id}", "info")
        return item

    def get_all(self) -> List[TextKnowledgeItem]:
        """获取所有文本知识条目"""
        return list(self._items.values())

    def get_by_id(self, item_id: str) -> Optional[TextKnowledgeItem]:
        """根据 ID 获取文本知识条目"""
        return self._items.get(item_id)

    def update(self, item_id: str, **kwargs) -> bool:
        """更新文本知识条目"""
        item = self._items.get(item_id)
        if item is None:
            return False

        for key, value in kwargs.items():
            if value is None or not hasattr(item, key):
                continue
            setattr(item, key, value)

        if "content" in kwargs and kwargs["content"] is not None and "summary" not in kwargs:
            item.summary = self._build_summary(item.content)

        item.updated_at = self._get_timestamp()
        self._save_index()
        log.print_log(f"文本知识更新成功: {item_id}", "info")
        return True

    def delete(self, item_id: str) -> bool:
        """删除文本知识条目"""
        if item_id not in self._items:
            return False

        del self._items[item_id]
        self._save_index()
        log.print_log(f"文本知识删除成功: {item_id}", "info")
        return True

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[TextKnowledgeItem]:
        """关键词搜索文本知识条目（双向匹配：query⊂field 或 field⊂query）"""
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        results: List[tuple[int, TextKnowledgeItem]] = []
        for item in self._items.values():
            if category and item.category != category:
                continue

            score = 0
            score += self._field_match_score(query_lower, item.title.lower(), 4)
            score += self._field_match_score(query_lower, item.summary.lower(), 3)
            score += self._field_match_score(query_lower, item.content.lower(), 2)
            if any(
                self._field_match_score(query_lower, tag.lower(), 2) > 0
                for tag in item.tags
            ):
                score += 2
            if item.category:
                score += self._field_match_score(query_lower, item.category.lower(), 1)

            if score > 0:
                results.append((score, item))

        results.sort(key=lambda entry: entry[0], reverse=True)
        return [item for _, item in results[:limit]]

    @staticmethod
    def _field_match_score(query: str, field: str, weight: int) -> int:
        """双向子串匹配：query⊂field 或 field⊂query 任一命中即得分"""
        if query in field or field in query:
            return weight
        return 0

    def increment_usage(self, item_id: str) -> bool:
        """增加文本知识使用计数"""
        item = self._items.get(item_id)
        if item is None:
            return False

        item.usage_count += 1
        item.updated_at = self._get_timestamp()
        self._save_index()
        return True

    def _build_summary(self, content: str, max_length: int = 160) -> str:
        """根据正文构建摘要"""
        normalized = " ".join(content.split())
        if len(normalized) <= max_length:
            return normalized
        return f"{normalized[:max_length].rstrip()}..."

    def _get_timestamp(self) -> str:
        """获取当前时间戳字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def count(self) -> int:
        """获取文本知识总数"""
        return len(self._items)
