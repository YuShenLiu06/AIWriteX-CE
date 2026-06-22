# -*- coding: UTF-8 -*-

import multiprocessing
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"


def _run_gui() -> None:
    """启动GUI应用程序（桌面模式）"""
    # GUI专用导入，避免server模式下触发ImportError
    from aiforge import AIForgeEngine  # noqa

    try:
        from src.ai_write_x.license import check_license_and_start

        check_license_and_start()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        raise


def run() -> None:
    """
    主入口函数，根据环境变量选择运行模式

    AIWRITEX_RUN_MODE:
    - "server" (默认): 纯服务器模式，调用 run_server
    - "gui": GUI桌面模式
    """
    mode = os.environ.get("AIWRITEX_RUN_MODE", "server").lower()

    if mode == "gui":
        _run_gui()
    else:  # server mode
        from src.ai_write_x.server import run_server

        run_server()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)

    # GUI模式下需要处理aiforge沙箱子进程
    if os.environ.get("AIWRITEX_RUN_MODE", "server").lower() == "gui":
        from aiforge import AIForgeEngine  # noqa

        if AIForgeEngine.handle_sandbox_subprocess(
            globals_dict=globals().copy(), sys_path=sys.path.copy()
        ):
            sys.exit(0)

    run()
