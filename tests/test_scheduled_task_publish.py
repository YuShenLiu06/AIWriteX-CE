# -*- coding: UTF-8 -*-
"""
定时任务自动发布修复的回归测试(对应 bug:定时任务完成生成后未自动发布)。

覆盖:
- ScheduledTaskExecutor._build_config_data 透传任务级 auto_publish
- config_data.apply_config_data 父/子进程行为分离(子进程独占覆盖、父进程不污染全局)
- _drain_generation_result 从子进程日志队列解析发布结果(成功 / 未发布 / 软失败)
- execute_task 把发布摘要如实写入执行记录(published / message / article_path)

注意:被测代码使用 Python 3.10+ 语法,本机 3.9 不兼容,需在容器(Python 3.11)内运行。
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# 确保项目根目录在 sys.path 中(与既有测试一致)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# _build_config_data 透传任务级 auto_publish
# ---------------------------------------------------------------------------


def test_build_config_data_carries_auto_publish_true():
    """任务 auto_publish=True 时,config_data 应带上 auto_publish=True。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor
    from src.ai_write_x.scheduler.scheduled_task_models import ScheduledTask

    # Arrange
    task = ScheduledTask(topic="测试话题", auto_publish=True)

    # Act
    data = ScheduledTaskExecutor._build_config_data(task)

    # Assert
    assert data["auto_publish"] is True
    assert data["custom_topic"] == "测试话题"


def test_build_config_data_carries_auto_publish_false_default():
    """未显式开启时,config_data 的 auto_publish 应为 False(任务级独占语义下即不发布)。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor
    from src.ai_write_x.scheduler.scheduled_task_models import ScheduledTask

    # Arrange
    task = ScheduledTask(topic="x")

    # Act
    data = ScheduledTaskExecutor._build_config_data(task)

    # Assert
    assert data["auto_publish"] is False


# ---------------------------------------------------------------------------
# apply_config_data 父/子进程行为分离
# ---------------------------------------------------------------------------


def _stub_config(auto_publish: bool = False) -> SimpleNamespace:
    """轻量 config 替身:仅含可写 .config dict,其余键由 setattr 写入。"""
    return SimpleNamespace(config={"auto_publish": auto_publish})


def test_apply_config_data_subprocess_overrides_auto_publish():
    """子进程(override=True)应把任务级 auto_publish 写入底层 dict,且普通键仍 setattr 生效。"""
    from src.ai_write_x.config_data import apply_config_data

    # Arrange
    cfg = _stub_config(auto_publish=False)

    # Act
    apply_config_data(
        cfg,
        {"auto_publish": True, "custom_topic": "话题"},
        override_auto_publish=True,
    )

    # Assert
    assert cfg.config["auto_publish"] is True
    assert cfg.custom_topic == "话题"


def test_apply_config_data_parent_skips_auto_publish():
    """父进程(override=False)不得改 auto_publish(只读 property + 避免污染全局),普通键仍生效。"""
    from src.ai_write_x.config_data import apply_config_data

    # Arrange
    cfg = _stub_config(auto_publish=False)

    # Act
    apply_config_data(
        cfg,
        {"auto_publish": True, "custom_topic": "话题"},
        override_auto_publish=False,
    )

    # Assert
    assert cfg.config["auto_publish"] is False, "父进程不应被任务级 auto_publish 污染"
    assert cfg.custom_topic == "话题"


def test_apply_config_data_skips_env_file_path():
    """env_file_path 不是配置属性,父子进程都应跳过。"""
    from src.ai_write_x.config_data import apply_config_data

    # Arrange
    cfg = _stub_config()

    # Act
    apply_config_data(
        cfg,
        {"env_file_path": "/tmp/env.json", "custom_topic": "t"},
        override_auto_publish=True,
    )

    # Assert
    assert not hasattr(cfg, "env_file_path")
    assert cfg.custom_topic == "t"


def test_apply_config_data_parent_does_not_mutate_real_singleton():
    """对真实 Config 单例以父进程模式调用,auto_publish 必须保持不变且不抛异常。"""
    from src.ai_write_x.config_data import apply_config_data
    from src.ai_write_x.config.config import Config

    # Arrange
    cfg = Config.get_instance()
    cfg.config = dict(cfg.default_config)  # 确保 auto_publish 键存在
    before = cfg.config["auto_publish"]

    # Act
    apply_config_data(cfg, {"auto_publish": not before}, override_auto_publish=False)

    # Assert
    assert cfg.config["auto_publish"] == before, "全局 auto_publish 不应被父进程改动"


# ---------------------------------------------------------------------------
# _drain_generation_result 解析子进程回传的发布结果
# ---------------------------------------------------------------------------


def test_drain_result_publish_success():
    """publish_result.success=True → published=True,且取到 article_path。"""
    import queue

    from src.ai_write_x.scheduler.scheduled_task_executor import _drain_generation_result

    # Arrange
    q = queue.Queue()
    q.put(
        {
            "type": "internal",
            "result": {
                "publish_result": {"success": True, "message": "发布成功"},
                "save_result": {"path": "/app/output/a.html"},
            },
        }
    )

    # Act
    summary = _drain_generation_result(q)

    # Assert
    assert summary["published"] is True
    assert summary["article_path"] == "/app/output/a.html"


def test_drain_result_not_published_when_publish_result_none():
    """publish_result=None(未满足发布条件)→ published=False,message 标注未发布。"""
    import queue

    from src.ai_write_x.scheduler.scheduled_task_executor import _drain_generation_result

    # Arrange
    q = queue.Queue()
    q.put(
        {
            "type": "internal",
            "result": {"publish_result": None, "save_result": {"path": "/b.html"}},
        }
    )

    # Act
    summary = _drain_generation_result(q)

    # Assert
    assert summary["published"] is False
    assert "未发布" in summary["message"]
    assert summary["article_path"] == "/b.html"


def test_drain_result_publish_soft_failure():
    """publish_result.success=False(发布软失败)→ published=False,message 透传失败原因。"""
    import queue

    from src.ai_write_x.scheduler.scheduled_task_executor import _drain_generation_result

    # Arrange
    q = queue.Queue()
    q.put(
        {
            "type": "internal",
            "result": {
                "publish_result": {"success": False, "message": "api unauthorized"},
                "save_result": {"path": "/c.html"},
            },
        }
    )

    # Act
    summary = _drain_generation_result(q)

    # Assert
    assert summary["published"] is False
    assert "api unauthorized" in summary["message"]


def test_drain_result_empty_queue_is_safe():
    """队列为空(子进程未回传结果)时不抛异常,published=False。"""
    import queue

    from src.ai_write_x.scheduler.scheduled_task_executor import _drain_generation_result

    # Arrange
    q = queue.Queue()

    # Act
    summary = _drain_generation_result(q)

    # Assert
    assert summary["published"] is False


# ---------------------------------------------------------------------------
# execute_task 把发布摘要写入执行记录
# ---------------------------------------------------------------------------


class _StubService:
    """最小 Service 替身,满足 execute_task 的调用面。"""

    def __init__(self):
        self.records = []

    def update_task_status(self, *args, **kwargs):
        pass

    def add_record(self, record):
        self.records.append(record)

    def update_record(self, record_id, **kwargs):
        pass

    def _persist_tasks(self):
        pass


def test_execute_task_records_published_true(monkeypatch):
    """生成+发布成功 → 执行记录 status=success、published=True、article_path 有值。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor
    from src.ai_write_x.scheduler.scheduled_task_models import ScheduledTask

    # Arrange
    executor = ScheduledTaskExecutor(_StubService())
    monkeypatch.setattr(
        ScheduledTaskExecutor,
        "_run_generation",
        staticmethod(
            lambda config_data: {
                "published": True,
                "message": "发布成功",
                "article_path": "/app/output/x.html",
            }
        ),
    )
    task = ScheduledTask(task_id="t1", name="n", topic="话题", auto_publish=True)

    # Act
    record = executor.execute_task(task)

    # Assert
    assert record.status == "success"
    assert record.published is True
    assert record.article_path == "/app/output/x.html"
    assert record.message == "发布成功"


def test_execute_task_records_published_false_when_not_published(monkeypatch):
    """任务级 auto_publish=False(或凭据无效)→ 生成成功但 published=False,message 标注未发布。"""
    from src.ai_write_x.scheduler.scheduled_task_executor import ScheduledTaskExecutor
    from src.ai_write_x.scheduler.scheduled_task_models import ScheduledTask

    # Arrange
    executor = ScheduledTaskExecutor(_StubService())
    monkeypatch.setattr(
        ScheduledTaskExecutor,
        "_run_generation",
        staticmethod(
            lambda config_data: {
                "published": False,
                "message": "未发布(任务级 auto_publish=False 或凭据无效,已跳过发布)",
                "article_path": "/app/output/y.html",
            }
        ),
    )
    task = ScheduledTask(task_id="t2", name="n2", topic="话题2", auto_publish=False)

    # Act
    record = executor.execute_task(task)

    # Assert
    assert record.status == "success"  # 生成本身成功
    assert record.published is False
    assert "未发布" in record.message
