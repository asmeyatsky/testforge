"""Tests for config adapter."""

from pathlib import Path

import pytest

from testforge.domain.errors import ConfigError
from testforge.infrastructure.config import ConfigAdapter


class TestConfigAdapter:
    def test_load_defaults_when_no_file(self, tmp_path: Path):
        adapter = ConfigAdapter()
        cfg = adapter.load(tmp_path)
        assert cfg["project"]["name"] == "unnamed"
        assert cfg["project"]["languages"] == ["python"]
        assert cfg["layers"]["unit"]["enabled"] is True
        assert cfg["ai"]["provider"] == "claude"
        assert cfg["output_dir"] == ".testforge_output"

    def test_load_from_file(self, tmp_path: Path):
        config_file = tmp_path / "testforge.yml"
        config_file.write_text(
            "project:\n  name: my-app\n  languages: [python, typescript]\n",
            encoding="utf-8",
        )
        adapter = ConfigAdapter()
        cfg = adapter.load(config_file)
        assert cfg["project"]["name"] == "my-app"
        assert cfg["project"]["languages"] == ["python", "typescript"]
        # Defaults still present for unspecified keys
        assert cfg["layers"]["unit"]["enabled"] is True

    def test_load_auto_discovers_config(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / "testforge.yml"
        config_file.write_text("project:\n  name: discovered\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        adapter = ConfigAdapter()
        cfg = adapter.load(tmp_path)
        assert cfg["project"]["name"] == "discovered"

    def test_load_merges_nested(self, tmp_path: Path):
        config_file = tmp_path / "testforge.yml"
        config_file.write_text(
            "layers:\n  unit:\n    output_dir: custom/unit\n",
            encoding="utf-8",
        )
        adapter = ConfigAdapter()
        cfg = adapter.load(config_file)
        assert cfg["layers"]["unit"]["output_dir"] == "custom/unit"
        assert cfg["layers"]["unit"]["enabled"] is True  # default preserved

    def test_load_invalid_yaml_raises(self, tmp_path: Path):
        bad = tmp_path / "testforge.yml"
        bad.write_text("{{invalid yaml", encoding="utf-8")
        adapter = ConfigAdapter()
        with pytest.raises(ConfigError):
            adapter.load(bad)

    def test_load_empty_yaml(self, tmp_path: Path):
        empty = tmp_path / "testforge.yml"
        empty.write_text("", encoding="utf-8")
        adapter = ConfigAdapter()
        cfg = adapter.load(empty)
        # Should return defaults
        assert cfg["project"]["name"] == "unnamed"
