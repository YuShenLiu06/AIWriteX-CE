"""定时任务执行器 - 复用现有生成链路"""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Dict, Optional

from src.ai_write_x.utils import log as _log

from .scheduled_task_models import ScheduledTask, ScheduledTaskExecutionRecord
from .scheduled_task_service import ScheduledTaskService


# 执行超时与轮询常量
DEADLINE = 600.0
DRAIN_POLL = 0.1


def _terminate_and_join(process) -> None:
    """终止进程并等待其退出。

    先尝试 terminate(优雅退出),10s 后若仍存活则强制 kill。
    """
    try:
        process.terminate()
    except Exception:
        pass
    process.join(timeout=10)
    if process.is_alive():
        try:
            process.kill()
        except Exception:
            pass
        process.join(timeout=5)


def _summarize_from_internal(result_dict: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """从子进程回传的 result dict 提取发布摘要。

    Args:
        result_dict: 子进程 internal 消息中的 result 字段,
                    包含 save_result 与 publish_result。

    Returns:
        {"published": bool, "message": str, "article_path": Optional[str]}
    """
    if not result_dict:
        return {
            "published": False,
            "message": "未发布(子进程未回传生成结果)",
            "article_path": None,
        }

    save_result = result_dict.get("save_result") or {}
    publish_result = result_dict.get("publish_result")
    article_path = save_result.get("path")

    if publish_result is None:
        return {
            "published": False,
            "message": "未发布(任务级 auto_publish=False 或凭据无效,已跳过发布)",
            "article_path": article_path,
        }
    if publish_result.get("success"):
        return {
            "published": True,
            "message": publish_result.get("message") or "发布成功",
            "article_path": article_path,
        }
    return {
        "published": False,
        "message": publish_result.get("message") or "发布失败",
        "article_path": article_path,
    }


def _drain_generation_result(log_queue) -> Dict[str, Any]:
    """排空子进程日志队列,提取生成结果摘要(兼容旧接口)。

    旧实现已抽取为 _summarize_from_internal,本函数保留为薄包装器。
    """
    result_dict: Optional[Dict[str, Any]] = None

    try:
        while True:
            msg = log_queue.get_nowait()
            if (
                isinstance(msg, dict)
                and msg.get("type") == "internal"
                and isinstance(msg.get("result"), dict)
            ):
                result_dict = msg["result"]
    except queue.Empty:
        pass

    return _summarize_from_internal(result_dict)


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
        _log.print_log(f"[定时任务] 开始执行: {task.name} ({task.task_id})", "info")

        try:
            config_data = self._build_config_data(task)
            gen_summary = self._run_generation(config_data)

            record.status = "success"
            record.published = bool(gen_summary.get("published", False))
            record.article_path = gen_summary.get("article_path")
            record.message = gen_summary.get("message") or "任务执行完成"
            self._service.update_task_status(task.task_id, "success")
            task.current_retry_count = 0

            _log.print_log(
                f"[定时任务] 执行成功: {task.name}(published={record.published})",
                "info",
            )

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

            _log.print_log(
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
            # 任务级发布开关:子进程内覆盖 config.auto_publish(任务级独占语义)
            "auto_publish": task.auto_publish,
        }

    @staticmethod
    def _run_generation(config_data: dict) -> dict:
        """调用现有生成链路(同步阻塞),返回生成结果摘要。

        使用并发排空循环避免死锁:一边等待进程退出,一边持续排空日志队列。
        子进程异常退出时 crew_main 会以 exitcode=1 退出(不再被 os._exit(0) 吞掉),
        本方法据此抛错,由 execute_task 记为失败;成功则排空日志队列,解析发布结果。
        """
        from src.ai_write_x.crew_main import ai_write_x_main

        result = ai_write_x_main(config_data)
        if not result or not result[0] or not result[1]:
            raise RuntimeError("生成任务启动失败")

        process, log_queue = result[0], result[1]
        process.start()

        deadline = time.monotonic() + DEADLINE
        captured_internal: Optional[Dict[str, Any]] = None

        # 并发排空循环:持续排空队列,同时监控进程退出与超时
        while True:
            # 每次轮询尽可能排空队列,避免堆积
            while True:
                try:
                    msg = log_queue.get_nowait()

                    # 捕获首个 internal 结果消息(任务完成/失败标记)
                    if (
                        isinstance(msg, dict)
                        and msg.get("type") == "internal"
                        and ("任务执行完成" in msg.get("message", "") or "任务执行失败" in msg.get("message", ""))
                    ):
                        if captured_internal is None:
                            captured_internal = msg

                    # 尝试写入文件日志(静默失败)
                    fh = _log.LogManager.get_instance().get_file_handler()
                    if fh:
                        try:
                            fh.write_log(msg)
                        except Exception:
                            pass
                except queue.Empty:
                    break

            # 进程已退出,退出循环(随后再做最后一次排空以捕获内部消息)
            if not process.is_alive():
                break

            # 超时检查
            if time.monotonic() >= deadline:
                _terminate_and_join(process)
                raise RuntimeError(f"生成任务执行超时 (>{int(DEADLINE)}s)")

            time.sleep(DRAIN_POLL)

        # 进程退出后的最后一次排空,捕获可能的内部结果消息
        while True:
            try:
                msg = log_queue.get_nowait()
                if (
                    isinstance(msg, dict)
                    and msg.get("type") == "internal"
                    and ("任务执行完成" in msg.get("message", "") or "任务执行失败" in msg.get("message", ""))
                ):
                    if captured_internal is None:
                        captured_internal = msg

                # 继续尝试写入文件日志
                fh = _log.LogManager.get_instance().get_file_handler()
                if fh:
                    try:
                        fh.write_log(msg)
                    except Exception:
                        pass
            except queue.Empty:
                break

        exit_code = process.exitcode

        # 异常退出(含子进程内 os._exit(1) 或未捕获异常)
        if exit_code != 0:
            if captured_internal and captured_internal.get("error"):
                raise RuntimeError(
                    f"生成任务异常退出 (exitcode={exit_code}): {captured_internal['error']}"
                )
            raise RuntimeError(f"生成任务异常退出 (exitcode={exit_code})")

        # 退出码为 0,但未回传结果 或回传的是失败标记
        if exit_code == 0 and (
            not captured_internal or "任务执行失败" in captured_internal.get("message", "")
        ):
            raise RuntimeError(
                (captured_internal or {}).get("error") or "生成任务执行失败(子进程未回传结果)"
            )

        # 成功:回传了 "任务执行完成" 的 internal 消息,且有 result 字段
        return _summarize_from_internal((captured_internal or {}).get("result"))
