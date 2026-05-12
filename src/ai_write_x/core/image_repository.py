# -*- coding: utf-8 -*-
"""
图片仓库模块 - 纯文件存储，遵循项目架构

提供图片资源的存储、索引和检索功能，支持描述和标签管理。
单例模式，使用 JSON 文件作为索引。
"""

import uuid
import shutil
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.utils import log


@dataclass
class ImageResource:
    """图片资源数据结构"""
    id: str
    original_filename: str
    stored_path: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    file_size: int = 0
    mime_type: str = "image/jpeg"
    metadata: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    created_at: str = ""


class ImageRepository:
    """图片仓库 - 单例模式，JSON索引文件"""

    _instance = None

    def __init__(self):
        self._storage_dir = PathManager.get_image_dir() / "resources"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._storage_dir / "image_index.json"
        self._images: Dict[str, ImageResource] = {}
        self._load_index()

    @classmethod
    def get_instance(cls) -> "ImageRepository":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_index(self) -> None:
        """加载索引文件"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._images = {
                        k: ImageResource(**v) for k, v in data.items()
                    }
                log.print_log(f"图片索引加载成功，共 {len(self._images)} 条记录", "info")
            except Exception as e:
                log.print_log(f"加载图片索引失败: {e}", "warning")
                self._images = {}

    def _save_index(self) -> None:
        """保存索引文件"""
        try:
            with open(self._index_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {k: asdict(v) for k, v in self._images.items()},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            log.print_log(f"保存图片索引失败: {e}", "error")

    def add_image(
        self,
        file_path: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> ImageResource:
        """
        添加图片到仓库

        Args:
            file_path: 图片文件的完整路径
            description: 图片描述（供AI检索使用）
            tags: 标签列表
            category: 分类

        Returns:
            ImageResource: 新创建的图片资源对象
        """
        tags = tags or []
        img_id = str(uuid.uuid4())
        ext = Path(file_path).suffix.lower() or ".jpg"
        stored_name = f"{img_id}{ext}"
        stored_path = self._storage_dir / stored_name

        # 复制文件到存储目录
        try:
            shutil.copy2(file_path, stored_path)
        except Exception as e:
            log.print_log(f"复制图片文件失败: {e}", "error")
            raise

        resource = ImageResource(
            id=img_id,
            original_filename=Path(file_path).name,
            stored_path=str(stored_path),
            description=description,
            tags=tags,
            category=category,
            file_size=stored_path.stat().st_size if stored_path.exists() else 0,
            mime_type=self._get_mime_type(ext),
            created_at=self._get_timestamp()
        )

        self._images[img_id] = resource
        self._save_index()
        log.print_log(f"图片添加成功: {img_id} -> {stored_path}", "info")

        return resource

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[ImageResource]:
        """
        关键词搜索图片

        Args:
            query: 搜索关键词
            category: 可选的分类过滤
            limit: 返回结果数量限制

        Returns:
            List[ImageResource]: 匹配的图片列表（按相关度排序）
        """
        results = []
        query_lower = query.lower()

        for img in self._images.values():
            # 分类过滤
            if category and img.category != category:
                continue

            # 计算相关度评分
            score = 0
            if query_lower in img.description.lower():
                score += 3
            if any(query_lower in tag.lower() for tag in img.tags):
                score += 2
            if img.category and query_lower in img.category.lower():
                score += 1

            if score > 0:
                results.append((score, img))

        # 按评分降序排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [img for _, img in results[:limit]]

    def get_all(self) -> List[ImageResource]:
        """获取所有图片"""
        return list(self._images.values())

    def get_by_id(self, img_id: str) -> Optional[ImageResource]:
        """根据ID获取图片"""
        return self._images.get(img_id)

    def update(self, img_id: str, **kwargs) -> bool:
        """
        更新图片信息

        Args:
            img_id: 图片ID
            **kwargs: 要更新的字段（description, tags, category, usage_count）

        Returns:
            bool: 更新是否成功
        """
        if img_id not in self._images:
            return False

        img = self._images[img_id]
        for key, value in kwargs.items():
            if hasattr(img, key):
                setattr(img, key, value)

        self._save_index()
        log.print_log(f"图片更新成功: {img_id}", "info")
        return True

    def delete(self, img_id: str) -> bool:
        """
        删除图片

        Args:
            img_id: 图片ID

        Returns:
            bool: 删除是否成功
        """
        if img_id not in self._images:
            return False

        img = self._images[img_id]
        # 删除实际文件
        try:
            Path(img.stored_path).unlink(missing_ok=True)
        except Exception as e:
            log.print_log(f"删除图片文件失败: {e}", "warning")

        del self._images[img_id]
        self._save_index()
        log.print_log(f"图片删除成功: {img_id}", "info")
        return True

    def increment_usage(self, img_id: str) -> bool:
        """增加图片使用计数"""
        if img_id in self._images:
            self._images[img_id].usage_count += 1
            self._save_index()
            return True
        return False

    def _get_mime_type(self, ext: str) -> str:
        """根据扩展名获取MIME类型"""
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".svg": "image/svg+xml",
        }
        return mime_types.get(ext, "image/jpeg")

    def _get_timestamp(self) -> str:
        """获取当前时间戳字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def count(self) -> int:
        """获取图片总数"""
        return len(self._images)