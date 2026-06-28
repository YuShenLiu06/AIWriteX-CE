# -*- coding: UTF-8 -*-
"""测试隔离:每个用例前后把 auth 模块的单例 _auth_config 复位为干净默认值。

背景:load_auth_config 在 FastAPI lifespan 中把鉴权配置缓存进模块级单例
_auth_config,跨用例不自动复位。先执行的集成用例(进入 TestClient → lifespan)
会把单例污染成"已加载"状态,继而破坏后续单元用例对 get_session_secret /
get_auth_config 的断言(它们假设单例为默认空值、回退读环境变量)。

本 autouse fixture 在每个用例前注入全新默认单例,用例结束由 monkeypatch 自动还原,
使整套测试与文件/用例执行顺序无关。
"""

import pytest


@pytest.fixture(autouse=True)
def _isolate_auth_singleton(monkeypatch):
    from src.ai_write_x.web import auth

    monkeypatch.setattr(auth, "_auth_config", auth.AuthConfig())
    yield
