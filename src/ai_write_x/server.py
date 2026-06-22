# -*- coding: UTF-8 -*-
"""
纯服务器模式入口
用于Docker部署或无GUI环境运行
"""

import multiprocessing
import os
import sys
from typing import NoReturn


def _ensure_project_root_in_path() -> None:
    """确保项目根目录在 sys.path 中"""
    # 获取 src/ai_write_x 目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 项目根目录是 src 的父目录
    project_root = os.path.dirname(os.path.dirname(current_dir))

    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def run_server() -> NoReturn:
    """
    启动 FastAPI 服务器

    从环境变量读取配置:
    - AIWRITEX_HOST: 默认 0.0.0.0
    - AIWRITEX_PORT: 默认 8888
    - AIWRITEX_LOG_LEVEL: 默认 info

    注意: workers 固定为 1，避免多进程导致的状态问题
    (Config 单例 + APScheduler 内存状态 + generate.py 全局变量)
    """
    _ensure_project_root_in_path()

    from uvicorn import run

    host = os.environ.get("AIWRITEX_HOST", "0.0.0.0")
    port = int(os.environ.get("AIWRITEX_PORT", "8888"))
    log_level = os.environ.get("AIWRITEX_LOG_LEVEL", "info")

    run(
        "src.ai_write_x.web.app:app",
        host=host,
        port=port,
        workers=1,  # 必须为1，避免多worker导致状态不一致
        reload=False,
        log_level=log_level,
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_server()
