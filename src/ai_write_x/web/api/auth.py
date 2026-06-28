# -*- coding: UTF-8 -*-
"""Session-cookie 认证路由:登录/登出/状态(公开)。"""
from fastapi import APIRouter, Form, HTTPException, Request, status

from ..auth import _check_basic_credentials, get_auth_config

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """校验账号密码,成功则写入 session cookie。"""
    cfg = get_auth_config()
    if cfg.enabled and not _check_basic_credentials(username, password, cfg):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    request.session["user"] = username or cfg.username or "anonymous"
    return {"ok": True, "user": request.session["user"]}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/status")
async def auth_status(request: Request):
    cfg = get_auth_config()
    if not cfg.enabled:
        return {"authenticated": True, "user": None}
    user = request.session.get("user")
    return {"authenticated": bool(user), "user": user}
