#!/usr/bin/env python
import sys
import os
import warnings
import multiprocessing
import signal
import time
import json

from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.tools import hotnews
from src.ai_write_x.crew import AIWriteXCrew
from src.ai_write_x.utils import utils
from src.ai_write_x.utils import log
from src.ai_write_x.config.config import Config

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.*")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.*")


def run_crew_in_process(inputs, appid, appsecret, author, log_queue, config_data):
    """在独立进程中运行 CrewAI 工作流"""
    try:
        # 设置信号处理器
        def signal_handler(signum, frame):
            log_queue.put(
                {"type": "system", "message": "收到终止信号，正在退出", "timestamp": time.time()}
            )
            os._exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # 恢复环境变量
        env_file_path = None
        if config_data and "env_file_path" in config_data:
            env_file_path = config_data["env_file_path"]
            try:
                if os.path.exists(env_file_path):
                    with open(env_file_path, "r", encoding="utf-8") as f:
                        parent_env = json.load(f)

                    # 更新当前进程的环境变量
                    os.environ.update(parent_env)
                else:
                    pass
            except Exception:
                pass

        # 获取子进程的 Config 实例
        config = Config.get_instance()

        # 设置进程队列引用，让 print_log 可以访问
        config._process_log_queue = log_queue

        # 同步主进程的配置数据到子进程（包括 ui_mode）
        if config_data:
            for key, value in config_data.items():
                # 跳过环境文件路径，这个不是配置属性
                if key != "env_file_path":
                    setattr(config, key, value)

        # 重新加载配置文件以确保基础配置正确
        config.load_config()

        # 设置进程专用日志系统
        log.setup_process_logging(log_queue)

        # 添加调试信息
        log.print_log(f"配置信息：API类型={config.api_type}，模型={config.api_model} ", "status")

        # 执行任务
        result = run(inputs, appid, appsecret, author)

        # 发送成功消息
        log_queue.put(
            {
                "type": "system",
                "message": "任务执行完成",
                "result": result,
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        log_queue.put({"type": "error", "message": str(e), "timestamp": time.time()})
    finally:
        # 清理环境变量文件
        if env_file_path and os.path.exists(env_file_path):
            try:
                os.remove(env_file_path)
            except Exception:
                pass

        # 发送进程结束消息
        log_queue.put({"type": "system", "message": "任务进程即将退出", "timestamp": time.time()})
        os._exit(0)


def run(inputs, appid, appsecret, author):
    """
    Run the crew.
    """
    try:
        return AIWriteXCrew(appid, appsecret, author).crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def ai_write_x_run(config, ui_mode, appid="", appsecret="", author="", config_data=None):
    """执行 AI 写作任务"""
    # 准备输入参数
    log.print_log("正在初始化配置参数，请耐心等待...")
    if not config.custom_topic:
        platform = utils.get_random_platform(config.platforms)
        topic = hotnews.select_platform_topic(platform, 5)  # 前五个热门话题根据一定权重选一个
        urls = []
        reference_ratio = 0
    else:
        topic = config.custom_topic
        urls = config.urls
        reference_ratio = config.reference_ratio
        platform = ""

    inputs = {
        "platform": platform,
        "topic": topic,
        "urls": urls,
        "reference_ratio": reference_ratio,
        "min_article_len": config.min_article_len,
        "max_article_len": config.max_article_len,
    }

    if ui_mode:
        try:
            # 创建进程间通信队列
            log_queue = multiprocessing.Queue()
            process = multiprocessing.Process(
                target=run_crew_in_process,
                args=(inputs, appid, appsecret, author, log_queue, config_data),
                daemon=False,
            )
            return process, log_queue
        except Exception as e:
            log.print_log(str(e), "error")
            return None, None
    else:
        # 非 UI 模式直接执行
        try:
            result = run(inputs, appid, appsecret, author)
            log.print_log("任务完成！")
            return result
        except Exception as e:
            log.print_log(f"执行出错：{str(e)}", "error")
            return None


def ai_write_x_main(ui_mode=False, config_data=None):
    """主入口函数"""
    config = Config.get_instance()

    if not ui_mode:
        if not config.load_config():
            log.print_log("加载配置失败，请检查是否有配置！", "error")
            return None, None
        elif not config.validate_config():
            log.print_log(f"配置填写有错误：{config.error_message}", "error")
            return None, None

    # 设置模式
    config.ui_mode = ui_mode

    # 如果是 UI 模式且传递了配置数据，应用到当前进程
    if ui_mode and config_data:
        for key, value in config_data.items():
            setattr(config, key, value)

    # 重新加载配置文件以获取最新的基础配置
    if not config.load_config():
        log.print_log("加载配置失败，请检查是否有配置！", "error")
        return None, None

    # 保存环境变量到临时文件
    if ui_mode:
        env_file = PathManager.get_temp_dir() / f"env_{os.getpid()}.json"
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                json.dump(dict(os.environ), f, ensure_ascii=False, indent=2)

            # 将环境文件路径添加到config_data
            if config_data is None:
                config_data = {}
            config_data["env_file_path"] = str(env_file)

        except Exception:
            pass

    # 设置环境变量
    os.environ[config.api_key_name] = config.api_key
    os.environ["MODEL"] = config.api_model
    os.environ["OPENAI_API_BASE"] = config.api_apibase

    if config.auto_publish:
        for credential in config.wechat_credentials:
            appid = credential["appid"]
            appsecret = credential["appsecret"]
            author = credential["author"]

            # 如果没有配置appid，则忽略该条
            if len(appid) == 0 or len(appsecret) == 0:
                continue

            return ai_write_x_run(config, ui_mode, appid, appsecret, author, config_data)
    else:
        return ai_write_x_run(config, ui_mode, config_data=config_data)


# ----------------由于参数原因，以下调用不可用------------------
def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {"topic": "AI LLMs"}
    try:
        AIWriteXCrew().crew().train(
            n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        AIWriteXCrew().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {"topic": "AI LLMs"}
    try:
        AIWriteXCrew().crew().test(
            n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    if not utils.get_is_release_ver():
        ai_write_x_main()
