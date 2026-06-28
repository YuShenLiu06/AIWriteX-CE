# -*- coding: UTF-8 -*-
"""
Issue #1 回归测试:鉴权 + 配置 + 模板目录三类 bug 的修复验证。

覆盖:
- Config 字典不变式守护(_ensure_config_dict):非 dict 状态可恢复且可观测
- load_config 对非字典 YAML 的兜底
- load_auth_config 容忍非 dict(ttuple/None)输入,不再抛 AttributeError
- PathManager.get_template_dir 在 dev 模式下自动创建目录

注意:被测代码使用 Python 3.10+ 语法(dict | None),需在 3.10+ 环境运行(容器内 Python 3.11)。
"""

import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中(与 server.py 的 _ensure_project_root_in_path 一致)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def test_config_ensure_dict_resets_non_dict_state():
    """_ensure_config_dict 应把被污染为非 dict 的 config 恢复为 dict。"""
    from src.ai_write_x.config.config import Config

    cfg = Config.get_instance()
    # 模拟历史 tuple 污染
    cfg.config = ("not", "a", "dict")  # type: ignore[assignment]
    assert not isinstance(cfg.config, dict)

    cfg._ensure_config_dict()

    assert isinstance(cfg.config, dict), "config 应被恢复为 dict"
    assert isinstance(cfg.default_config, dict), "default_config 必须是 dict"


def test_load_config_falls_back_on_non_dict_yaml(tmp_path, monkeypatch):
    """config.yaml 解析为非 dict(如纯列表)时,应回退到默认配置而非污染 self.config。"""
    from src.ai_write_x.config.config import Config

    cfg = Config.get_instance()
    bad_yaml = tmp_path / "config.yaml"
    # 一个合法 YAML 但顶层是列表(非 dict)
    bad_yaml.write_text("- not\n- a\n- dict\n", encoding="utf-8")
    monkeypatch.setattr(cfg, "config_path", str(bad_yaml))

    ret = cfg.load_config()

    assert isinstance(cfg.config, dict), "非字典 YAML 不应让 config 变成 list"
    assert "platforms" in cfg.config, "应回退到默认配置"
    assert ret is True or ret is False  # 不抛异常即可


def test_load_auth_config_tolerates_tuple():
    """传入 tuple(历史污染场景)不应抛 'tuple' object has no attribute 'get'。"""
    from src.ai_write_x.web import auth

    # 历史场景:config 被污染为 tuple
    auth_cfg = auth.load_auth_config(("polluted", "tuple"))  # type: ignore[arg-type]

    assert isinstance(auth_cfg, auth.AuthConfig)
    # 环境变量未设 + 无凭证时关闭;关键是“不抛异常”
    assert auth_cfg.enabled in (True, False)


def test_load_auth_config_tolerates_none():
    """传入 None 不应抛异常。"""
    from src.ai_write_x.web import auth

    auth_cfg = auth.load_auth_config(None)
    assert isinstance(auth_cfg, auth.AuthConfig)


def test_get_template_dir_creates_directory(tmp_path, monkeypatch):
    """dev 模式下 get_template_dir 应自动创建目录,避免 iterdir 抛 FileNotFoundError。"""
    from src.ai_write_x.utils import path_manager
    from src.ai_write_x.utils import utils

    # 强制 dev 模式(sys.frozen 不存在)
    monkeypatch.setattr(utils, "get_is_release_ver", lambda: False)
    fake_root = tmp_path / "appdata"
    monkeypatch.setattr(path_manager.PathManager, "get_app_data_dir", lambda: fake_root)

    template_dir = path_manager.PathManager.get_template_dir()

    assert template_dir.exists(), "dev 模式应自动创建 templates 目录"
    assert template_dir.is_dir()
    # iterdir 在已创建的空目录上不应抛异常
    assert list(template_dir.iterdir()) == []


def test_app_lifespan_initializes_auth_even_when_config_broken(monkeypatch):
    """app.lifespan 中即使配置加载抛异常,鉴权仍应被初始化(不被吞掉)。"""
    from src.ai_write_x.web import app as app_module
    from src.ai_write_x.web import auth

    # 让 load_config 抛异常,模拟“配置加载失败”
    class BoomConfig:
        config = {}
        def load_config(self):
            raise RuntimeError("simulated config load failure")

    monkeypatch.setattr(app_module.Config, "get_instance", classmethod(lambda cls: BoomConfig()))
    # 提供凭证,确保鉴权可启用
    monkeypatch.setenv("AIWRITEX_AUTH_ENABLED", "true")
    monkeypatch.setenv("AIWRITEX_AUTH_PASSWORD", "pw")
    monkeypatch.setattr(auth, "_auth_config", auth.AuthConfig())

    import asyncio

    async def run():
        async with app_module.lifespan(app_module.app):
            pass

    asyncio.run(run())

    # 鉴权应已初始化并启用(配置加载失败没有阻断它)
    assert auth.get_auth_config().enabled is True, "配置加载失败不应让鉴权静默关闭"
