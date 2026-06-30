# -*- coding: UTF-8 -*-
"""
定时任务启动一致性修复测试。

测试 ScheduledTaskService.reconcile_orphaned_executions:
- 将残留的 running 记录标记为 failed,追加服务重启消息
- 将残留的 running 任务状态标记为 failed
- 幂等性:多次调用不重复计数
- 持久化:修复后重启服务仍保持 failed 状态
"""

import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def test_reconcile_running_records_and_tasks(tmp_path, monkeypatch):
    """修复残留的 running 记录和任务,持久化后重启仍保持 failed。"""
    monkeypatch.setenv("AIWRITEX_CONFIG_DIR", str(tmp_path))

    from src.ai_write_x.scheduler.scheduled_task_models import (
        ScheduledTask,
        ScheduledTaskExecutionRecord,
    )
    from src.ai_write_x.scheduler.scheduled_task_repository import (
        ScheduledTaskRepository,
    )
    from src.ai_write_x.scheduler.scheduled_task_service import (
        ScheduledTaskService,
    )

    # Arrange:创建含 running 状态的任务与记录
    repo = ScheduledTaskRepository()
    service = ScheduledTaskService(repo)

    task = ScheduledTask(
        task_id="t1", name="Test Task", topic="Topic", enabled=True
    )
    task.last_status = "running"
    task.last_run_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    service._tasks.append(task)
    service._persist_tasks()

    record = ScheduledTaskExecutionRecord(
        task_id="t1", status="running", retry_attempt=0
    )
    service._records.append(record)
    service._persist_records()

    # Act:执行修复
    repaired = service.reconcile_orphaned_executions()

    # Assert:修复了 2 条(1 任务 + 1 记录)
    assert repaired == 2
    assert task.last_status == "failed"
    assert "服务重启" in task.last_error
    assert record.status == "failed"
    assert record.finished_at is not None
    assert "服务重启" in record.message

    # 验证持久化:重新创建服务实例,状态仍为 failed
    service2 = ScheduledTaskService(ScheduledTaskRepository())
    reloaded_task = service2.get_task("t1")
    reloaded_records = service2.get_records("t1")

    assert reloaded_task.last_status == "failed"
    assert any(r.status == "failed" for r in reloaded_records)


def test_reconcile_idempotent(tmp_path, monkeypatch):
    """幂等性:对已修复的状态再次调用,不增加计数。"""
    monkeypatch.setenv("AIWRITEX_CONFIG_DIR", str(tmp_path))

    from src.ai_write_x.scheduler.scheduled_task_models import (
        ScheduledTask,
        ScheduledTaskExecutionRecord,
    )
    from src.ai_write_x.scheduler.scheduled_task_repository import (
        ScheduledTaskRepository,
    )
    from src.ai_write_x.scheduler.scheduled_task_service import (
        ScheduledTaskService,
    )

    # Arrange
    repo = ScheduledTaskRepository()
    service = ScheduledTaskService(repo)

    task = ScheduledTask(
        task_id="t2", name="Task", topic="T", enabled=True
    )
    task.last_status = "running"
    service._tasks.append(task)

    record = ScheduledTaskExecutionRecord(
        task_id="t2", status="running", retry_attempt=0
    )
    service._records.append(record)

    # Act:第一次修复
    repaired1 = service.reconcile_orphaned_executions()

    # Act:第二次修复(不应再计数)
    repaired2 = service.reconcile_orphaned_executions()

    # Assert
    assert repaired1 == 2
    assert repaired2 == 0
    assert task.last_status == "failed"
    assert record.status == "failed"


def test_reconcile_clean_state_noop(tmp_path, monkeypatch):
    """干净状态(仅 success/failed)→ 不修改任何记录,返回 0。"""
    monkeypatch.setenv("AIWRITEX_CONFIG_DIR", str(tmp_path))

    from src.ai_write_x.scheduler.scheduled_task_models import (
        ScheduledTask,
        ScheduledTaskExecutionRecord,
    )
    from src.ai_write_x.scheduler.scheduled_task_repository import (
        ScheduledTaskRepository,
    )
    from src.ai_write_x.scheduler.scheduled_task_service import (
        ScheduledTaskService,
    )

    # Arrange:任务与记录均为非 running 状态
    repo = ScheduledTaskRepository()
    service = ScheduledTaskService(repo)

    task = ScheduledTask(
        task_id="t3", name="Task", topic="T", enabled=True
    )
    task.last_status = "success"
    service._tasks.append(task)

    record = ScheduledTaskExecutionRecord(
        task_id="t3", status="success", retry_attempt=0
    )
    service._records.append(record)

    # Act
    repaired = service.reconcile_orphaned_executions()

    # Assert
    assert repaired == 0
    assert task.last_status == "success"
    assert record.status == "success"


def test_reconcile_record_with_existing_message(tmp_path, monkeypatch):
    """已有 message 的记录在修复时追加而非覆盖。"""
    monkeypatch.setenv("AIWRITEX_CONFIG_DIR", str(tmp_path))

    from src.ai_write_x.scheduler.scheduled_task_models import (
        ScheduledTaskExecutionRecord,
    )
    from src.ai_write_x.scheduler.scheduled_task_repository import (
        ScheduledTaskRepository,
    )
    from src.ai_write_x.scheduler.scheduled_task_service import (
        ScheduledTaskService,
    )

    # Arrange:记录已有 message
    repo = ScheduledTaskRepository()
    service = ScheduledTaskService(repo)

    record = ScheduledTaskExecutionRecord(
        task_id="t4", status="running", retry_attempt=0, message="原有错误"
    )
    service._records.append(record)

    # Act
    service.reconcile_orphaned_executions()

    # Assert:message 追加而非覆盖
    assert record.status == "failed"
    assert "原有错误" in record.message
    assert "服务重启" in record.message


def test_reconcile_record_without_finished_at_sets_timestamp(tmp_path, monkeypatch):
    """无 finished_at 的记录在修复时补上时间戳。"""
    monkeypatch.setenv("AIWRITEX_CONFIG_DIR", str(tmp_path))

    from src.ai_write_x.scheduler.scheduled_task_models import (
        ScheduledTaskExecutionRecord,
    )
    from src.ai_write_x.scheduler.scheduled_task_repository import (
        ScheduledTaskRepository,
    )
    from src.ai_write_x.scheduler.scheduled_task_service import (
        ScheduledTaskService,
    )

    # Arrange:记录无 finished_at
    repo = ScheduledTaskRepository()
    service = ScheduledTaskService(repo)

    record = ScheduledTaskExecutionRecord(
        task_id="t5", status="running", retry_attempt=0
    )
    assert record.finished_at is None
    service._records.append(record)

    # Act
    service.reconcile_orphaned_executions()

    # Assert:finished_at 被设置
    assert record.status == "failed"
    assert record.finished_at is not None
