"""Domain value objects."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path


class TestLayer(enum.Enum):
    __test__ = False

    UNIT = "unit"
    INTEGRATION = "integration"
    UAT = "uat"
    SOAK = "soak"
    PERFORMANCE = "performance"


@dataclass(frozen=True)
class FilePath:
    path: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))

    @property
    def suffix(self) -> str:
        return self.path.suffix

    @property
    def stem(self) -> str:
        return self.path.stem

    def __str__(self) -> str:
        return str(self.path)


@dataclass(frozen=True)
class FunctionSignature:
    name: str
    parameters: tuple[str, ...]
    return_type: str | None = None
    decorators: tuple[str, ...] = ()
    is_async: bool = False
    docstring: str | None = None
    line_number: int = 0
    external_calls: tuple[str, ...] = ()  # e.g. ("requests.get", "db.query")
    fixtures_needed: tuple[str, ...] = ()  # e.g. ("tmp_path", "monkeypatch")


@dataclass(frozen=True)
class ClassInfo:
    name: str
    methods: tuple[FunctionSignature, ...] = ()
    bases: tuple[str, ...] = ()
    decorators: tuple[str, ...] = ()
    docstring: str | None = None
    line_number: int = 0


@dataclass(frozen=True)
class APIEndpoint:
    method: str  # GET, POST, etc.
    path: str
    handler_name: str
    file_path: str


@dataclass(frozen=True)
class ModuleInfo:
    file_path: FilePath
    functions: tuple[FunctionSignature, ...] = ()
    classes: tuple[ClassInfo, ...] = ()
    imports: tuple[str, ...] = ()
    endpoints: tuple[APIEndpoint, ...] = ()


@dataclass(frozen=True)
class DependencyGraph:
    """Maps module paths to their import dependencies."""
    edges: tuple[tuple[str, str], ...] = ()

    @property
    def modules(self) -> frozenset[str]:
        sources = {e[0] for e in self.edges}
        targets = {e[1] for e in self.edges}
        return frozenset(sources | targets)

    def dependents_of(self, module: str) -> frozenset[str]:
        return frozenset(e[0] for e in self.edges if e[1] == module)

    def dependencies_of(self, module: str) -> frozenset[str]:
        return frozenset(e[1] for e in self.edges if e[0] == module)
