"""Soak test generator — produces k6 soak test scripts from API endpoints."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class SoakGenerator:
    """Generates k6 soak test scripts from API endpoints in the strategy."""

    layer = TestLayer.SOAK

    def __init__(self, template_dir: Path | None = None) -> None:
        tpl_dir = template_dir or _TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(tpl_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite:
        suite = strategy.suite_for_layer(TestLayer.SOAK)
        if not suite or not suite.test_cases:
            # Fall back: build soak targets from any endpoints in integration/uat suites
            endpoints = self._collect_endpoints(strategy)
            if not endpoints:
                return TestSuite(layer=TestLayer.SOAK)
        else:
            endpoints = [
                {"method": "GET", "path": f"/{tc.target_function}", "name": tc.target_function}
                for tc in suite.test_cases
            ]

        output_dir.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("k6_soak.js.j2")
        content = template.render(endpoints=endpoints)
        out_file = output_dir / "soak_test.js"
        out_file.write_text(content, encoding="utf-8")

        return suite or TestSuite(layer=TestLayer.SOAK)

    def _collect_endpoints(self, strategy: TestStrategy) -> list[dict]:
        """Gather endpoint info from integration/uat suites."""
        endpoints: list[dict] = []
        for layer in (TestLayer.INTEGRATION, TestLayer.UAT):
            s = strategy.suite_for_layer(layer)
            if s:
                for tc in s.test_cases:
                    method = "GET"
                    for tag in tc.tags:
                        if tag.upper() in ("POST", "PUT", "DELETE", "PATCH"):
                            method = tag.upper()
                    endpoints.append({
                        "method": method,
                        "path": f"/{tc.target_function}",
                        "name": tc.target_function,
                    })
        return endpoints
