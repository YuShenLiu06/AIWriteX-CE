# -*- coding: utf-8 -*-
"""
知识库管理器 - 封装 CrewAI Knowledge

统一管理图片知识库和文本知识库：
- 为前端管理页提供检索、统计、刷新能力
- 为工作流层提供 CrewAI 原生 knowledge_sources、embedder、knowledge_config
"""

import os
import httpx
from typing import Any, Dict, List, Optional

from crewai.knowledge.knowledge import Knowledge
from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

from src.ai_write_x.core.image_repository import ImageRepository
from src.ai_write_x.core.text_knowledge_repository import TextKnowledgeRepository
from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager

# Embedder API 连通性检测超时（秒）
_EMBEDDER_CONNECT_TIMEOUT = 10
_EMBEDDER_HEALTH_CHECK_MODEL = "embedding-v1"


class KnowledgeManager:
    """知识库管理器 - 单例模式，封装 CrewAI Knowledge"""

    _instance = None

    def __init__(self):
        self._image_knowledge: Optional[Knowledge] = None
        self._text_knowledge: Optional[Knowledge] = None
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "KnowledgeManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_knowledge_config(self) -> Dict[str, Any]:
        """获取知识库配置"""
        try:
            from src.ai_write_x.config.config import Config

            config = Config.get_instance()
            return config.config.get("knowledge", {})
        except Exception as e:
            log.print_log(f"获取知识库配置失败: {e}", "warning")
            return {}

    def check_embedder_connectivity(self) -> bool:
        """检测 Embedder API 连通性，返回是否可用"""
        config = self._get_embedder_config()
        base_url = config.get("base_url", "")
        api_key = config.get("api_key", "")
        model = config.get("model", _EMBEDDER_HEALTH_CHECK_MODEL)

        if not base_url or not api_key:
            log.print_log(
                "Embedder 配置不完整: 缺少 base_url 或 api_key，跳过连通性检测",
                "warning",
            )
            return False

        url = f"{base_url.rstrip('/')}/embeddings"
        log.print_log(f"检测 Embedder API 连通性: {url} (model={model})", "info")

        try:
            with httpx.Client(timeout=_EMBEDDER_CONNECT_TIMEOUT) as client:
                resp = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": "health_check", "model": model},
                )
                if resp.status_code == 200:
                    log.print_log(
                        f"Embedder API 连通性检测通过 (HTTP {resp.status_code})", "info"
                    )
                    return True
                else:
                    log.print_log(
                        f"Embedder API 返回异常状态: HTTP {resp.status_code} - {resp.text[:200]}",
                        "error",
                    )
                    return False
        except httpx.TimeoutException as e:
            log.print_log(
                f"[知识库] Embedder API 连接超时 ({_EMBEDDER_CONNECT_TIMEOUT}s): "
                f"url={url}, model={model}, error={e}",
                "error",
            )
            return False
        except httpx.ConnectError as e:
            log.print_log(
                f"[知识库] Embedder API 无法连接: url={url}, error={e}",
                "error",
            )
            return False
        except Exception as e:
            log.print_log(
                f"[知识库] Embedder API 检测失败: url={url}, error={e}",
                "error",
            )
            return False

    def is_text_enabled(self) -> bool:
        """文本知识库是否启用"""
        return self._get_knowledge_config().get("text_enabled", True)

    def is_image_enabled(self) -> bool:
        """图片知识库是否启用"""
        return self._get_knowledge_config().get("image_enabled", True)

    def _get_embedder_config(self) -> Dict[str, Any]:
        """从配置中获取 embedder 设置，兼容数组和单值两种格式"""
        try:
            from src.ai_write_x.config.config import Config

            config = Config.get_instance()
            knowledge_config = config.config.get("knowledge", {})
            embedder_config = knowledge_config.get("embedder", {})

            # api_key: 兼容 ["sk-xxx"] 和 "sk-xxx" 两种格式
            raw_api_key = embedder_config.get("api_key", "")
            if isinstance(raw_api_key, list):
                key_index = embedder_config.get("key_index", 0)
                api_key = (
                    raw_api_key[key_index]
                    if key_index < len(raw_api_key)
                    else (raw_api_key[0] if raw_api_key else "")
                )
            else:
                api_key = raw_api_key

            # model: 兼容 ["model-a"] 和 "model-a" 两种格式
            raw_model = embedder_config.get("model", "text-embedding-3-small")
            if isinstance(raw_model, list):
                model_index = embedder_config.get("model_index", 0)
                model = (
                    raw_model[model_index]
                    if model_index < len(raw_model)
                    else (raw_model[0] if raw_model else "text-embedding-3-small")
                )
            else:
                model = raw_model

            return {
                "provider": embedder_config.get("provider", "openai"),
                "api_key": api_key,
                "model": model,
                "base_url": embedder_config.get("base_url", ""),
            }
        except Exception as e:
            log.print_log(f"获取 embedder 配置失败，使用默认: {e}", "warning")
            return {
                "provider": "openai",
                "api_key": "",
                "model": "text-embedding-3-small",
                "base_url": "",
            }

    def _build_embedder(self) -> Dict[str, Any]:
        """构建 CrewAI embedder 配置，确保 model/api_key/base_url 正确传递到 ChromaDB"""
        config = self._get_embedder_config()
        embedder_config: Dict[str, Any] = {
            "model": config["model"],
        }
        # api_key: openai/azure/voyageai/google 需要，ollama 不需要
        if config["provider"] != "ollama" and config["api_key"]:
            embedder_config["api_key"] = config["api_key"]
        # base_url: 同时设置两个键，覆盖所有 provider
        # openai/azure 读 "api_base"，ollama 读 "url"
        if config["base_url"]:
            embedder_config["api_base"] = config["base_url"]
            embedder_config["url"] = config["base_url"]
        return {
            "provider": config["provider"],
            "config": embedder_config,
        }

    def _configure_storage(self) -> None:
        """设置 CrewAI 存储目录到项目数据目录"""
        storage_dir = PathManager.get_app_data_dir() / "knowledge_storage"
        os.environ["CREWAI_STORAGE_DIR"] = str(storage_dir)
        log.print_log(f"CrewAI 知识库存储目录: {storage_dir}", "info")

    def get_image_knowledge_sources(self) -> List[BaseKnowledgeSource]:
        """构建图片知识源列表"""
        if not self.is_image_enabled():
            log.print_log("图片知识库已禁用", "info")
            return []
        sources: List[BaseKnowledgeSource] = []
        repo = ImageRepository.get_instance()
        for img in repo.get_all():
            if not img.description:
                continue
            content = (
                f"图片描述: {img.description} | "
                f"标签: {','.join(img.tags) if img.tags else '无'} | "
                f"分类: {img.category or '未分类'}"
            )
            sources.append(
                StringKnowledgeSource(
                    content=content,
                    metadata={
                        "knowledge_type": "image",
                        "image_id": img.id,
                        "stored_path": img.stored_path,
                        "original_filename": img.original_filename,
                        "category": img.category or "",
                    },
                )
            )
        return sources

    def get_text_knowledge_sources(self) -> List[BaseKnowledgeSource]:
        """构建文本知识源列表"""
        if not self.is_text_enabled():
            log.print_log("文本知识库已禁用", "info")
            return []
        sources: List[BaseKnowledgeSource] = []
        repo = TextKnowledgeRepository.get_instance()
        for item in repo.get_all():
            if not item.content.strip() and not item.summary.strip():
                continue
            content = (
                f"标题: {item.title} | "
                f"摘要: {item.summary or '无'} | "
                f"标签: {','.join(item.tags) if item.tags else '无'} | "
                f"分类: {item.category or '未分类'}"
            )
            sources.append(
                StringKnowledgeSource(
                    content=content,
                    metadata={
                        "knowledge_type": "text",
                        "item_id": item.id,
                        "title": item.title,
                        "category": item.category or "",
                        "source_type": item.source_type,
                    },
                )
            )
        return sources

    def get_all_knowledge_sources(self) -> List[BaseKnowledgeSource]:
        """获取全部知识源"""
        return [
            *self.get_image_knowledge_sources(),
            *self.get_text_knowledge_sources(),
        ]

    def get_embedder(self) -> Dict[str, Any]:
        """获取统一 embedder 配置"""
        return self._build_embedder()

    def get_knowledge_config(self) -> Optional[Any]:
        """获取可选知识配置"""
        return None

    def initialize(self) -> None:
        """初始化图片知识库和文本知识库"""
        if self._initialized:
            return

        try:
            self._configure_storage()
            embedder = self._build_embedder()

            # 预检：检测 Embedder API 连通性
            embedder_config = self._get_embedder_config()
            base_url = embedder_config.get("base_url", "未配置")
            model = embedder_config.get("model", "未配置")
            if not self.check_embedder_connectivity():
                log.print_log(
                    f"[知识库] Embedder API 连通性检测失败，跳过知识库初始化 "
                    f"(base_url={base_url}, model={model})",
                    "warning",
                )
                return

            # 根据开关决定初始化哪些知识库
            if self.is_image_enabled():
                image_sources = self.get_image_knowledge_sources()
                if image_sources:
                    self._image_knowledge = Knowledge(
                        collection_name="image_knowledge",
                        sources=image_sources,
                        embedder=embedder,
                    )
                    log.print_log(f"图片知识库初始化完成，共 {len(image_sources)} 条", "info")
                else:
                    log.print_log("图片知识库无数据或已禁用，跳过初始化", "info")
            else:
                log.print_log("图片知识库已禁用，跳过初始化", "info")

            if self.is_text_enabled():
                text_sources = self.get_text_knowledge_sources()
                if text_sources:
                    self._text_knowledge = Knowledge(
                        collection_name="text_knowledge",
                        sources=text_sources,
                        embedder=embedder,
                    )
                    log.print_log(f"文本知识库初始化完成，共 {len(text_sources)} 条", "info")
                else:
                    log.print_log("文本知识库无数据或已禁用，跳过初始化", "info")
            else:
                log.print_log("文本知识库已禁用，跳过初始化", "info")

            self._initialized = True
        except TimeoutError as e:
            log.print_log(
                f"[知识库] 初始化超时 - Embedder API 响应超时 "
                f"(base_url={self._get_embedder_config().get('base_url', '未知')}, "
                f"model={self._get_embedder_config().get('model', '未知')}): {e}",
                "error",
            )
            self._image_knowledge = None
            self._text_knowledge = None
            self._initialized = False
        except ConnectionError as e:
            log.print_log(
                f"[知识库] 初始化失败 - Embedder API 连接错误 "
                f"(base_url={self._get_embedder_config().get('base_url', '未知')}): {e}",
                "error",
            )
            self._image_knowledge = None
            self._text_knowledge = None
            self._initialized = False
        except Exception as e:
            error_msg = str(e)
            is_timeout = "timed out" in error_msg.lower() or "timeout" in error_msg.lower()
            if is_timeout:
                log.print_log(
                    f"[知识库] 初始化失败 - Embedder API 请求超时 "
                    f"(base_url={self._get_embedder_config().get('base_url', '未知')}, "
                    f"model={self._get_embedder_config().get('model', '未知')}): {e}",
                    "error",
                )
            else:
                log.print_log(f"[知识库] 初始化失败: {e}", "error")
            self._image_knowledge = None
            self._text_knowledge = None
            self._initialized = False

    def search_images(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """检索相关图片"""
        if not self.is_image_enabled():
            return []
        if not self._initialized:
            self.initialize()
        if not self._image_knowledge:
            return []

        try:
            results = self._image_knowledge.query([query], limit=limit)
            return [
                {
                    "image_id": result.get("metadata", {}).get("image_id"),
                    "stored_path": result.get("metadata", {}).get("stored_path"),
                    "original_filename": result.get("metadata", {}).get("original_filename"),
                    "category": result.get("metadata", {}).get("category"),
                    "content": result.get("content"),
                    "score": result.get("score", 0),
                }
                for result in results
            ]
        except Exception as e:
            log.print_log(f"图片检索失败: {e}", "error")
            return []

    def search_texts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """检索相关文本知识"""
        if not self.is_text_enabled():
            return []
        if not self._initialized:
            self.initialize()
        if not self._text_knowledge:
            return []

        try:
            results = self._text_knowledge.query([query], limit=limit)
            output = []
            repo = TextKnowledgeRepository.get_instance()
            for result in results:
                metadata = result.get("metadata", {})
                item_id = metadata.get("item_id")
                item = repo.get_by_id(item_id) if item_id else None
                output.append(
                    {
                        "item_id": item_id,
                        "title": metadata.get("title") or (item.title if item else ""),
                        "category": metadata.get("category") or (item.category if item else ""),
                        "summary": item.summary if item else "",
                        "content": result.get("content"),
                        "score": result.get("score", 0),
                    }
                )
            return output
        except Exception as e:
            log.print_log(f"文本知识检索失败: {e}", "error")
            return []

    def refresh(self) -> None:
        """刷新全部知识库"""
        log.print_log("刷新知识库...", "info")
        self._image_knowledge = None
        self._text_knowledge = None
        self._initialized = False
        self.initialize()

    def refresh_images(self) -> None:
        """刷新图片知识库"""
        self.refresh()

    def refresh_texts(self) -> None:
        """刷新文本知识库"""
        self.refresh()

    def get_stats(self) -> Dict[str, int]:
        """获取知识库统计信息"""
        image_repo = ImageRepository.get_instance()
        text_repo = TextKnowledgeRepository.get_instance()
        image_knowledge_count = len([img for img in image_repo.get_all() if img.description.strip()])
        return {
            "image_count": image_repo.count,
            "image_knowledge_count": image_knowledge_count,
            "text_knowledge_count": text_repo.count,
            "total_knowledge_count": image_knowledge_count + text_repo.count,
        }

    @property
    def is_initialized(self) -> bool:
        """知识库是否已初始化"""
        return self._initialized
