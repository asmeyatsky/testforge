"""Unit test generator — Jinja2 templates with optional AI-powered test bodies."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class UnitTestGenerator:
    """Generates pytest unit test files from TestCase objects.

    When an AI adapter is provided, generates real test implementations.
    Otherwise falls back to Jinja2 template scaffolds.
    """

    layer = TestLayer.UNIT

    def __init__(
        self,
        template_dir: Path | None = None,
        ai_adapter: object | None = None,
        source_root: Path | None = None,
    ) -> None:
        tpl_dir = template_dir or _TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(tpl_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._ai = ai_adapter
        self._source_root = source_root

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite:
        suite = strategy.suite_for_layer(TestLayer.UNIT)
        if not suite:
            return TestSuite(layer=TestLayer.UNIT)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Group test cases by target module
        by_module: dict[str, list] = {}
        for tc in suite.test_cases:
            by_module.setdefault(tc.target_module, []).append(tc)

        for module_path, cases in by_module.items():
            module_name = Path(module_path).stem
            out_file = output_dir / f"test_{module_name}.py"

            if self._ai and hasattr(self._ai, "generate_test_code"):
                content = self._generate_with_ai(module_path, cases)
            else:
                content = self._generate_with_template(module_path, module_name, cases)

            out_file.write_text(content, encoding="utf-8")

        return suite

    def _generate_with_ai(self, module_path: str, cases: list) -> str:
        """Use AI to generate real test implementations."""
        source_code = self._read_source(module_path)
        imports_hint = self._build_imports_hint(module_path, cases)

        try:
            code = self._ai.generate_test_code(  # type: ignore[union-attr]
                target_module=module_path,
                source_code=source_code,
                test_cases=cases,
                imports_hint=imports_hint,
            )
            return code
        except Exception:
            logger.warning("AI generation failed for %s, falling back to template", module_path, exc_info=True)
            return self._generate_with_template(module_path, Path(module_path).stem, cases)

    def _generate_with_template(self, module_path: str, module_name: str, cases: list) -> str:
        """Fallback: generate scaffold using Jinja2 template."""
        template = self._env.get_template("pytest_unit.py.j2")
        return template.render(
            module_path=module_path,
            module_name=module_name,
            test_cases=cases,
        )

    def _read_source(self, module_path: str) -> str:
        """Read the source code of the target module."""
        if not self._source_root:
            return "# Source code not available"
        source_file = self._source_root / module_path
        if source_file.exists():
            try:
                return source_file.read_text(encoding="utf-8")
            except Exception:
                pass
        return "# Source code not available"

    def _build_imports_hint(self, module_path: str, cases: list) -> str:
        """Build import hint based on the module path."""
        # Convert file path to Python module path
        mod = module_path.replace("/", ".").replace("\\", ".")
        if mod.endswith(".py"):
            mod = mod[:-3]
        functions = list({c.target_function for c in cases})
        return f"from {mod} import {', '.join(functions)}"
