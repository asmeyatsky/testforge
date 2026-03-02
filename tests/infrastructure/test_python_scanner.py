"""Tests for the Python AST scanner against real sample files."""

import textwrap
from pathlib import Path

import pytest

from testforge.infrastructure.scanners.python_scanner import PythonScanner


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a minimal sample Python project."""
    # Simple module
    (tmp_path / "utils.py").write_text(
        textwrap.dedent("""\
        import os
        from pathlib import Path

        def format_name(name: str) -> str:
            \"\"\"Format a name.\"\"\"
            return name.strip().title()

        def _private_helper():
            pass

        class Formatter:
            def __init__(self, prefix: str):
                self.prefix = prefix

            def format(self, value: str) -> str:
                return f"{self.prefix}: {value}"
        """),
        encoding="utf-8",
    )

    # Flask-style app
    (tmp_path / "app.py").write_text(
        textwrap.dedent("""\
        from flask import Flask

        app = Flask(__name__)

        @app.get("/users")
        def get_users():
            return []

        @app.post("/users")
        def create_user():
            return {}

        @app.route("/health")
        def health():
            return "ok"
        """),
        encoding="utf-8",
    )

    # Subpackage
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "service.py").write_text(
        textwrap.dedent("""\
        from utils import Formatter

        async def process(data):
            pass
        """),
        encoding="utf-8",
    )

    return tmp_path


class TestPythonScanner:
    def test_scan_finds_modules(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)
        assert analysis.total_modules >= 3  # utils, app, service (+ __init__)

    def test_scan_extracts_functions(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)

        all_funcs = []
        for mod in analysis.modules:
            all_funcs.extend(mod.functions)

        func_names = {f.name for f in all_funcs}
        assert "format_name" in func_names
        assert "_private_helper" in func_names
        assert "get_users" in func_names

    def test_scan_extracts_classes(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)

        all_classes = []
        for mod in analysis.modules:
            all_classes.extend(mod.classes)

        class_names = {c.name for c in all_classes}
        assert "Formatter" in class_names

    def test_scan_extracts_endpoints(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)

        assert len(analysis.endpoints) >= 3
        paths = {ep.path for ep in analysis.endpoints}
        assert "/users" in paths
        assert "/health" in paths

    def test_scan_detects_async(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)

        for mod in analysis.modules:
            for func in mod.functions:
                if func.name == "process":
                    assert func.is_async is True
                    return
        pytest.fail("async function 'process' not found")

    def test_scan_extracts_imports(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)

        all_imports: set[str] = set()
        for mod in analysis.modules:
            all_imports.update(mod.imports)

        assert "os" in all_imports
        assert "pathlib" in all_imports

    def test_scan_extracts_return_type(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)

        for mod in analysis.modules:
            for func in mod.functions:
                if func.name == "format_name":
                    assert func.return_type == "str"
                    return
        pytest.fail("function 'format_name' not found")

    def test_scan_extracts_docstring(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)

        for mod in analysis.modules:
            for func in mod.functions:
                if func.name == "format_name":
                    assert func.docstring == "Format a name."
                    return
        pytest.fail("function 'format_name' not found")

    def test_scan_builds_dependency_graph(self, sample_project: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(sample_project)
        assert len(analysis.dependency_graph.edges) > 0

    def test_scan_empty_dir(self, tmp_path: Path):
        scanner = PythonScanner()
        analysis = scanner.scan(tmp_path)
        assert analysis.total_modules == 0

    def test_scan_skips_syntax_errors(self, tmp_path: Path):
        (tmp_path / "bad.py").write_text("def broken(:\n  pass", encoding="utf-8")
        (tmp_path / "good.py").write_text("def ok(): pass", encoding="utf-8")

        scanner = PythonScanner()
        analysis = scanner.scan(tmp_path)
        assert analysis.total_modules == 1
