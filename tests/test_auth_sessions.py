# -*- coding: UTF-8 -*-
"""
Issue #1 第四类问题回归测试:Session Cookie 鉴权(Basic Auth + SPA fetch 不传递的修复)。

覆盖:
- get_session_secret:env 优先 / 密码派生 / 稳定可复现 / 改密失效
- _principal:鉴权关闭→anonymous;session / api-key / basic 解析;无一命中→None
- HTTP 流:GET / 未登录 303→/login;登录成功→cookie→受保护端点 200;错密 401;
          status 翻转;logout 失效;向后兼容(Basic / X-API-Key);无凭证 401

需在 3.10+ 环境运行(容器内 Python 3.11)。
"""

import os
import sys
import base64
from pathlib import Path
from types import SimpleNamespace

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# 在导入 app 之前固定鉴权环境,确保 lifespan 启用鉴权且凭证已知;
# 同时固定 session secret,使 cookie 签名可复现。
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
KEY = "testkey-abc"


def _client() -> TestClient:
    """每次进入上下文触发 lifespan,重新读取已固定的鉴权环境并隔离 cookie 状态。"""
    return TestClient(app)


def _fake_request(session=None, headers=None):
    return SimpleNamespace(session=session or {}, headers=headers or {})


# ---------------- 单元:get_session_secret ----------------


def test_session_secret_env_takes_priority(monkeypatch):
    monkeypatch.setenv("AIWRITEX_SESSION_SECRET", "explicit-secret")
    assert auth.get_session_secret() == "explicit-secret"


def test_session_secret_derived_from_password_and_stable(monkeypatch):
    monkeypatch.delenv("AIWRITEX_SESSION_SECRET", raising=False)
    monkeypatch.setenv("AIWRITEX_AUTH_PASSWORD", "pw-A")
    same_again = auth.get_session_secret()
    monkeypatch.setenv("AIWRITEX_AUTH_PASSWORD", "pw-B")
    after_change = auth.get_session_secret()
    monkeypatch.setenv("AIWRITEX_AUTH_PASSWORD", "pw-A")
    reproduced = auth.get_session_secret()

    assert reproduced == same_again, "相同密码应派生相同密钥(重启不丢登录)"
    assert same_again != after_change, "改密码应令密钥变化(旧 session 失效)"
    assert same_again != "aiwritex-insecure-default-session-secret"


# ---------------- 单元:_principal ----------------


def test_principal_anonymous_when_disabled(monkeypatch):
    monkeypatch.setattr(auth, "_auth_config", auth.AuthConfig(enabled=False))
    assert auth._principal(_fake_request()) == "anonymous"


def test_principal_session_user_wins(monkeypatch):
    cfg = auth.AuthConfig(enabled=True, username=USER, password=PWD, api_key=KEY)
    monkeypatch.setattr(auth, "_auth_config", cfg)
    req = _fake_request(session={"user": "admin-from-cookie"})
    assert auth._principal(req) == "admin-from-cookie"


def test_principal_api_key_channel(monkeypatch):
    cfg = auth.AuthConfig(enabled=True, username=USER, password=PWD, api_key=KEY)
    monkeypatch.setattr(auth, "_auth_config", cfg)
    assert auth._principal(_fake_request(headers={"x-api-key": KEY})) == "api-key"


def test_principal_basic_header_channel(monkeypatch):
    cfg = auth.AuthConfig(enabled=True, username=USER, password=PWD, api_key=KEY)
    monkeypatch.setattr(auth, "_auth_config", cfg)
    token = base64.b64encode(f"{USER}:{PWD}".encode()).decode()
    req = _fake_request(headers={"authorization": f"Basic {token}"})
    assert auth._principal(req) == USER


def test_principal_rejects_when_nothing_matches(monkeypatch):
    cfg = auth.AuthConfig(enabled=True, username=USER, password=PWD, api_key=KEY)
    monkeypatch.setattr(auth, "_auth_config", cfg)
    assert auth._principal(_fake_request()) is None


# ---------------- HTTP 流(鉴权开启)----------------


def test_root_redirects_to_login_when_unauthenticated():
    with _client() as c:
        resp = c.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"].rstrip("/").endswith("/login")


def test_login_page_served_when_unauthenticated():
    with _client() as c:
        resp = c.get("/login", follow_redirects=False)
        assert resp.status_code == 200


def test_login_failure_returns_401_and_keeps_unauthenticated():
    with _client() as c:
        resp = c.post("/api/auth/login", data={"username": USER, "password": "wrong"})
        assert resp.status_code == 401
        assert c.get("/api/auth/status").json()["authenticated"] is False


def test_login_success_sets_cookie_and_grants_access():
    with _client() as c:
        resp = c.post("/api/auth/login", data={"username": USER, "password": PWD})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "user": USER}
        # cookie 由 TestClient 自动保存,后续请求自动携带(模拟浏览器同源 fetch)
        assert c.get("/api/auth/status").json() == {"authenticated": True, "user": USER}
        assert c.get("/api/config/").status_code == 200
        assert c.get("/api/templates/categories").status_code == 200
        assert c.get("/").status_code == 200  # 已登录不再重定向


def test_logout_invalidates_session():
    with _client() as c:
        c.post("/api/auth/login", data={"username": USER, "password": PWD})
        assert c.post("/api/auth/logout").status_code == 200
        assert c.get("/api/config/").status_code == 401


def test_backward_compat_basic_auth_still_works():
    with _client() as c:
        assert c.get("/api/config/", auth=(USER, PWD)).status_code == 200


def test_backward_compat_api_key_header_still_works():
    with _client() as c:
        resp = c.get("/api/config/", headers={"X-API-Key": KEY})
        assert resp.status_code == 200


def test_unauthenticated_api_returns_401():
    with _client() as c:
        assert c.get("/api/config/").status_code == 401
