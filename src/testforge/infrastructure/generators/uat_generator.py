"""UAT test pack generator — produces markdown acceptance test packs."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class UATGenerator:
    """Generates UAT test packs in markdown format."""

    layer = TestLayer.UAT

    def __init__(
        self,
        template_dir: Path | None = None,
        ai_adapter: object | None = None,
    ) -> None:
        tpl_dir = template_dir or _TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(tpl_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._ai = ai_adapter

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite:
        suite = strategy.suite_for_layer(TestLayer.UAT)
        if not suite or not suite.test_cases:
            return TestSuite(layer=TestLayer.UAT)

        output_dir.mkdir(parents=True, exist_ok=True)

        if self._ai and hasattr(self._ai, "generate_uat_pack"):
            content = self._generate_with_ai(suite)
        else:
            content = self._generate_with_template(suite)

        out_file = output_dir / "uat_testpack.md"
        out_file.write_text(content, encoding="utf-8")

        return suite

    def _generate_with_ai(self, suite: TestSuite) -> str:
        """Use AI to generate a rich UAT pack."""
        from testforge.domain.value_objects import APIEndpoint
        endpoints = []
        for tc in suite.test_cases:
            endpoints.append(APIEndpoint(
                method="GET", path=f"/{tc.target_function}",
                handler_name=tc.target_function, file_path=tc.target_module,
            ))
        try:
            return self._ai.generate_uat_pack(endpoints=endpoints)  # type: ignore[union-attr]
        except Exception:
            logger.warning("AI UAT generation failed, using template", exc_info=True)
            return self._generate_with_template(suite)

    def _generate_with_template(self, suite: TestSuite) -> str:
        """Generate UAT pack using Jinja2 template."""
        template = self._env.get_template("uat_testpack.md.j2")
        return template.render(
            test_cases=suite.test_cases,
            layer="uat",
        )
