#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import time
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware

import uvicorn

from src.ai_write_x.version import get_version
from src.ai_write_x.version import get_version_with_prefix 
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import utils

# 导入状态管理
from .state import app_state

# 导入API路由
from .api.config import router as config_router
from .api.templates import router as templates_router
from .api.articles import router as articles_router
from .api.generate import router as generate_router, ws_router
from .api.images import router as images_router
from .api.text_knowledge import router as text_knowledge_router
from .api.knowledge import router as knowledge_router
from .api.scheduled_tasks import router as scheduled_tasks_router
from .api.convert import router as convert_router
from .api.auth import router as auth_router
from .auth import load_auth_config, verify_auth, get_session_secret, _principal

# 添加全局状态
app_shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import queue
    from src.ai_write_x.utils import comm, log

    # 初始化主进程日志队列
    app_state.log_queue = queue.Queue()
    app_state.is_running = True

    # 初始化 UI 模式
    log.init_ui_mode()

    # 连接 comm 到队列
    comm.set_log_queue(app_state.log_queue)

    # 1) 配置加载(独立异常边界:失败不阻断鉴权与调度器初始化)
    app_state.config = Config.get_instance()
    try:
        if not app_state.config.load_config():
            log.print_log("配置加载失败，使用默认配置", "warning")
    except Exception as e:
        log.print_log(f"配置加载异常: {e}", "error")

    # 2) 鉴权初始化(独立于配置加载,任何情况下都必须执行,杜绝公网越权)
    try:
        load_auth_config(app_state.config.config)
    except Exception as e:
        log.print_log(f"鉴权初始化异常,改用环境变量兜底: {e}", "error")
        try:
            load_auth_config({})
        except Exception as e2:
            log.print_log(f"鉴权兜底初始化失败: {e2}", "error")

    # 3) 初始化定时任务模块(独立异常边界)
    try:
        from src.ai_write_x.scheduler import (
            ScheduledTaskRepository,
            ScheduledTaskService,
            ScheduledTaskExecutor,
            ScheduledTaskScheduler,
        )

        repository = ScheduledTaskRepository()
        service = ScheduledTaskService(repository)

        # 启动一致性修复:将残留的 running 记录/任务标记为 failed
        service.reconcile_orphaned_executions()

        executor = ScheduledTaskExecutor(service)
        scheduler = ScheduledTaskScheduler(service, executor)

        app_state.scheduled_task_service = service
        app_state.scheduled_task_executor = executor
        app_state.scheduled_task_scheduler = scheduler

        scheduler.start()
    except Exception as e:
        log.print_log(f"定时任务模块初始化失败: {e}", "warning")

    yield

    # 关闭时执行
    if app_state.scheduled_task_scheduler:
        app_state.scheduled_task_scheduler.stop()
    app_state.is_running = False
    log.print_log("AIWriteX Web服务正在关闭", "info")


# 创建FastAPI应用，使用lifespan
app = FastAPI(
    title="AIWriteX Web API",
    version=get_version(),
    description="智能内容创作平台Web接口",
    lifespan=lifespan,
)

# 获取Web模块路径
# 获取Web模块路径
if utils.get_is_release_ver():
    web_path = Path(utils.get_res_path("web"))
else:
    web_path = Path(__file__).parent

static_path = web_path / "static"
templates_path = web_path / "templates"

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
app.mount("/images", StaticFiles(directory=PathManager.get_image_dir()), name="images")

app.add_middleware(GZipMiddleware, minimum_size=1000)
# HTTPS 才能开启 cookie 的 Secure 标志;默认 False 以兼容 HTTP 本地/LAN 访问。
# 生产置于 TLS 反代之后时设 AIWRITEX_COOKIE_SECURE=true。
_cookie_secure = os.environ.get("AIWRITEX_COOKIE_SECURE", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret(),
    session_cookie="aiwritex_session",
    https_only=_cookie_secure,
    same_site="lax",
    max_age=7 * 24 * 3600,
    path="/",
)

# CORS:仅当显式配置 AIWRITEX_CORS_ORIGINS 时启用(生产建议同源反代)
_raw_cors = os.environ.get("AIWRITEX_CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _raw_cors.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 模板引擎
templates = Jinja2Templates(directory=str(templates_path))

# 注册API路由
app.include_router(config_router)
app.include_router(templates_router)
app.include_router(articles_router)
app.include_router(generate_router)
app.include_router(ws_router)
app.include_router(images_router)
app.include_router(text_knowledge_router)
app.include_router(knowledge_router)
app.include_router(scheduled_tasks_router)
app.include_router(convert_router)
app.include_router(auth_router)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """返回主界面"""
    if _principal(request) is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request, "index.html", {"version": get_version_with_prefix()}
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页(公开)"""
    if _principal(request) is not None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {})


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": time.time()}


# 添加关闭接口
@app.post("/shutdown", dependencies=[Depends(verify_auth)])
async def shutdown():
    """关闭服务器"""
    app_shutdown_event.set()
    return {"status": "shutting down"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8888, log_level="info")
