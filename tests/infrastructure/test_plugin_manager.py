"""Tests for plugin architecture."""

from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.plugin_manager import (
    PluginManager,
    PluginRegistry,
)


class _FakeScanner:
    def scan(self, root_path):
        pass


class _FakeGenerator:
    layer = TestLayer.UNIT

    def generate(self, strategy, output_dir):
        pass


class TestPluginRegistry:
    def test_empty_registry(self):
        reg = PluginRegistry()
        assert reg.total_loaded == 0

    def test_total_loaded(self):
        from testforge.infrastructure.plugin_manager import PluginInfo
        reg = PluginRegistry()
        reg.plugins.append(PluginInfo(name="a", group="scanners", module="mod", loaded=True))
        reg.plugins.append(PluginInfo(name="b", group="scanners", module="mod", loaded=False))
        assert reg.total_loaded == 1


class TestPluginManager:
    def test_discover_returns_registry(self):
        pm = PluginManager()
        reg = pm.discover_all()
        assert isinstance(reg, PluginRegistry)

    def test_register_scanner(self):
        pm = PluginManager()
        pm.register_scanner("fake", _FakeScanner)
        assert "fake" in pm.registry.scanners

    def test_register_generator(self):
        pm = PluginManager()
        pm.register_generator("fake", _FakeGenerator)
        assert "fake" in pm.registry.generators

    def test_get_scanner(self):
        pm = PluginManager()
        pm.register_scanner("fake", _FakeScanner)
        scanner = pm.get_scanner("fake")
        assert scanner is not None
        assert hasattr(scanner, "scan")

    def test_get_scanner_missing(self):
        pm = PluginManager()
        assert pm.get_scanner("nonexistent") is None

    def test_get_generator(self):
        pm = PluginManager()
        pm.register_generator("fake", _FakeGenerator)
        gen = pm.get_generator("fake")
        assert gen is not None

    def test_get_generators_for_layer(self):
        pm = PluginManager()
        pm.register_generator("fake_unit", _FakeGenerator)
        gens = pm.get_generators_for_layer(TestLayer.UNIT)
        assert len(gens) == 1

    def test_register_validator(self):
        pm = PluginManager()
        pm.register_validator("fake", _FakeScanner)
        assert "fake" in pm.registry.validators
