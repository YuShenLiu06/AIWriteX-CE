"""定时任务 CRUD 服务"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from src.ai_write_x.utils import log

from .scheduled_task_models import ScheduledTask, ScheduledTaskExecutionRecord
from .scheduled_task_repository import ScheduledTaskRepository


class ScheduledTaskService:
    """任务管理、启停、下次执行时间计算"""

    def __init__(self, repository: ScheduledTaskRepository) -> None:
        self._repo = repository
        self._tasks: List[ScheduledTask] = []
        self._records: List[ScheduledTaskExecutionRecord] = []
        self._load()

    def _load(self) -> None:
        self._tasks = self._repo.load_tasks()
        self._records = self._repo.load_records()
        self._recalculate_next_runs()

    def _persist_tasks(self) -> None:
        self._repo.save_tasks(self._tasks)

    def _persist_records(self) -> None:
        self._repo.save_records(self._records)

    def _recalculate_next_runs(self) -> None:
        for task in self._tasks:
            if task.enabled:
                task.next_run_at = self.calculate_next_run(task)
        self._persist_tasks()

    def list_tasks(self) -> List[ScheduledTask]:
        return list(self._tasks)

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return next((t for t in self._tasks if t.task_id == task_id), None)

    def create_task(self, data: dict) -> ScheduledTask:
        task = ScheduledTask.from_dict(data)
        if not task.name.strip():
            raise ValueError("任务名称不能为空")
        if not task.topic.strip():
            raise ValueError("任务话题不能为空")

        self._validate_schedule(task)

        task.next_run_at = self.calculate_next_run(task) if task.enabled else None
        self._tasks.append(task)
        self._persist_tasks()
        log.print_log(f"创建定时任务: {task.name} ({task.task_id})", "info")
        return task

    def update_task(self, task_id: str, data: dict) -> ScheduledTask:
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        updates = {
            k: v for k, v in data.items()
            if k in ("name", "topic", "schedule_type", "time_of_day",
                     "cron_expression", "enabled", "auto_publish", "max_retries",
                     "reference_urls", "reference_ratio", "template_category",
                     "template_name", "platform")
        }

        if "topic" in updates and not updates["topic"].strip():
            raise ValueError("任务话题不能为空")
        if "name" in updates and not updates["name"].strip():
            raise ValueError("任务名称不能为空")

        for key, value in updates.items():
            setattr(task, key, value)

        self._validate_schedule(task)

        task.updated_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        task.next_run_at = self.calculate_next_run(task) if task.enabled else None
        self._persist_tasks()
        log.print_log(f"更新定时任务: {task.name} ({task.task_id})", "info")
        return task

    def delete_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        self._tasks = [t for t in self._tasks if t.task_id != task_id]
        self._persist_tasks()
        log.print_log(f"删除定时任务: {task.name} ({task_id})", "info")
        return True

    def toggle_task(self, task_id: str) -> ScheduledTask:
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        task.enabled = not task.enabled
        task.next_run_at = self.calculate_next_run(task) if task.enabled else None
        task.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist_tasks()
        log.print_log(f"切换任务状态: {task.name} -> {'启用' if task.enabled else '停用'}", "info")
        return task

    def update_task_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        task.last_status = status
        task.last_error = error
        task.last_run_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        task.updated_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        self._persist_tasks()

    def add_record(self, record: ScheduledTaskExecutionRecord) -> None:
        self._records.append(record)
        if len(self._records) > 500:
            self._records = self._records[-500:]
        self._persist_records()

    def update_record(self, record_id: str, **kwargs) -> None:
        for rec in self._records:
            if rec.record_id == record_id:
                for key, value in kwargs.items():
                    if hasattr(rec, key):
                        setattr(rec, key, value)
                self._persist_records()
                return

    def get_records(self, task_id: str) -> List[ScheduledTaskExecutionRecord]:
        return [r for r in self._records if r.task_id == task_id]

    @staticmethod
    def calculate_next_run(task: ScheduledTask) -> Optional[str]:
        if not task.enabled:
            return None

        now = datetime.now(ZoneInfo("Asia/Shanghai"))

        if task.schedule_type == "fixed_time" and task.time_of_day:
            parts = task.time_of_day.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0

            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.isoformat()

        if task.schedule_type == "cron" and task.cron_expression:
            try:
                from croniter import croniter
                cron = croniter(task.cron_expression, now)
                return cron.get_next(datetime).isoformat()
            except Exception:
                return None

        return None

    def reconcile_orphaned_executions(self) -> int:
        """启动时把残留的 running 记录/任务标记为 failed。幂等。

        Returns:
            修复的记录/任务数量。
        """
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo

        repaired = 0
        now_iso = dt.now(ZoneInfo("Asia/Shanghai")).isoformat()
        failure_msg = "服务重启，任务中断"

        # 修复残留的 running 记录
        for rec in self._records:
            if rec.status == "running":
                rec.status = "failed"
                if not rec.finished_at:
                    rec.finished_at = now_iso
                if rec.message:
                    rec.message = rec.message + " " + failure_msg
                else:
                    rec.message = failure_msg
                repaired += 1

        # 修复残留的 running 任务状态
        for task in self._tasks:
            if task.last_status == "running":
                task.last_status = "failed"
                task.last_error = failure_msg
                repaired += 1

        if repaired > 0:
            self._persist_records()
            self._persist_tasks()
            log.print_log(
                f"[定时任务] 启动一致性修复: {repaired} 条 running 记录/任务标记为 failed",
                "warning",
            )

        return repaired

    @staticmethod
    def _validate_schedule(task: ScheduledTask) -> None:
        if task.schedule_type == "fixed_time" and not task.time_of_day:
            raise ValueError("固定时间模式必须指定触发时间")
        if task.schedule_type == "cron":
            if not task.cron_expression:
                raise ValueError("Cron 模式必须提供 cron 表达式")
            try:
                from croniter import croniter
                croniter(task.cron_expression)
            except Exception as e:
                raise ValueError(f"Cron 表达式无效: {e}") from e
