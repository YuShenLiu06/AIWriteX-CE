import PySimpleGUI as sg
import re
import copy
import sys

from src.ai_write_x.config.config import Config, DEFAULT_TEMPLATE_CATEGORIES
from src.ai_write_x.utils import utils
from src.ai_write_x.utils.path_manager import PathManager


class ConfigEditor:
    def __init__(self):
        """初始化配置编辑器，使用单例配置"""
        sg.theme("systemdefault")
        self.config = Config.get_instance()
        self.platform_count = len(self.config.platforms)
        self.wechat_count = len(self.config.wechat_credentials)
        self.fonts = sg.Text.fonts_installed_list()
        # 应用字体过滤
        self.fonts = self._filter_fonts()

        self.global_font = sg.user_settings_get_entry("-global_font-", None)
        if not self._validate_font_selection(self.global_font):
            self.global_font = "Helvetica"

        self.window = sg.Window(
            "AIWriteX - 配置管理",
            self.create_layout(),
            size=(500, 600),
            resizable=False,
            finalize=True,
            icon=utils.get_gui_icon(),
            keep_on_top=True,
        )

        # 设置默认选中的API类型的TAB
        self.__default_select_api_tab()

    def set_global_font(self, font_name, size=10):
        """设置全局字体"""
        try:
            # 使用元组格式，避免空格解析问题
            if isinstance(font_name, str) and " " in font_name:
                font_tuple = (font_name, size)
            else:
                font_tuple = f"{font_name} {size}"

            sg.set_options(font=font_tuple)
            # 保存时使用特殊格式标记
            sg.user_settings_set_entry("-global_font-", f"{font_name}|{size}")
        except Exception:
            sg.set_options(font="Helvetica 10")

    def _filter_fonts(self):
        """过滤掉横向字体，只保留适合界面显示的字体"""
        if not hasattr(self, "fonts") or not self.fonts:
            return []

        # 定义需要排除的字体模式
        excluded_patterns = [
            "@",  # 横向字体通常以@开头
            "Vertical",  # 包含Vertical的字体
            "V-",  # 以V-开头的字体
            "縦",  # 日文中的纵向字体标识
            "Vert",  # 其他可能的纵向标识
        ]

        # 过滤字体列表
        filtered_fonts = []
        for font in self.fonts:
            # 检查字体名称是否包含排除模式
            should_exclude = any(pattern in font for pattern in excluded_patterns)
            if not should_exclude:
                filtered_fonts.append(font)

        return filtered_fonts

    def _validate_font_selection(self, font_name):
        """验证字体选择是否合适"""
        if not font_name:
            return True

        # 检查是否为横向字体
        excluded_patterns = ["@", "Vertical", "V-", "縦", "Vert"]
        if any(pattern in font_name for pattern in excluded_patterns):
            return False

        return True

    def create_platforms_tab(self):
        """创建平台 TAB 布局"""
        # 确保使用最新的 self.config.platforms 数据
        self.platform_count = len(self.config.platforms)
        platform_rows = [
            [
                sg.InputText(
                    platform["name"], key=f"-PLATFORM_NAME_{i}-", size=(20, 1), disabled=True
                ),
                sg.Text("权重:", size=(6, 1)),
                sg.InputText(platform["weight"], key=f"-PLATFORM_WEIGHT_{i}-", size=(50, 1)),
            ]
            for i, platform in enumerate(self.config.platforms)
        ]
        layout = [
            [sg.Text("热搜平台列表")],
            *platform_rows,
            [
                sg.Text(
                    "Tips：\n"
                    "1、根据权重随机一个平台，获取其当前的最热门话题；\n"
                    "2、权重总和超过1，默认选取微博作为热搜话题。\n",
                    size=(70, 3),
                    text_color="gray",
                ),
            ],
            [
                sg.Button("保存配置", key="-SAVE_PLATFORMS-"),
                sg.Button("恢复默认", key="-RESET_PLATFORMS-"),
            ],
        ]
        # 使用 sg.Column 包裹布局，设置 pad=(0, 0) 确保顶部无额外边距
        return [[sg.Column(layout, scrollable=False, vertical_scroll_only=False, pad=(0, 0))]]

    def create_wechat_tab(self):
        """创建微信 TAB 布局 (垂直排列，标签固定宽度对齐，支持滚动)"""
        credentials = self.config.wechat_credentials
        self.wechat_count = len(credentials)
        label_width = 8
        wechat_rows = []
        for i, cred in enumerate(credentials):
            call_sendall = cred.get("call_sendall", False)
            sendall = cred.get("sendall", False)

            wechat_rows.append(
                [sg.Text(f"凭证 {i+1}:", size=(label_width, 1), key=f"-WECHAT_TITLE_{i}-")]
            )
            wechat_rows.append(
                [
                    sg.Text("AppID*:", size=(label_width, 1)),
                    sg.InputText(
                        cred["appid"],
                        key=f"-WECHAT_APPID_{i}-",
                        size=(20, 1),
                        enable_events=True,
                    ),
                    sg.Text("作者:", size=(4, 1)),
                    sg.InputText(cred["author"], key=f"-WECHAT_AUTHOR_{i}-", size=(20, 1)),
                ]
            )
            wechat_rows.append(
                [
                    sg.Text("AppSecret*:", size=(label_width, 1)),
                    sg.InputText(
                        cred["appsecret"],
                        key=f"-WECHAT_SECRET_{i}-",
                        size=(49, 1),
                        enable_events=True,
                    ),
                ]
            )
            wechat_rows.append(
                [
                    sg.Text("群发选项:", size=(label_width, 1), tooltip="仅对【已认证公众号】有效"),
                    sg.Checkbox(
                        "启用群发",
                        default=call_sendall,
                        enable_events=True,
                        key=f"-WECHAT_CALL_SENDALL_{i}-",
                        tooltip="1. 启用群发，群发才有效\n2. 否则不启用，需要网页后台群发",
                    ),
                    sg.Checkbox(
                        "群发",
                        enable_events=True,
                        default=sendall,
                        disabled=not call_sendall,
                        key=f"-WECHAT_SENDALL_{i}-",
                        tooltip="1. 认证号群发数量有限，群发可控\n2. 非认证号，此选项无效（不支持群发）",
                    ),
                    sg.Text("标签组ID:", size=(label_width, 1)),
                    sg.InputText(
                        cred.get("tag_id", 0),
                        key=f"-WECHAT_TAG_ID_{i}-",
                        size=(15, 1),
                        disabled=not call_sendall or sendall,
                        tooltip="1. 群发时不用填写（填写无效）\n2. 不群发时，必须填写标签组ID",
                    ),
                ]
            )
            wechat_rows.append([sg.Button("删除", key=f"-DELETE_WECHAT_{i}-", disabled=i == 0)])
            wechat_rows.append([sg.HorizontalSeparator()])

        layout = [
            [sg.Text("微信公众号凭证")],
            [
                sg.Column(
                    wechat_rows,
                    key="-WECHAT_CREDENTIALS_COLUMN-",
                    scrollable=True,
                    vertical_scroll_only=True,
                    size=(480, 400),
                    expand_y=True,
                )
            ],
            [
                sg.Text(
                    "Tips：添加凭证、填写后，请先保存再继续添加（至少填写一个）。",
                    size=(70, 1),
                    text_color="gray",
                ),
            ],
            [sg.Button("添加凭证", key="-ADD_WECHAT-")],
            [
                sg.Button("保存配置", key="-SAVE_WECHAT-"),
                sg.Button("恢复默认", key="-RESET_WECHAT-"),
            ],
        ]
        return [[sg.Column(layout, scrollable=False, vertical_scroll_only=False, pad=(0, 0))]]

    def create_api_sub_tab(self, api_name, api_data):
        """创建 API 子 TAB 布局"""
        layout = [
            [sg.Text(f"{api_name.upper()} 配置")],
            [
                sg.Text("KEY名称:", size=(15, 1)),
                sg.InputText(api_data["key"], key=f"-{api_name}_KEY-", disabled=True),
            ],
            [
                sg.Text("API BASE:", size=(15, 1)),
                sg.InputText(api_data["api_base"], key=f"-{api_name}_API_BASE-", disabled=True),
            ],
            [
                sg.Text("KEY索引*:", size=(15, 1)),
                sg.InputText(api_data["key_index"], key=f"-{api_name}_KEY_INDEX-"),
            ],
            [
                sg.Text("API KEY*:", size=(15, 1)),
                sg.InputText(
                    ", ".join(api_data["api_key"]), key=f"-{api_name}_API_KEYS-", enable_events=True
                ),
            ],
            [
                sg.Text("模型索引*:", size=(15, 1)),
                sg.InputText(api_data["model_index"], key=f"-{api_name}_MODEL_INDEX-"),
            ],
            [
                sg.Text("模型*:", size=(15, 1)),
                sg.InputText(", ".join(api_data["model"]), key=f"-{api_name}_MODEL-"),
            ],
            [
                sg.Text(
                    "Tips：\n"
                    "1、API KEY和模型都是列表，如果有多个用逗号分隔；\n"
                    "2、索引即使用哪个API KEY、模型（从0开始）；\n"
                    "3、默认已提供较多模型，原则上只需要填写API KEY；\n"
                    "4、只需要填写选中的API类型相应的参数。",
                    size=(70, 5),
                    text_color="gray",
                ),
            ],
        ]
        return layout

    def __default_select_api_tab(self):
        # 设置 API TabGroup 的默认选中子 TAB
        api_data = self.config.get_config()["api"]
        api_type = api_data["api_type"]

        # 转换为显示名称
        if api_type == "SiliconFlow":
            target_tab_text = "硅基流动"
        else:
            target_tab_text = api_type

        tab_group = self.window["-API_TAB_GROUP-"]
        for tab in tab_group.Widget.tabs():  # type: ignore
            tab_text = tab_group.Widget.tab(tab, "text")  # type: ignore
            if tab_text == target_tab_text:
                tab_group.Widget.select(tab)  # type: ignore
                break
        self.window.refresh()

    def create_api_tab(self):
        """创建 API TAB 布局"""
        api_data = self.config.get_config()["api"]
        current_api_type = api_data["api_type"]
        if current_api_type == "SiliconFlow":
            display_api_type = "硅基流动"
        else:
            display_api_type = current_api_type

        layout = [
            [
                sg.Text("API 类型: "),
                sg.Combo(
                    self.config.api_list_display,
                    default_value=display_api_type,
                    key="-API_TYPE-",
                    enable_events=True,
                    size=(20, 1),
                ),
            ],
            [
                sg.TabGroup(
                    [
                        [sg.Tab("Grok", self.create_api_sub_tab("Grok", api_data["Grok"]))],
                        [sg.Tab("Qwen", self.create_api_sub_tab("Qwen", api_data["Qwen"]))],
                        [sg.Tab("Gemini", self.create_api_sub_tab("Gemini", api_data["Gemini"]))],
                        [
                            sg.Tab(
                                "OpenRouter",
                                self.create_api_sub_tab("OpenRouter", api_data["OpenRouter"]),
                            )
                        ],
                        [sg.Tab("Ollama", self.create_api_sub_tab("Ollama", api_data["Ollama"]))],
                        [
                            sg.Tab(
                                "Deepseek",
                                self.create_api_sub_tab("Deepseek", api_data["Deepseek"]),
                            )
                        ],
                        [
                            sg.Tab(
                                "硅基流动",
                                self.create_api_sub_tab("SiliconFlow", api_data["SiliconFlow"]),
                            )
                        ],
                    ],
                    key="-API_TAB_GROUP-",
                    enable_events=True,
                )
            ],
            [
                sg.Button("保存配置", key="-SAVE_API-"),
                sg.Button("恢复默认", key="-RESET_API-"),
            ],
        ]
        # 使用 sg.Column 包裹布局，设置 pad=(0, 0) 确保顶部无额外边距
        return [[sg.Column(layout, scrollable=False, vertical_scroll_only=False, pad=(0, 0))]]

    def create_img_api_tab(self):
        """创建图像 API TAB 布局"""
        img_api = self.config.get_config()["img_api"]

        # API类型配置区块
        api_type_layout = [
            [
                sg.Text("API类型:", size=(15, 1), tooltip="选择图片生成API类型"),
                sg.Combo(
                    ["picsum", "ali"],
                    default_value=img_api["api_type"],
                    key="-IMG_API_TYPE-",
                    size=(50, 1),
                    readonly=True,
                    tooltip="picsum: 免费随机图片API; ali: 阿里云通义万相图片生成API",
                ),
            ],
        ]

        # 阿里API配置区块
        ali_layout = [
            [
                sg.Text("API KEY:", size=(15, 1), tooltip="阿里云通义万相API密钥"),
                sg.InputText(
                    img_api["ali"]["api_key"],
                    key="-ALI_API_KEY-",
                    size=(50, 1),
                    enable_events=True,
                    tooltip="阿里云通义万相API密钥，与QWen API KEY相同",
                ),
            ],
            [
                sg.Text("模型:", size=(15, 1), tooltip="图片生成模型"),
                sg.InputText(
                    img_api["ali"]["model"],
                    key="-ALI_MODEL-",
                    size=(50, 1),
                    tooltip="阿里云通义万相图片生成模型名称",
                ),
            ],
        ]

        # Picsum API配置区块
        picsum_layout = [
            [
                sg.Text("API KEY:", size=(15, 1), tooltip="Picsum API密钥（免费服务无需配置）"),
                sg.InputText(
                    img_api["picsum"]["api_key"],
                    key="-PICSUM_API_KEY-",
                    size=(50, 1),
                    disabled=True,
                    tooltip="Picsum提供免费随机图片服务，无需API KEY",
                ),
            ],
            [
                sg.Text("模型:", size=(15, 1), tooltip="Picsum模型（免费服务无需配置）"),
                sg.InputText(
                    img_api["picsum"]["model"],
                    key="-PICSUM_MODEL-",
                    size=(50, 1),
                    disabled=True,
                    tooltip="Picsum提供免费随机图片服务，无需指定模型",
                ),
            ],
            [
                sg.Text(
                    "Tips：Picsum提供免费的随机图片服务，无需配置API KEY和模型。",
                    size=(70, 1),
                    text_color="gray",
                ),
            ],
        ]

        # 主布局
        content_layout = [
            [
                sg.Frame(
                    "API类型配置",
                    api_type_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "阿里API配置",
                    ali_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "Picsum API配置",
                    picsum_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Text(
                    "使用说明：\n"
                    "1、选择picsum时，使用免费随机图片服务，无需填写KEY和模型；\n"
                    "2、选择阿里时，需要配置API KEY和模型，API KEY与QWen相同。",
                    size=(70, 3),
                    text_color="gray",
                ),
            ],
            [sg.VPush()],  # 垂直填充，将按钮推到底部
            [
                sg.Button("保存配置", key="-SAVE_IMG_API-"),
                sg.Button("恢复默认", key="-RESET_IMG_API-"),
            ],
        ]

        # 使用Frame包装内容，避免滚动问题
        content_frame = sg.Frame("", content_layout, border_width=0, pad=(0, 0))

        # 外层Column充满高度，不启用滚动
        return [
            [
                sg.Column(
                    [[content_frame]],
                    expand_x=True,
                    expand_y=True,
                    pad=(0, 0),
                )
            ]
        ]

    def create_base_tab(self):
        """创建基础 TAB 布局"""
        # 获取所有分类
        categories = PathManager.get_all_categories(DEFAULT_TEMPLATE_CATEGORIES)

        # 获取当前配置的模板信息
        current_category = self.config.template_category
        current_template = self.config.template

        # 获取当前分类下的模板
        current_templates = PathManager.get_templates_by_category(current_category)

        # 检查是否有模板
        is_template_empty = len(categories) == 0

        if self.global_font:
            # 从保存的字体字符串中提取字体名称
            if "|" in self.global_font:
                # 新格式：字体名|大小
                font_name = self.global_font.split("|")[0]
            else:
                # 旧格式：字体名 大小
                font_parts = self.global_font.split()
                if len(font_parts) >= 2:
                    font_name = " ".join(font_parts[:-1])
                else:
                    font_name = font_parts[0] if font_parts else "Helvetica"

            # 当字体为 Helvetica 时，设置为系统默认字体
            is_sys_font = font_name == "Helvetica"
        else:
            is_sys_font = True
            font_name = "Helvetica"

        # 过滤字体列表，排除横向字体
        filtered_fonts = self._filter_fonts()

        # 设置字体下拉列表的默认值
        if is_sys_font:
            font_default_value = None
        else:
            font_default_value = font_name if font_name in filtered_fonts else None

        # Define tooltips for each relevant element
        tips = {
            "auto_publish": "自动发布文章：\n- 自动：生成文章后，自动发布到配置的微信公众号\n"
            "- 不自动：生成文章后，需要手动选择发布",
            "use_template": "- 使用：\n  随机模板：程序随机选取一个并将生成的文章填充到模板里\n  "
            "选定模板：使用指定的模板\n- 不使用：AI根据要求生成模板，并填充文章",
            "template_category": "选择分类：\n- 随机分类：程序随机选取一个分类下的模板\n"
            "- 指定分类：选择特定分类，然后从该分类下选择模板",
            "template": "选择模板：\n- 随机模板：从选定分类中随机选取模板\n"
            "- 指定模板：使用选定分类下的特定模板文件",
            "use_compress": "压缩模板：\n- 压缩：读取模板后压缩，降低token消耗，可能影响AI解析模板\n"
            "- 不压缩：token消耗，AI可能理解更精确",
            "aiforge_search_max_results": "最大搜索数量：返回的最大搜索结果数（1~20）",
            "aiforge_search_min_results": "最小搜索数量：返回的最小搜索结果数（1~10）",
            "min_article_len": "最小文章字数：生成文章的最小字数（500）",
            "max_article_len": "最大文章字数：生成文章的最大字数（5000）",
            "article_format": "生成文章的格式：非HTML时，只生成文章，不用模板（不执行模板适配任务）",
            "format_publish": "格式化发布文章：非HTML格式，直接发布效果混乱，建议格式化发布",
            "ui_font": "设置界面字体后保存，需要重新打开才能生效",
        }

        # 发布配置区块
        publish_layout = [
            [
                sg.Text("发布平台：", size=(15, 1), tooltip="选择内容发布的目标平台"),
                sg.Combo(
                    ["微信公众号", "小红书", "抖音", "今日头条", "百家号", "知乎", "豆瓣"],
                    default_value=self._get_platform_display_name(self.config.publish_platform),
                    key="-PUBLISH_PLATFORM-",
                    size=(15, 1),
                    readonly=True,
                    tooltip="选择内容发布的目标平台",
                    disabled=True,
                ),
            ],
            [
                sg.Text("文章发布：", size=(15, 1), tooltip=tips["auto_publish"]),
                sg.Checkbox(
                    "自动发布",
                    default=self.config.auto_publish,
                    key="-AUTO_PUBLISH-",
                    tooltip=tips["auto_publish"],
                ),
            ],
            [
                sg.Text("文章格式：", size=(15, 1), tooltip=tips["article_format"]),
                sg.Combo(
                    ["html", "markdown", "txt"],
                    default_value=self.config.article_format,
                    key="-ARTICLE_FORMAT-",
                    size=(11, 1),
                    readonly=True,
                    tooltip=tips["article_format"],
                    enable_events=True,
                ),
                sg.Text("格式化发布：", size=(13, 1), tooltip=tips["format_publish"]),
                sg.Checkbox(
                    "格式化",
                    default=self.config.format_publish,
                    key="-FORMAT_PUBLISH-",
                    tooltip=tips["format_publish"],
                    disabled=self.config.article_format.lower() == "html",
                ),
            ],
        ]

        # 模板配置区块
        template_layout = [
            [
                sg.Checkbox(
                    "使用模板：",
                    default=self.config.use_template and not is_template_empty,
                    key="-USE_TEMPLATE-",
                    enable_events=True,
                    disabled=is_template_empty,
                    tooltip=tips["use_template"],
                    size=(12, 1),
                ),
                sg.Combo(
                    ["随机分类"] + categories,
                    default_value=(
                        current_category
                        if current_category and self.config.use_template
                        else "随机分类"
                    ),
                    key="-TEMPLATE_CATEGORY-",
                    size=(18, 1),
                    disabled=not self.config.use_template or is_template_empty,
                    readonly=True,
                    enable_events=True,
                    tooltip=tips["template_category"],
                ),
                sg.Combo(
                    ["随机模板"]
                    + (current_templates if self.config.use_template and current_category else []),
                    default_value=(
                        current_template
                        if current_template and self.config.use_template
                        else "随机模板"
                    ),
                    key="-TEMPLATE-",
                    size=(18, 1),
                    disabled=not self.config.use_template or is_template_empty,
                    readonly=True,
                    tooltip=tips["template"],
                ),
            ],
            [
                sg.Text("模板压缩：", size=(15, 1), tooltip=tips["use_compress"]),
                sg.Checkbox(
                    "压缩模板",
                    default=self.config.use_compress,
                    key="-USE_COMPRESS-",
                    tooltip=tips["use_compress"],
                ),
            ],
        ]

        # 生成配置区块
        generation_layout = [
            [
                sg.Text("最大搜索数量：", size=(15, 1), tooltip=tips["aiforge_search_max_results"]),
                sg.InputText(
                    self.config.aiforge_search_max_results,
                    key="-AIFORGE_SEARCH_MAX_RESULTS-",
                    size=(10, 1),
                    tooltip=tips["aiforge_search_max_results"],
                ),
                sg.Text("最小搜索数量：", size=(15, 1), tooltip=tips["aiforge_search_min_results"]),
                sg.InputText(
                    self.config.aiforge_search_min_results,
                    key="-AIFORGE_SEARCH_MIN_RESULTS-",
                    size=(10, 1),
                    tooltip=tips["aiforge_search_min_results"],
                ),
            ],
            [
                sg.Text("最小文章字数：", size=(15, 1), tooltip=tips["min_article_len"]),
                sg.InputText(
                    self.config.min_article_len,
                    key="-MIN_ARTICLE_LEN-",
                    size=(10, 1),
                    tooltip=tips["min_article_len"],
                ),
                sg.Text("最大文章字数：", size=(15, 1), tooltip=tips["max_article_len"]),
                sg.InputText(
                    self.config.max_article_len,
                    key="-MAX_ARTICLE_LEN-",
                    size=(10, 1),
                    tooltip=tips["max_article_len"],
                ),
            ],
        ]

        # 界面配置区块
        ui_layout = [
            [
                sg.Text("界面字体：", size=(15, 1), tooltip=tips["ui_font"]),
                sg.Combo(
                    filtered_fonts,
                    default_value=font_default_value,
                    key="-FONT_COMBO-",
                    size=(27, 1),
                    disabled=is_sys_font,
                ),
                sg.Checkbox(
                    "默认字体",
                    default=is_sys_font,
                    key="-SYS_FONT-",
                    tooltip="使用系统默认字体",
                    enable_events=True,
                ),
            ],
            [
                sg.Text(
                    "Tips：鼠标悬停标签/输入框，可查看该条目的详细说明。",
                    size=(70, 1),
                    text_color="gray",
                ),
            ],
        ]

        # 使用Frame将不同配置区块分组
        content_layout = [
            [
                sg.Frame(
                    "发布配置",
                    publish_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "模板配置",
                    template_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "生成配置",
                    generation_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "界面配置",
                    ui_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [sg.VPush()],  # 垂直填充，将按钮和版本信息推到底部
            # 按钮行
            [
                sg.Button("保存配置", key="-SAVE_BASE-"),
                sg.Button("恢复默认", key="-RESET_BASE-"),
            ],
            # 软件版本信息固定在底部
            [
                sg.Push(),  # 将版本信息推到右侧
                sg.Text(
                    f"软件版本: {self.config.get_config_version()}",
                    key="-CONFIG_VERSION-",
                    font=("Arial", 8),
                    text_color="gray",
                ),
            ],
        ]

        # 使用Frame包装内容，避免滚动问题
        content_frame = sg.Frame("", content_layout, border_width=0, pad=(0, 0))

        # 外层Column充满高度，不启用滚动
        return [
            [
                sg.Column(
                    [[content_frame]],
                    expand_x=True,
                    expand_y=True,
                    pad=(0, 0),
                )
            ]
        ]

    def create_aiforge_tab(self):
        """创建 AIForge 配置 TAB 布局，显示选中的 LLM 提供商的所有参数"""
        aiforge_config = self.config.aiforge_config
        llm_providers = list(aiforge_config["llm"].keys())
        default_provider = aiforge_config["default_llm_provider"]

        # 获取当前提供商的配置，防止键不存在
        provider_config = aiforge_config["llm"].get(default_provider, {})

        # 通用配置区块
        general_layout = [
            [
                sg.Text("语言:", size=(15, 1), tooltip="AIForge使用的语言"),
                sg.InputText(
                    "中文",
                    key="-AIFORGE_LOCALE-",
                    size=(50, 1),
                    tooltip="AIForge使用的语言",
                    disabled=True,
                ),
            ],
            [
                sg.Text("最大重试次数:", size=(15, 1)),
                sg.InputText(
                    aiforge_config["max_rounds"],
                    key="-AIFORGE_MAXROUNDS-",
                    size=(11, 1),
                    tooltip="代码生成最大重试次数",
                ),
                sg.Text("默认最大Tokens:", size=(15, 1)),
                sg.InputText(
                    aiforge_config.get("max_tokens", 4096),
                    key="-AIFORGE_DEFAULT_MAX_TOKENS-",
                    size=(11, 1),
                    tooltip="默认的最大Token数量",
                ),
            ],
        ]

        # LLM提供商配置区块
        llm_layout = [
            [
                sg.Text("模型提供商*:", size=(15, 1)),
                sg.Combo(
                    llm_providers,
                    default_value=default_provider,
                    key="-AIFORGE_DEFAULT_LLM_PROVIDER-",
                    size=(15, 1),
                    readonly=True,
                    enable_events=True,
                    tooltip="AIForge使用的LLM 提供商",
                ),
                sg.Text("类型:", size=(10, 1)),
                sg.InputText(
                    provider_config.get("type", ""),
                    key="-AIFORGE_TYPE-",
                    size=(15, 1),
                    disabled=True,  # 类型通常不可编辑
                ),
            ],
            [
                sg.Text("模型*:", size=(15, 1)),
                sg.InputText(
                    provider_config.get("model", ""),
                    key="-AIFORGE_MODEL-",
                    size=(50, 1),
                    tooltip="使用的具体模型名称",
                ),
            ],
            [
                sg.Text("API KEY*:", size=(15, 1)),
                sg.InputText(
                    provider_config.get("api_key", ""),
                    key="-AIFORGE_API_KEY-",
                    size=(50, 1),
                    tooltip="模型提供商的API KEY（必填）",
                    enable_events=True,
                    # password_char="*",
                ),
            ],
            [
                sg.Text("Base URL*:", size=(15, 1)),
                sg.InputText(
                    provider_config.get("base_url", ""),
                    key="-AIFORGE_BASE_URL-",
                    size=(50, 1),
                    tooltip="API的基础地址",
                ),
            ],
            [
                sg.Text("超时时间 (秒):", size=(15, 1)),
                sg.InputText(
                    provider_config.get("timeout", 30),
                    key="-AIFORGE_TIMEOUT-",
                    size=(11, 1),
                    tooltip="API请求的超时时间（秒）",
                ),
                sg.Text("最大 Tokens:", size=(15, 1)),
                sg.InputText(
                    provider_config.get("max_tokens", 8192),
                    key="-AIFORGE_MAX_TOKENS-",
                    size=(11, 1),
                    tooltip="控制生成内容的长度，建议根据模型支持范围设置",
                ),
            ],
        ]

        # 缓存配置区块
        cache_config = aiforge_config.get("cache", {}).get("code", {})
        cache_layout = [
            [
                sg.Text("启用缓存:", size=(15, 1)),
                sg.Checkbox(
                    "",
                    default=cache_config.get("enabled", True),
                    key="-CACHE_ENABLED-",
                    tooltip="缓存代码有助于后续执行速度（相当于本地执行），但首次较慢",
                ),
            ],
            [
                sg.Text("最大模块数:", size=(15, 1)),
                sg.InputText(
                    cache_config.get("max_modules", 20),
                    key="-CACHE_MAX_MODULES-",
                    size=(10, 1),
                    tooltip="缓存中保存的最大模块数量",
                ),
                sg.Text("失败阈值:", size=(10, 1)),
                sg.InputText(
                    cache_config.get("failure_threshold", 0.8),
                    key="-CACHE_FAILURE_THRESHOLD-",
                    size=(10, 1),
                    tooltip="缓存失败率阈值（0.0-1.0）",
                ),
            ],
            [
                sg.Text("最大保存天数:", size=(15, 1)),
                sg.InputText(
                    cache_config.get("max_age_days", 30),
                    key="-CACHE_MAX_AGE_DAYS-",
                    size=(10, 1),
                    tooltip="缓存数据的最大保存天数",
                ),
                sg.Text("清理间隔 (分钟):", size=(15, 1)),
                sg.InputText(
                    cache_config.get("cleanup_interval", 10),
                    key="-CACHE_CLEANUP_INTERVAL-",
                    size=(10, 1),
                    tooltip="自动清理缓存的时间间隔（分钟）",
                ),
            ],
        ]

        # 使用Frame将不同配置区块分组
        content_layout = [
            [
                sg.Frame(
                    "通用配置",
                    general_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "LLM提供商配置",
                    llm_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "代码缓存配置",
                    cache_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [sg.VPush()],  # 垂直填充，将按钮推到底部
            [
                sg.Button("保存配置", key="-SAVE_AIFORGE-"),
                sg.Button("恢复默认", key="-RESET_AIFORGE-"),
            ],
        ]

        # 使用Frame包装内容，避免滚动问题
        content_frame = sg.Frame("", content_layout, border_width=0, pad=(0, 0))

        # 外层Column充满高度，不启用滚动
        return [
            [
                sg.Column(
                    [[content_frame]],
                    expand_x=True,
                    expand_y=True,
                    pad=(0, 0),
                )
            ]
        ]

    def create_creative_tab(self):
        """创建创意模式配置标签页"""
        config = self.config.get_config()
        creative_config = config.get("creative_config", {})

        # 风格转换配置
        style_config = creative_config.get("style_transform", {})
        style_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=style_config.get("enabled", False),
                    key="-STYLE_TRANSFORM_ENABLED-",
                    enable_events=True,
                    tooltip="启用风格转换",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                ),
                sg.Text("风格类型:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Combo(
                    [
                        "莎士比亚戏剧",
                        "侦探小说",
                        "科幻小说",
                        "古典诗词",
                        "现代诗歌",
                        "学术论文",
                        "新闻报道",
                    ],
                    default_value=self._get_style_display_name(
                        style_config.get("style_target", "shakespeare")
                    ),
                    key="-STYLE_TARGET-",
                    size=(15, 1),
                    readonly=True,
                    disabled=not style_config.get("enabled", False),
                    tooltip="选择文体转换风格",
                    pad=((0, 3), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 时空穿越配置
        time_config = creative_config.get("time_travel", {})
        time_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=time_config.get("enabled", False),
                    key="-TIME_TRAVEL_ENABLED-",
                    enable_events=True,
                    tooltip="启用时空穿越",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                ),
                sg.Text("时空视角:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Combo(
                    ["古代视角", "现代视角", "未来视角"],
                    default_value=self._get_time_display_name(
                        time_config.get("time_perspective", "ancient")
                    ),
                    key="-TIME_PERSPECTIVE-",
                    size=(17, 1),
                    readonly=True,
                    disabled=not time_config.get("enabled", False),
                    tooltip="选择时空视角",
                    pad=((0, 3), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 角色扮演配置
        role_config = creative_config.get("role_play", {})
        current_role = role_config.get("role_character", "libai")
        custom_character = role_config.get("custom_character", "")

        role_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=role_config.get("enabled", False),
                    key="-ROLE_PLAY_ENABLED-",
                    enable_events=True,
                    tooltip="启用角色扮演",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                ),
                sg.Text("角色类型:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Combo(
                    self._get_all_role_display_names(),
                    default_value=self._get_role_display_name(current_role),
                    key="-ROLE_CHARACTER-",
                    size=(20, 1),
                    readonly=True,
                    disabled=not role_config.get("enabled", False),
                    enable_events=True,
                    tooltip="选择角色身份或自定义人物",
                    pad=((0, 8), (0, 0)),
                ),
                sg.Text("自定义:", size=(6, 1), pad=((0, 5), (0, 0))),
                sg.Input(
                    default_text=custom_character,
                    key="-CUSTOM_CHARACTER-",
                    size=(15, 1),
                    disabled=current_role != "custom" or not role_config.get("enabled", False),
                    tooltip="先选择自定义，输入要模仿的人物名称，如：张三、李四、王五等",
                    pad=((0, 3), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 多维度创意配置
        multi_config = creative_config.get("multi_dimensional", {})
        multi_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=multi_config.get("enabled", False),
                    key="-MULTI_DIMENSIONAL_ENABLED-",
                    enable_events=True,
                    tooltip="启用多维度创意",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                ),
                sg.Text("目标受众:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Combo(
                    [
                        "通用受众",
                        "Z世代",
                        "职场精英",
                        "学生党",
                        "宝妈群体",
                        "退休人员",
                        "创业者",
                        "技术人员",
                        "文艺青年",
                        "商务人士",
                        "教育工作者",
                        "医护人员",
                        "自由职业者",
                        "投资者",
                        "运动爱好者",
                    ],
                    default_value=(
                        multi_config.get("target_audience", "通用受众")
                        if multi_config.get("target_audience")
                        else "通用受众"
                    ),
                    key="-TARGET_AUDIENCE-",
                    size=(15, 1),
                    readonly=False,  # 允许用户输入自定义受众
                    disabled=not multi_config.get("enabled", False),
                    tooltip="选择目标受众群体或输入自定义受众",
                    pad=((0, 8), (0, 0)),
                ),
                sg.Text("创意程度:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Combo(
                    ["保守型", "平衡型", "实验型"],
                    default_value=self._get_creativity_display_name(
                        multi_config.get("creativity_level", "balanced")
                    ),
                    key="-CREATIVITY_LEVEL-",
                    size=(12, 1),
                    readonly=True,
                    disabled=not multi_config.get("enabled", False),
                    tooltip="保守型：稳妅可靠；平衡型：创意与实用并重；实验型：大胆创新",
                    pad=((0, 3), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 文化融合配置
        cultural_config = creative_config.get("cultural_fusion", {})
        cultural_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=cultural_config.get("enabled", False),
                    key="-CULTURAL_FUSION_ENABLED-",
                    enable_events=True,
                    tooltip="启用文化融合",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                ),
                sg.Text("文化视角:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Combo(
                    ["东方哲学", "西方思辨", "日式物哀", "法式浪漫", "美式自由"],
                    default_value=self._get_cultural_display_name(
                        cultural_config.get("cultural_perspective", "eastern_philosophy")
                    ),
                    key="-CULTURAL_PERSPECTIVE-",
                    size=(15, 1),
                    readonly=True,
                    disabled=not cultural_config.get("enabled", False),
                    tooltip="选择文化视角进行内容重新诠释",
                    pad=((0, 3), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 动态变形配置
        dynamic_config = creative_config.get("dynamic_transform", {})
        dynamic_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=dynamic_config.get("enabled", False),
                    key="-DYNAMIC_TRANSFORM_ENABLED-",
                    enable_events=True,
                    tooltip="启用动态变形",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                ),
                sg.Text("变形场景:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Combo(
                    [
                        "电梯演讲版",
                        "睡前故事版",
                        "辩论赛版",
                        "诗歌版",
                        "漫画脚本版",
                        "播客脚本版",
                        "社交媒体版",
                    ],
                    default_value=self._get_scenario_display_name(
                        dynamic_config.get("scenario", "elevator_pitch")
                    ),
                    key="-SCENARIO-",
                    size=(15, 1),
                    readonly=True,
                    disabled=not dynamic_config.get("enabled", False),
                    tooltip="选择内容变形的目标场景",
                    pad=((0, 3), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 体裁融合配置
        genre_config = creative_config.get("genre_fusion", {})
        genre_combination = genre_config.get("genre_combination", ["scifi", "wuxia"])

        genre_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=genre_config.get("enabled", False),
                    key="-GENRE_FUSION_ENABLED-",
                    enable_events=True,
                    tooltip="启用体裁融合",
                    size=(1, 1),
                    pad=((0, 0), (0, 0)),
                ),
                sg.Text("体裁组合:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Checkbox(
                    "科幻",
                    default="scifi" in genre_combination,
                    key="-GENRE_SCIFI-",
                    size=(5, 1),
                    disabled=not genre_config.get("enabled", False),
                    pad=((0, 0), (0, 0)),
                ),
                sg.Checkbox(
                    "武侠",
                    default="wuxia" in genre_combination,
                    key="-GENRE_WUXIA-",
                    size=(5, 1),
                    disabled=not genre_config.get("enabled", False),
                    pad=((0, 0), (0, 0)),
                ),
            ],
            [
                sg.Text("", size=(9, 1)),  # 空白占位符，与上一行对齐
                sg.Checkbox(
                    "推理",
                    default="mystery" in genre_combination,
                    key="-GENRE_MYSTERY-",
                    size=(5, 1),
                    disabled=not genre_config.get("enabled", False),
                    pad=((0, 0), (0, 0)),
                ),
                sg.Checkbox(
                    "爱情",
                    default="romance" in genre_combination,
                    key="-GENRE_ROMANCE-",
                    size=(5, 1),
                    disabled=not genre_config.get("enabled", False),
                    pad=((0, 0), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # AI人格配置
        ai_persona_config = creative_config.get("ai_persona", {})
        ai_persona_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=ai_persona_config.get("enabled", False),
                    key="-AI_PERSONA_ENABLED-",
                    enable_events=True,
                    tooltip="启用AI人格",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                ),
                sg.Text("人格类型:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Combo(
                    [
                        "自动选择",
                        "梦境诗人",
                        "数据哲学家",
                        "时空旅者",
                        "情感治愈师",
                        "悬疑侦探",
                        "文化探索者",
                        "科技预言家",
                        "生活观察家",
                    ],
                    default_value=self._get_persona_display_name(
                        ai_persona_config.get("persona_type", "auto")
                    ),
                    key="-PERSONA_TYPE-",
                    size=(10, 1),
                    readonly=True,
                    disabled=not ai_persona_config.get("enabled", False),
                    tooltip="选择AI人格类型，或让系统自动根据话题选择最合适的人格",
                    pad=((0, 3), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 组合模式配置
        combination_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=creative_config.get("combination_mode", False),
                    key="-COMBINATION_MODE-",
                    tooltip="允许组合使用",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                ),
                sg.Text(
                    "启用后可同时使用多个创意模块，按顺序应用变换效果",
                    size=(50, 1),
                    text_color="gray",
                    pad=((0, 3), (0, 0)),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 智能推荐配置
        smart_config = creative_config.get("smart_recommendation", {})
        smart_layout = [
            [sg.VPush()],  # 顶部填充
            [
                sg.Checkbox(
                    "",
                    default=smart_config.get("enabled", True),
                    key="-SMART_RECOMMENDATION-",
                    tooltip="启用智能推荐",
                    size=(1, 1),
                    pad=((3, 0), (0, 0)),
                    enable_events=True,
                ),
                sg.Text("推荐类型:", size=(8, 1), pad=((0, 5), (0, 0))),
                sg.Checkbox(
                    "基于话题",
                    default=smart_config.get("topic_based", True),
                    key="-TOPIC_BASED-",
                    size=(8, 1),
                    pad=((0, 5), (0, 0)),
                    disabled=not smart_config.get("enabled", True),
                ),
                sg.Checkbox(
                    "基于受众",
                    default=smart_config.get("audience_based", True),
                    key="-AUDIENCE_BASED-",
                    size=(8, 1),
                    pad=((0, 5), (0, 0)),
                    disabled=not smart_config.get("enabled", True),
                ),
                sg.Checkbox(
                    "基于平台",
                    default=smart_config.get("platform_based", True),
                    key="-PLATFORM_BASED-",
                    size=(8, 1),
                    pad=((0, 3), (0, 0)),
                    disabled=not smart_config.get("enabled", True),
                ),
            ],
            [sg.VPush()],  # 底部填充
        ]

        # 主布局，使用Frame分组，采用与基础配置界面相同的风格
        content_layout = [
            # 创意模式 - 两个一行，各占一半宽度
            [
                sg.Frame(
                    "风格转换",
                    style_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                ),
                sg.Frame(
                    "时空穿越",
                    time_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                ),
            ],
            [
                sg.Frame(
                    "角色扮演",
                    role_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "多维度创意",
                    multi_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "文化融合",
                    cultural_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                ),
                sg.Frame(
                    "动态变形",
                    dynamic_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                ),
            ],
            [
                sg.Frame(
                    "体裁融合",
                    genre_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                ),
                sg.Frame(
                    "AI人格团队",
                    ai_persona_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                ),
            ],
            # 组合和智能推荐配置
            [
                sg.Frame(
                    "组合模式",
                    combination_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [
                sg.Frame(
                    "智能推荐",
                    smart_layout,
                    font=("Arial", 10, "bold"),
                    relief=sg.RELIEF_GROOVE,
                    border_width=2,
                    pad=(5, 5),
                    expand_x=True,
                )
            ],
            [sg.VPush()],  # 垂直填充，将按钮推到底部
            [
                sg.Button("保存配置", key="-SAVE_CREATIVE_CONFIG-"),
                sg.Button("恢复默认", key="-RESET_CREATIVE_CONFIG-"),
            ],
        ]

        # 使用Frame包装内容，避免滚动问题
        content_frame = sg.Frame("", content_layout, border_width=0, pad=(0, 0))

        # 外层Column充满高度，不启用滚动
        return [
            [
                sg.Column(
                    [[content_frame]],
                    expand_x=True,
                    expand_y=True,
                    pad=(0, 0),
                )
            ]
        ]

    def create_layout(self):
        """创建主布局"""
        return [
            [
                sg.TabGroup(
                    [
                        [sg.Tab("基础", self.create_base_tab(), key="-TAB_BASE-")],
                        [sg.Tab("创意", self.create_creative_tab(), key="-TAB_CREATIVE-")],
                        [sg.Tab("热搜平台", self.create_platforms_tab(), key="-TAB_PLATFORM-")],
                        [sg.Tab("微信公众号*", self.create_wechat_tab(), key="-TAB_WECHAT-")],
                        [sg.Tab("大模型API*", self.create_api_tab(), key="-TAB_API-")],
                        [sg.Tab("图片生成API", self.create_img_api_tab(), key="-TAB_IMG_API-")],
                        [sg.Tab("AIForge", self.create_aiforge_tab(), key="-TAB_AIFORGE-")],
                    ],
                    key="-TAB_GROUP-",
                )
            ],
        ]

    def clear_tab(self, tab):
        """清空指定 tab 的内容，并清理相关的 key，但不清理 Tab 本身的 key"""
        tab_widget = tab.Widget
        tab_key = tab.Key  # 获取 Tab 本身的 key，例如 "-TAB_PLATFORM-"
        # 收集 tab 内的所有 key，但排除 Tab 本身的 key
        keys_to_remove = []
        # 遍历 window 的 key_dict，检查哪些 key 属于当前 tab
        for key, element in list(self.window.key_dict.items()):  # 使用 list 避免运行时修改字典
            if key == tab_key:  # 跳过 Tab 本身的 key
                continue
            if hasattr(element, "Widget") and element.Widget:
                try:
                    # 获取元素所在的父容器
                    parent = element.Widget
                    # 向上遍历父容器，直到找到顶层容器
                    while parent:
                        if parent == tab_widget:
                            keys_to_remove.append(key)
                            break
                        parent = parent.master  # 继续向上查找父容器
                except Exception as e:  # noqa 841
                    continue

        # 从 window 的 key_dict 中移除这些 key
        for key in keys_to_remove:
            if key in self.window.key_dict:
                del self.window.key_dict[key]

        # 清空 tab 的内容
        for widget in tab_widget.winfo_children():
            widget.destroy()

    def update_tab(self, tab_key, new_layout):
        """更新指定 tab 的内容"""
        # 清空现有内容
        tab = self.window[tab_key]
        self.clear_tab(tab)
        # 直接使用 new_layout（已经是 [[sg.Column(...)]]
        self.window.extend_layout(self.window[tab_key], new_layout)
        # 强制刷新布局，确保内容正确渲染
        self.window.refresh()

    def get_mac_clipboard_events(self):
        """获取需要适配macOS剪贴板问题的输入框事件列表"""
        mac_clipboard_events = []

        # 微信凭证 - 根据实际数量动态生成
        for i in range(self.wechat_count):
            mac_clipboard_events.extend([f"-WECHAT_APPID_{i}-", f"-WECHAT_SECRET_{i}-"])

        # 大模型API - 根据配置中实际存在的API提供商动态生成
        for api in self.config.api_list:
            mac_clipboard_events.append(f"-{api}_API_KEYS-")

        # 图片API和AIForge
        mac_clipboard_events.extend(["-ALI_API_KEY-", "-AIFORGE_API_KEY-"])

        return mac_clipboard_events

    def _get_style_display_name(self, style_key):
        """获取风格的显示名称"""
        style_mapping = {
            "shakespeare": "莎士比亚戏剧",
            "detective": "侦探小说",
            "scifi": "科幻小说",
            "classical_poetry": "古典诗词",
            "modern_poetry": "现代诗歌",
            "academic": "学术论文",
            "news": "新闻报道",
        }
        return style_mapping.get(style_key, "莎士比亚戏剧")

    def _get_style_key(self, display_name):
        """获取风格的配置键"""
        display_mapping = {
            "莎士比亚戏剧": "shakespeare",
            "侦探小说": "detective",
            "科幻小说": "scifi",
            "古典诗词": "classical_poetry",
            "现代诗歌": "modern_poetry",
            "学术论文": "academic",
            "新闻报道": "news",
        }
        return display_mapping.get(display_name, "shakespeare")

    def _get_time_display_name(self, time_key):
        """获取时空视角的显示名称"""
        time_mapping = {"ancient": "古代视角", "modern": "现代视角", "future": "未来视角"}
        return time_mapping.get(time_key, "古代视角")

    def _get_time_key(self, display_name):
        """获取时空视角的配置键"""
        display_mapping = {"古代视角": "ancient", "现代视角": "modern", "未来视角": "future"}
        return display_mapping.get(display_name, "ancient")

    def _get_all_role_display_names(self):
        """获取所有角色的显示名称列表"""
        return [
            "李白（浪漫主义诗人）",
            "杜甫（现实主义诗人）",
            "苏轼（豪放派词人）",
            "李清照（婉约派词人）",
            "曹雪芹（红楼梦作者）",
            "施耐庵（水浒传作者）",
            "吴承恩（西游记作者）",
            "蒲松龄（聊斋志异作者）",
            "鲁迅（现代文学奠基人）",
            "老舍（人民艺术家）",
            "巴金（现代作家）",
            "钱钟书（学者作家）",
            "金庸（武侠小说大师）",
            "古龙（新派武侠代表）",
            "白岩松（央视主持人）",
            "崔永元（知名主持人）",
            "杨澜（媒体人）",
            "鲁豫（访谈节目主持人）",
            "周杰伦（流行音乐天王）",
            "邓丽君（华语歌坛传奇）",
            "李荣浩（创作型歌手）",
            "郭德纲（相声演员）",
            "赵本山（小品演员）",
            "自定义人物",
        ]

    def _get_role_display_name(self, role_key):
        """获取角色的显示名称"""
        role_mapping = {
            "libai": "李白（浪漫主义诗人）",
            "dufu": "杜甫（现实主义诗人）",
            "sushi": "苏轼（豪放派词人）",
            "liqingzhao": "李清照（婉约派词人）",
            "caoxueqin": "曹雪芹（红楼梦作者）",
            "shinaian": "施耐庵（水浒传作者）",
            "wuchengen": "吴承恩（西游记作者）",
            "pusonglin": "蒲松龄（聊斋志异作者）",
            "luxun": "鲁迅（现代文学奠基人）",
            "laoshe": "老舍（人民艺术家）",
            "bajin": "巴金（现代作家）",
            "qianjunru": "钱钟书（学者作家）",
            "jinyong": "金庸（武侠小说大师）",
            "gulongxia": "古龙（新派武侠代表）",
            "baiyansong": "白岩松（央视主持人）",
            "cuiyongyuan": "崔永元（知名主持人）",
            "yanglan": "杨澜（媒体人）",
            "luyu": "鲁豫（访谈节目主持人）",
            "zhoujielun": "周杰伦（流行音乐天王）",
            "denglijun": "邓丽君（华语歌坛传奇）",
            "lironghao": "李荣浩（创作型歌手）",
            "guodegang": "郭德纲（相声演员）",
            "zhaobenshang": "赵本山（小品演员）",
            "custom": "自定义人物",
        }
        return role_mapping.get(role_key, "李白（浪漫主义诗人）")

    def _get_role_key(self, display_name):
        """获取角色的配置键"""
        display_mapping = {
            "李白（浪漫主义诗人）": "libai",
            "杜甫（现实主义诗人）": "dufu",
            "苏轼（豪放派词人）": "sushi",
            "李清照（婉约派词人）": "liqingzhao",
            "曹雪芹（红楼梦作者）": "caoxueqin",
            "施耐庵（水浒传作者）": "shinaian",
            "吴承恩（西游记作者）": "wuchengen",
            "蒲松龄（聊斋志异作者）": "pusonglin",
            "鲁迅（现代文学奠基人）": "luxun",
            "老舍（人民艺术家）": "laoshe",
            "巴金（现代作家）": "bajin",
            "钱钟书（学者作家）": "qianjunru",
            "金庸（武侠小说大师）": "jinyong",
            "古龙（新派武侠代表）": "gulongxia",
            "白岩松（央视主持人）": "baiyansong",
            "崔永元（知名主持人）": "cuiyongyuan",
            "杨澜（媒体人）": "yanglan",
            "鲁豫（访谈节目主持人）": "luyu",
            "周杰伦（流行音乐天王）": "zhoujielun",
            "邓丽君（华语歌坛传奇）": "denglijun",
            "李荣浩（创作型歌手）": "lironghao",
            "郭德纲（相声演员）": "guodegang",
            "赵本山（小品演员）": "zhaobenshang",
            "自定义人物": "custom",
        }
        return display_mapping.get(display_name, "libai")

    def _get_platform_display_name(self, platform_key):
        """获取平台的显示名称"""
        platform_mapping = {
            "wechat": "微信公众号",
            "xiaohongshu": "小红书",
            "douyin": "抖音",
            "toutiao": "今日头条",
            "baijiahao": "百家号",
            "zhihu": "知乎",
            "douban": "豆瓣",
        }
        return platform_mapping.get(platform_key, "微信公众号")

    def _get_platform_key(self, display_name):
        """获取平台的配置键"""
        display_mapping = {
            "微信公众号": "wechat",
            "小红书": "xiaohongshu",
            "抖音": "douyin",
            "今日头条": "toutiao",
            "百家号": "baijiahao",
            "知乎": "zhihu",
            "豆瓣": "douban",
        }
        return display_mapping.get(display_name, "wechat")

    def _get_creativity_display_name(self, key):
        """将创意程度键转换为显示名称"""
        mapping = {"conservative": "保守型", "balanced": "平衡型", "experimental": "实验型"}
        return mapping.get(key, "平衡型")

    def _get_creativity_key(self, display_name):
        """将创意程度显示名称转换为键"""
        mapping = {"保守型": "conservative", "平衡型": "balanced", "实验型": "experimental"}
        return mapping.get(display_name, "balanced")

    def _get_cultural_display_name(self, key):
        """将文化视角键转换为显示名称"""
        mapping = {
            "eastern_philosophy": "东方哲学",
            "western_logic": "西方思辨",
            "japanese_mono": "日式物哀",
            "french_romance": "法式浪漫",
            "american_freedom": "美式自由",
        }
        return mapping.get(key, "东方哲学")

    def _get_cultural_key(self, display_name):
        """将文化视角显示名称转换为键"""
        mapping = {
            "东方哲学": "eastern_philosophy",
            "西方思辨": "western_logic",
            "日式物哀": "japanese_mono",
            "法式浪漫": "french_romance",
            "美式自由": "american_freedom",
        }
        return mapping.get(display_name, "eastern_philosophy")

    def _get_scenario_display_name(self, key):
        """将变形场景键转换为显示名称"""
        mapping = {
            "elevator_pitch": "电梯演讲版",
            "bedtime_story": "睡前故事版",
            "debate_argument": "辩论赛版",
            "poetry_version": "诗歌版",
            "comic_script": "漫画脚本版",
            "podcast_script": "播客脚本版",
            "social_media": "社交媒体版",
        }
        return mapping.get(key, "电梯演讲版")

    def _get_scenario_key(self, display_name):
        """将变形场景显示名称转换为键"""
        mapping = {
            "电梯演讲版": "elevator_pitch",
            "睡前故事版": "bedtime_story",
            "辩论赛版": "debate_argument",
            "诗歌版": "poetry_version",
            "漫画脚本版": "comic_script",
            "播客脚本版": "podcast_script",
            "社交媒体版": "social_media",
        }
        return mapping.get(display_name, "elevator_pitch")

    def _get_genre_display_name(self, key):
        """将体裁键转换为显示名称"""
        mapping = {
            "scifi": "科幻",
            "wuxia": "武侠",
            "detective": "推理",
            "romance": "爱情",
            "history": "历史",
            "fantasy": "奇幻",
            "thriller": "惊悚",
            "comedy": "喜剧",
        }
        return mapping.get(key, "科幻")

    def _get_genre_key(self, display_name):
        """将体裁显示名称转换为键"""
        mapping = {
            "科幻": "scifi",
            "武侠": "wuxia",
            "推理": "detective",
            "爱情": "romance",
            "历史": "history",
            "奇幻": "fantasy",
            "惊悚": "thriller",
            "喜剧": "comedy",
        }
        return mapping.get(display_name, "scifi")

    def _get_persona_display_name(self, key):
        """将AI人格键转换为显示名称"""
        mapping = {
            "auto": "自动选择",
            "dreamer_poet": "梦境诗人",
            "data_philosopher": "数据哲学家",
            "time_traveler": "时空旅者",
            "emotion_healer": "情感治愈师",
            "mystery_detective": "悬疑侦探",
            "culture_explorer": "文化探索者",
            "tech_visionary": "科技预言家",
            "life_observer": "生活观察家",
        }
        return mapping.get(key, "自动选择")

    def _get_persona_key(self, display_name):
        """将AI人格显示名称转换为键"""
        mapping = {
            "自动选择": "auto",
            "梦境诗人": "dreamer_poet",
            "数据哲学家": "data_philosopher",
            "时空旅者": "time_traveler",
            "情感治愈师": "emotion_healer",
            "悬疑侦探": "mystery_detective",
            "文化探索者": "culture_explorer",
            "科技预言家": "tech_visionary",
            "生活观察家": "life_observer",
        }
        return mapping.get(display_name, "auto")

    def run(self):
        while True:
            event, values = self.window.read()  # type: ignore
            if event in (sg.WIN_CLOSED, "-EXIT-"):
                break
            # 在事件循环中使用
            elif event in self.get_mac_clipboard_events():
                if sys.platform == "darwin" and values[event]:
                    fixed_value = utils.fix_mac_clipboard(values[event])
                    if fixed_value != values[event]:  # 只有内容真正改变时才更新
                        self.window[event].update(fixed_value)
                        self.window.refresh()
                        # 可选：重新设置焦点确保用户体验
                        self.window[event].set_focus()
            elif event == "-ARTICLE_FORMAT-":
                if values["-ARTICLE_FORMAT-"] == "html":
                    # HTML格式禁用格式化勾选框
                    self.window["-FORMAT_PUBLISH-"].update(disabled=True)
                else:
                    # 其他格式（markdown, txt）启用格式化勾选框
                    self.window["-FORMAT_PUBLISH-"].update(disabled=False)

            # 动态启用/禁用下拉列表
            elif event == "-USE_TEMPLATE-":
                is_enabled = values["-USE_TEMPLATE-"]
                self.window["-TEMPLATE_CATEGORY-"].update(disabled=not is_enabled)
                self.window["-TEMPLATE-"].update(disabled=not is_enabled)
                if not is_enabled:
                    self.window["-TEMPLATE_CATEGORY-"].update(value="随机分类")
                    self.window["-TEMPLATE-"].update(value="随机模板")
                self.window.refresh()

            elif event == "-TEMPLATE_CATEGORY-":
                selected_category = values["-TEMPLATE_CATEGORY-"]

                if selected_category == "随机分类":
                    templates = ["随机模板"]
                    self.window["-TEMPLATE-"].update(
                        values=templates, value="随机模板", disabled=False
                    )
                else:
                    templates = PathManager.get_templates_by_category(selected_category)

                    if not templates:
                        sg.popup_error(
                            f"分类 『{selected_category}』 的模板数量为0，不可选择",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                        self.window["-TEMPLATE_CATEGORY-"].update(value="随机分类")
                        self.window["-TEMPLATE-"].update(
                            values=["随机模板"], value="随机模板", disabled=False
                        )
                    else:
                        template_options = ["随机模板"] + templates
                        self.window["-TEMPLATE-"].update(
                            values=template_options, value="随机模板", disabled=False
                        )

                self.window.refresh()

            # 切换API TAB
            elif event == "-API_TYPE-":
                tab_group = self.window["-API_TAB_GROUP-"]
                # 遍历 TabGroup 的子 TAB，找到匹配的标题
                for tab in tab_group.Widget.tabs():  # type: ignore
                    tab_text = tab_group.Widget.tab(tab, "text")  # type: ignore
                    if tab_text == values["-API_TYPE-"]:
                        tab_group.Widget.select(tab)  # type: ignore
                        break
                self.window.refresh()

            # 添加微信凭证
            elif event == "-ADD_WECHAT-":
                credentials = self.config.wechat_credentials  # 直接使用内存中的 credentials
                credentials.append(
                    {
                        "appid": "",
                        "appsecret": "",
                        "author": "",
                        "call_sendall": False,
                        "sendall": True,
                        "tag_id": 0,
                    }
                )
                self.wechat_count = len(credentials)
                try:
                    self.update_tab("-TAB_WECHAT-", self.create_wechat_tab())
                    self.window["-WECHAT_CREDENTIALS_COLUMN-"].contents_changed()  # type: ignore
                    self.window["-WECHAT_CREDENTIALS_COLUMN-"].Widget.canvas.yview_moveto(1.0)  # type: ignore # noqa 501
                    self.window.TKroot.update_idletasks()
                    self.window.TKroot.update()
                    self.window.refresh()
                    self.window["-TAB_WECHAT-"].Widget.update()  # type: ignore
                    self.window["-WECHAT_CREDENTIALS_COLUMN-"].Widget.update()  # type: ignore
                except Exception as e:
                    sg.popup_error(
                        f"添加凭证失败: {e}",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
            # 删除微信凭证
            elif event.startswith("-DELETE_WECHAT_"):
                match = re.search(r"-DELETE_WECHAT_(\d+)", event)
                if match:
                    index = int(match.group(1))
                    credentials = self.config.wechat_credentials  # 直接使用内存中的 credentials
                    if 0 <= index < len(credentials):
                        try:
                            credentials.pop(index)
                            self.wechat_count = len(credentials)
                            self.update_tab("-TAB_WECHAT-", self.create_wechat_tab())
                            self.window.TKroot.update_idletasks()
                            self.window.TKroot.update()
                            self.window.refresh()
                            self.window["-TAB_WECHAT-"].Widget.update()  # type: ignore
                            self.window["-WECHAT_CREDENTIALS_COLUMN-"].Widget.update()  # type: ignore # noqa 501
                        except Exception as e:
                            sg.popup_error(
                                f"删除凭证失败: {e}",
                                title="系统提示",
                                icon=utils.get_gui_icon(),
                                keep_on_top=True,
                            )
                    else:
                        sg.popup_error(
                            f"无效的凭证索引: {index}",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )

            # 保存平台配置
            elif event.startswith("-SAVE_PLATFORMS-"):
                config = self.config.get_config().copy()
                platforms = []
                total_weight = 0.0
                # 动态检测界面上实际的平台数量
                i = 0
                while f"-PLATFORM_NAME_{i}-" in values:
                    try:
                        weight = float(values[f"-PLATFORM_WEIGHT_{i}-"])
                        # 限定weight范围
                        if weight < 0:
                            weight = 0
                            sg.popup_error(
                                f"平台 {values[f'-PLATFORM_NAME_{i}-']} 权重小于0，将被设为0",
                                title="系统提示",
                                icon=utils.get_gui_icon(),
                                keep_on_top=True,
                            )
                            # 更新界面上的权重值
                            self.window[f"-PLATFORM_WEIGHT_{i}-"].update(value=str(weight))
                        elif weight > 1:
                            weight = 1
                            sg.popup_error(
                                f"平台 {values[f'-PLATFORM_NAME_{i}-']} 权重大于1，将被设为1",
                                title="系统提示",
                                icon=utils.get_gui_icon(),
                                keep_on_top=True,
                            )
                            # 更新界面上的权重值
                            self.window[f"-PLATFORM_WEIGHT_{i}-"].update(value=str(weight))

                        total_weight += weight
                        platforms.append({"name": values[f"-PLATFORM_NAME_{i}-"], "weight": weight})
                    except ValueError:
                        sg.popup_error(
                            f"平台 {values[f'-PLATFORM_NAME_{i}-']} 权重必须是数字",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                        break
                    i += 1
                else:
                    if total_weight > 1.0:
                        sg.popup(
                            "平台权重之和超过1，将默认选取微博热搜。",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                    config["platforms"] = platforms
                    if self.config.save_config(config):
                        self.platform_count = len(platforms)  # 同步更新计数器
                        sg.popup(
                            "平台配置已保存",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                    else:
                        sg.popup_error(
                            self.config.error_message,
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )

            # 保存微信配置
            elif event.startswith("-SAVE_WECHAT-"):
                config = self.config.get_config().copy()
                credentials = []
                # 遍历窗口中所有可能的微信凭证键
                max_index = -1
                for key in self.window.AllKeysDict:
                    if isinstance(key, str) and key.startswith("-WECHAT_APPID_"):  # 添加类型检查
                        try:
                            # 提取索引，移除尾部连字符
                            index = int(key.split("_")[-1].rstrip("-"))
                            max_index = max(max_index, index)
                        except ValueError:
                            continue  # 跳过无效键
                max_index = max_index + 1 if max_index >= 0 else 0
                i = 0
                while i <= max_index:
                    appid_key = f"-WECHAT_APPID_{i}-"
                    secret_key = f"-WECHAT_SECRET_{i}-"
                    author_key = f"-WECHAT_AUTHOR_{i}-"
                    call_sendall_key = f"-WECHAT_CALL_SENDALL_{i}-"
                    sendall_key = f"-WECHAT_SENDALL_{i}-"
                    tag_id_key = f"-WECHAT_TAG_ID_{i}-"
                    if (
                        appid_key in self.window.AllKeysDict
                        and secret_key in self.window.AllKeysDict
                        and author_key in self.window.AllKeysDict
                        and call_sendall_key in self.window.AllKeysDict
                        and sendall_key in self.window.AllKeysDict
                        and tag_id_key in self.window.AllKeysDict
                        and self.window[appid_key].visible
                    ):
                        tag_id_value = values.get(tag_id_key, 0)
                        appid = values.get(appid_key, "")
                        appsecret = values.get(secret_key, "")
                        call_sendall = values.get(call_sendall_key, False)
                        sendall = values.get(sendall_key, False)

                        # 只有真正使用tag_id，才校验
                        tag_id = 0
                        if appid and appsecret and call_sendall and not sendall:
                            try:
                                tag_id = int(tag_id_value) if str(tag_id_value).isdigit() else 0
                                if tag_id < 1:
                                    tag_id = 0
                                    sg.popup_error(
                                        f"【凭证 {i+1} 】标签组ID必须 ≥ 1，已设为0（即无效，如果未勾选群发将发布失败）",
                                        title="系统提示",
                                        icon=utils.get_gui_icon(),
                                        keep_on_top=True,
                                    )
                                    self.window[tag_id_key].update(value=str(tag_id))
                            except ValueError:
                                tag_id = 0
                                sg.popup_error(
                                    f"【凭证 {i+1} 】标签组ID必须为数字，已设为0（即无效，如果未勾选群发将发布失败）",
                                    title="系统提示",
                                    icon=utils.get_gui_icon(),
                                    keep_on_top=True,
                                )
                                self.window[tag_id_key].update(value=str(tag_id))

                        credentials.append(
                            {
                                "appid": values.get(appid_key, ""),
                                "appsecret": values.get(secret_key, ""),
                                "author": values.get(author_key, ""),
                                "call_sendall": values.get(call_sendall_key, False),
                                "sendall": values.get(sendall_key, False),
                                "tag_id": tag_id,
                            }
                        )
                    i += 1
                config["wechat"]["credentials"] = credentials
                if self.config.save_config(config):
                    self.wechat_count = len(credentials)  # 同步更新计数器
                    # 刷新界面以确保一致
                    self.update_tab("-TAB_WECHAT-", self.create_wechat_tab())
                    self.window.TKroot.update_idletasks()
                    self.window.TKroot.update()
                    self.window.refresh()
                    self.window["-TAB_WECHAT-"].Widget.update()  # type: ignore
                    self.window["-WECHAT_CREDENTIALS_COLUMN-"].Widget.update()  # type: ignore
                    sg.popup(
                        "微信配置已保存",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 保存 API 配置
            elif event.startswith("-SAVE_API-"):
                config = self.config.get_config().copy()
                api_type = values["-API_TYPE-"]
                if api_type == "硅基流动":
                    api_type = "SiliconFlow"

                config["api"]["api_type"] = api_type
                for api_name in self.config.api_list:
                    try:
                        model_index = int(values[f"-{api_name}_MODEL_INDEX-"])
                        key_index = int(values[f"-{api_name}_KEY_INDEX-"])
                        models = [
                            m.strip()
                            for m in re.split(r",|，", values[f"-{api_name}_MODEL-"])
                            if m.strip()
                        ]
                        api_keys = [
                            k.strip()
                            for k in re.split(r",|，", values[f"-{api_name}_API_KEYS-"])
                            if k.strip()
                        ]
                        if not api_keys:
                            api_keys = [""]  # 确保至少有一个空密钥
                        if key_index >= len(api_keys):
                            raise ValueError(f"{api_name} API KEY 索引超出范围")
                        if model_index >= len(models):
                            raise ValueError(f"{api_name} 模型索引超出范围")
                        api_data = {
                            "key": values[f"-{api_name}_KEY-"],
                            "key_index": key_index,
                            "api_key": api_keys,
                            "model_index": model_index,
                            "api_base": values[f"-{api_name}_API_BASE-"],
                            "model": models,
                        }
                        config["api"][api_name].update(api_data)
                    except ValueError as e:
                        sg.popup_error(
                            f"{api_name} 配置错误: {e}",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                        break
                else:
                    if self.config.save_config(config):
                        sg.popup(
                            "API 配置已保存",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                    else:
                        sg.popup_error(
                            self.config.error_message,
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
            elif event == "-API_TAB_GROUP-":
                try:
                    tab_group = self.window["-API_TAB_GROUP-"]
                    selected_tab_index = tab_group.Widget.index("current")  # type: ignore
                    selected_tab_text = tab_group.Widget.tab(selected_tab_index, "text")  # type: ignore # noqa 501

                    # 转换 tab 文本为显示名称（保持一致性）
                    if selected_tab_text == "硅基流动":
                        display_api_type = "硅基流动"
                    else:
                        display_api_type = selected_tab_text

                    # 更新 API TYPE 下拉框，避免触发循环事件
                    current_value = self.window["-API_TYPE-"].get()
                    if current_value != display_api_type:
                        self.window["-API_TYPE-"].update(value=display_api_type)

                except Exception:
                    # 静默处理异常，避免影响用户体验
                    pass

            # 保存图像 API 配置
            elif event.startswith("-SAVE_IMG_API-"):
                config = self.config.get_config().copy()
                config["img_api"]["api_type"] = values["-IMG_API_TYPE-"]
                config["img_api"]["ali"].update(
                    {"api_key": values["-ALI_API_KEY-"], "model": values["-ALI_MODEL-"]}
                )
                config["img_api"]["picsum"].update(
                    {"api_key": values["-PICSUM_API_KEY-"], "model": values["-PICSUM_MODEL-"]}
                )
                if self.config.save_config(config):
                    sg.popup(
                        "图像 API 配置已保存",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 保存基础配置
            elif event == "-SYS_FONT-":
                if values["-SYS_FONT-"]:
                    self.window["-FONT_COMBO-"].update(disabled=True)
                else:
                    self.window["-FONT_COMBO-"].update(disabled=False)
            elif event.startswith("-SAVE_BASE-"):
                config = self.config.get_config().copy()
                config["publish_platform"] = self._get_platform_key(values["-PUBLISH_PLATFORM-"])
                config["auto_publish"] = values["-AUTO_PUBLISH-"]
                config["format_publish"] = values["-FORMAT_PUBLISH-"]
                config["use_template"] = values["-USE_TEMPLATE-"]
                config["use_compress"] = values["-USE_COMPRESS-"]
                config["article_format"] = values["-ARTICLE_FORMAT-"]

                if values["-SYS_FONT-"]:
                    self.set_global_font("Helvetica")
                else:
                    if values["-FONT_COMBO-"]:
                        if self._validate_font_selection(values["-FONT_COMBO-"]):
                            self.set_global_font(values["-FONT_COMBO-"])
                        else:
                            sg.popup_error(
                                "所选字体不适合界面显示，已重置为默认字体",
                                title="系统提示",
                                icon=utils.get_gui_icon(),
                                keep_on_top=True,
                            )
                            self.window["-FONT_COMBO-"].update(disabled=True)
                            self.set_global_font("Helvetica")
                    else:
                        self.set_global_font("Helvetica")

                if str(values["-AIFORGE_SEARCH_MAX_RESULTS-"]).isdigit():
                    input_value = int(values["-AIFORGE_SEARCH_MAX_RESULTS-"])
                    config["aiforge_search_max_results"] = (
                        input_value
                        if 1 < input_value <= 20
                        else self.config.default_config["aiforge_search_max_results"]
                    )
                    if not (1 < input_value <= 20):
                        self.window["-AIFORGE_SEARCH_MAX_RESULTS-"].update(
                            value=self.config.default_config["aiforge_search_max_results"]
                        )
                else:
                    config["aiforge_search_max_results"] = self.config.default_config[
                        "aiforge_search_max_results"
                    ]
                    self.window["-AIFORGE_SEARCH_MAX_RESULTS-"].update(
                        value=self.config.default_config["aiforge_search_max_results"]
                    )

                if str(values["-AIFORGE_SEARCH_MIN_RESULTS-"]).isdigit():
                    input_value = int(values["-AIFORGE_SEARCH_MIN_RESULTS-"])
                    config["aiforge_search_min_results"] = (
                        input_value
                        if 1
                        < input_value
                        <= self.config.default_config["aiforge_search_max_results"]
                        and input_value
                        < config["aiforge_search_max_results"]  # 最大为10且不能比最大值大
                        else self.config.default_config["aiforge_search_min_results"]
                    )
                    if not (
                        1 < input_value <= self.config.default_config["aiforge_search_max_results"]
                    ):
                        self.window["-AIFORGE_SEARCH_MIN_RESULTS-"].update(
                            value=self.config.default_config["aiforge_search_min_results"]
                        )
                else:
                    config["aiforge_search_min_results"] = self.config.default_config[
                        "aiforge_search_min_results"
                    ]
                    self.window["-AIFORGE_SEARCH_MIN_RESULTS-"].update(
                        value=self.config.default_config["aiforge_search_min_results"]
                    )

                # 文章字数控制
                min_len_input = values["-MIN_ARTICLE_LEN-"]
                max_len_input = values["-MAX_ARTICLE_LEN-"]
                parsed_min_len = None
                parsed_max_len = None

                try:
                    if isinstance(min_len_input, str) and min_len_input.isdigit():
                        parsed_min_len = int(min_len_input)
                    if isinstance(max_len_input, str) and max_len_input.isdigit():
                        parsed_max_len = int(max_len_input)
                except ValueError:
                    pass

                if (
                    parsed_min_len is not None
                    and parsed_max_len is not None
                    and parsed_min_len >= 500
                    and parsed_max_len <= 5000
                    and parsed_min_len <= parsed_max_len
                ):
                    config["min_article_len"] = parsed_min_len
                    config["max_article_len"] = parsed_max_len
                else:
                    config["min_article_len"] = self.config.default_config["min_article_len"]
                    config["max_article_len"] = self.config.default_config["max_article_len"]
                    self.window["-MIN_ARTICLE_LEN-"].update(
                        value=self.config.default_config["min_article_len"]
                    )
                    self.window["-MAX_ARTICLE_LEN-"].update(
                        value=self.config.default_config["max_article_len"]
                    )

                # 处理 template 保存逻辑
                if values["-USE_TEMPLATE-"]:
                    category_value = values["-TEMPLATE_CATEGORY-"]
                    template_value = values["-TEMPLATE-"]

                    config["template_category"] = (
                        category_value if category_value != "随机分类" else ""
                    )
                    config["template"] = template_value if template_value != "随机模板" else ""
                else:
                    config["template_category"] = ""
                    config["template"] = ""

                if self.config.save_config(config):
                    sg.popup(
                        "基础配置已保存",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 恢复默认配置 - 平台
            elif event.startswith("-RESET_PLATFORMS-"):
                config = self.config.get_config().copy()
                config["platforms"] = copy.deepcopy(self.config.default_config["platforms"])
                if self.config.save_config(config):
                    self.platform_count = len(config["platforms"])
                    # 清空并重建平台 tab
                    self.update_tab("-TAB_PLATFORM-", self.create_platforms_tab())
                    sg.popup(
                        "已恢复默认平台配置",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 恢复默认配置 - 微信
            elif event.startswith("-RESET_WECHAT-"):
                config = self.config.get_config().copy()
                config["wechat"]["credentials"] = copy.deepcopy(
                    self.config.default_config["wechat"]["credentials"]
                )
                if self.config.save_config(config):
                    self.wechat_count = len(config["wechat"]["credentials"])
                    # 清空并重建微信 tab
                    self.update_tab("-TAB_WECHAT-", self.create_wechat_tab())
                    sg.popup(
                        "已恢复默认微信配置",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 恢复默认配置 - API
            elif event.startswith("-RESET_API-"):
                config = self.config.get_config().copy()
                config["api"] = copy.deepcopy(self.config.default_config["api"])
                if self.config.save_config(config):
                    # 清空并重建 API tab
                    self.update_tab("-TAB_API-", self.create_api_tab())
                    self.__default_select_api_tab()
                    sg.popup(
                        "已恢复默认API配置",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 恢复默认配置 - 图像 API
            elif event.startswith("-RESET_IMG_API-"):
                config = self.config.get_config().copy()
                config["img_api"] = copy.deepcopy(self.config.default_config["img_api"])
                if self.config.save_config(config):
                    # 清空并重建图像 API tab
                    self.update_tab("-TAB_IMG_API-", self.create_img_api_tab())
                    sg.popup(
                        "已恢复默认图像API配置",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 恢复默认配置 - 基础
            elif event.startswith("-RESET_BASE-"):
                config = self.config.get_config().copy()
                config["auto_publish"] = self.config.default_config["auto_publish"]
                config["format_publish"] = self.config.default_config["format_publish"]
                config["use_template"] = self.config.default_config["use_template"]
                config["use_compress"] = self.config.default_config["use_compress"]
                config["article_format"] = self.config.default_config["article_format"]
                config["aiforge_search_max_results"] = self.config.default_config[
                    "aiforge_search_max_results"
                ]
                config["aiforge_search_min_results"] = self.config.default_config[
                    "aiforge_search_min_results"
                ]
                config["min_article_len"] = self.config.default_config["min_article_len"]
                config["max_article_len"] = self.config.default_config["max_article_len"]
                config["template"] = self.config.default_config["template"]
                self.set_global_font("Helvetica")
                if self.config.save_config(config):
                    self.update_tab("-TAB_BASE-", self.create_base_tab())
                    sg.popup(
                        "已恢复默认基础配置",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 动态更新 AIForge 提供商的所有参数
            elif event == "-AIFORGE_DEFAULT_LLM_PROVIDER-":
                try:
                    selected_provider = values["-AIFORGE_DEFAULT_LLM_PROVIDER-"]
                    # 获取新选中的提供商的配置
                    provider_config = self.config.aiforge_config["llm"].get(selected_provider, {})
                    # 更新所有参数的输入框
                    self.window["-AIFORGE_TYPE-"].update(value=provider_config.get("type", ""))
                    self.window["-AIFORGE_MODEL-"].update(value=provider_config.get("model", ""))
                    self.window["-AIFORGE_API_KEY-"].update(
                        value=provider_config.get("api_key", "")
                    )
                    self.window["-AIFORGE_BASE_URL-"].update(
                        value=provider_config.get("base_url", "")
                    )
                    self.window["-AIFORGE_TIMEOUT-"].update(
                        value=provider_config.get("timeout", 30)
                    )
                    self.window["-AIFORGE_MAX_TOKENS-"].update(
                        value=provider_config.get("max_tokens", 8192)
                    )
                    self.window.refresh()
                except Exception as e:
                    sg.popup_error(
                        f"更新 AIForge 提供商配置失败: {e}",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            # 保存 AIForge 配置
            elif event.startswith("-SAVE_AIFORGE-"):
                aiforge_config = self.config.aiforge_config.copy()
                try:
                    selected_provider = values["-AIFORGE_DEFAULT_LLM_PROVIDER-"]
                    aiforge_config["default_llm_provider"] = selected_provider

                    # 不支持修改AIForge的内置语言
                    # aiforge_config["locale"] = values["-AIFORGE_LOCALE-"]

                    # 处理通用配置
                    try:
                        max_rounds = int(values["-AIFORGE_MAXROUNDS-"])
                        if 1 <= max_rounds <= 16:
                            aiforge_config["max_rounds"] = max_rounds
                        else:
                            aiforge_config["max_rounds"] = 5  # 默认值
                            self.window["-AIFORGE_MAXROUNDS-"].update(value=5)
                    except (ValueError, TypeError):
                        aiforge_config["max_rounds"] = 5  # 默认值
                        self.window["-AIFORGE_MAXROUNDS-"].update(value=5)

                    # 保存默认最大Tokens
                    try:
                        default_max_tokens = int(values.get("-AIFORGE_DEFAULT_MAX_TOKENS-", 4096))
                        aiforge_config["max_tokens"] = default_max_tokens
                    except (ValueError, TypeError):
                        aiforge_config["max_tokens"] = 4096

                    # 更新选中的提供商的所有参数
                    aiforge_config["llm"][selected_provider]["type"] = values.get(
                        "-AIFORGE_TYPE-", ""
                    )
                    aiforge_config["llm"][selected_provider]["model"] = values.get(
                        "-AIFORGE_MODEL-", ""
                    )
                    aiforge_config["llm"][selected_provider]["api_key"] = values.get(
                        "-AIFORGE_API_KEY-", ""
                    )
                    aiforge_config["llm"][selected_provider]["base_url"] = values.get(
                        "-AIFORGE_BASE_URL-", ""
                    )

                    try:
                        aiforge_config["llm"][selected_provider]["timeout"] = int(
                            values.get("-AIFORGE_TIMEOUT-", 30)
                        )
                        aiforge_config["llm"][selected_provider]["max_tokens"] = int(
                            values.get("-AIFORGE_MAX_TOKENS-", 8192)
                        )
                    except (ValueError, TypeError):
                        sg.popup_error(
                            "超时时间或最大 Tokens 必须是整数",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                        return

                    # 处理缓存配置
                    if "cache" not in aiforge_config:
                        aiforge_config["cache"] = {}
                    if "code" not in aiforge_config["cache"]:
                        aiforge_config["cache"]["code"] = {}

                    cache_config = aiforge_config["cache"]["code"]
                    cache_config["enabled"] = values.get("-CACHE_ENABLED-", True)

                    try:
                        cache_config["max_modules"] = int(values.get("-CACHE_MAX_MODULES-", 20))
                        cache_config["failure_threshold"] = float(
                            values.get("-CACHE_FAILURE_THRESHOLD-", 0.8)
                        )
                        cache_config["max_age_days"] = int(values.get("-CACHE_MAX_AGE_DAYS-", 30))
                        cache_config["cleanup_interval"] = int(
                            values.get("-CACHE_CLEANUP_INTERVAL-", 10)
                        )
                    except (ValueError, TypeError):
                        sg.popup_error(
                            "缓存配置参数必须是有效的数值",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                        return

                    # 保存配置
                    if self.config.save_config(self.config.get_config(), aiforge_config):
                        sg.popup(
                            "AIForge 配置已保存",
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )
                    else:
                        sg.popup_error(
                            self.config.error_message,
                            title="系统提示",
                            icon=utils.get_gui_icon(),
                            keep_on_top=True,
                        )

                except Exception as e:
                    sg.popup_error(
                        f"保存配置时发生错误: {str(e)}",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
            # 恢复默认 AIForge 配置
            elif event.startswith("-RESET_AIFORGE-"):
                aiforge_config = copy.deepcopy(self.config.default_aiforge_config)
                if self.config.save_config(self.config.get_config(), aiforge_config):
                    self.update_tab("-TAB_AIFORGE-", self.create_aiforge_tab())
                    sg.popup(
                        "已恢复默认 AIForge 配置",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            elif event.startswith("-WECHAT_CALL_SENDALL_") or event.startswith("-WECHAT_SENDALL_"):
                match = re.search(r"_(\d+)-$", event)
                if match:
                    index = int(match.group(1))
                    call_sendall_key = f"-WECHAT_CALL_SENDALL_{index}-"
                    sendall_key = f"-WECHAT_SENDALL_{index}-"
                    tag_id_key = f"-WECHAT_TAG_ID_{index}-"

                    if all(
                        key in self.window.AllKeysDict
                        for key in [call_sendall_key, sendall_key, tag_id_key]
                    ):
                        call_sendall_enabled = values.get(call_sendall_key, False)
                        sendall_enabled = values.get(sendall_key, False)

                        if call_sendall_enabled:
                            self.window[sendall_key].update(disabled=False)
                            if sendall_enabled:
                                self.window[tag_id_key].update(disabled=True)
                            else:
                                self.window[tag_id_key].update(disabled=False)
                        else:
                            self.window[sendall_key].update(disabled=True)
                            self.window[tag_id_key].update(disabled=True)

            # 创意模式相关事件
            elif event in [
                "-STYLE_TRANSFORM_ENABLED-",
                "-TIME_TRAVEL_ENABLED-",
                "-ROLE_PLAY_ENABLED-",
                # 新增的创意模式事件
                "-MULTI_DIMENSIONAL_ENABLED-",
                "-CULTURAL_FUSION_ENABLED-",
                "-DYNAMIC_TRANSFORM_ENABLED-",
                "-GENRE_FUSION_ENABLED-",
                "-AI_PERSONA_ENABLED-",
            ]:
                # 动态启用/禁用相关控件
                if event == "-STYLE_TRANSFORM_ENABLED-":
                    enabled = values["-STYLE_TRANSFORM_ENABLED-"]
                    self.window["-STYLE_TARGET-"].update(disabled=not enabled)
                elif event == "-TIME_TRAVEL_ENABLED-":
                    enabled = values["-TIME_TRAVEL_ENABLED-"]
                    self.window["-TIME_PERSPECTIVE-"].update(disabled=not enabled)
                elif event == "-ROLE_PLAY_ENABLED-":
                    enabled = values["-ROLE_PLAY_ENABLED-"]
                    self.window["-ROLE_CHARACTER-"].update(disabled=not enabled)
                    # 根据当前选择决定是否启用自定义输入框
                    current_role = self._get_role_key(values["-ROLE_CHARACTER-"])
                    self.window["-CUSTOM_CHARACTER-"].update(
                        disabled=not enabled or current_role != "custom"
                    )
                # 新增创意模式的控件启用/禁用处理
                elif event == "-MULTI_DIMENSIONAL_ENABLED-":
                    enabled = values["-MULTI_DIMENSIONAL_ENABLED-"]
                    self.window["-TARGET_AUDIENCE-"].update(disabled=not enabled)
                    self.window["-CREATIVITY_LEVEL-"].update(disabled=not enabled)
                elif event == "-CULTURAL_FUSION_ENABLED-":
                    enabled = values["-CULTURAL_FUSION_ENABLED-"]
                    self.window["-CULTURAL_PERSPECTIVE-"].update(disabled=not enabled)
                elif event == "-DYNAMIC_TRANSFORM_ENABLED-":
                    enabled = values["-DYNAMIC_TRANSFORM_ENABLED-"]
                    self.window["-SCENARIO-"].update(disabled=not enabled)
                elif event == "-GENRE_FUSION_ENABLED-":
                    enabled = values["-GENRE_FUSION_ENABLED-"]
                    self.window["-GENRE_SCIFI-"].update(disabled=not enabled)
                    self.window["-GENRE_WUXIA-"].update(disabled=not enabled)
                    self.window["-GENRE_MYSTERY-"].update(disabled=not enabled)
                    self.window["-GENRE_ROMANCE-"].update(disabled=not enabled)
                elif event == "-AI_PERSONA_ENABLED-":
                    enabled = values["-AI_PERSONA_ENABLED-"]
                    self.window["-PERSONA_TYPE-"].update(disabled=not enabled)

            elif event == "-SMART_RECOMMENDATION-":
                # 智能推荐主开关事件
                enabled = values["-SMART_RECOMMENDATION-"]
                self.window["-TOPIC_BASED-"].update(disabled=not enabled)
                self.window["-AUDIENCE_BASED-"].update(disabled=not enabled)
                self.window["-PLATFORM_BASED-"].update(disabled=not enabled)

            elif event == "-ROLE_CHARACTER-":
                selected_role = self._get_role_key(values["-ROLE_CHARACTER-"])
                enabled = values["-ROLE_PLAY_ENABLED-"]

                # 当选择"自定义"时启用输入框，否则禁用
                if selected_role == "custom":
                    self.window["-CUSTOM_CHARACTER-"].update(disabled=not enabled)
                else:
                    self.window["-CUSTOM_CHARACTER-"].update(disabled=True, value="")

                self.window.refresh()

            elif event == "-SAVE_CREATIVE_CONFIG-":
                config = self.config.get_config().copy()

                # 构建创意配置
                selected_role = self._get_role_key(values["-ROLE_CHARACTER-"])
                custom_character = values["-CUSTOM_CHARACTER-"] if selected_role == "custom" else ""

                creative_config = {
                    # 原有的创意模式配置
                    "style_transform": {
                        "enabled": values["-STYLE_TRANSFORM_ENABLED-"],
                        "style_target": self._get_style_key(values["-STYLE_TARGET-"]),
                        "available_styles": [
                            "shakespeare",
                            "detective",
                            "scifi",
                            "classical_poetry",
                            "modern_poetry",
                            "academic",
                            "news",
                        ],
                    },
                    "time_travel": {
                        "enabled": values["-TIME_TRAVEL_ENABLED-"],
                        "time_perspective": self._get_time_key(values["-TIME_PERSPECTIVE-"]),
                        "available_perspectives": ["ancient", "modern", "future"],
                    },
                    "role_play": {
                        "enabled": values["-ROLE_PLAY_ENABLED-"],
                        "role_character": selected_role,
                        "custom_character": custom_character,
                        "available_roles": [
                            # 古典诗词
                            "libai",
                            "dufu",
                            "sushi",
                            "liqingzhao",
                            # 古典小说
                            "caoxueqin",
                            "shinaian",
                            "wuchengen",
                            "pusonglin",
                            # 现代文学
                            "luxun",
                            "laoshe",
                            "bajin",
                            "qianjunru",
                            # 武侠小说
                            "jinyong",
                            "gulongxia",
                            # 新闻主播/评论员
                            "baiyansong",
                            "cuiyongyuan",
                            "yanglan",
                            "luyu",
                            # 音乐人
                            "zhoujielun",
                            "denglijun",
                            "lironghao",
                            # 相声曲艺
                            "guodegang",
                            "zhaobenshang",
                            # 自定义
                            "custom",
                        ],
                    },
                    # 新增的创意模式配置
                    "multi_dimensional": {
                        "enabled": values["-MULTI_DIMENSIONAL_ENABLED-"],
                        "target_audience": values["-TARGET_AUDIENCE-"],
                        "creativity_level": self._get_creativity_key(values["-CREATIVITY_LEVEL-"]),
                        "available_creativity_levels": ["conservative", "balanced", "experimental"],
                        "auto_select_dimensions": True,
                    },
                    "cultural_fusion": {
                        "enabled": values["-CULTURAL_FUSION_ENABLED-"],
                        "cultural_perspective": self._get_cultural_key(
                            values["-CULTURAL_PERSPECTIVE-"]
                        ),
                        "available_perspectives": [
                            "eastern_philosophy",
                            "western_logic",
                            "japanese_mono",
                            "french_romance",
                            "american_freedom",
                        ],
                    },
                    "dynamic_transform": {
                        "enabled": values["-DYNAMIC_TRANSFORM_ENABLED-"],
                        "scenario": self._get_scenario_key(values["-SCENARIO-"]),
                        "available_scenarios": [
                            "elevator_pitch",
                            "bedtime_story",
                            "debate_argument",
                            "poetry_version",
                            "comic_script",
                            "podcast_script",
                            "social_media",
                        ],
                    },
                    "genre_fusion": {
                        "enabled": values["-GENRE_FUSION_ENABLED-"],
                        "genre_combination": [
                            genre
                            for genre, checked in [
                                ("scifi", values["-GENRE_SCIFI-"]),
                                ("wuxia", values["-GENRE_WUXIA-"]),
                                ("mystery", values["-GENRE_MYSTERY-"]),
                                ("romance", values["-GENRE_ROMANCE-"]),
                            ]
                            if checked
                        ],
                        "available_genres": [
                            "scifi",
                            "wuxia",
                            "detective",
                            "romance",
                            "history",
                            "fantasy",
                            "thriller",
                            "comedy",
                        ],
                        "max_genres": 3,
                    },
                    "ai_persona": {
                        "enabled": values["-AI_PERSONA_ENABLED-"],
                        "persona_type": self._get_persona_key(values["-PERSONA_TYPE-"]),
                        "available_personas": [
                            "auto",
                            "dreamer_poet",
                            "data_philosopher",
                            "time_traveler",
                            "emotion_healer",
                            "mystery_detective",
                            "culture_explorer",
                            "tech_visionary",
                            "life_observer",
                        ],
                        "persona_descriptions": {
                            "dreamer_poet": "梦境诗人 - 善于将现实与梦境交织",
                            "data_philosopher": "数据哲学家 - 用数据思维解读人文",
                            "time_traveler": "时空旅者 - 穿梭时代的独特视角",
                            "emotion_healer": "情感治愈师 - 温暖人心的文字治愈",
                            "mystery_detective": "悬疑侦探 - 逻辑推理揭秘真相",
                            "culture_explorer": "文化探索者 - 深入挖掘文化内涵",
                            "tech_visionary": "科技预言家 - 洞察科技趋势",
                            "life_observer": "生活观察家 - 从平凡中发现不平凡",
                        },
                    },
                    "combination_mode": values["-COMBINATION_MODE-"],
                    # 智能推荐配置
                    "smart_recommendation": {
                        "enabled": values["-SMART_RECOMMENDATION-"],
                        "topic_based": values["-TOPIC_BASED-"],
                        "audience_based": values["-AUDIENCE_BASED-"],
                        "platform_based": values["-PLATFORM_BASED-"],
                    },
                    # 添加模式优先级和冲突规则
                    "mode_priority": [
                        "ai_persona",
                        "multi_dimensional",
                        "cultural_fusion",
                        "genre_fusion",
                        "dynamic_transform",
                        "style_transform",
                        "time_travel",
                        "role_play",
                    ],
                    "mode_conflicts": {
                        "ai_persona": ["role_play"],
                        "multi_dimensional": ["style_transform"],
                    },
                }

                # 确定主创意模式 - 包含新增模式
                enabled_modes = []
                if creative_config["style_transform"]["enabled"]:
                    enabled_modes.append("style_transform")
                if creative_config["time_travel"]["enabled"]:
                    enabled_modes.append("time_travel")
                if creative_config["role_play"]["enabled"]:
                    enabled_modes.append("role_play")
                # 新增模式
                if creative_config["multi_dimensional"]["enabled"]:
                    enabled_modes.append("multi_dimensional")
                if creative_config["cultural_fusion"]["enabled"]:
                    enabled_modes.append("cultural_fusion")
                if creative_config["dynamic_transform"]["enabled"]:
                    enabled_modes.append("dynamic_transform")
                if creative_config["genre_fusion"]["enabled"]:
                    enabled_modes.append("genre_fusion")
                if creative_config["ai_persona"]["enabled"]:
                    enabled_modes.append("ai_persona")

                # 检查模式冲突
                conflict_detected = False
                conflicts = creative_config["mode_conflicts"]
                for mode in enabled_modes:
                    conflicting_modes = conflicts.get(mode, [])
                    for conflict_mode in conflicting_modes:
                        if conflict_mode in enabled_modes:
                            conflict_detected = True
                            sg.popup_error(
                                f"检测到模式冲突：{mode} 与 {conflict_mode} 不能同时启用\n"
                                f"系统将自动禁用冲突的模式",
                                title="模式冲突警告",
                                icon=utils.get_gui_icon(),
                                keep_on_top=True,
                            )
                            # 移除冲突的模式（保留优先级高的）
                            priority = creative_config["mode_priority"]
                            if priority.index(mode) < priority.index(conflict_mode):
                                enabled_modes.remove(conflict_mode)
                            else:
                                enabled_modes.remove(mode)

                # 设置 creative_mode
                if len(enabled_modes) == 0:
                    config["creative_mode"] = ""
                elif len(enabled_modes) == 1:
                    config["creative_mode"] = enabled_modes[0]
                elif creative_config["combination_mode"]:
                    config["creative_mode"] = ",".join(enabled_modes)  # 组合模式
                else:
                    # 不允许组合时，只取第一个
                    config["creative_mode"] = enabled_modes[0]
                    sg.popup_error(
                        "不允许组合模式时，只会使用第一个启用的创意模块",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

                config["creative_config"] = creative_config

                if self.config.save_config(config):
                    success_msg = "创意配置已保存"
                    if conflict_detected:
                        success_msg += "\n注意：已自动解决模式冲突"
                    sg.popup(
                        success_msg,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

            elif event == "-RESET_CREATIVE_CONFIG-":
                # 重置为默认配置
                config = self.config.get_config().copy()
                config["creative_mode"] = ""
                config["creative_config"] = self.config.default_config["creative_config"]

                if self.config.save_config(config):
                    # 更新界面
                    self.update_tab("-TAB_CREATIVE-", self.create_creative_tab())
                    sg.popup(
                        "创意配置已重置",
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )
                else:
                    sg.popup_error(
                        self.config.error_message,
                        title="系统提示",
                        icon=utils.get_gui_icon(),
                        keep_on_top=True,
                    )

        self.window.close()


def gui_start():
    ConfigEditor().run()
