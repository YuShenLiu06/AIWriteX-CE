"""Configuration storage for AIWriteX CLI."""

from pathlib import Path
from typing import Any, Optional
import yaml


class ConfigStore:
    """Store and retrieve CLI configuration."""

    _config_path: Path = Path.home() / ".aiwritex" / "config.yaml"
    _defaults: dict[str, Any] = {
        "base_url": "http://127.0.0.1:8888",
        "api_key": None,
        "username": None,
        "password": None,
        "timeout": 30,
    }

    @classmethod
    def load(cls) -> dict[str, Any]:
        """Load configuration from file."""
        if not cls._config_path.exists():
            cls._config_path.parent.mkdir(parents=True, exist_ok=True)
            cls._config_path.write_text(
                yaml.dump(cls._defaults, allow_unicode=True), encoding="utf-8"
            )
            return cls._defaults.copy()

        try:
            with open(cls._config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            return {**cls._defaults, **config}
        except Exception:
            return cls._defaults.copy()

    @classmethod
    def save(cls, config: dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            cls._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cls._config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception:
            return False

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a single configuration value."""
        config = cls.load()
        return config.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> bool:
        """Set a single configuration value."""
        config = cls.load()
        config[key] = value
        return cls.save(config)
