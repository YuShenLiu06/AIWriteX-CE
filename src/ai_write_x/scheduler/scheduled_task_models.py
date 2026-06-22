"""定时任务数据模型"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


def _now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class ScheduledTask:
    """定时任务定义"""

    task_id: str = field(default_factory=lambda: _new_id("task"))
    name: str = ""
    topic: str = ""
    schedule_type: str = "fixed_time"
    time_of_day: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: bool = True
    auto_publish: bool = False
    max_retries: int = 3
    current_retry_count: int = 0
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_status: str = "idle"
    last_error: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    # 生成配置扩展字段
    reference_urls: str = ""
    reference_ratio: int = 0
    template_category: str = ""
    template_name: str = ""
    platform: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "topic": self.topic,
            "schedule_type": self.schedule_type,
            "time_of_day": self.time_of_day,
            "cron_expression": self.cron_expression,
            "enabled": self.enabled,
            "auto_publish": self.auto_publish,
            "max_retries": self.max_retries,
            "current_retry_count": self.current_retry_count,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reference_urls": self.reference_urls,
            "reference_ratio": self.reference_ratio,
            "template_category": self.template_category,
            "template_name": self.template_name,
            "platform": self.platform,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScheduledTask:
        return cls(
            task_id=data.get("task_id", _new_id("task")),
            name=data.get("name", ""),
            topic=data.get("topic", ""),
            schedule_type=data.get("schedule_type", "fixed_time"),
            time_of_day=data.get("time_of_day"),
            cron_expression=data.get("cron_expression"),
            enabled=data.get("enabled", True),
            auto_publish=data.get("auto_publish", False),
            max_retries=data.get("max_retries", 3),
            current_retry_count=data.get("current_retry_count", 0),
            last_run_at=data.get("last_run_at"),
            next_run_at=data.get("next_run_at"),
            last_status=data.get("last_status", "idle"),
            last_error=data.get("last_error"),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
            reference_urls=data.get("reference_urls", ""),
            reference_ratio=data.get("reference_ratio", 0),
            template_category=data.get("template_category", ""),
            template_name=data.get("template_name", ""),
            platform=data.get("platform", ""),
        )


@dataclass
class ScheduledTaskExecutionRecord:
    """定时任务执行记录"""

    record_id: str = field(default_factory=lambda: _new_id("rec"))
    task_id: str = ""
    started_at: str = field(default_factory=_now_iso)
    finished_at: Optional[str] = None
    status: str = "running"
    retry_attempt: int = 0
    message: Optional[str] = None
    article_path: Optional[str] = None
    published: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "task_id": self.task_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "retry_attempt": self.retry_attempt,
            "message": self.message,
            "article_path": self.article_path,
            "published": self.published,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScheduledTaskExecutionRecord:
        return cls(
            record_id=data.get("record_id", _new_id("rec")),
            task_id=data.get("task_id", ""),
            started_at=data.get("started_at", _now_iso()),
            finished_at=data.get("finished_at"),
            status=data.get("status", "running"),
            retry_attempt=data.get("retry_attempt", 0),
            message=data.get("message"),
            article_path=data.get("article_path"),
            published=data.get("published", False),
        )
