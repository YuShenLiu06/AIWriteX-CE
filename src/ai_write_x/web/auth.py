# -*- coding: UTF-8 -*-
"""
统一认证模块:HTTP Basic Auth + 静态 API Key 双轨鉴权。

Web 端:浏览器收到 401 + WWW-Authenticate 头后自动弹出原生 Basic 登录框,
登录成功后缓存凭证,后续同源 /api/* 请求自动带 Authorization 头。
CLI/API 端:通过 X-API-Key 头或 Basic(user:pass)鉴权,二者任一通过即可。

启用优先级(高 → 低):
    1. 环境变量 AIWRITEX_AUTH_ENABLED 显式设置(true/false)
    2. 凭证存在即启用(password 或 api_key 任一非空)

注意:config.yaml 的 auth.enabled 字段不再被使用(旧版默认 false 会持续误导)。
凭证来源优先级:环境变量 > config.yaml 的 auth 段 > 默认值。
    AIWRITEX_AUTH_ENABLED   true/false   显式启停(可选,不设则按凭证自动判断)
    AIWRITEX_AUTH_USER      Basic 用户名
    AIWRITEX_AUTH_PASSWORD  Basic 密码
    AIWRITEX_AUTH_API_KEY   静态 API Key
"""

import os
import secrets
from dataclasses import dataclass, field
from typing import Tuple

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.ai_write_x.utils import log

# auto_error=False:Basic 头缺失时不自动 400,以便先尝试 X-API-Key
_basic_security = HTTPBasic(auto_error=False)

_AUTH_REALM = 'Basic realm="AIWriteX"'
_DEFAULT_PUBLIC_PATHS = ("/health", "/static", "/images")


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

    cfg = (config or {}).get("auth", {}) or {}
    password = os.environ.get("AIWRITEX_AUTH_PASSWORD") or cfg.get("password") or ""
    api_key = os.environ.get("AIWRITEX_AUTH_API_KEY") or cfg.get("api_key") or ""
    auth_cfg = AuthConfig(
        enabled=_resolve_enabled(cfg, password, api_key),
        username=os.environ.get("AIWRITEX_AUTH_USER") or cfg.get("username") or "admin",
        password=password,
        api_key=api_key,
        public_paths=tuple(cfg.get("public_paths") or _DEFAULT_PUBLIC_PATHS),
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


def _check_basic(credentials: HTTPBasicCredentials | None, auth_cfg: AuthConfig) -> bool:
    if credentials is None or not auth_cfg.password:
        return False
    user_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"), auth_cfg.username.encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"), auth_cfg.password.encode("utf-8")
    )
    return user_ok and pass_ok


def verify_auth(
    credentials: HTTPBasicCredentials | None = Depends(_basic_security),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """统一鉴权依赖:X-API-Key 或 Basic Auth 任一通过即可。

    返回通过方式标识("api-key"/用户名/"anonymous",鉴权关闭时放行);
    全部失败返回 401 + WWW-Authenticate,触发浏览器原生 Basic 弹窗。
    """
    auth_cfg = get_auth_config()
    if not auth_cfg.enabled:
        return "anonymous"
    if _check_api_key(x_api_key, auth_cfg):
        return "api-key"
    if _check_basic(credentials, auth_cfg):
        return auth_cfg.username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": _AUTH_REALM},
    )
