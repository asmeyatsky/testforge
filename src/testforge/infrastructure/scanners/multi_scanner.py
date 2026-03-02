"""Multi-language scanner — auto-detects and combines results from language-specific scanners."""

from __future__ import annotations

from pathlib import Path

from testforge.domain.entities import CodebaseAnalysis
from testforge.domain.value_objects import DependencyGraph
from testforge.infrastructure.scanners.python_scanner import PythonScanner
from testforge.infrastructure.scanners.typescript_scanner import TypeScriptScanner


class MultiScanner:
    """Scans a codebase using all available language scanners and merges results."""

    def __init__(self) -> None:
        self._python = PythonScanner()
        self._typescript = TypeScriptScanner()

    def scan(self, root_path: Path) -> CodebaseAnalysis:
        languages_detected = self._detect_languages(root_path)

        analyses: list[CodebaseAnalysis] = []
        if "python" in languages_detected:
            analyses.append(self._python.scan(root_path))
        if "typescript" in languages_detected or "javascript" in languages_detected:
            analyses.append(self._typescript.scan(root_path))

        if not analyses:
            return CodebaseAnalysis(root_path=str(root_path))

        return self._merge(analyses, root_path)

    def _detect_languages(self, root_path: Path) -> set[str]:
        """Detect languages by file extensions present in the project."""
        languages: set[str] = set()
        skip = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

        for child in root_path.rglob("*"):
            if any(part in skip or part.startswith(".") for part in child.parts):
                continue
            if not child.is_file():
                continue
            suffix = child.suffix
            if suffix == ".py":
                languages.add("python")
            elif suffix in (".ts", ".tsx"):
                languages.add("typescript")
            elif suffix in (".js", ".jsx"):
                languages.add("javascript")
            # Early exit if we've found all we can scan
            if languages >= {"python", "typescript"}:
                break

        return languages

    def _merge(self, analyses: list[CodebaseAnalysis], root_path: Path) -> CodebaseAnalysis:
        """Merge multiple CodebaseAnalysis results into one."""
        all_modules = []
        all_endpoints = []
        all_edges = []
        all_languages: set[str] = set()

        for analysis in analyses:
            all_modules.extend(analysis.modules)
            all_endpoints.extend(analysis.endpoints)
            all_edges.extend(analysis.dependency_graph.edges)
            all_languages.update(analysis.languages)

        return CodebaseAnalysis(
            root_path=str(root_path),
            modules=tuple(all_modules),
            dependency_graph=DependencyGraph(edges=tuple(all_edges)),
            endpoints=tuple(all_endpoints),
            languages=tuple(sorted(all_languages)),
        )
