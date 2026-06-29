"""Shared infrastructure for the server-config command group.

This module is the only file Phase-A pre-builds before Phase-B agents
fan out. It centralizes constants, Typer app instances, and helper
functions so that __init__.py / llm.py / creative.py can import a
single source of truth without cross-importing each other.
"""

import typer

from ...client import AIWriteXClient
from ...errors import AIWriteXError
from ...formatters import print_error, print_warning

# ---------------------------------------------------------------------------
# Constants — keep here to prevent drift across command files
# ---------------------------------------------------------------------------

# 15 creative dimensions (config.py:263-279).
DIMENSIONAL_KEYS: list[str] = [
    "style", "culture", "time", "personality", "emotion", "format",
    "scene", "audience", "theme", "technique", "language", "tone",
    "perspective", "structure", "rhythm",
]

DIMENSIONAL_NAMES_ZH: dict[str, str] = {
    "style": "文体风格",
    "culture": "文化视角",
    "time": "时空背景",
    "personality": "人格角色",
    "emotion": "情感调性",
    "format": "表达格式",
    "scene": "场景环境",
    "audience": "目标受众",
    "theme": "主题内容",
    "technique": "表现技法",
    "language": "语言风格",
    "tone": "语调语气",
    "perspective": "叙述视角",
    "structure": "文章结构",
    "rhythm": "节奏韵律",
}

# 5 dimension groups (mirrors web/static/js/config-manager.js:4-35).
# Synchronize when the web taxonomy changes.
DIMENSION_GROUPS: dict[str, dict] = {
    "expression": {
        "name": "文体表达维度",
        "dimensions": ["style", "language", "tone"],
        "description": "控制文章的文体风格、语言风格和语调语气",
    },
    "culture": {
        "name": "文化时空维度",
        "dimensions": ["culture", "time", "scene"],
        "description": "设置文化视角、时空背景和场景环境",
    },
    "character": {
        "name": "角色技法维度",
        "dimensions": ["personality", "technique", "perspective"],
        "description": "选择人格角色、表现技法和叙述视角",
    },
    "structure": {
        "name": "结构节奏维度",
        "dimensions": ["structure", "rhythm"],
        "description": "定义文章结构和节奏韵律",
    },
    "audience": {
        "name": "受众主题维度",
        "dimensions": ["audience", "theme", "emotion", "format"],
        "description": "针对目标受众、主题内容、情感调性和表达格式",
    },
}

# Reverse lookup: dimension key -> group key
DIMENSION_TO_GROUP: dict[str, str] = {
    dim: g for g, info in DIMENSION_GROUPS.items() for dim in info["dimensions"]
}

# Top-level global fields of dimensional_creative that users can toggle.
# name -> (type_hint, description). Used by `creative config set`.
DIMENSIONAL_GLOBAL_FIELDS: dict[str, dict] = {
    "enabled": {"type": bool, "desc": "总开关：是否启用维度化创意"},
    "creative_intensity": {"type": float, "desc": "创意强度 (0.0-1.0)"},
    "auto_dimension_selection": {"type": bool, "desc": "自动维度选择（启用时细分维度由系统选，与 Web 一致：关闭后才能单独配置）"},
    "max_dimensions": {"type": int, "desc": "单次生成最多应用的维度数"},
    "compatibility_threshold": {"type": float, "desc": "维度兼容性阈值 (0.0-1.0)"},
    "preserve_core_info": {"type": bool, "desc": "保持核心信息不被创意改写"},
    "allow_experimental": {"type": bool, "desc": "允许实验性维度组合"},
}

# LLM providers (config.py:98-235). Used for argument validation in llm commands.
LLM_PROVIDERS: list[str] = [
    "OpenRouter", "Deepseek", "Grok", "Claude", "Qwen", "Gemini",
    "Ollama", "SiliconFlow", "Kimi", "GLM", "MiniMax",
]

# HTTP endpoints (config.py web/api). Centralized so a future refactor is one edit.
EP_CONFIG = "/api/config/"
EP_CONFIG_DEFAULT = "/api/config/default"

# ---------------------------------------------------------------------------
# Typer app instances — shared across the package
# ---------------------------------------------------------------------------

app = typer.Typer(help="管理服务端配置 (LLM/创意维度/业务参数)")
llm_app = typer.Typer(help="LLM 提供商配置")
creative_app = typer.Typer(help="创意维度配置")


# ---------------------------------------------------------------------------
# Helpers — used by every write command to align with Web UI auto-save
# ---------------------------------------------------------------------------

def _auto_save(client: AIWriteXClient) -> bool:
    """Persist current in-memory config to disk via POST /api/config/.

    Returns True on success, False if persistence failed (the in-memory
    update is still applied). Matches Web UI behavior where every edit
    is immediately saved.
    """
    try:
        client.post_json(EP_CONFIG)
        return True
    except AIWriteXError as e:
        print_warning(f"内存配置已更新，但落盘失败：{e}")
        return False


def _patch_and_save(client: AIWriteXClient, payload: dict) -> bool:
    """PATCH {config_data: payload} then auto-save. Unified write pipeline.

    Args:
        payload: nested dict matching server config sections, e.g.
            {"api": {"OpenRouter": {"api_key": ["xxx"]}}} or
            {"dimensional_creative": {"enabled_dimensions": {"emotion": True}}}.

    Returns True if both PATCH and save succeeded.
    """
    client.patch_json(EP_CONFIG, json={"config_data": payload})
    return _auto_save(client)


def _validate_dims(dims_csv: str) -> list[str]:
    """Parse & validate comma-separated dimension keys.

    On any invalid key, prints an error listing valid keys and raises
    typer.Exit(1). Returns the cleaned list of valid keys otherwise.
    """
    keys = [k.strip() for k in dims_csv.split(",") if k.strip()]
    invalid = [k for k in keys if k not in DIMENSIONAL_KEYS]
    if invalid:
        print_error(f"无效的创意维度: {', '.join(invalid)}")
        valid_hint = ", ".join(f"{k}({DIMENSIONAL_NAMES_ZH[k]})" for k in DIMENSIONAL_KEYS)
        print_error(f"合法维度: {valid_hint}")
        raise typer.Exit(1)
    return keys


__all__ = [
    "DIMENSIONAL_KEYS", "DIMENSIONAL_NAMES_ZH", "DIMENSION_GROUPS",
    "DIMENSION_TO_GROUP", "DIMENSIONAL_GLOBAL_FIELDS",
    "LLM_PROVIDERS",
    "EP_CONFIG", "EP_CONFIG_DEFAULT",
    "app", "llm_app", "creative_app",
    "_auto_save", "_patch_and_save", "_validate_dims",
]
