"""Port protocols — interfaces for the domain."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from testforge.domain.entities import CodebaseAnalysis, TestStrategy, TestSuite
from testforge.domain.events import DomainEvent
from testforge.domain.value_objects import TestLayer


@runtime_checkable
class CodeScannerPort(Protocol):
    def scan(self, root_path: Path) -> CodebaseAnalysis: ...


@runtime_checkable
class AIStrategyPort(Protocol):
    def generate_strategy(
        self,
        analysis: CodebaseAnalysis,
        layers: list[TestLayer],
        prd_content: str | None = None,
    ) -> TestStrategy: ...


@runtime_checkable
class TestGeneratorPort(Protocol):
    @property
    def layer(self) -> TestLayer: ...

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite: ...


@runtime_checkable
class ConfigPort(Protocol):
    def load(self, path: Path | None = None) -> dict: ...


@runtime_checkable
class FileSystemPort(Protocol):
    def read_text(self, path: Path) -> str: ...
    def write_text(self, path: Path, content: str) -> None: ...
    def list_files(self, root: Path, pattern: str = "**/*") -> list[Path]: ...
    def exists(self, path: Path) -> bool: ...
    def mkdir(self, path: Path) -> None: ...


@runtime_checkable
class EventBusPort(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: type[DomainEvent], handler: object) -> None: ...
