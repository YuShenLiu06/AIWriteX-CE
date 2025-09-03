import os
import glob
import platform
from pathlib import Path
from src.ai_write_x.utils import utils


class PathManager:
    """跨平台路径管理器，确保所有写入操作使用正确的可写目录"""

    @staticmethod
    def get_app_data_dir():
        """获取应用数据目录"""
        # 开发模式：使用项目根目录
        if not utils.get_is_release_ver():
            # 从当前文件位置回到项目根目录
            return Path(__file__).parent.parent.parent.parent

        # 发布模式：使用系统用户数据目录
        if platform.system() == "Darwin":  # macOS
            return Path.home() / "Library/Application Support/AIWriteX"
        elif platform.system() == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "AIWriteX"
        else:  # Linux
            return Path.home() / ".config/AIWriteX"

    @staticmethod
    def get_config_dir():
        """获取配置文件目录"""
        if not utils.get_is_release_ver():
            # 开发模式：使用源码目录
            return Path(__file__).parent.parent / "config"
        else:
            # 发布模式：使用用户数据目录
            config_dir = PathManager.get_app_data_dir() / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir

    @staticmethod
    def get_article_dir():
        """获取文章目录"""
        if not utils.get_is_release_ver():
            # 开发模式：使用项目根目录下的 articles
            article_dir = PathManager.get_app_data_dir() / "output/article"
        else:
            # 发布模式：使用用户数据目录
            article_dir = PathManager.get_app_data_dir() / "output/article"

        article_dir.mkdir(parents=True, exist_ok=True)
        return article_dir

    @staticmethod
    def get_template_dir():
        """获取模板目录 - 始终返回用户可写目录"""
        if not utils.get_is_release_ver():
            # 开发模式：使用项目目录
            return PathManager.get_app_data_dir() / "knowledge/templates"
        else:
            # 发布模式：使用用户数据目录
            template_dir = PathManager.get_app_data_dir() / "templates"
            template_dir.mkdir(parents=True, exist_ok=True)

            # 首次运行时，从资源目录复制默认模板到用户目录
            res_template_dir = utils.get_res_path("templates")
            template_files = glob.glob(os.path.join(template_dir, "*", "*.html"))
            if os.path.exists(res_template_dir) and not template_files:
                import shutil

                shutil.copytree(res_template_dir, template_dir, dirs_exist_ok=True)

            return template_dir

    @staticmethod
    def get_image_dir():
        """获取图片目录"""
        if not utils.get_is_release_ver():
            # 开发模式：使用项目根目录下的 image
            image_dir = PathManager.get_app_data_dir() / "image"
        else:
            # 发布模式：使用用户数据目录
            image_dir = PathManager.get_app_data_dir() / "image"

        image_dir.mkdir(parents=True, exist_ok=True)
        return image_dir

    @staticmethod
    def get_log_dir():
        """获取日志目录"""
        if not utils.get_is_release_ver():
            # 开发模式：使用项目根目录下的 logs
            log_dir = PathManager.get_app_data_dir() / "logs"
        else:
            # 发布模式：使用用户数据目录
            log_dir = PathManager.get_app_data_dir() / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @staticmethod
    def get_config_path(file_name="config.yaml"):
        """获取配置文件的完整路径"""
        return PathManager.get_config_dir() / file_name

    @staticmethod
    def ensure_directory_exists(path):
        """确保目录存在，如果不存在则创建"""
        Path(path).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_writable(path):
        """检查路径是否可写"""
        try:
            test_file = Path(path) / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False
