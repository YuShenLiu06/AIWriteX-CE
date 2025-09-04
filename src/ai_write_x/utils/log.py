import logging
import sys
import re
import time
import traceback
import multiprocessing
import threading

from src.ai_write_x.utils import comm
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import utils


def strip_ansi_codes(text):
    """去除 ANSI 颜色代码"""
    ansi_pattern = r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
    return re.sub(ansi_pattern, "", text)


# ==================== 进程间通信日志处理器 ====================


class ProcessLoggingHandler(logging.Handler):
    """进程专用日志处理器"""

    def __init__(self, process_queue: multiprocessing.Queue):
        super().__init__()
        self.process_queue = process_queue

    def emit(self, record):
        try:
            # 过滤掉不需要的日志
            if record.name in ["litellm", "httpx", "httpcore", "openai"]:
                return

            msg = self.format(record)
            msg = strip_ansi_codes(msg)
            self.process_queue.put(
                {
                    "type": "log",
                    "level": record.levelname,
                    "message": msg,
                    "timestamp": record.created,
                    "logger_name": record.name,
                }
            )
        except Exception:
            # 在进程环境下，不能调用 handleError
            pass


class ProcessStreamHandler:
    """进程专用标准输出处理器"""

    def __init__(self, process_queue: multiprocessing.Queue):
        self.process_queue = process_queue
        self.original_stdout = sys.__stdout__
        self._buffer = ""
        self._last_write_time = 0
        self._flush_delay = 0.05  # 减少延迟
        self._timer = None
        self._lock = threading.Lock()
        self._pending_flush = False
        self._max_buffer_size = 10000  # 添加缓冲区大小限制

    def write(self, msg):
        if not msg:
            return

        # 只在开发模式下输出到终端
        if not utils.get_is_release_ver() and self.original_stdout:
            try:
                self.original_stdout.write(msg)
                self.original_stdout.flush()
            except Exception:
                pass

        with self._lock:
            current_time = time.time()

            # 累积消息
            self._buffer += msg
            self._last_write_time = current_time

            # 检查缓冲区大小，防止超长内容积累
            if len(self._buffer) > self._max_buffer_size:
                # 强制刷新超长内容
                self._force_flush()
                return

            # 如果遇到换行符，立即处理
            if "\\n" in self._buffer:
                # 取消任何待处理的定时器
                if self._timer and self._timer.is_alive():
                    self._timer.cancel()
                    self._timer = None
                self._pending_flush = False

                lines = self._buffer.split("\\n")
                # 处理除最后一个元素外的所有行
                for line in lines[:-1]:
                    if line.strip():
                        clean_msg = strip_ansi_codes(line.strip())
                        self._send_to_queue(
                            {"type": "print", "message": clean_msg, "timestamp": current_time}
                        )

                # 保留最后一个不完整的行
                self._buffer = lines[-1]
            else:
                # 如果没有换行符且没有待处理的刷新，设置延迟刷新
                if not self._pending_flush:
                    self._pending_flush = True
                    self._timer = threading.Timer(self._flush_delay, self._delayed_flush)
                    self._timer.start()

    def _force_flush(self):
        """强制刷新超长内容"""
        if self._buffer.strip():
            clean_msg = strip_ansi_codes(self._buffer.strip())
            # 统一格式化
            self._send_to_queue({"type": "print", "message": clean_msg, "timestamp": time.time()})
            self._buffer = ""

    def _send_to_queue(self, message):
        """安全地发送消息到队列"""
        try:
            # 确保消息格式统一
            if isinstance(message, str):
                formatted_message = {"type": "print", "message": message, "timestamp": time.time()}
            else:
                formatted_message = message

            self.process_queue.put(formatted_message, timeout=1.0)
        except Exception:
            pass

    def _delayed_flush(self):
        """延迟刷新缓冲区"""
        with self._lock:
            if self._pending_flush:
                self.flush()
                self._pending_flush = False
            self._timer = None

    def flush(self):
        # 发送缓冲区中剩余的内容
        if self._buffer.strip():
            clean_msg = strip_ansi_codes(self._buffer.strip())
            self._send_to_queue({"type": "print", "message": clean_msg, "timestamp": time.time()})
            self._buffer = ""


def setup_process_logging(process_queue: multiprocessing.Queue):
    """在子进程中设置日志系统"""
    # 1. 重定向所有标准输出
    sys.stdout = ProcessStreamHandler(process_queue)
    sys.stderr = ProcessStreamHandler(process_queue)

    # 2. 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = ProcessLoggingHandler(process_queue)
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s]: %(message)s")
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING)  # 设置为 WARNING 级别

    # 3. 完全禁用特定库的日志输出
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    logging.getLogger("openai").setLevel(logging.ERROR)
    logging.getLogger("litellm").setLevel(logging.ERROR)  # 完全禁用 LiteLLM 日志

    # 4. 设置 CrewAI 特定日志记录器
    crewai_logger = logging.getLogger("crewai")
    crewai_logger.setLevel(logging.WARNING)  # 只显示警告和错误
    crewai_logger.propagate = True


# ==================== 线程间通信日志处理器 ====================


class QueueLoggingHandler(logging.Handler):
    """线程队列日志处理器（主进程使用）"""

    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            # 过滤掉不需要的日志
            if record.name in ["litellm", "httpx", "httpcore", "openai"]:
                return

            msg = self.format(record)
            msg = strip_ansi_codes(msg)
            self.queue.put({"type": "status", "value": f"LOG: {msg}"})
        except Exception:
            self.handleError(record)


class QueueStreamHandler:
    """线程队列标准输出处理器（主进程使用）"""

    def __init__(self, queue):
        self.queue = queue
        self.original_stdout = sys.__stdout__

    def write(self, msg):
        if msg.strip():
            clean_msg = strip_ansi_codes(msg.rstrip())
            self.queue.put({"type": "status", "value": f"PRINT: {clean_msg}"})

            # 只在开发模式下输出到终端
            if not utils.get_is_release_ver() and self.original_stdout is not None:
                try:
                    self.original_stdout.write(msg.rstrip() + "\n")
                    self.original_stdout.flush()
                except UnicodeEncodeError:
                    try:
                        encoded_msg = (
                            msg.rstrip()
                            .encode(self.original_stdout.encoding or "utf-8", errors="replace")
                            .decode(self.original_stdout.encoding or "utf-8")
                        )
                        self.original_stdout.write(encoded_msg + "\n")
                        self.original_stdout.flush()
                    except Exception:
                        safe_msg = msg.rstrip().encode("ascii", errors="ignore").decode("ascii")
                        self.original_stdout.write(safe_msg + "\n")
                        self.original_stdout.flush()

    def flush(self):
        if self.original_stdout is not None:
            self.original_stdout.flush()

    def fileno(self):
        if self.original_stdout is not None:
            try:
                return self.original_stdout.fileno()
            except (AttributeError, IOError):
                pass
        raise IOError("Stream has no fileno")


def setup_logging(log_name, queue):
    """配置日志处理器，将 CrewAI 日志发送到队列"""
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.WARNING)  # 改为 WARNING 级别
    handler = QueueLoggingHandler(queue)
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    for h in logger.handlers[:]:
        if isinstance(h, logging.StreamHandler) and h is not handler:
            logger.removeHandler(h)

    # 只在 UI 模式下重定向 stdout，保留终端输出
    config = Config.get_instance()
    if config.ui_mode and not hasattr(sys.stdout, "_is_queue_handler"):
        # 创建一个包装器，同时输出到队列和终端
        class DualOutputHandler:
            def __init__(self, queue, original_stdout):
                self.queue_handler = QueueStreamHandler(queue)
                self.original_stdout = original_stdout
                self._is_queue_handler = True  # 标记避免重复包装

            def write(self, msg):
                # 发送到队列（用于 UI）
                self.queue_handler.write(msg)

                # 只在开发模式下输出到终端
                if not utils.get_is_release_ver() and self.original_stdout:
                    try:
                        self.original_stdout.write(msg)
                        self.original_stdout.flush()
                    except Exception:
                        pass

            def flush(self):
                self.queue_handler.flush()
                if self.original_stdout:
                    try:
                        self.original_stdout.flush()
                    except Exception:
                        pass

            def fileno(self):
                return self.queue_handler.fileno()

        sys.stdout = DualOutputHandler(queue, sys.stdout)


# ==================== 统一日志接口 ====================


def print_log(msg, msg_type="status"):
    """统一日志接口函数"""
    config = Config.get_instance()

    if config.ui_mode:
        # 检查是否在子进程中
        if hasattr(config, "_process_log_queue") and config._process_log_queue:
            # 子进程模式：直接发送到进程队列
            config._process_log_queue.put(
                {"type": msg_type, "message": msg, "timestamp": time.time()}
            )
        else:
            # 主进程模式：发送到线程队列
            comm.send_update(msg_type, msg)

        # 在开发模式下同时输出到终端
        if not utils.get_is_release_ver():
            try:
                terminal_msg = f"[{time.strftime('%H:%M:%S')}] [{msg_type.upper()}]: {msg}"
                sys.__stdout__.write(terminal_msg + "\n")
                sys.__stdout__.flush()
            except Exception:
                pass
    else:
        # 命令行模式：直接打印
        print(f"[{time.strftime('%H:%M:%S')}] [{msg_type.upper()}]: {msg}")


def print_traceback(what, e):
    """统一错误追踪接口函数"""
    error_traceback = traceback.format_exc()
    tb = e.__traceback__
    filename = tb.tb_frame.f_code.co_filename
    line_number = tb.tb_lineno

    ret = (
        f"{what}发生错误: {str(e)}\n错误位置: {filename}:{line_number}\n错误详情:{error_traceback}"
    )

    # 使用 print_log 统一处理
    print_log(ret, "error")
    return ret
