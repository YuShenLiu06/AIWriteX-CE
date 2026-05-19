"""APScheduler 调度器封装"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from zoneinfo import ZoneInfo

from src.ai_write_x.utils import log

if TYPE_CHECKING:
    from .scheduled_task_executor import ScheduledTaskExecutor
    from .scheduled_task_models import ScheduledTask
    from .scheduled_task_service import ScheduledTaskService


class ScheduledTaskScheduler:
    """调度器启动、恢复注册、关闭清理"""

    def __init__(
        self,
        service: ScheduledTaskService,
        executor: ScheduledTaskExecutor,
    ) -> None:
        self._service = service
        self._executor = executor
        self._scheduler = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """启动调度器并恢复已启用任务"""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            self._scheduler = BackgroundScheduler(
                timezone="Asia/Shanghai",
                job_defaults={"coalesce": True, "max_instances": 1},
            )

            tasks = self._service.list_tasks()
            registered = 0
            for task in tasks:
                if task.enabled:
                    self._register_task(task)
                    registered += 1

            self._scheduler.start()
            self._running = True
            log.print_log(
                f"[调度器] 已启动，恢复注册 {registered} 个任务", "info"
            )

        except Exception as e:
            log.print_log(f"[调度器] 启动失败: {e}", "error")

    def stop(self) -> None:
        """安全关闭调度器"""
        if self._scheduler and self._running:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception as e:
                log.print_log(f"[调度器] 关闭异常: {e}", "warning")
            self._running = False
            log.print_log("[调度器] 已停止", "info")

    def register_task(self, task: ScheduledTask) -> None:
        """注册单个任务到调度器"""
        if not self._scheduler or not self._running:
            return
        self._unregister_task(task.task_id)
        if task.enabled:
            self._register_task(task)

    def unregister_task(self, task_id: str) -> None:
        """从调度器移除任务"""
        self._unregister_task(task_id)

    def refresh_task(self, task: ScheduledTask) -> None:
        """刷新任务调度（更新时调用）"""
        self.register_task(task)

    def get_runtime_status(self) -> dict:
        """返回调度器运行时状态"""
        next_run = None
        next_task_name = ""
        enabled_count = 0

        tasks = self._service.list_tasks()
        for task in tasks:
            if task.enabled:
                enabled_count += 1
                if task.next_run_at:
                    if next_run is None or task.next_run_at < next_run:
                        next_run = task.next_run_at
                        next_task_name = task.name

        return {
            "scheduler_status": "running" if self._running else "stopped",
            "is_running": self._executor.is_running,
            "current_task_id": "",
            "current_task_name": "",
            "next_run_at": next_run,
            "next_task_name": next_task_name,
            "pending_tasks": enabled_count,
            "updated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        }

    def _register_task(self, task: ScheduledTask) -> None:
        """内部注册实现"""
        job_id = f"scheduled_task_{task.task_id}"

        try:
            if task.schedule_type == "fixed_time" and task.time_of_day:
                parts = task.time_of_day.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0

                self._scheduler.add_job(
                    self._trigger_task,
                    "cron",
                    hour=hour,
                    minute=minute,
                    id=job_id,
                    replace_existing=True,
                    args=[task.task_id],
                )

            elif task.schedule_type == "cron" and task.cron_expression:
                self._scheduler.add_job(
                    self._trigger_task,
                    "cron",
                    **self._parse_cron(task.cron_expression),
                    id=job_id,
                    replace_existing=True,
                    args=[task.task_id],
                )

            task.next_run_at = self._service.calculate_next_run(task)
            log.print_log(
                f"[调度器] 注册任务: {task.name} (job_id={job_id})", "info"
            )

        except Exception as e:
            log.print_log(
                f"[调度器] 注册任务失败: {task.name} - {e}", "error"
            )

    def _unregister_task(self, task_id: str) -> None:
        """内部移除实现"""
        if not self._scheduler:
            return
        job_id = f"scheduled_task_{task_id}"
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

    def _trigger_task(self, task_id: str) -> None:
        """调度器触发回调"""
        task = self._service.get_task(task_id)
        if not task or not task.enabled:
            return

        if self._executor.is_running:
            from .scheduled_task_models import ScheduledTaskExecutionRecord

            record = ScheduledTaskExecutionRecord(
                task_id=task_id,
                status="skipped",
                message="当前已有任务运行，本次触发跳过",
            )
            self._service.add_record(record)
            self._service.update_task_status(task_id, "skipped", "互斥跳过")
            log.print_log(
                f"[调度器] 任务 {task.name} 因互斥被跳过", "warning"
            )
            return

        if self._executor.acquire_execution():
            try:
                self._executor.execute_task(task)
            finally:
                self._executor.release_execution()
        else:
            log.print_log(
                f"[调度器] 任务 {task.name} 获取执行锁失败，跳过", "warning"
            )

    @staticmethod
    def _parse_cron(expression: str) -> dict:
        """将标准 cron 表达式解析为 APScheduler cron 参数"""
        parts = expression.strip().split()
        result = {}
        if len(parts) >= 1:
            result["minute"] = parts[0]
        if len(parts) >= 2:
            result["hour"] = parts[1]
        if len(parts) >= 3:
            result["day"] = parts[2]
        if len(parts) >= 4:
            result["month"] = parts[3]
        if len(parts) >= 5:
            result["day_of_week"] = parts[4]
        return result
