"""Plugin architecture — discover and load custom scanners, generators, validators via entry points."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any

from testforge.domain.ports import CodeScannerPort, TestGeneratorPort
from testforge.domain.value_objects import TestLayer

logger = logging.getLogger(__name__)

# Entry point groups
SCANNER_GROUP = "testforge.scanners"
GENERATOR_GROUP = "testforge.generators"
VALIDATOR_GROUP = "testforge.validators"


@dataclass
class PluginInfo:
    """Metadata about a discovered plugin."""
    name: str
    group: str
    module: str
    loaded: bool = False
    error: str = ""


@dataclass
class PluginRegistry:
    """Registry of all discovered plugins."""
    scanners: dict[str, Any] = field(default_factory=dict)
    generators: dict[str, Any] = field(default_factory=dict)
    validators: dict[str, Any] = field(default_factory=dict)
    plugins: list[PluginInfo] = field(default_factory=list)

    @property
    def total_loaded(self) -> int:
        return sum(1 for p in self.plugins if p.loaded)


class PluginManager:
    """Discovers and loads TestForge plugins via Python entry points.

    Plugins register via pyproject.toml:
        [project.entry-points."testforge.scanners"]
        my_scanner = "my_package.scanner:MyScanner"

        [project.entry-points."testforge.generators"]
        my_generator = "my_package.generator:MyGenerator"

        [project.entry-points."testforge.validators"]
        my_validator = "my_package.validator:MyValidator"
    """

    def __init__(self) -> None:
        self._registry = PluginRegistry()

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    def discover_all(self) -> PluginRegistry:
        """Discover and load all plugins from entry points."""
        self._discover_group(SCANNER_GROUP, self._registry.scanners)
        self._discover_group(GENERATOR_GROUP, self._registry.generators)
        self._discover_group(VALIDATOR_GROUP, self._registry.validators)
        return self._registry

    def _discover_group(self, group: str, target: dict[str, Any]) -> None:
        """Discover plugins in a specific entry point group."""
        try:
            eps = entry_points(group=group)
        except TypeError:
            # Python < 3.12 compatibility
            all_eps = entry_points()
            eps = all_eps.get(group, [])  # type: ignore[assignment]

        for ep in eps:
            info = PluginInfo(name=ep.name, group=group, module=ep.value)
            try:
                plugin_class = ep.load()
                target[ep.name] = plugin_class
                info.loaded = True
                logger.info("Loaded plugin: %s from %s", ep.name, ep.value)
            except Exception as e:
                info.error = str(e)
                logger.warning("Failed to load plugin %s: %s", ep.name, e)
            self._registry.plugins.append(info)

    def get_scanner(self, name: str) -> CodeScannerPort | None:
        """Get a scanner plugin by name and instantiate it."""
        cls = self._registry.scanners.get(name)
        if cls is None:
            return None
        try:
            return cls()  # type: ignore[return-value]
        except Exception:
            return None

    def get_generator(self, name: str) -> TestGeneratorPort | None:
        """Get a generator plugin by name and instantiate it."""
        cls = self._registry.generators.get(name)
        if cls is None:
            return None
        try:
            return cls()  # type: ignore[return-value]
        except Exception:
            return None

    def get_generators_for_layer(self, layer: TestLayer) -> list[TestGeneratorPort]:
        """Get all generator plugins that handle a specific layer."""
        results = []
        for name, cls in self._registry.generators.items():
            try:
                instance = cls()
                if hasattr(instance, "layer") and instance.layer == layer:
                    results.append(instance)
            except Exception:
                continue
        return results

    def register_scanner(self, name: str, scanner_class: type) -> None:
        """Manually register a scanner plugin."""
        self._registry.scanners[name] = scanner_class
        self._registry.plugins.append(PluginInfo(
            name=name, group=SCANNER_GROUP, module=str(scanner_class), loaded=True,
        ))

    def register_generator(self, name: str, generator_class: type) -> None:
        """Manually register a generator plugin."""
        self._registry.generators[name] = generator_class
        self._registry.plugins.append(PluginInfo(
            name=name, group=GENERATOR_GROUP, module=str(generator_class), loaded=True,
        ))

    def register_validator(self, name: str, validator_class: type) -> None:
        """Manually register a validator plugin."""
        self._registry.validators[name] = validator_class
        self._registry.plugins.append(PluginInfo(
            name=name, group=VALIDATOR_GROUP, module=str(validator_class), loaded=True,
        ))
