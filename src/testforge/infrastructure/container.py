"""Composition root — wires all adapters to ports."""

from __future__ import annotations

import os
from pathlib import Path

from testforge.domain.events import DomainEvent
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.config import ConfigAdapter
from testforge.infrastructure.filesystem import FileSystemAdapter
from testforge.infrastructure.generators.integration_generator import IntegrationTestGenerator
from testforge.infrastructure.generators.performance_generator import PerformanceGenerator
from testforge.infrastructure.generators.soak_generator import SoakGenerator
from testforge.infrastructure.generators.uat_generator import UATGenerator
from testforge.infrastructure.generators.unit_generator import UnitTestGenerator
from testforge.infrastructure.scanners.multi_scanner import MultiScanner
from testforge.infrastructure.scanners.python_scanner import PythonScanner
from testforge.infrastructure.scanners.typescript_scanner import TypeScriptScanner


class SimpleEventBus:
    """Minimal in-process event bus."""

    def __init__(self) -> None:
        self._handlers: dict[type, list] = {}

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def subscribe(self, event_type: type[DomainEvent], handler: object) -> None:
        self._handlers.setdefault(event_type, []).append(handler)


class Container:
    """Dependency injection container — composition root."""

    def __init__(self, config: dict | None = None) -> None:
        self._config_adapter = ConfigAdapter()
        self._config = config or self._config_adapter.load()
        self._event_bus = SimpleEventBus()
        self._fs = FileSystemAdapter()

    @property
    def config(self) -> dict:
        return self._config

    @property
    def event_bus(self) -> SimpleEventBus:
        return self._event_bus

    @property
    def filesystem(self) -> FileSystemAdapter:
        return self._fs

    def scanner(self, language: str | None = None) -> PythonScanner | TypeScriptScanner | MultiScanner:
        langs = self._config.get("project", {}).get("languages", ["python"])
        lang = language or (langs[0] if langs else "python")
        if lang == "auto" or len(langs) > 1:
            return MultiScanner()
        if lang in ("typescript", "javascript"):
            return TypeScriptScanner()
        return PythonScanner()

    def ai_strategy(self):
        """Returns Claude adapter if API key is available, else None."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        from testforge.infrastructure.ai.claude_adapter import ClaudeAdapter

        model = self._config.get("ai", {}).get("model", "claude-sonnet-4-20250514")
        return ClaudeAdapter(api_key=api_key, model=model)

    def generators(self, source_root: Path | None = None) -> dict[TestLayer, object]:
        ai = self.ai_strategy()
        return {
            TestLayer.UNIT: UnitTestGenerator(ai_adapter=ai, source_root=source_root),
            TestLayer.INTEGRATION: IntegrationTestGenerator(ai_adapter=ai, source_root=source_root),
            TestLayer.UAT: UATGenerator(ai_adapter=ai),
            TestLayer.SOAK: SoakGenerator(),
            TestLayer.PERFORMANCE: PerformanceGenerator(),
        }
