"""定时任务 JSON 持久化仓储"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import List

from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager

from .scheduled_task_models import ScheduledTask, ScheduledTaskExecutionRecord


class ScheduledTaskRepository:
    """JSON 文件读写，线程安全"""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    @staticmethod
    def _tasks_path() -> Path:
        return PathManager.get_scheduled_tasks_path()

    @staticmethod
    def _records_path() -> Path:
        return PathManager.get_scheduled_task_records_path()

    def load_tasks(self) -> List[ScheduledTask]:
        return self._load_json(
            self._tasks_path(),
            "tasks",
            ScheduledTask.from_dict,
        )

    def save_tasks(self, tasks: List[ScheduledTask]) -> None:
        self._save_json(
            self._tasks_path(),
            {"tasks": [t.to_dict() for t in tasks]},
        )

    def load_records(self) -> List[ScheduledTaskExecutionRecord]:
        return self._load_json(
            self._records_path(),
            "records",
            ScheduledTaskExecutionRecord.from_dict,
        )

    def save_records(self, records: List[ScheduledTaskExecutionRecord]) -> None:
        self._save_json(
            self._records_path(),
            {"records": [r.to_dict() for r in records]},
        )

    def _load_json(self, path: Path, key: str, factory) -> list:
        with self._lock:
            if not path.exists():
                return []
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                items = data.get(key, [])
                return [factory(item) for item in items]
            except Exception as e:
                log.print_log(f"加载 {path.name} 失败: {e}", "error")
                return []

    def _save_json(self, path: Path, data: dict) -> None:
        with self._lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                log.print_log(f"保存 {path.name} 失败: {e}", "error")
