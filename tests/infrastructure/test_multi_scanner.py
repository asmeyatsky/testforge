"""Tests for multi-language scanner."""

from pathlib import Path

from testforge.infrastructure.scanners.multi_scanner import MultiScanner


class TestMultiScanner:
    def test_scan_python_only(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("def hello(): pass\n")
        scanner = MultiScanner()
        analysis = scanner.scan(tmp_path)
        assert "python" in analysis.languages
        assert analysis.total_functions >= 1

    def test_scan_typescript_only(self, tmp_path: Path):
        (tmp_path / "app.ts").write_text("export function greet(): void {}\n")
        scanner = MultiScanner()
        analysis = scanner.scan(tmp_path)
        assert "typescript" in analysis.languages

    def test_scan_polyglot(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("def py_func(): pass\n")
        (tmp_path / "utils.ts").write_text("export function ts_func(): void {}\n")
        scanner = MultiScanner()
        analysis = scanner.scan(tmp_path)
        assert "python" in analysis.languages
        assert "typescript" in analysis.languages
        assert analysis.total_modules >= 2

    def test_scan_empty(self, tmp_path: Path):
        scanner = MultiScanner()
        analysis = scanner.scan(tmp_path)
        assert analysis.total_modules == 0
