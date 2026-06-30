"""Tests for AIWriteX CLI tasks commands.

Mocked HTTP — no real server needed. CLI package is added to sys.path so the
test runs regardless of whether aiwritex_cli is installed in the environment.
"""

from pathlib import Path
import sys

# Make `aiwritex_cli` importable without installing it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "client"))

from unittest.mock import patch  # noqa: E402

from typer.testing import CliRunner  # noqa: E402

from aiwritex_cli.commands.tasks import app  # noqa: E402

runner = CliRunner()


def test_list_reads_task_id() -> None:
    """list 命令应读取 task_id 而非 id。"""
    payload = {
        "data": {
            "tasks": [
                {
                    "task_id": "task_abc",
                    "name": "T",
                    "topic": "x",
                    "schedule_type": "fixed_time",
                    "enabled": True,
                }
            ]
        }
    }
    with patch("aiwritex_cli.commands.tasks.AIWriteXClient") as MockClient:
        MockClient.return_value.get_json.return_value = payload
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "task_abc" in result.stdout


def test_records_reads_correct_fields() -> None:
    """records 命令应读取真实字段（status/published/message）。"""
    payload = {
        "data": {
            "records": [
                {
                    "started_at": "2026-06-30T14:00:00+08:00",
                    "finished_at": "2026-06-30T14:05:00+08:00",
                    "status": "failed",
                    "published": False,
                    "retry_attempt": 1,
                    "message": "API down",
                    "article_path": None,
                }
            ]
        }
    }
    with patch("aiwritex_cli.commands.tasks.AIWriteXClient") as MockClient:
        MockClient.return_value.get_json.return_value = payload
        result = runner.invoke(app, ["records", "task_abc"])
    assert result.exit_code == 0
    assert "失败" in result.stdout
    assert "未发布" in result.stdout
    assert "API down" in result.stdout


def test_records_success_published() -> None:
    """status=success 且 published=True 应显示 成功/已发布。"""
    payload = {
        "data": {
            "records": [
                {
                    "started_at": "2026-06-30T14:00:00+08:00",
                    "finished_at": "2026-06-30T14:05:00+08:00",
                    "status": "success",
                    "published": True,
                    "retry_attempt": 0,
                    "message": "ok",
                    "article_path": "/output/a.html",
                }
            ]
        }
    }
    with patch("aiwritex_cli.commands.tasks.AIWriteXClient") as MockClient:
        MockClient.return_value.get_json.return_value = payload
        result = runner.invoke(app, ["records", "task_abc"])
    assert result.exit_code == 0
    assert "成功" in result.stdout
    assert "已发布" in result.stdout


def test_status_command() -> None:
    """status 命令应渲染调度器运行时状态。"""
    payload = {
        "data": {
            "scheduler_status": "running",
            "is_running": False,
            "pending_tasks": 3,
            "next_run_at": "2026-07-01T09:00:00+08:00",
            "next_task_name": "早报",
        }
    }
    with patch("aiwritex_cli.commands.tasks.AIWriteXClient") as MockClient:
        MockClient.return_value.get_json.return_value = payload
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "运行中" in result.stdout
    assert "3" in result.stdout
