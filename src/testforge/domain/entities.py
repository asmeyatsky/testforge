"""Domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from testforge.domain.value_objects import (
    APIEndpoint,
    DependencyGraph,
    ModuleInfo,
    TestLayer,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class CodebaseAnalysis:
    id: str = field(default_factory=_new_id)
    root_path: str = ""
    modules: tuple[ModuleInfo, ...] = ()
    dependency_graph: DependencyGraph = field(default_factory=DependencyGraph)
    endpoints: tuple[APIEndpoint, ...] = ()
    languages: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def total_functions(self) -> int:
        return sum(len(m.functions) for m in self.modules)

    @property
    def total_classes(self) -> int:
        return sum(len(m.classes) for m in self.modules)

    @property
    def total_modules(self) -> int:
        return len(self.modules)


@dataclass(frozen=True)
class TestCase:
    __test__ = False

    id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    layer: TestLayer = TestLayer.UNIT
    target_function: str = ""
    target_module: str = ""
    priority: int = 1  # 1 = highest
    tags: tuple[str, ...] = ()
    external_calls: tuple[str, ...] = ()
    fixtures_needed: tuple[str, ...] = ()


@dataclass(frozen=True)
class TestSuite:
    __test__ = False

    id: str = field(default_factory=_new_id)
    layer: TestLayer = TestLayer.UNIT
    test_cases: tuple[TestCase, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def size(self) -> int:
        return len(self.test_cases)


@dataclass(frozen=True)
class TestStrategy:
    __test__ = False

    id: str = field(default_factory=_new_id)
    analysis_id: str = ""
    suites: tuple[TestSuite, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def suite_for_layer(self, layer: TestLayer) -> TestSuite | None:
        for suite in self.suites:
            if suite.layer == layer:
                return suite
        return None

    @property
    def total_test_cases(self) -> int:
        return sum(s.size for s in self.suites)

    @property
    def layers_covered(self) -> tuple[TestLayer, ...]:
        return tuple(s.layer for s in self.suites)
