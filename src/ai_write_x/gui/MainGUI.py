#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

主界面

"""

import time
import queue
import threading
import os
from collections import deque
from datetime import datetime

import PySimpleGUI as sg
import tkinter as tk

from src.ai_write_x.crew_main import ai_write_x_main

from src.ai_write_x.utils import comm
from src.ai_write_x.utils import utils
from src.ai_write_x.utils import log
from src.ai_write_x.config.config import Config

from src.ai_write_x.gui import ConfigEditor
from src.ai_write_x.gui import ArticleManager
from src.ai_write_x.gui import TemplateManager
from src.ai_write_x.config.config import DEFAULT_TEMPLATE_CATEGORIES
from src.ai_write_x.utils.path_manager import PathManager


__author__ = "iniwaper@gmail.com"
__copyright__ = "Copyright (C) 2025 iniwap"
# __date__ = "2025/04/17"

__version___ = "v2.1.8"


class MainGUI(object):
    def __init__(self):
        self._log_list = []
        self._is_running = False  # 跟踪任务状态
        self._update_queue = comm.get_update_queue()
        self._log_buffer = deque(maxlen=100)
        self._ui_log_path = (
            PathManager.get_log_dir() / f"UI_{datetime.now().strftime('%Y-%m-%d')}.log"
        )
        self._log_list = self.__get_logs()
        # 配置 CrewAI 日志处理器
        log.setup_logging("crewai", self._update_queue)
        # 终止信号和线程
        self._stop_event = threading.Event()
        self._crew_thread = None
        self.load_saved_font()

        # 加载配置，不验证
        config = Config.get_instance()
        if not config.load_config():
            # 配置信息未填写，仅作提示，用户点击开始任务时才禁止操作并提示错误
            log.print_log(config.error_message, "error")

        # 获取模板分类和当前配置
        categories = utils.get_all_categories(DEFAULT_TEMPLATE_CATEGORIES)
        current_category = config.custom_template_category
        current_template = config.custom_template
        current_templates = (
            utils.get_templates_by_category(current_category) if current_category else []
        )

        # 设置主题
        sg.theme("systemdefault")

        menu_list = [
            ["配置", ["配置管理", "CrewAI文件", "AIForge文件"]],
            ["发布", ["文章管理"]],
            ["模板", ["模板管理"]],
            ["日志", self._log_list],
            ["帮助", ["帮助", "关于", "官网"]],
        ]

        # 根据平台选择菜单组件
        import sys

        if sys.platform == "darwin":  # macOS
            menu_component = [sg.MenubarCustom(menu_list, key="-MENU-")]
        else:  # Windows 和 Linux
            menu_component = [sg.Menu(menu_list, key="-MENU-")]

        layout = [
            menu_component,
            # 顶部品牌区域
            [
                sg.Image(
                    s=(640, 120),
                    filename=utils.get_res_path(
                        os.path.join("UI", "bg.png"), os.path.dirname(__file__)
                    ),
                    key="-BG-IMG-",
                    expand_x=True,
                )
            ],
            # 使用提示区域
            [
                sg.Frame(
                    "",
                    [
                        [
                            sg.Text(
                                "💡 快速开始：1. 配置→配置管理 填写使用的 API KEY  2. 勾选自定义话题启用借鉴模式，默认使用热搜话题",  # noqa 501
                                font=("", 8),
                                text_color="#666666",
                                pad=((10, 10), (5, 5)),
                            )
                        ]
                    ],
                    border_width=0,
                    pad=((15, 15), (5, 10)),
                    expand_x=True,
                )
            ],
            # 主要配置区域
            [
                sg.Frame(
                    "借鉴模式",
                    [
                        # 话题配置行
                        [
                            sg.Text("自定义话题", size=(10, 1), pad=((10, 5), (8, 5))),
                            sg.Checkbox(
                                "",
                                key="-CUSTOM_TOPIC-",
                                enable_events=True,
                                pad=((8, 10), (8, 5)),
                                tooltip="启用自定义话题和借鉴文章模式",
                            ),
                            sg.InputText(
                                "",
                                key="-TOPIC_INPUT-",
                                disabled=True,
                                size=(35, 1),
                                pad=((0, 10), (8, 5)),
                                tooltip="输入自定义话题，或留空以自动获取热搜",
                            ),
                        ],
                        # 模板配置行
                        [
                            sg.Text("模板选择", size=(10, 1), pad=((10, 5), (5, 5))),
                            sg.Combo(
                                ["随机分类"] + categories,
                                default_value=current_category if current_category else "随机分类",
                                key="-TEMPLATE_CATEGORY-",
                                disabled=True,
                                size=(17, 1),
                                readonly=True,
                                enable_events=True,
                                pad=((15, 5), (5, 5)),
                            ),
                            sg.Combo(
                                ["随机模板"] + current_templates,
                                default_value=current_template if current_template else "随机模板",
                                key="-TEMPLATE-",
                                disabled=True,
                                size=(17, 1),
                                readonly=True,
                                pad=((5, 10), (5, 5)),
                            ),
                        ],
                        # 参考链接配置行
                        [
                            sg.Text("参考链接", size=(10, 1), pad=((10, 5), (5, 8))),
                            sg.InputText(
                                "",
                                key="-URLS_INPUT-",
                                disabled=True,
                                size=(30, 1),
                                pad=((15, 5), (5, 8)),
                                tooltip="多个链接用竖线(|)分隔",
                            ),
                            sg.Text("借鉴比例", size=(8, 1), pad=((10, 5), (5, 8))),
                            sg.Combo(
                                ["10%", "20%", "30%", "50%", "75%"],
                                default_value="30%",
                                key="-REFERENCE_RATIO-",
                                disabled=True,
                                size=(8, 1),
                                pad=((5, 10), (5, 8)),
                            ),
                        ],
                    ],
                    border_width=1,
                    relief=sg.RELIEF_RIDGE,
                    pad=((15, 15), (5, 15)),
                    expand_x=True,
                    font=("", 9, "bold"),
                )
            ],
            # 操作按钮区域
            [
                sg.Frame(
                    "",
                    [
                        [
                            sg.Push(),
                            sg.Button(
                                "开始执行",
                                size=(15, 2),
                                key="-START_BTN-",
                                button_color=("#FFFFFF", "#2E8B57"),
                                font=("", 10, "bold"),
                                pad=((10, 15), (10, 10)),
                            ),
                            sg.Button(
                                "停止执行",
                                size=(15, 2),
                                key="-STOP_BTN-",
                                disabled=not self._is_running,
                                button_color=("#FFFFFF", "#CD5C5C"),
                                font=("", 10, "bold"),
                                pad=((15, 10), (10, 10)),
                            ),
                            sg.Push(),
                        ]
                    ],
                    border_width=0,
                    pad=((15, 15), (5, 10)),
                    expand_x=True,
                )
            ],
            # 分隔线
            [sg.HSeparator(pad=((20, 20), (10, 10)))],
            # 日志控制区域
            [
                sg.Frame(
                    "运行日志",
                    [
                        [
                            sg.Text("显示条数:", size=(8, 1), pad=((10, 5), (5, 5))),
                            sg.Spin(
                                [10, 20, 50, 100, 200, 500, 1000],
                                initial_value=100,
                                key="-LOG_LIMIT-",
                                size=(8, 1),
                                pad=((5, 10), (5, 5)),
                            ),
                            sg.Button(
                                "应用",
                                key="-SET_LOG_LIMIT-",
                                size=(8, 1),
                                pad=((5, 10), (5, 5)),
                            ),
                            sg.Button(
                                "清空",
                                key="-CLEAR_LOG-",
                                size=(8, 1),
                                pad=((5, 10), (5, 5)),
                            ),
                        ],
                        [
                            sg.Multiline(
                                size=(90, 16),
                                key="-STATUS-",
                                autoscroll=True,
                                pad=((10, 10), (5, 10)),
                                # font=("Consolas", 9),
                                background_color="#F8F8F8",
                                text_color="#333333",
                            )
                        ],
                    ],
                    border_width=1,
                    relief=sg.RELIEF_RIDGE,
                    pad=((15, 15), (5, 15)),
                    expand_x=True,
                    font=("", 9, "bold"),
                )
            ],
        ]
        self._window = sg.Window(
            f"AIWriteX - {__version___}",
            layout,
            default_element_size=(12, 1),
            size=(650, 720),
            icon=self.__get_icon(),
            finalize=True,
            resizable=False,
            element_justification="left",
            margins=(10, 10),
        )

        # 根据平台和菜单类型初始化菜单引用
        if sys.platform == "darwin":  # macOS 使用 MenubarCustom
            self._menu = None  # MenubarCustom 没有 TKMenu 属性
            self._use_menubar_custom = True
        else:  # Windows 和 Linux 使用标准 Menu
            self._menu = self._window["-MENU-"].TKMenu
            self._use_menubar_custom = False

    def load_saved_font(self):
        """加载保存的字体设置"""
        saved_font = sg.user_settings_get_entry("-global_font-", "Helvetica|10")

        try:
            if "|" in saved_font:
                # 新格式：字体名|大小
                font_name, size = saved_font.split("|", 1)
            else:
                # 兼容旧格式
                parts = saved_font.split()
                if len(parts) >= 2:
                    size = parts[-1]
                    font_name = " ".join(parts[:-1])
                else:
                    # 如果格式不正确，使用默认字体
                    sg.set_options(font="Helvetica 10")
                    return "Helvetica|10"

            # 检查是否为横向字体
            excluded_patterns = [
                "@",  # 横向字体通常以@开头
                "Vertical",  # 包含Vertical的字体
                "V-",  # 以V-开头的字体
                "縦",  # 日文中的纵向字体标识
                "Vert",  # 其他可能的纵向标识
            ]

            # 如果是横向字体，使用默认字体
            is_horizontal_font = any(pattern in font_name for pattern in excluded_patterns)
            if is_horizontal_font:
                sg.set_options(font="Helvetica 10")
                return "Helvetica|10"

            # 正常字体，应用设置
            font_tuple = (font_name, int(size))
            sg.set_options(font=font_tuple)
            return saved_font

        except Exception:
            sg.set_options(font="Helvetica 10")
            return "Helvetica|10"

    def __get_icon(self):
        return utils.get_res_path(os.path.join("UI", "icon.ico"), os.path.dirname(__file__))

    def __save_ui_log(self, log_entry):
        # 如果日志不存在，则更新日志列表
        need_update = False
        if not os.path.exists(self._ui_log_path):
            need_update = True

        with open(self._ui_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            f.flush()

        if need_update:
            self._log_list = self.__get_logs()

        return need_update

    def __get_logs(self, max_files=5):
        try:
            # 获取所有 .log 文件
            log_dir = PathManager.get_log_dir()
            log_files = list(log_dir.glob("*.log"))
            if not log_files:
                return ["更多..."]

            # 按修改时间排序（降序）
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            # 提取文件名（不含路径），限制数量
            log_filenames = [os.path.basename(f) for f in log_files[:max_files]]
            if len(log_files) > max_files:
                log_filenames.append("更多...")

            return log_filenames
        except Exception as e:  # noqa 841
            return ["更多..."]

    def __update_menu(self):
        if self._use_menubar_custom:
            # MenubarCustom 需要重新创建整个菜单
            self.update_log_menu(self._log_list)
            return

        if self._menu is None:
            return  # 跳过菜单更新

        try:
            # 缓存"日志"菜单引用，初始化时查找一次
            if not hasattr(self, "_log_menu"):
                for i in range(self._menu.index(tk.END) + 1):
                    if self._menu.entrycget(i, "label") == "日志":
                        self._log_menu = self._menu.nametowidget(self._menu.entrycget(i, "menu"))
                        break
                else:
                    return

            # 清空"日志"菜单并更新
            self._log_menu.delete(0, tk.END)
            for log_item in self._log_list:
                self._log_menu.add_command(
                    label=log_item,
                    command=lambda item=log_item: self._window.write_event_value(item, None),
                )
        except Exception:
            pass

    def update_log_menu(self, log_list):
        """更新日志菜单（用于 MenubarCustom）"""
        self._log_list = log_list
        # 重建菜单
        menu_list = [
            ["配置", ["配置管理", "CrewAI文件", "AIForge文件"]],
            ["发布", ["文章管理"]],
            ["模板", ["模板管理"]],
            ["日志", self._log_list],
            ["帮助", ["帮助", "关于", "官网"]],
        ]
        # 刷新菜单
        try:
            self._window["-MENU-"].update(menu_definition=menu_list)
        except Exception:
            pass

    # 处理消息队列
    def process_queue(self):
        try:
            msg = self._update_queue.get_nowait()
            if msg["type"] == "progress":
                # 暂时不支持 进度显示
                """[
                    sg.Text("进度:", size=(6, 1), pad=((10, 5), (5, 5))),
                    sg.Text("0%", size=(4, 1), key="-PROGRESS-", pad=((5, 5), (5, 5))),
                    sg.ProgressBar(100, orientation='h', size=(20, 20), key="-PROGRESS_BAR-")
                ],"""
                # self._window["-PROGRESS-"].update(f"{msg['value']}%")
                # self._window["-PROGRESS_BAR-"].update(msg["value"])
                pass
            elif msg["type"] in ["status", "warning", "error"]:
                # 追加日志到缓冲区
                if msg["value"].startswith("PRINT:"):
                    log_entry = f"[{time.strftime('%H:%M:%S')}][PRINT]: {msg['value'][6:]}"
                elif msg["value"].startswith("FILE_LOG:"):
                    log_entry = f"[{time.strftime('%H:%M:%S')}][FILE]: {msg['value'][9:]}"
                elif msg["value"].startswith("LOG:"):
                    log_entry = f"[{time.strftime('%H:%M:%S')}][LOG]: {msg['value']}"
                else:
                    log_entry = (
                        f"[{time.strftime('%H:%M:%S')}] [{msg['type'].upper()}]: {msg['value']}"
                    )
                self._log_buffer.append(log_entry)
                if self.__save_ui_log(log_entry):
                    # 需要更新日志列表
                    self.__update_menu()

                # 更新 Multiline，显示所有日志
                self._window["-STATUS-"].update("\n".join(self._log_buffer), append=False)
                if msg["type"] == "status" and (
                    msg["value"].startswith("任务完成！") or msg["value"] == "CrewAI 任务被终止"
                ):
                    self._window["-START_BTN-"].update(disabled=False)
                    self._window["-STOP_BTN-"].update(disabled=True)
                    self._is_running = False
                    self._crew_thread = None
                elif msg["type"] == "error":
                    sg.popup_error(
                        f"任务错误: {msg['value']}",
                        title="错误",
                        icon=self.__get_icon(),
                        non_blocking=True,
                    )
                    self._window["-START_BTN-"].update(disabled=False)
                    self._window["-STOP_BTN-"].update(disabled=True)
                    self._is_running = False
                    self._crew_thread = None
                elif msg["type"] == "warning":
                    sg.popup(
                        f"出现错误但不影响运行，告警信息：{msg['value']}",
                        title="系统提示",
                        icon=self.__get_icon(),
                        non_blocking=True,
                    )
        except queue.Empty:
            pass

    def run(self):
        try:
            while True:
                event, values = self._window.read(timeout=100)
                if event == sg.WIN_CLOSED:  # always,  always give a way out!
                    if self._is_running and self._crew_thread and self._crew_thread.is_alive():
                        self._stop_event.set()
                        self._crew_thread.join(timeout=2.0)
                        if self._crew_thread.is_alive():
                            log.print_log("警告：任务终止超时，可能未完全停止")

                    break

                # 处理 MenubarCustom 事件（格式为 "菜单::子菜单"）
                if self._use_menubar_custom and "::" in str(event):
                    menu_parts = event.split("::")
                    if len(menu_parts) == 2:
                        main_menu, submenu = menu_parts
                        if main_menu == "配置":
                            if submenu == "配置管理":
                                event = "配置管理"
                            elif submenu == "CrewAI文件":
                                event = "CrewAI文件"
                            elif submenu == "AIForge文件":
                                event = "AIForge文件"
                        elif main_menu == "发布":
                            if submenu == "文章管理":
                                event = "文章管理"
                        elif main_menu == "模板":
                            if submenu == "模板管理":
                                event = "模板管理"
                        elif main_menu == "日志":
                            event = submenu  # 日志文件名
                        elif main_menu == "帮助":
                            if submenu == "帮助":
                                event = "帮助"
                            elif submenu == "关于":
                                event = "关于"
                            elif submenu == "官网":
                                event = "官网"

                # 原有的事件处理逻辑保持不变
                if event == "配置管理":
                    ConfigEditor.gui_start()
                elif event == "CrewAI文件":
                    try:
                        import sys

                        if sys.platform == "win32":
                            os.system(
                                "start /B  notepad " + Config.get_instance().get_config_path()
                            )
                        elif sys.platform == "darwin":  # macOS
                            os.system("open -a TextEdit " + Config.get_instance().get_config_path())
                        else:  # Linux
                            os.system("gedit " + Config.get_instance().get_config_path() + " &")
                    except Exception as e:
                        sg.popup(
                            "无法打开CrewAI配置文件 :( \n错误信息：" + str(e),
                            title="系统提示",
                            icon=self.__get_icon(),
                        )
                elif event == "AIForge文件":
                    try:
                        import sys

                        if sys.platform == "win32":
                            os.system(
                                "start /B  notepad " + Config.get_instance().config_aiforge_path
                            )
                        elif sys.platform == "darwin":  # macOS
                            os.system(
                                "open -a TextEdit " + Config.get_instance().config_aiforge_path
                            )
                        else:  # Linux
                            os.system("gedit " + Config.get_instance().config_aiforge_path + " &")
                    except Exception as e:
                        sg.popup(
                            "无法打开AIForge配置文件 :( \n错误信息：" + str(e),
                            title="系统提示",
                            icon=self.__get_icon(),
                        )
                elif event == "-CUSTOM_TOPIC-":
                    # 根据复选框状态启用/禁用输入框和下拉框
                    is_enabled = values["-CUSTOM_TOPIC-"]
                    self._window["-TOPIC_INPUT-"].update(disabled=not is_enabled)
                    self._window["-URLS_INPUT-"].update(disabled=not is_enabled)
                    self._window["-REFERENCE_RATIO-"].update(disabled=not is_enabled)
                    self._window["-TEMPLATE_CATEGORY-"].update(disabled=not is_enabled)
                    self._window["-TEMPLATE-"].update(disabled=not is_enabled)
                elif event == "-TEMPLATE_CATEGORY-":
                    selected_category = values["-TEMPLATE_CATEGORY-"]

                    if selected_category == "随机分类":
                        templates = ["随机模板"]
                        self._window["-TEMPLATE-"].update(
                            values=templates, value="随机模板", disabled=False
                        )
                    else:
                        templates = utils.get_templates_by_category(selected_category)

                        if not templates:
                            sg.popup_error(
                                f"分类 『{selected_category}』 的模板数量为0，不可选择",
                                title="系统提示",
                                icon=self.__get_icon(),
                            )
                            self._window["-TEMPLATE_CATEGORY-"].update(value="随机分类")
                            self._window["-TEMPLATE-"].update(
                                values=["随机模板"], value="随机模板", disabled=False
                            )
                        else:
                            template_options = ["随机模板"] + templates
                            self._window["-TEMPLATE-"].update(
                                values=template_options, value="随机模板", disabled=False
                            )

                    self._window.refresh()
                elif event == "-START_BTN-":
                    config = Config.get_instance()
                    if not config.validate_config():
                        sg.popup_error(
                            f"无法执行，配置错误：{config.error_message}",
                            title="系统提示",
                            icon=self.__get_icon(),
                            non_blocking=True,
                        )
                        continue
                    elif not self._is_running:
                        # 处理自定义话题、链接和借鉴比例
                        if values["-CUSTOM_TOPIC-"]:
                            topic = values["-TOPIC_INPUT-"].strip()
                            if not topic:
                                sg.popup_error(
                                    "自定义话题不能为空",
                                    title="系统提示",
                                    icon=self.__get_icon(),
                                    non_blocking=True,
                                )
                                continue
                            config.custom_topic = topic
                            urls_input = values["-URLS_INPUT-"].strip()
                            if urls_input:
                                urls = [url.strip() for url in urls_input.split("|") if url.strip()]
                                valid_urls = [url for url in urls if utils.is_valid_url(url)]
                                if len(valid_urls) != len(urls):
                                    sg.popup_error(
                                        "存在无效的URL，请检查输入（确保使用http://或https://）",
                                        title="系统提示",
                                        icon=self.__get_icon(),
                                        non_blocking=True,
                                    )
                                    continue
                                config.urls = valid_urls
                            else:
                                config.urls = []
                            # 将比例转换为浮点数
                            config.reference_ratio = (
                                float(values["-REFERENCE_RATIO-"].strip("%")) / 100
                            )
                            config.custom_template_category = (
                                values["-TEMPLATE_CATEGORY-"]
                                if values["-TEMPLATE_CATEGORY-"] != "随机分类"
                                else ""
                            )
                            config.custom_template = (
                                values["-TEMPLATE-"] if values["-TEMPLATE-"] != "随机模板" else ""
                            )

                        else:
                            config.custom_topic = ""
                            config.urls = []
                            config.reference_ratio = 0.0  # 重置为0
                            config.custom_template_category = ""  # 自定义话题时，模板分类
                            config.custom_template = ""  # 自定义话题时，模板

                        # -----这里分类模板适配完成后删除适配提醒-------------
                        sg.popup(
                            "更多界面功能开发中，请关注项目 :)\n点击OK开始执行",
                            title="系统提示",
                            icon=self.__get_icon(),
                        )
                        self._window["-START_BTN-"].update(disabled=True)
                        self._window["-STOP_BTN-"].update(disabled=False)
                        self._is_running = True
                        self._stop_event.clear()
                        self._crew_thread = threading.Thread(
                            target=ai_write_x_main,
                            args=(self._stop_event, True),
                            daemon=True,
                        )
                        self._crew_thread.start()
                        # 记录任务开始日志
                        log.print_log(
                            f"开始任务，话题：{config.custom_topic or '采用热门话题'}"
                            + (
                                f"，链接：{config.urls}，借鉴比例：{config.reference_ratio*100:.0f}%"
                                if config.custom_topic
                                else ""
                            )
                        )
                elif event == "-STOP_BTN-":
                    if self._is_running and self._crew_thread and self._crew_thread.is_alive():
                        self._stop_event.set()
                        self._crew_thread.join(timeout=2.0)
                        if self._crew_thread.is_alive():
                            log.print_log("警告：任务终止超时，可能未完全停止")
                        else:
                            log.print_log("CrewAI 任务被终止")
                        self._crew_thread = None
                        self._window["-START_BTN-"].update(disabled=False)
                        self._window["-STOP_BTN-"].update(disabled=True)
                        self._is_running = False
                        sg.popup(
                            "任务已终止",
                            title="系统提示",
                            icon=self.__get_icon(),
                            non_blocking=True,
                        )
                elif event == "关于":
                    sg.popup(
                        "关于软件 AIWriteX",
                        f"当前版本 {__version___}",
                        "Copyright (C) 2025 iniwap,All Rights Reserved",
                        title="系统提示",
                        icon=self.__get_icon(),
                    )
                elif event == "官网":
                    utils.open_url("https://github.com/iniwap/AIWriteX")
                elif event == "帮助":
                    sg.popup(
                        "———————————配置说明———————————\n"
                        "1、微信公众号AppID，AppSecrect必填（至少一个）\n"
                        "2、CrewAI使用的API的API KEY必填（使用的）\n"
                        "3、AIForge的模型提供商的API KEY必填（使用的）\n"
                        "4、其他使用默认即可，根据需求填写\n"
                        "———————————操作说明———————————\n"
                        "1、打开配置界面，首先进行必要的配置\n"
                        "2、点击开始执行，AI自动开始工作\n"
                        "3、陆续加入更多操作中...\n"
                        "———————————功能说明———————————\n"
                        "1、配置->配置管理：打开配置编辑界面\n"
                        "2、发布->发布管理：打开文章管理界面\n"
                        "3、模板->模板管理：打开模板管理界面\n"
                        "4、日志->日志文件：查看日志\n"
                        "5、配置->CrewAI/AIForge：直接查看或编辑配置文件\n"
                        "6、部分界面内容，悬停会有提示",
                        title="使用帮助",
                        icon=self.__get_icon(),
                    )
                elif event == "-SET_LOG_LIMIT-":
                    self._log_buffer = deque(self._log_buffer, maxlen=values["-LOG_LIMIT-"])
                    self._window["-STATUS-"].update("\n".join(self._log_buffer))
                elif event == "-CLEAR_LOG-":
                    self._log_buffer.clear()
                    self._window["-STATUS-"].update("")
                elif event in self._log_list:
                    if event == "更多...":
                        logs_path = os.path.abspath(PathManager.get_log_dir())
                        import sys

                        if sys.platform == "win32":
                            logs_path = logs_path.replace("/", "\\")
                        filename = sg.popup_get_file(
                            "打开文件",
                            default_path=logs_path,
                            file_types=(("log文件", "*.log"),),
                            initial_folder=logs_path,
                            no_window=True,
                        )
                        if not filename:
                            continue

                        try:
                            if sys.platform == "win32":
                                os.system("start /B  notepad " + filename)
                            elif sys.platform == "darwin":  # macOS
                                os.system("open -a TextEdit " + filename)
                            else:  # Linux
                                os.system("gedit " + filename + " &")
                        except Exception as e:
                            sg.popup(
                                "无法打开日志文件 :( \n错误信息：" + str(e),
                                title="系统提示",
                                icon=self.__get_icon(),
                            )
                    else:
                        try:
                            import sys

                            log_file_path = os.path.join(PathManager.get_log_dir(), event)
                            if sys.platform == "win32":
                                os.system("start /B  notepad " + log_file_path)
                            elif sys.platform == "darwin":  # macOS
                                os.system("open -a TextEdit " + log_file_path)
                            else:  # Linux
                                os.system("gedit " + log_file_path + " &")
                        except Exception as e:
                            sg.popup(
                                "无法打开日志文件 :( \n错误信息：" + str(e),
                                title="系统提示",
                                icon=self.__get_icon(),
                            )

                elif event == "文章管理":
                    ArticleManager.gui_start()
                elif event == "模板管理":
                    TemplateManager.gui_start()

                # 处理队列更新（非阻塞）
                if self._is_running:
                    self.process_queue()
        finally:
            if self._is_running and self._crew_thread and self._crew_thread.is_alive():
                self._stop_event.set()
                self._crew_thread.join(timeout=2.0)
            self._window.close()


def gui_start():
    MainGUI().run()


if __name__ == "__main__":
    gui_start()
