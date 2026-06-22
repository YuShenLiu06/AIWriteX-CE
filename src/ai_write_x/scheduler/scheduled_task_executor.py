"""定时任务执行器 - 复用现有生成链路"""

from __future__ import annotations

import threading
from typing import Optional

from src.ai_write_x.utils import log

from .scheduled_task_models import ScheduledTask, ScheduledTaskExecutionRecord
from .scheduled_task_service import ScheduledTaskService


class ScheduledTaskExecutor:
    """执行一次定时任务，复用 crew_main.ai_write_x_main"""

    def __init__(self, service: ScheduledTaskService) -> None:
        self._service = service
        self._generation_running = False
        self._generation_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._generation_running

    def acquire_execution(self) -> bool:
        """尝试获取执行权，成功返回 True"""
        acquired = self._generation_lock.acquire(blocking=False)
        if acquired:
            self._generation_running = True
        return acquired

    def release_execution(self) -> None:
        """释放执行权"""
        self._generation_running = False
        try:
            self._generation_lock.release()
        except RuntimeError:
            pass

    def execute_task(self, task: ScheduledTask) -> ScheduledTaskExecutionRecord:
        """同步执行任务，调用现有生成链路"""
        record = ScheduledTaskExecutionRecord(
            task_id=task.task_id,
            status="running",
            retry_attempt=task.current_retry_count,
        )

        self._service.update_task_status(task.task_id, "running")
        self._service.add_record(record)
        log.print_log(f"[定时任务] 开始执行: {task.name} ({task.task_id})", "info")

        try:
            config_data = self._build_config_data(task)
            self._run_generation(config_data)

            record.status = "success"
            record.message = "任务执行完成"
            self._service.update_task_status(task.task_id, "success")
            task.current_retry_count = 0

            log.print_log(f"[定时任务] 执行成功: {task.name}", "info")

        except Exception as e:
            error_msg = str(e)
            record.status = "failed"
            record.message = error_msg

            should_retry = task.current_retry_count < task.max_retries
            if should_retry:
                task.current_retry_count += 1
                self._service.update_task_status(
                    task.task_id, "retrying", error_msg
                )
                record.status = "retrying"
            else:
                self._service.update_task_status(
                    task.task_id, "failed", error_msg
                )
                task.current_retry_count = 0

            log.print_log(
                f"[定时任务] 执行失败: {task.name} - {error_msg}", "error"
            )

        finally:
            record.finished_at = (
                __import__("datetime").datetime.now(
                    __import__("zoneinfo").ZoneInfo("Asia/Shanghai")
                ).isoformat()
            )
            update_data = record.to_dict()
            update_data.pop("record_id", None)
            self._service.update_record(record.record_id, **update_data)
            self._service._persist_tasks()

        return record

    @staticmethod
    def _build_config_data(task: ScheduledTask) -> dict:
        """将任务定义转为 generate.py 可消费的 config_data"""
        from src.ai_write_x.utils import utils

        # 解析参考URL:按 | 分割后过滤无效URL
        urls = []
        if task.reference_urls:
            raw_urls = task.reference_urls.split("|")
            urls = [u.strip() for u in raw_urls if u.strip() and utils.is_valid_url(u.strip())]

        # 参考比例:整数转百分比(0-100 -> 0.0-1.0)
        ratio = float(task.reference_ratio or 0) / 100.0

        return {
            "custom_topic": task.topic.strip(),
            "urls": urls,
            "reference_ratio": ratio,
            "custom_template_category": task.template_category or "",
            "custom_template": task.template_name or "",
            "platform": task.platform or "",
        }

    @staticmethod
    def _run_generation(config_data: dict) -> None:
        """调用现有生成链路（同步阻塞）"""
        from src.ai_write_x.crew_main import ai_write_x_main

        result = ai_write_x_main(config_data)
        if not result or not result[0] or not result[1]:
            raise RuntimeError("生成任务启动失败")

        process = result[0]
        process.start()
        process.join(timeout=600)

        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            raise RuntimeError("生成任务执行超时")

        exit_code = process.exitcode
        if exit_code != 0:
            raise RuntimeError(f"生成任务异常退出 (exitcode={exit_code})")
