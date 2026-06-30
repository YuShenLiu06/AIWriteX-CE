# -*- coding: UTF-8 -*-
"""config_data 应用工具(入口 → Config 的契约)。

将入口(Web 手动生成 / 定时任务)传入的 config_data 应用到 Config 实例。
刻意保持零项目内依赖(纯函数),便于在不拉起 CrewAI 重依赖的情况下做单测。
"""

from __future__ import annotations

from typing import Any, MutableMapping


def apply_config_data(config: Any, config_data: MutableMapping, *, override_auto_publish: bool) -> None:
    """将 config_data 应用到 Config 实例。

    - env_file_path 永远跳过(它是临时环境文件路径,不是配置属性)。
    - auto_publish 在 Config 上是只读 @property(无 setter):
        * 子进程(override_auto_publish=True):直接写 config.config["auto_publish"],
          用于注入定时任务级的发布开关(任务级独占语义)。
        * 父进程(override_auto_publish=False):跳过,既避免 setattr 抛 AttributeError,
          也避免污染父进程全局单例、进而影响后续手动生成。
    - 其余键照旧 setattr(如 custom_topic / urls / platform 等普通可写属性)。
    """
    for key, value in (config_data or {}).items():
        if key == "env_file_path":
            continue
        if key == "auto_publish":
            if override_auto_publish:
                config.config["auto_publish"] = value
            continue
        setattr(config, key, value)
