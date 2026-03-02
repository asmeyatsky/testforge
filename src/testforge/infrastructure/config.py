"""YAML configuration adapter."""

from __future__ import annotations

from pathlib import Path

import yaml

from testforge.domain.errors import ConfigError

DEFAULT_CONFIG_NAMES = ("testforge.yml", "testforge.yaml", ".testforge.yml")

DEFAULT_CONFIG: dict = {
    "project": {
        "name": "unnamed",
        "languages": ["python"],
        "test_framework": "pytest",
    },
    "layers": {
        "unit": {"enabled": True, "output_dir": "tests/unit"},
        "integration": {"enabled": True, "output_dir": "tests/integration"},
        "uat": {"enabled": True, "output_dir": "tests/uat"},
        "soak": {"enabled": False},
        "performance": {"enabled": False},
    },
    "ai": {
        "provider": "claude",
        "model": "claude-sonnet-4-20250514",
    },
    "prd_path": None,
    "output_dir": ".testforge_output",
}


class ConfigAdapter:
    """Reads testforge.yml and returns typed config."""

    def load(self, path: Path | None = None) -> dict:
        if path and path.is_file():
            return self._read(path)

        # Search for config in current directory
        search_dir = path if path and path.is_dir() else Path.cwd()
        for name in DEFAULT_CONFIG_NAMES:
            candidate = search_dir / name
            if candidate.is_file():
                return self._read(candidate)

        return dict(DEFAULT_CONFIG)

    def _read(self, path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) or {}
        except Exception as exc:
            raise ConfigError(f"Failed to read config {path}: {exc}") from exc

        return self._merge(DEFAULT_CONFIG, data)

    def _merge(self, defaults: dict, overrides: dict) -> dict:
        result = dict(defaults)
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result
