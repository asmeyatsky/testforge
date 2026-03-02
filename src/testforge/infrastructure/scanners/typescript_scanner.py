"""TypeScript scanner — stub for future implementation."""

from __future__ import annotations

from pathlib import Path

from testforge.domain.entities import CodebaseAnalysis
from testforge.domain.errors import UnsupportedLanguageError


class TypeScriptScanner:
    """Stub scanner for TypeScript codebases.

    Will be implemented in a future phase using tree-sitter or ts-morph.
    """

    def scan(self, root_path: Path) -> CodebaseAnalysis:
        raise UnsupportedLanguageError("typescript")
