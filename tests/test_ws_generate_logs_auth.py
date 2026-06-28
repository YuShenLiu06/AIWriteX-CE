# -*- coding: UTF-8 -*-
"""
回归测试:WebSocket 日志流路由 /api/ws/generate/logs 的鉴权与连通性。

背景:generate_router 曾带路由级 dependencies=[Depends(verify_auth)]。
FastAPI 会把路由级依赖套用到其下的 WebSocket 路由,但 WS 依赖解析器无法为
verify_auth(request: Request) 注入 request,于是零参调用 → TypeError,
异常在 websocket_logs 执行/accept 之前被 ServerErrorMiddleware 捕获并掐断连接,
浏览器 new WebSocket() 触发 onerror/onclose 且无重连 → 日志面板静默断流
(与此同时生成子进程独立运行,文章照常产出)。

修复:WS 路由挂到无路由级依赖的 ws_router,鉴权由 handler 内
_check_websocket_auth 自行处理(session cookie,Starlette SessionMiddleware
已为 ws 填充 scope["session"])。

覆盖:
- 已登录(session cookie):WS 正常连通(回归前连接被掐断)
- 鉴权关闭:WS 可连通
- 未登录且鉴权开启:连接被以 4401 关闭(鉴权未丢失)

需在 3.10+ 环境运行(容器内 Python 3.11)。
"""

import os
import sys
from pathlib import Path

import pytest
from starlette.websockets import WebSocketDisconnect

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# 在导入 app 之前固定鉴权环境(与 test_auth_sessions.py 一致),保证 lifespan
# 启用鉴权且凭证已知,并固定 session secret 使 cookie 签名可复现。
os.environ["AIWRITEX_AUTH_ENABLED"] = "true"
os.environ["AIWRITEX_AUTH_USER"] = "testadmin"
os.environ["AIWRITEX_AUTH_PASSWORD"] = "testpw-12345"
os.environ["AIWRITEX_AUTH_API_KEY"] = "testkey-abc"
os.environ.setdefault("AIWRITEX_SESSION_SECRET", "test-session-secret-fixed")

from fastapi.testclient import TestClient  # noqa: E402

from src.ai_write_x.web import auth  # noqa: E402
from src.ai_write_x.web.app import app  # noqa: E402

USER = "testadmin"
PWD = "testpw-12345"
WS_URL = "/api/ws/generate/logs"


def _client() -> TestClient:
    """每次进入上下文触发 lifespan,重新读取已固定的鉴权环境并隔离 cookie 状态。"""
    return TestClient(app)


def test_ws_connects_when_logged_in():
    """已登录:session cookie 随 WS 握手携带,连接应被 accept(回归前被 TypeError 掐断)。"""
    with _client() as c:
        assert c.post("/api/auth/login", data={"username": USER, "password": PWD}).status_code == 200
        with c.websocket_connect(WS_URL) as ws:
            # 连通即通过;handler 在无任务时空转,退出 with 触发 WebSocketDisconnect 正常收尾
            assert ws is not None


def test_ws_connects_when_auth_disabled(monkeypatch):
    """鉴权关闭:WS 直接放行(覆盖 _check_websocket_auth 的 enabled 分支)。"""
    with _client() as c:
        # 必须在进入上下文(lifespan → load_auth_config 缓存 _auth_config)之后再覆盖,
        # 否则 lifespan 会把鉴权重置回已启用状态。
        monkeypatch.setattr(auth, "_auth_config", auth.AuthConfig(enabled=False))
        with c.websocket_connect(WS_URL) as ws:
            assert ws is not None


def test_ws_rejected_when_unauthenticated():
    """未登录且鉴权开启:连接被以 4401 关闭(证明鉴权未丢失)。"""
    with _client() as c:
        with pytest.raises(WebSocketDisconnect) as exc:
            with c.websocket_connect(WS_URL):
                pass
        assert exc.value.code == 4401
