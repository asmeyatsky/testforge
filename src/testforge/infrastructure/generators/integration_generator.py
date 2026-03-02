"""Integration test generator — produces FastAPI/Flask test client tests."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class IntegrationTestGenerator:
    """Generates integration test files from API endpoint test cases."""

    layer = TestLayer.INTEGRATION

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
        suite = strategy.suite_for_layer(TestLayer.INTEGRATION)
        if not suite or not suite.test_cases:
            return TestSuite(layer=TestLayer.INTEGRATION)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Group by target module
        by_module: dict[str, list] = {}
        for tc in suite.test_cases:
            by_module.setdefault(tc.target_module, []).append(tc)

        for module_path, cases in by_module.items():
            module_name = Path(module_path).stem
            framework = self._detect_framework(module_path)

            if self._ai and hasattr(self._ai, "generate_integration_tests"):
                content = self._generate_with_ai(framework, cases, module_path)
            else:
                content = self._generate_with_template(framework, module_path, module_name, cases)

            out_file = output_dir / f"test_integration_{module_name}.py"
            out_file.write_text(content, encoding="utf-8")

        return suite

    def _detect_framework(self, module_path: str) -> str:
        """Try to detect web framework from source code."""
        if not self._source_root:
            return "flask"
        source_file = self._source_root / module_path
        if source_file.exists():
            try:
                content = source_file.read_text(encoding="utf-8")
                if "fastapi" in content.lower() or "FastAPI" in content:
                    return "fastapi"
                if "django" in content.lower():
                    return "django"
            except Exception:
                pass
        return "flask"

    def _generate_with_ai(self, framework: str, cases: list, module_path: str) -> str:
        """Use AI to generate integration tests."""
        source_code = self._read_source(module_path)
        from testforge.domain.value_objects import APIEndpoint
        endpoints = []
        for tc in cases:
            # Reconstruct endpoint info from test case tags
            method = "GET"
            for tag in tc.tags:
                if tag.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    method = tag.upper()
            endpoints.append(APIEndpoint(
                method=method, path=f"/{tc.target_function}",
                handler_name=tc.target_function, file_path=tc.target_module,
            ))
        try:
            return self._ai.generate_integration_tests(  # type: ignore[union-attr]
                framework=framework, endpoints=endpoints, source_code=source_code,
            )
        except Exception:
            logger.warning("AI integration gen failed for %s, using template", module_path, exc_info=True)
            return self._generate_with_template(framework, module_path, Path(module_path).stem, cases)

    def _generate_with_template(self, framework: str, module_path: str, module_name: str, cases: list) -> str:
        template = self._env.get_template("pytest_integration.py.j2")
        return template.render(
            module_path=module_path,
            module_name=module_name,
            framework=framework,
            test_cases=cases,
        )

    def _read_source(self, module_path: str) -> str:
        if not self._source_root:
            return "# Source not available"
        source_file = self._source_root / module_path
        if source_file.exists():
            try:
                return source_file.read_text(encoding="utf-8")
            except Exception:
                pass
        return "# Source not available"
