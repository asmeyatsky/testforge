"""Coverage gap analyser — compares existing tests against codebase analysis."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from testforge.domain.entities import CodebaseAnalysis


@dataclass
class ModuleGap:
    file_path: str
    tested: list[str] = field(default_factory=list)
    untested: list[str] = field(default_factory=list)

    @property
    def tested_count(self) -> int:
        return len(self.tested)

    @property
    def total_count(self) -> int:
        return len(self.tested) + len(self.untested)


@dataclass
class GapReport:
    modules: list[ModuleGap] = field(default_factory=list)

    @property
    def tested(self) -> int:
        return sum(m.tested_count for m in self.modules)

    @property
    def total(self) -> int:
        return sum(m.total_count for m in self.modules)

    @property
    def untested(self) -> list[str]:
        result: list[str] = []
        for m in self.modules:
            for fn in m.untested:
                result.append(f"{m.file_path}::{fn}")
        return result

    @property
    def coverage_percent(self) -> float:
        return (self.tested / self.total * 100) if self.total else 100.0


class GapAnalyser:
    """Analyses gaps between codebase functions and existing tests."""

    def analyse(self, analysis: CodebaseAnalysis, test_dir: Path) -> GapReport:
        # Collect all test function names from existing test files
        tested_names = self._collect_test_targets(test_dir)

        modules: list[ModuleGap] = []
        for module in analysis.modules:
            tested: list[str] = []
            untested: list[str] = []

            for func in module.functions:
                if self._is_tested(func.name, tested_names):
                    tested.append(func.name)
                else:
                    untested.append(func.name)

            for cls in module.classes:
                for method in cls.methods:
                    if method.name.startswith("_") and method.name != "__init__":
                        continue
                    full_name = f"{cls.name}.{method.name}"
                    short_name = method.name
                    if self._is_tested(full_name, tested_names) or self._is_tested(short_name, tested_names):
                        tested.append(full_name)
                    else:
                        untested.append(full_name)

            if tested or untested:
                modules.append(ModuleGap(
                    file_path=str(module.file_path),
                    tested=tested,
                    untested=untested,
                ))

        return GapReport(modules=modules)

    def _collect_test_targets(self, test_dir: Path) -> set[str]:
        """Extract function/method names that are being tested from test files."""
        targets: set[str] = set()

        if not test_dir.exists():
            return targets

        for test_file in test_dir.rglob("test_*.py"):
            try:
                source = test_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    # Extract the target name from the test name
                    # e.g., "test_format_name" -> "format_name"
                    target = node.name[5:]  # strip "test_"
                    targets.add(target)
                    # Also handle class-method pattern: "test_ClassName_method"
                    parts = target.split("_", 1)
                    if len(parts) == 2:
                        targets.add(f"{parts[0]}.{parts[1]}")

        return targets

    @staticmethod
    def _is_tested(func_name: str, tested_names: set[str]) -> bool:
        """Check if a function appears to be tested."""
        # Direct match
        if func_name in tested_names:
            return True
        # Normalized match (lowercase, underscores)
        normalized = func_name.lower().replace(".", "_")
        return any(normalized in t.lower() for t in tested_names)
