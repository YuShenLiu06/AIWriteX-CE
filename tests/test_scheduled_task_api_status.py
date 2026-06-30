# -*- coding: UTF-8 -*-
"""
定时任务 API 端到端测试:任务执行后记录状态正确更新。

覆盖:
- POST /api/scheduled-tasks 创建任务
- POST /{id}/run-now 立即执行
- GET /{id}/records 获取执行记录
- 验证执行记录的 status / finished_at / published / message / article_path

关键断言:执行完成后 status != "running",finished_at 非空(防止回归)。
"""

import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# 鉴权与配置目录均在每个用例内通过 monkeypatch.setenv 局部设置,
# 避免 module-level os.environ 副作用污染其他测试(如 test_auth_sessions / test_ws_generate_logs_auth)。

from fastapi.testclient import TestClient

from src.ai_write_x.web.app import app
from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor


def test_run_now_creates_success_record_with_finished_at(tmp_path, monkeypatch):
    """立即执行成功 → 记录 status=success,finished_at 非空。"""
    monkeypatch.setenv("AIWRITEX_CONFIG_DIR", str(tmp_path))
    # 局部关闭鉴权:lifespan 会按当前环境重新 load_auth_config,
    # 用 monkeypatch 确保仅本用例生效,用例结束自动还原。
    monkeypatch.setenv("AIWRITEX_AUTH_ENABLED", "false")

    # Arrange:mock _run_generation 返回成功结果
    monkeypatch.setattr(
        ScheduledTaskExecutor,
        "_run_generation",
        staticmethod(
            lambda cfg: {
                "published": False,
                "message": "发布失败：微信凭据未配置",
                "article_path": "/app/output/test.html",
            }
        ),
    )

    with TestClient(app) as client:
        # 创建任务
        resp = client.post(
            "/api/scheduled-tasks",
            json={
                "name": "Test Task",
                "topic": "Test Topic",
                "schedule_type": "fixed_time",
                "time_of_day": "00:00",
                "enabled": False,  # 禁用调度,仅测试立即执行
                "auto_publish": True,
                "max_retries": 3,
            },
        )
        assert resp.status_code == 200
        task_id = resp.json()["data"]["task"]["task_id"]

        # 立即执行
        resp = client.post(f"/api/scheduled-tasks/{task_id}/run-now")
        assert resp.status_code == 200

        # 轮询直到执行完成
        deadline = time.time() + 15
        while time.time() < deadline:
            resp = client.get(f"/api/scheduled-tasks/{task_id}/records")
            assert resp.status_code == 200
            records = resp.json()["data"]["records"]
            if records and records[0].get("finished_at"):
                break
            time.sleep(0.2)
        else:
            assert False, "执行未在 15 秒内完成"

        # 验证最新记录
        newest = records[0]
        # CRITICAL:status 不能是 running,finished_at 必须非空
        assert newest["status"] != "running", "记录应已完成,不应卡在 running"
        assert newest["finished_at"] is not None, "finished_at 必须非空"
        assert newest["status"] == "success"
        assert newest["published"] is False
        assert "发布失败" in newest["message"]
        assert newest["article_path"] == "/app/output/test.html"

        # 验证所有预期字段存在
        expected_keys = {
            "record_id",
            "task_id",
            "started_at",
            "finished_at",
            "status",
            "retry_attempt",
            "message",
            "article_path",
            "published",
        }
        assert set(newest.keys()) == expected_keys


def test_run_now_with_max_retries_zero_creates_failed_record(tmp_path, monkeypatch):
    """max_retries=0 且 _run_generation 抛异常 → 记录 status=failed。"""
    monkeypatch.setenv("AIWRITEX_CONFIG_DIR", str(tmp_path))
    # 局部关闭鉴权:lifespan 会按当前环境重新 load_auth_config,
    # 用 monkeypatch 确保仅本用例生效,用例结束自动还原。
    monkeypatch.setenv("AIWRITEX_AUTH_ENABLED", "false")

    # Arrange:mock _run_generation 抛异常
    monkeypatch.setattr(
        ScheduledTaskExecutor,
        "_run_generation",
        staticmethod(lambda cfg: (_ for _ in ()).throw(RuntimeError("API down"))),
    )

    with TestClient(app) as client:
        # 创建任务(max_retries=0)
        resp = client.post(
            "/api/scheduled-tasks",
            json={
                "name": "Failing Task",
                "topic": "Test Topic",
                "schedule_type": "fixed_time",
                "time_of_day": "00:00",
                "enabled": False,
                "auto_publish": False,
                "max_retries": 0,
            },
        )
        assert resp.status_code == 200
        task_id = resp.json()["data"]["task"]["task_id"]

        # 立即执行
        resp = client.post(f"/api/scheduled-tasks/{task_id}/run-now")
        assert resp.status_code == 200

        # 轮询直到执行完成
        deadline = time.time() + 15
        while time.time() < deadline:
            resp = client.get(f"/api/scheduled-tasks/{task_id}/records")
            assert resp.status_code == 200
            records = resp.json()["data"]["records"]
            if records and records[0].get("finished_at"):
                break
            time.sleep(0.2)
        else:
            assert False, "执行未在 15 秒内完成"

        # 验证最新记录
        newest = records[0]
        assert newest["status"] != "running"
        assert newest["finished_at"] is not None
        assert newest["status"] == "failed"
        assert "API down" in newest["message"]
