"""File system adapter."""

from __future__ import annotations

from pathlib import Path


class FileSystemAdapter:
    """Concrete file system operations."""

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_files(self, root: Path, pattern: str = "**/*") -> list[Path]:
        return sorted(p for p in root.glob(pattern) if p.is_file())

    def exists(self, path: Path) -> bool:
        return path.exists()

    def mkdir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
