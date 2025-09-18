from typing import Any, Dict
import os
import yaml
import threading
import tomlkit

from src.ai_write_x.utils import log
from src.ai_write_x.utils import utils
from src.ai_write_x.utils.path_manager import PathManager

# 默认分类配置
DEFAULT_TEMPLATE_CATEGORIES = {
    "TechDigital": "科技数码",
    "FinanceInvestment": "财经投资",
    "EducationLearning": "教育学习",
    "HealthWellness": "健康养生",
    "FoodTravel": "美食旅行",
    "FashionLifestyle": "时尚生活",
    "CareerDevelopment": "职场发展",
    "EmotionPsychology": "情感心理",
    "EntertainmentGossip": "娱乐八卦",
    "NewsCurrentAffairs": "新闻时事",
    "Others": "其他",
}


# 自定义 Dumper，仅调整数组子元素缩进
class IndentedDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        # 强制数组子元素（-）缩进 2 个空格
        return super().increase_indent(flow, False)


class Config:
    """
    配置管理类 - 统一版本管理策略

    版本管理最佳实践:
    1. 配置版本号统一跟随软件版本，不再单独维护
    2. 使用智能合并策略处理配置兼容性，替代复杂的版本迁移逻辑
    3. 总是以最新默认配置为基准，保留用户有效配置值
    4. 版本号主要用于用户界面显示，不影响核心功能
    """

    _instance = None
    _lock = threading.Lock()
    # _lock = threading.RLock()  # 可重入锁

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.config: Dict[Any, Any] = {}
        self.aiforge_config: Dict[Any, Any] = {}
        self.error_message = None
        self.config_path = self.__get_config_path()
        self.config_aiforge_path = self.__get_config_path("aiforge.toml")
        self.default_config = {
            "config_version": "2.2.1",  # 统一使用软件版本号
            "platforms": [
                {"name": "微博", "weight": 0.3},
                {"name": "抖音", "weight": 0.20},
                {"name": "小红书", "weight": 0.12},
                {"name": "今日头条", "weight": 0.1},
                {"name": "百度热点", "weight": 0.08},
                {"name": "哔哩哔哩", "weight": 0.06},
                {"name": "快手", "weight": 0.05},
                {"name": "虎扑", "weight": 0.05},
                {"name": "豆瓣小组", "weight": 0.02},
                {"name": "澎湃新闻", "weight": 0.01},
                {"name": "知乎热榜", "weight": 0.01},
            ],
            "publish_platform": "wechat",
            "wechat": {
                "credentials": [
                    {
                        "appid": "",
                        "appsecret": "",
                        "author": "",
                        "call_sendall": False,
                        "sendall": True,
                        "tag_id": 0,
                    },
                    {
                        "appid": "",
                        "appsecret": "",
                        "author": "",
                        "call_sendall": False,
                        "sendall": True,
                        "tag_id": 0,
                    },
                    {
                        "appid": "",
                        "appsecret": "",
                        "author": "",
                        "call_sendall": False,
                        "sendall": True,
                        "tag_id": 0,
                    },
                ]
            },
            "api": {
                "api_type": "OpenRouter",
                "Grok": {
                    "key": "XAI_API_KEY",
                    "key_index": 0,
                    "api_key": ["", ""],
                    "model_index": 0,
                    "model": ["xai/grok-3"],
                    "api_base": "https://api.x.ai/v1/chat/completions",
                },
                "Qwen": {
                    "key": "OPENAI_API_KEY",
                    "key_index": 0,
                    "api_key": ["", ""],
                    "model_index": 0,
                    "model": ["openai/qwen-plus"],
                    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                },
                "Gemini": {
                    "key": "GEMINI_API_KEY",
                    "key_index": 0,
                    "api_key": ["", ""],
                    "model_index": 0,
                    "model": [
                        "gemini/gemini-1.5-flash",
                        "gemini/gemini-1.5-pro",
                        "gemini/gemini-2.0-flash",
                    ],
                    "api_base": "https://generativelanguage.googleapis.com/v1beta/openai/",
                },
                "OpenRouter": {
                    "key": "OPENROUTER_API_KEY",
                    "model_index": 0,
                    "key_index": 0,
                    "api_key": ["", ""],
                    "model": [
                        "openrouter/deepseek/deepseek-chat-v3-0324:free",
                        "openrouter/deepseek/deepseek-r1:free",
                        "openrouter/deepseek/deepseek-chat:free",
                        "openrouter/qwen/qwq-32b:free",
                        "openrouter/google/gemini-2.0-flash-lite-preview-02-05:free",
                        "openrouter/google/gemini-2.0-flash-thinking-exp:free",
                    ],
                    "api_base": "https://openrouter.ai/api/v1",
                },
                "Ollama": {
                    "key": "OPENAI_API_KEY",
                    "model_index": 0,
                    "key_index": 0,
                    "api_key": ["tmp-key", ""],
                    "model": ["ollama/deepseek-r1:14b", "ollama/deepseek-r1:7b"],
                    "api_base": "http://localhost:11434",
                },
                "Deepseek": {
                    "key": "DEEPSEEK_API_KEY",
                    "key_index": 0,
                    "api_key": [""],
                    "model_index": 0,
                    "model": [
                        "deepseek/deepseek-chat",
                        "deepseek/deepseek-reasoner",
                    ],
                    "api_base": "https://api.deepseek.com/v1",
                },
                "SiliconFlow": {
                    "key": "SILICONFLOW_API_KEY",
                    "key_index": 0,
                    "api_key": ["", ""],
                    "model_index": 0,
                    "model": [
                        "siliconflow/deepseek-chat",
                        "siliconflow/qwen-turbo",
                        "siliconflow/glm-4-chat",
                        "siliconflow/yi-lightning",
                    ],
                    "api_base": "https://api.siliconflow.cn/v1",
                },
            },
            "img_api": {
                "api_type": "picsum",
                "ali": {"api_key": "", "model": "wanx2.0-t2i-turbo"},
                "picsum": {"api_key": "", "model": ""},
            },
            "use_template": True,
            "template_category": "",
            "template": "",
            "use_compress": True,
            "aiforge_search_max_results": 10,
            "aiforge_search_min_results": 1,
            "min_article_len": 1000,
            "max_article_len": 2000,
            "auto_publish": True,
            "article_format": "html",
            "format_publish": True,
            "creative_mode": "",
            "creative_config": {
                "style_transform": {
                    "enabled": False,
                    "style_target": "shakespeare",
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
                    "enabled": False,
                    "time_perspective": "ancient",
                    "available_perspectives": ["ancient", "modern", "future"],
                },
                "role_play": {
                    "enabled": False,
                    "role_character": "libai",
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
                    "custom_character": "",
                },
                # 新增的创意模式配置
                "multi_dimensional": {
                    "enabled": False,
                    "target_audience": "",  # 目标受众
                    "creativity_level": "balanced",  # 创意程度：conservative, balanced, experimental
                    "available_creativity_levels": ["conservative", "balanced", "experimental"],
                    "auto_select_dimensions": True,  # 自动选择创意维度
                },
                "cultural_fusion": {
                    "enabled": False,
                    "cultural_perspective": "eastern_philosophy",
                    "available_perspectives": [
                        "eastern_philosophy",
                        "western_logic",
                        "japanese_mono",
                        "french_romance",
                        "american_freedom",
                    ],
                },
                "dynamic_transform": {
                    "enabled": False,
                    "scenario": "elevator_pitch",
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
                    "enabled": False,
                    "genre_combination": ["scifi", "wuxia"],
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
                    "max_genres": 3,  # 最多融合的体裁数量
                },
                "ai_persona": {
                    "enabled": False,
                    "persona_type": "auto",  # auto表示自动选择
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
                "combination_mode": False,
                # 新增：创意模式优先级和互斥规则
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
                    # 定义互斥的创意模式组合
                    "ai_persona": ["role_play"],  # AI人格与角色扮演互斥
                    "multi_dimensional": ["style_transform"],  # 多维度创意与单一风格转换互斥
                },
                # 创意模式智能推荐配置
                "smart_recommendation": {
                    "enabled": True,
                    "topic_based": True,  # 基于话题推荐
                    "audience_based": True,  # 基于受众推荐
                    "platform_based": True,  # 基于平台推荐
                },
            },
        }
        self.default_aiforge_config = {
            "locale": "zh",
            "max_rounds": 5,
            "max_tokens": 4096,
            "default_llm_provider": "openrouter",
            "llm": {
                "openrouter": {
                    "type": "openai",
                    "model": "deepseek/deepseek-chat-v3-0324:free",
                    "api_key": "",
                    "base_url": "https://openrouter.ai/api/v1",
                    "timeout": 30,
                    "max_tokens": 8192,
                },
                "grok": {
                    "type": "grok",
                    "model": "xai/grok-3",
                    "api_key": "",
                    "base_url": "https://api.x.ai/v1/chat/completions",
                    "timeout": 30,
                    "max_tokens": 8192,
                },
                "qwen": {
                    "type": "openai",
                    "model": "openai/qwen-plus",
                    "api_key": "",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "timeout": 30,
                    "max_tokens": 8192,
                },
                "gemini": {
                    "type": "gemini",
                    "model": "gemini-2.5-pro-exp-03-25",
                    "api_key": "",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                    "timeout": 30,
                    "max_tokens": 8192,
                },
                "ollama": {
                    "type": "ollama",
                    "model": "ollama/deepseek-r1:14b",
                    "api_key": "",
                    "base_url": "http://localhost:11434",
                    "timeout": 30,
                    "max_tokens": 8192,
                },
                "deepseek": {
                    "type": "deepseek",
                    "model": "deepseek-chat",
                    "api_key": "",
                    "base_url": "https://api.deepseek.com",
                    "timeout": 30,
                    "max_tokens": 8192,
                },
            },
            "cache": {
                "code": {
                    "enabled": True,
                    "max_modules": 20,
                    "failure_threshold": 0.8,
                    "max_age_days": 30,
                    "cleanup_interval": 10,
                },
            },
        }

        # 自定义话题和文章参考链接，根据是否为空判断是否自定义
        self.custom_topic = ""  # 自定义话题（字符串）
        self.urls = []  # 参考链接（列表）
        self.reference_ratio = 0.0  # 文章借鉴比例[0-1]
        self.custom_template_category = ""  # 自定义话题时，模板分类
        self.custom_template = ""  # 自定义话题时，模板
        self.current_preview_cover = ""  # 当前设置的封面

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def platforms(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["platforms"]

    @property
    def wechat_credentials(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["wechat"]["credentials"]

    @property
    def api_type(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["api"]["api_type"]

    @property
    def api_key_name(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["api"][self.config["api"]["api_type"]]["key"]

    @property
    def api_key(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            api_key = self.config["api"][self.config["api"]["api_type"]]["api_key"]
            key_index = self.config["api"][self.config["api"]["api_type"]]["key_index"]
            return api_key[key_index]

    @property
    def api_model(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            model = self.config["api"][self.config["api"]["api_type"]]["model"]
            model_index = self.config["api"][self.config["api"]["api_type"]]["model_index"]
            return model[model_index]

    @property
    def api_apibase(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["api"][self.config["api"]["api_type"]]["api_base"]

    @property
    def img_api_type(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["img_api"]["api_type"]

    @property
    def img_api_key(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["img_api"][self.config["img_api"]["api_type"]]["api_key"]

    @property
    def img_api_model(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["img_api"][self.config["img_api"]["api_type"]]["model"]

    @property
    def use_template(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["use_template"]

    @property
    def template_category(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["template_category"]

    @property
    def template(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["template"]

    @property
    def use_compress(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["use_compress"]

    @property
    def aiforge_search_max_results(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["aiforge_search_max_results"]

    @property
    def aiforge_search_min_results(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["aiforge_search_min_results"]

    @property
    def min_article_len(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["min_article_len"]

    @property
    def max_article_len(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["max_article_len"]

    @property
    def article_format(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["article_format"]

    @property
    def auto_publish(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["auto_publish"]

    @property
    def format_publish(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["format_publish"]

    @property
    def publish_platform(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["publish_platform"]

    @property
    def creative_mode(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config["creative_mode"]

    @property
    def creative_config(self):
        """获取创意配置"""
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config.get("creative_config", {})

    @property
    def config_version(self):
        """获取配置版本号（跟随软件版本）"""
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config.get("config_version", "2.2.1")

    def set_config_version(self, version: str):
        """设置配置版本号（保持API兼容性）"""
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            self.config["config_version"] = version

    def is_legacy_config(self) -> bool:
        """
        检查是否为旧版本配置（简化版）
        注：由于使用智能合并策略，版本检查不再关键，保留仅为兼容性
        """
        with self._lock:
            current_version = self.config_version
            # 简化版本检查：只要不是空版本就认为是新版本
            return current_version in ["1.0.0", "", None]

    # 新增的创意模式配置属性
    @property
    def multi_dimensional_config(self):
        """多维度创意配置"""
        with self._lock:
            return self.creative_config.get("multi_dimensional", {})

    @property
    def cultural_fusion_config(self):
        """文化融合配置"""
        with self._lock:
            return self.creative_config.get("cultural_fusion", {})

    @property
    def dynamic_transform_config(self):
        """动态变形配置"""
        with self._lock:
            return self.creative_config.get("dynamic_transform", {})

    @property
    def genre_fusion_config(self):
        """体裁融合配置"""
        with self._lock:
            return self.creative_config.get("genre_fusion", {})

    @property
    def ai_persona_config(self):
        """AI人格配置"""
        with self._lock:
            return self.creative_config.get("ai_persona", {})

    @property
    def smart_recommendation_config(self):
        """智能推荐配置"""
        with self._lock:
            return self.creative_config.get("smart_recommendation", {})

    def get_enabled_creative_modes(self):
        """获取已启用的创意模式列表"""
        with self._lock:
            enabled_modes = []
            creative_config = self.creative_config

            for mode_name, mode_config in creative_config.items():
                if isinstance(mode_config, dict) and mode_config.get("enabled", False):
                    enabled_modes.append(mode_name)

            return enabled_modes

    def is_creative_mode_enabled(self, mode_name: str) -> bool:
        """检查指定创意模式是否启用"""
        with self._lock:
            mode_config = self.creative_config.get(mode_name, {})
            return mode_config.get("enabled", False)

    @property
    def api_list(self):
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")

            api_keys_list = list(self.config["api"].keys())
            if "api_type" in api_keys_list:
                api_keys_list.remove("api_type")

            return api_keys_list

    @property
    def api_list_display(self):
        """返回用于界面显示的API类型列表"""
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")

            api_keys_list = list(self.config["api"].keys())
            if "api_type" in api_keys_list:
                api_keys_list.remove("api_type")

            # 转换为显示名称
            display_list = []
            for api_type in api_keys_list:
                if api_type == "SiliconFlow":
                    display_list.append("硅基流动")
                else:
                    display_list.append(api_type)

            return display_list

    # aiforge 配置
    @property
    def aiforge_default_llm_provider(self):
        with self._lock:
            if not self.aiforge_config:
                raise ValueError("配置未加载")
            return self.aiforge_config["default_llm_provider"]

    @property
    def aiforge_api_key(self):
        with self._lock:
            if not self.aiforge_config:
                raise ValueError("配置未加载")
            return self.aiforge_config["llm"][self.aiforge_config["default_llm_provider"]][
                "api_key"
            ]

    def __get_config_path(self, file_name="config.yaml"):
        """获取配置文件路径并确保文件存在"""

        config_path = str(PathManager.get_config_path(file_name))

        if utils.get_is_release_ver():
            # 发布模式：使用PathManager获取跨平台可写路径
            # 将资源文件复制到配置目录下（保留原有逻辑）
            res_config_path = utils.get_res_path(f"config/{file_name}")
            if os.path.exists(res_config_path):
                utils.copy_file(res_config_path, config_path)

        return config_path

    def get_sendall_by_appid(self, target_appid):
        for cred in self.config["wechat"]["credentials"]:
            if cred["appid"] == target_appid:
                return cred["sendall"]
        return False

    def get_call_sendall_by_appid(self, target_appid):
        for cred in self.config["wechat"]["credentials"]:
            if cred["appid"] == target_appid:
                return cred["call_sendall"]
        return False

    def get_tagid_by_appid(self, target_appid):
        for cred in self.config["wechat"]["credentials"]:
            if cred["appid"] == target_appid:
                return cred["tag_id"]
        return False

    def load_config(self):
        """加载配置，从 config.yaml 或默认配置，不验证"""
        with self._lock:
            ret = True
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        self.config = yaml.safe_load(f)
                        if not self.config:
                            self.config = self.default_config
                except Exception as e:
                    self.error_message = f"加载 config.yaml 失败: {e}"
                    log.print_log(self.error_message, "error")
                    self.config = self.default_config
                    ret = False
            else:
                self.config = self.default_config

            if os.path.exists(self.config_aiforge_path):
                try:
                    with open(self.config_aiforge_path, "r", encoding="utf-8") as f:
                        self.aiforge_config = tomlkit.parse(f.read())
                        if not self.aiforge_config:
                            self.aiforge_config = self.default_aiforge_config
                except Exception as e:
                    self.error_message = f"加载 aiforge.toml 失败: {e}"
                    log.print_log(self.error_message, "error")
                    self.aiforge_config = self.default_aiforge_config
                    ret = False
            else:
                self.aiforge_config = self.default_aiforge_config

            return ret

    def validate_config(self):
        """验证配置，仅在 CrewAI 执行时调用"""
        try:
            if self.api_key == "":
                self.error_message = f"未配置API KEY，请打开配置填写{self.api_type}的api_key"
                return False

            if self.api_model == "":
                self.error_message = f"未配置Model，请打开配置填写{self.api_type}的model"
                return False

            if self.img_api_type != "picsum":
                if self.img_api_key == "":
                    self.error_message = (
                        f"未配置图片生成模型的API KEY，请打开配置填写{self.img_api_type}的api_key"
                    )
                    return False
                elif self.img_api_model == "":
                    self.error_message = (
                        f"未配置图片生成的模型，请打开配置填写{self.img_api_type}的model"
                    )
                    return False

            # 只有自动发布才需要检验公众号配置
            if self.auto_publish:
                valid_cred = any(
                    cred["appid"] and cred["appsecret"] for cred in self.wechat_credentials
                )
                if not valid_cred:
                    self.error_message = "【自动发布】时，需配置微信公众号appid和appsecret"
                    return False

            # 检查是否配置了aiforge api_key
            if not self.aiforge_api_key:
                log.print_log("AIForge未配置有效的llm提供商的api_key，将不使用搜索功能")

            total_weight = sum(platform["weight"] for platform in self.platforms)
            if abs(total_weight - 1.0) > 0.01:
                self.error_message = f"平台权重之和 {total_weight} 不等于 1"
                return True  # 这里可以不失败，会默认使用微博

            return True

        except Exception as e:
            self.error_message = f"配置验证失败: {e}"
            return False

    def get_config(self):
        """获取配置，不验证"""
        with self._lock:
            if not self.config:
                raise ValueError("配置未加载")
            return self.config

    def save_config(self, config, aiforge_config=None):
        """保存配置到 config.yaml，不验证"""
        with self._lock:
            ret = True
            self.config = config
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        config,
                        f,
                        Dumper=IndentedDumper,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                        indent=2,
                    )
            except Exception as e:
                self.error_message = f"保存 config.yaml 失败: {e}"
                log.print_log(self.error_message, "error")
                ret = False

            # 如果传递了
            if aiforge_config is not None:
                self.aiforge_config = aiforge_config
                try:
                    with open(self.config_aiforge_path, "w", encoding="utf-8") as f:
                        f.write(tomlkit.dumps(self.aiforge_config))

                except Exception as e:
                    self.error_message = f"保存 aiforge.toml 失败: {e}"
                    log.print_log(self.error_message, "error")
                    ret = False

            return ret

    def get_config_version(self):
        """获取当前配置版本号（统一使用软件版本）"""
        with self._lock:
            if not self.config:
                return "2.2.1"  # 默认返回最新版本
            return self.config.get("config_version", "2.2.1")

    def reload_config(self):
        """重新加载配置文件"""
        with self._lock:
            log.print_log("重新加载配置文件...", "info")
            return self.load_config()

    def merge_with_user_config(self, user_config: dict) -> dict:
        """
        智能合并用户配置：以默认配置为基础，保留用户已配置的有效值
        这是配置处理的核心逻辑，替代复杂的版本迁移
        """
        import copy

        # 以默认配置为基础
        merged_config = copy.deepcopy(self.default_config)

        if not user_config:
            return merged_config

        preserved_count = 0

        # 递归合并函数
        def merge_dict(default_dict: dict, user_dict: dict, path: str = "") -> int:
            nonlocal preserved_count
            count = 0

            for key, user_value in user_dict.items():
                current_path = f"{path}.{key}" if path else key

                # 版本号由系统统一管理，始终使用最新版本
                if key == "config_version":
                    continue

                # 如果默认配置中不存在该键，跳过（废弃的配置）
                if key not in default_dict:
                    continue

                default_value = default_dict[key]

                # 对于字典类型，递归合并
                if isinstance(default_value, dict) and isinstance(user_value, dict):
                    count += merge_dict(default_value, user_value, current_path)

                # 对于非空的有意义值，保留用户配置
                elif self._is_meaningful_value(user_value, default_value):
                    default_dict[key] = user_value
                    count += 1

            return count

        preserved_count = merge_dict(merged_config, user_config)

        return merged_config

    def _is_meaningful_value(self, user_value, default_value) -> bool:
        """判断用户值是否有意义（值得保留）"""
        # 对于字符串，不保留空字符串
        if isinstance(user_value, str):
            return user_value.strip() != ""

        # 对于列表，不保留空列表或只有空字符串的列表
        if isinstance(user_value, list):
            if not user_value:
                return False
            # 检查是否所有元素都是空字符串
            if all(isinstance(item, str) and item.strip() == "" for item in user_value):
                return False
            return True

        # 对于布尔值，只有与默认值不同时才保留
        if isinstance(user_value, bool):
            return user_value != default_value

        # 对于数字，只有与默认值不同时才保留
        if isinstance(user_value, (int, float)):
            return user_value != default_value

        # 其他类型，默认保留
        return True

    def smart_update_config(self):
        """
        智能更新配置：替代复杂的版本迁移逻辑
        使用最新默认配置 + 保留用户配置值的方式
        版本号统一使用软件版本，不再单独维护
        """
        with self._lock:
            try:
                user_config = None

                # 读取用户配置（如果存在）
                if os.path.exists(self.config_path):
                    try:
                        with open(self.config_path, "r", encoding="utf-8") as f:
                            user_config = yaml.safe_load(f)
                    except Exception as e:
                        log.print_log(f"读取用户配置失败: {e}", "warning")
                        user_config = None

                # 合并配置（版本号自动更新为最新）
                merged_config = self.merge_with_user_config(user_config or {})

                # 保存合并后的配置
                with open(self.config_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        merged_config,
                        f,
                        Dumper=IndentedDumper,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                        indent=2,
                    )

                # 更新内存中的配置
                self.config = merged_config

                log.print_log("配置数据加载成功", "success")
                return True

            except Exception as e:
                log.print_log(f"配置数据加载失败: {e}", "error")
                return False

    def migrate_config_if_needed(self):
        """
        智能配置更新：替代复杂的版本迁移逻辑
        总是使用最新默认配置 + 保留用户配置值
        版本号统一使用软件版本，不再单独维护
        """
        try:
            return self.smart_update_config()
        except Exception:
            # 失败时使用默认配置
            try:
                # 直接使用默认配置重写（版本号已是最新）
                config_path = str(PathManager.get_config_path("config.yaml"))
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        self.default_config,
                        f,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                        indent=2,
                    )

                self.config = self.default_config.copy()
                return True

            except Exception:
                return False
