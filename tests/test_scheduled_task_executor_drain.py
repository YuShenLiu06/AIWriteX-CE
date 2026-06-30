# -*- coding: UTF-8 -*-
"""
定时任务执行器并发排空逻辑测试。

测试 scheduled_task_executor._run_generation 在各种子进程行为下的正确性:
- 成功+发布 → 返回 published=True
- 成功但未发布 → 返回 published=False,消息含未发布
- 子进程异常退出(exitcode=1) → 抛出 RuntimeError
- 超时 → 终止进程并抛出超时异常
- 最终排空捕获延迟到达的 internal 消息
"""

import queue
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


class FakeProcess:
    """进程替身:按脚本驱动 is_alive/exitcode,记录 terminate/kill 调用。"""

    def __init__(self, script):
        """
        Args:
            script: [("alive", True/False), ("exit", int)] 序列。
                    每次 is_alive() 消费一项,返回该项的值。
                    exitcode 从 "exit" 项获取。
        """
        self._script = list(script)
        self._terminated = False
        self._killed = False
        self.exitcode = None

    def is_alive(self):
        if not self._script:
            return False
        typ, val = self._script.pop(0)
        if typ == "alive":
            return val
        if typ == "exit":
            self.exitcode = val
        return False

    def start(self):
        pass

    def terminate(self):
        self._terminated = True

    def kill(self):
        self._killed = True

    def join(self, timeout=None):
        pass


class FakeQueue:
    """队列替身:预置消息列表,get_nowait 弹出。"""

    def __init__(self, messages, final_straggler=None):
        """
        Args:
            messages: 预置消息列表(按放入顺序)。
            final_straggler: 队列耗尽前最后插入的一条消息(模拟延迟到达)。
        """
        self._msgs = list(messages)
        self._final_straggler = final_straggler
        self._emptied = False

    def get_nowait(self):
        if not self._msgs:
            if self._final_straggler and not self._emptied:
                self._msgs.append(self._final_straggler)
                self._emptied = True
            else:
                raise queue.Empty
        return self._msgs.pop(0)


def test_run_generation_success_with_publish(monkeypatch):
    """成功+发布 → published=True,article_path 存在。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import (
        DEADLINE,
        ScheduledTaskExecutor,
    )

    # 快速超时(避免真实等待)
    monkeypatch.setattr(
        "src.ai_write_x.scheduler.scheduled_task_executor.DEADLINE", 10.0
    )

    q = FakeQueue(
        [
            {"type": "log", "message": "开始生成"},
            {
                "type": "internal",
                "message": "任务执行完成",
                "result": {
                    "publish_result": {"success": True, "message": "发布成功"},
                    "save_result": {"path": "/app/output/a.html"},
                },
            },
        ]
    )
    p = FakeProcess([("alive", True), ("alive", True), ("exit", 0)])

    monkeypatch.setattr(
        "src.ai_write_x.crew_main.ai_write_x_main",
        staticmethod(lambda cfg: (p, q)),
    )

    # Act
    result = ScheduledTaskExecutor._run_generation({})

    # Assert
    assert result["published"] is True
    assert result["article_path"] == "/app/output/a.html"
    assert "发布成功" in result["message"]


def test_run_generation_success_without_publish(monkeypatch):
    """成功但 publish_result=None → published=False,消息标注未发布。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor

    q = FakeQueue(
        [
            {
                "type": "internal",
                "message": "任务执行完成",
                "result": {
                    "publish_result": None,
                    "save_result": {"path": "/app/output/b.html"},
                },
            }
        ]
    )
    p = FakeProcess([("exit", 0)])

    monkeypatch.setattr(
        "src.ai_write_x.crew_main.ai_write_x_main",
        staticmethod(lambda cfg: (p, q)),
    )

    # Act
    result = ScheduledTaskExecutor._run_generation({})

    # Assert
    assert result["published"] is False
    assert "未发布" in result["message"]
    assert result["article_path"] == "/app/output/b.html"


def test_run_generation_exitcode_nonzero_with_internal_error(monkeypatch):
    """exitcode=1 且 internal 消息带 error → RuntimeError 包含该错误。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor

    q = FakeQueue(
        [
            {
                "type": "internal",
                "message": "任务执行失败",
                "error": "API key 无效",
            }
        ]
    )
    p = FakeProcess([("exit", 1)])

    monkeypatch.setattr(
        "src.ai_write_x.crew_main.ai_write_x_main",
        staticmethod(lambda cfg: (p, q)),
    )

    # Act/Assert
    try:
        ScheduledTaskExecutor._run_generation({})
        assert False, "应抛出 RuntimeError"
    except RuntimeError as e:
        assert "exitcode=1" in str(e)
        assert "API key 无效" in str(e)


def test_run_generation_exitcode_nonzero_without_internal(monkeypatch):
    """exitcode=1 但无 internal 消息 → RuntimeError 仅含退出码。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor

    q = FakeQueue([])
    p = FakeProcess([("exit", 1)])

    monkeypatch.setattr(
        "src.ai_write_x.crew_main.ai_write_x_main",
        staticmethod(lambda cfg: (p, q)),
    )

    # Act/Assert
    try:
        ScheduledTaskExecutor._run_generation({})
        assert False, "应抛出 RuntimeError"
    except RuntimeError as e:
        assert "exitcode=1" in str(e)


def test_run_generation_exitcode_zero_no_internal_result(monkeypatch):
    """exitcode=0 但未回传 internal 结果 → RuntimeError。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor

    q = FakeQueue([])
    p = FakeProcess([("exit", 0)])

    monkeypatch.setattr(
        "src.ai_write_x.crew_main.ai_write_x_main",
        staticmethod(lambda cfg: (p, q)),
    )

    # Act/Assert
    try:
        ScheduledTaskExecutor._run_generation({})
        assert False, "应抛出 RuntimeError"
    except RuntimeError as e:
        assert "未回传结果" in str(e)


def test_run_generation_timeout_terminates_process(monkeypatch):
    """超时 → 终止进程并抛出超时异常。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import (
        DEADLINE,
        ScheduledTaskExecutor,
    )

    # 设置极短超时
    monkeypatch.setattr(
        "src.ai_write_x.scheduler.scheduled_task_executor.DEADLINE", 0.05
    )

    q = FakeQueue([])
    # 进程持续存活,触发超时
    p = FakeProcess([("alive", True)] * 100 + [("exit", 0)])

    monkeypatch.setattr(
        "src.ai_write_x.crew_main.ai_write_x_main",
        staticmethod(lambda cfg: (p, q)),
    )

    # Act/Assert
    try:
        ScheduledTaskExecutor._run_generation({})
        assert False, "应抛出超时 RuntimeError"
    except RuntimeError as e:
        assert "超时" in str(e)
        assert p._terminated  # 应调用过 terminate


def test_run_generation_final_straggler_drain(monkeypatch):
    """进程退出后,最终排空捕获延迟到达的 internal 消息。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor

    # 进程立即退出,但 internal 消息延迟到达(通过 final_straggler)
    q = FakeQueue(
        [],  # 初始无消息
        final_straggler={
            "type": "internal",
            "message": "任务执行完成",
            "result": {
                "publish_result": {"success": True, "message": "发布成功"},
                "save_result": {"path": "/app/output/straggler.html"},
            },
        },
    )
    p = FakeProcess([("exit", 0)])

    monkeypatch.setattr(
        "src.ai_write_x.crew_main.ai_write_x_main",
        staticmethod(lambda cfg: (p, q)),
    )

    # Act
    result = ScheduledTaskExecutor._run_generation({})

    # Assert
    assert result["published"] is True
    assert result["article_path"] == "/app/output/straggler.html"


def test_summarize_from_internal_none_result():
    """result_dict 为 None → 返回默认未发布消息。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import (
        _summarize_from_internal,
    )

    result = _summarize_from_internal(None)

    assert result["published"] is False
    assert "未发布(子进程未回传生成结果)" == result["message"]
    assert result["article_path"] is None


def test_summarize_from_internal_publish_success():
    """publish_result.success=True → published=True。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import (
        _summarize_from_internal,
    )

    result = _summarize_from_internal(
        {
            "publish_result": {"success": True, "message": "发布成功"},
            "save_result": {"path": "/x.html"},
        }
    )

    assert result["published"] is True
    assert result["message"] == "发布成功"
    assert result["article_path"] == "/x.html"


def test_summarize_from_internal_publish_soft_failure():
    """publish_result.success=False → published=False,消息透传。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import (
        _summarize_from_internal,
    )

    result = _summarize_from_internal(
        {
            "publish_result": {"success": False, "message": "api 失败"},
            "save_result": {"path": "/y.html"},
        }
    )

    assert result["published"] is False
    assert "api 失败" in result["message"]


def test_summarize_from_internal_publish_none():
    """publish_result=None → published=False,消息标注未发布。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import (
        _summarize_from_internal,
    )

    result = _summarize_from_internal(
        {"publish_result": None, "save_result": {"path": "/z.html"}}
    )

    assert result["published"] is False
    assert "未发布" in result["message"]
    assert result["article_path"] == "/z.html"
