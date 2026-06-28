# -*- coding: UTF-8 -*-
"""
统一认证模块:Session Cookie(主)+ Basic Auth / API Key(回退)三轨鉴权。

Web 端:登录成功后由 Starlette SessionMiddleware 写入签名加密的 session cookie,
后续 fetch/XHR/WebSocket 请求同源自动携带 cookie,无需前端手动拼 Authorization。
CLI/API 端:通过 X-API-Key 头或 Basic(user:pass)鉴权,二者任一通过即可,
便于无法持有 cookie 的脚本/CI 场景。

启用优先级(高 → 低):
    1. 环境变量 AIWRITEX_AUTH_ENABLED 显式设置(true/false)
    2. 凭证存在即启用(password 或 api_key 任一非空)

注意:config.yaml 的 auth.enabled 字段不再被使用(旧版默认 false 会持续误导)。
凭证来源优先级:环境变量 > config.yaml 的 auth 段 > 默认值。
    AIWRITEX_AUTH_ENABLED       true/false   显式启停(可选,不设则按凭证自动判断)
    AIWRITEX_AUTH_USER          Basic 用户名
    AIWRITEX_AUTH_PASSWORD      Basic 密码
    AIWRITEX_AUTH_API_KEY       静态 API Key
    AIWRITEX_SESSION_SECRET     显式指定 session cookie 签名密钥(可选)
                                不设则按密码稳定派生,改密即失效
"""

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from typing import Optional, Tuple

from fastapi import HTTPException, Request, status

from src.ai_write_x.utils import log

_AUTH_REALM = 'Basic realm="AIWriteX"'
_DEFAULT_PUBLIC_PATHS = ("/health", "/static", "/images")

# Session cookie 名称,Starlette SessionMiddleware 必须用同样的 cookie 名。
_SESSION_COOKIE_NAME = "aiwritex_session"
# 未配置 session secret / 密码时的不安全兜底密钥(仅避免启动崩溃)。
_INSECURE_DEFAULT_SESSION_SECRET = "aiwritex-insecure-default-session-secret"
# HMAC 派生 session 密钥时的固定 key(变更后会令所有旧 session 失效)。
_SESSION_DERIVE_KEY = b"aiwritex-session-v1"
# Session 最大有效期:7 天(秒)。
_SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600


@dataclass
class AuthConfig:
    """鉴权配置(运行期只读快照)。"""

    enabled: bool = False
    username: str = "admin"
    password: str = ""
    api_key: str = ""
    public_paths: Tuple[str, ...] = field(default_factory=lambda: _DEFAULT_PUBLIC_PATHS)


# 模块级单例,由 load_auth_config 在应用 lifespan 中初始化
_auth_config: AuthConfig = AuthConfig()


def _resolve_enabled(cfg_auth: dict, password: str, api_key: str) -> bool:
    """鉴权启用状态解析(忽略 config.yaml 的 enabled 字段,避免旧版默认值持续误导)。

    优先级:
    1. 环境变量 AIWRITEX_AUTH_ENABLED 显式非空设置 → 跟随该值(便于 dev 显式关闭)
    2. 凭证(password 或 api_key)任一存在即启用
    """
    env_raw = os.environ.get("AIWRITEX_AUTH_ENABLED")
    if env_raw is not None and env_raw.strip() != "":
        return env_raw.strip().lower() in ("1", "true", "yes", "on")
    return bool(password) or bool(api_key)


def load_auth_config(config: dict | None = None) -> AuthConfig:
    """根据 config.yaml 的 auth 段与环境变量构建鉴权配置,并缓存为模块单例。

    启用规则:AIWRITEX_AUTH_ENABLED 环境变量显式设置时跟随;否则凭证存在即启用。
    凭证优先级:环境变量 > config.yaml 的 auth 段 > 默认值。
    """
    global _auth_config

    # 容忍非 dict 的 config(历史 tuple/None 污染曾导致此处抛异常),环境变量为准
    cfg_source = config if isinstance(config, dict) else {}
    cfg_auth = cfg_source.get("auth") if isinstance(cfg_source.get("auth"), dict) else {}
    password = os.environ.get("AIWRITEX_AUTH_PASSWORD") or cfg_auth.get("password") or ""
    api_key = os.environ.get("AIWRITEX_AUTH_API_KEY") or cfg_auth.get("api_key") or ""
    auth_cfg = AuthConfig(
        enabled=_resolve_enabled(cfg_auth, password, api_key),
        username=os.environ.get("AIWRITEX_AUTH_USER") or cfg_auth.get("username") or "admin",
        password=password,
        api_key=api_key,
        public_paths=tuple(cfg_auth.get("public_paths") or _DEFAULT_PUBLIC_PATHS),
    )

    if auth_cfg.enabled and not auth_cfg.password and not auth_cfg.api_key:
        log.print_log(
            "[Auth] 已启用鉴权但未配置任何凭证(password/api_key 均为空),API 将完全不可访问",
            "error",
        )
    elif auth_cfg.enabled:
        log.print_log(
            f"[Auth] 鉴权已启用,user={auth_cfg.username},api_key 已配置={bool(auth_cfg.api_key)}",
            "info",
        )
    else:
        log.print_log(
            "[Auth] 鉴权已关闭,所有 API 与 Web 界面公网可访问。"
            "如需启用请配置 AIWRITEX_AUTH_PASSWORD / AIWRITEX_AUTH_API_KEY,"
            "或显式设 AIWRITEX_AUTH_ENABLED=true",
            "warning",
        )

    _auth_config = auth_cfg
    return auth_cfg


def get_auth_config() -> AuthConfig:
    """获取已加载的鉴权配置单例。"""
    return _auth_config


def _check_api_key(x_api_key: str | None, auth_cfg: AuthConfig) -> bool:
    if not x_api_key or not auth_cfg.api_key:
        return False
    return secrets.compare_digest(x_api_key, auth_cfg.api_key)


def _check_basic_credentials(
    username: Optional[str], password: Optional[str], auth_cfg: AuthConfig
) -> bool:
    """恒定时间比较用户名/密码(对空值/None 安全)。"""
    if not username or not password or not auth_cfg.password:
        return False
    user_ok = secrets.compare_digest(
        username.encode("utf-8"), auth_cfg.username.encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        password.encode("utf-8"), auth_cfg.password.encode("utf-8")
    )
    return user_ok and pass_ok


def _check_basic(
    credentials: Optional[object], auth_cfg: AuthConfig
) -> bool:
    """兼容旧调用:HTTPBasicCredentials 形态的 Basic 凭证校验。"""
    if credentials is None:
        return False
    username = getattr(credentials, "username", None)
    password = getattr(credentials, "password", None)
    return _check_basic_credentials(username, password, auth_cfg)


def get_session_secret() -> str:
    """获取 session cookie 签名密钥。

    优先级:
    1. 环境变量 AIWRITEX_SESSION_SECRET(显式)
    2. 由密码稳定派生 HMAC(改密即令旧 session 失效)
    3. 兜底固定密钥(仅保证启动不崩溃,记 warning)
    """
    env_secret = os.environ.get("AIWRITEX_SESSION_SECRET")
    if env_secret:
        return env_secret
    password_input = (
        get_auth_config().password
        or os.environ.get("AIWRITEX_AUTH_PASSWORD")
        or ""
    )
    if not password_input:
        log.print_log(
            "[Auth] 未配置 AIWRITEX_SESSION_SECRET 且无密码,"
            "session 密钥使用不安全默认值",
            "warning",
        )
        return _INSECURE_DEFAULT_SESSION_SECRET
    return hmac.new(
        _SESSION_DERIVE_KEY,
        password_input.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _principal(request: Request) -> Optional[str]:
    """统一身份解析(Session > API Key > Basic),返回 principal 或 None。

    鉴权关闭 → 返回 "anonymous";否则按 session cookie、X-API-Key、
    Authorization: Basic 的顺序尝试,首个通过即返回。供 verify_auth 与
    GET / / /login 路由共用,避免各处重复实现。
    """
    auth_cfg = get_auth_config()
    if not auth_cfg.enabled:
        return "anonymous"

    # 1. Session cookie(Starlette 已自动解密并写入 request.session)
    try:
        user = request.session.get("user")
    except Exception:
        user = None
    if isinstance(user, str) and user:
        return user

    # 2. X-API-Key 头
    if _check_api_key(request.headers.get("x-api-key"), auth_cfg):
        return "api-key"

    # 3. Authorization: Basic 头(手动解析,恒定时间比较)
    auth_header = request.headers.get("authorization", "") or ""
    if auth_header.startswith("Basic "):
        encoded = auth_header[len("Basic "):].strip()
        try:
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        except Exception:
            return None
        if ":" not in decoded:
            return None
        username, password = decoded.split(":", 1)
        if _check_basic_credentials(username, password, auth_cfg):
            return auth_cfg.username

    return None


def verify_auth(request: Request) -> str:
    """统一鉴权依赖:Session Cookie / X-API-Key / Basic Auth 任一通过即可。

    返回 principal 标识(用户名 / "api-key" / "anonymous");
    全部失败返回 401。保留 WWW-Authenticate 头以便 API 客户端识别,
    浏览器对 fetch/XHR 的 401 不会弹出原生 Basic 框。
    """
    principal = _principal(request)
    if principal is not None:
        return principal
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": _AUTH_REALM},
    )
