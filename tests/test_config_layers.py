"""Tests for config-driven layer filtering."""

from testforge.domain.value_objects import TestLayer
from testforge.presentation.cli import _enabled_layers, _resolve_layers


class TestConfigLayerFiltering:
    def test_enabled_layers_from_config(self):
        cfg = {
            "layers": {
                "unit": {"enabled": True},
                "integration": {"enabled": True},
                "uat": {"enabled": False},
                "soak": {"enabled": False},
                "performance": {"enabled": False},
            }
        }
        result = _enabled_layers(cfg)
        assert TestLayer.UNIT in result
        assert TestLayer.INTEGRATION in result
        assert TestLayer.UAT not in result

    def test_all_disabled_defaults_to_unit(self):
        cfg = {"layers": {}}
        result = _resolve_layers(None, cfg)
        assert result == [TestLayer.UNIT]

    def test_explicit_layers_override_config(self):
        cfg = {
            "layers": {
                "unit": {"enabled": True},
                "integration": {"enabled": False},
            }
        }
        explicit = [TestLayer.INTEGRATION, TestLayer.UAT]
        result = _resolve_layers(explicit, cfg)
        assert result == [TestLayer.INTEGRATION, TestLayer.UAT]

    def test_no_explicit_uses_config(self):
        cfg = {
            "layers": {
                "unit": {"enabled": True},
                "integration": {"enabled": True},
                "uat": {"enabled": True},
            }
        }
        result = _resolve_layers(None, cfg)
        assert TestLayer.UNIT in result
        assert TestLayer.INTEGRATION in result
        assert TestLayer.UAT in result
