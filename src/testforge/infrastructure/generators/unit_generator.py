"""Unit test generator — fully working with Jinja2 templates."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class UnitTestGenerator:
    """Generates pytest unit test files from TestCase objects."""

    layer = TestLayer.UNIT

    def __init__(self, template_dir: Path | None = None) -> None:
        tpl_dir = template_dir or _TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(tpl_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite:
        suite = strategy.suite_for_layer(TestLayer.UNIT)
        if not suite:
            return TestSuite(layer=TestLayer.UNIT)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Group test cases by target module
        by_module: dict[str, list] = {}
        for tc in suite.test_cases:
            by_module.setdefault(tc.target_module, []).append(tc)

        template = self._env.get_template("pytest_unit.py.j2")

        for module_path, cases in by_module.items():
            module_name = Path(module_path).stem
            content = template.render(
                module_path=module_path,
                module_name=module_name,
                test_cases=cases,
            )
            out_file = output_dir / f"test_{module_name}.py"
            out_file.write_text(content, encoding="utf-8")

        return suite
