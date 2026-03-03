"""Incremental test generation — only regenerate tests for changed files."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DiffResult:
    """Files changed since last known state."""
    modified: tuple[str, ...]
    added: tuple[str, ...]
    deleted: tuple[str, ...]

    @property
    def all_changed(self) -> tuple[str, ...]:
        return self.modified + self.added

    @property
    def has_changes(self) -> bool:
        return bool(self.modified or self.added or self.deleted)


class DiffDetector:
    """Detects changed source files using git diff or mtime comparison."""

    def __init__(self, root_path: Path) -> None:
        self._root = root_path

    def detect_git_changes(self, ref: str = "HEAD") -> DiffResult:
        """Detect changes vs a git ref (default: uncommitted changes vs HEAD)."""
        logger.info("Detecting git changes against %s in %s", ref, self._root)
        try:
            # Get staged + unstaged changes
            proc = subprocess.run(
                ["git", "diff", "--name-status", ref],
                cwd=self._root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return DiffResult((), (), ())

            # Also get untracked files
            untracked_proc = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self._root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            modified: list[str] = []
            added: list[str] = []
            deleted: list[str] = []

            for line in proc.stdout.strip().splitlines():
                if not line:
                    continue
                parts = line.split("\t", 1)
                if len(parts) < 2:
                    continue
                status, path = parts[0].strip(), parts[1].strip()
                if not self._is_source_file(path):
                    continue
                if status.startswith("M"):
                    modified.append(path)
                elif status.startswith("A"):
                    added.append(path)
                elif status.startswith("D"):
                    deleted.append(path)

            # Add untracked source files as "added"
            if untracked_proc.returncode == 0:
                for path in untracked_proc.stdout.strip().splitlines():
                    if path and self._is_source_file(path):
                        added.append(path)

            return DiffResult(
                modified=tuple(sorted(set(modified))),
                added=tuple(sorted(set(added))),
                deleted=tuple(sorted(set(deleted))),
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return DiffResult((), (), ())

    def detect_changes_between(self, base: str, head: str = "HEAD") -> DiffResult:
        """Detect changes between two git refs."""
        try:
            proc = subprocess.run(
                ["git", "diff", "--name-status", f"{base}...{head}"],
                cwd=self._root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return DiffResult((), (), ())

            modified: list[str] = []
            added: list[str] = []
            deleted: list[str] = []

            for line in proc.stdout.strip().splitlines():
                if not line:
                    continue
                parts = line.split("\t", 1)
                if len(parts) < 2:
                    continue
                status, path = parts[0].strip(), parts[1].strip()
                if not self._is_source_file(path):
                    continue
                if status.startswith("M"):
                    modified.append(path)
                elif status.startswith("A"):
                    added.append(path)
                elif status.startswith("D"):
                    deleted.append(path)

            return DiffResult(
                modified=tuple(sorted(set(modified))),
                added=tuple(sorted(set(added))),
                deleted=tuple(sorted(set(deleted))),
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return DiffResult((), (), ())

    @staticmethod
    def _is_source_file(path: str) -> bool:
        """Check if a path is a source file we care about."""
        exts = {".py", ".ts", ".tsx", ".js", ".jsx"}
        return any(path.endswith(ext) for ext in exts)

    def filter_analysis_to_changed(self, analysis, diff: DiffResult):
        """Filter a CodebaseAnalysis to only include changed modules."""
        from testforge.domain.entities import CodebaseAnalysis

        changed_paths = set(diff.all_changed)
        if not changed_paths:
            return analysis

        filtered_modules = tuple(
            m for m in analysis.modules
            if str(m.file_path) in changed_paths
        )
        filtered_endpoints = tuple(
            e for e in analysis.endpoints
            if e.file_path in changed_paths
        )

        return CodebaseAnalysis(
            root_path=analysis.root_path,
            modules=filtered_modules,
            dependency_graph=analysis.dependency_graph,
            endpoints=filtered_endpoints,
            languages=analysis.languages,
        )
