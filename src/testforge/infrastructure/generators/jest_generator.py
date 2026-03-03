"""Jest/Vitest test generator for TypeScript codebases."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class JestGenerator:
    """Generates Jest/Vitest test files for TypeScript modules."""

    layer = TestLayer.UNIT

    def __init__(
        self,
        template_dir: Path | None = None,
        ai_adapter: object | None = None,
        source_root: Path | None = None,
        framework: str = "jest",  # "jest" or "vitest"
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
        self._framework = framework

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite:
        suite = strategy.suite_for_layer(TestLayer.UNIT)
        if not suite:
            return TestSuite(layer=TestLayer.UNIT)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Filter for TypeScript targets and group by module
        ts_cases = [
            tc for tc in suite.test_cases
            if tc.target_module.endswith((".ts", ".tsx", ".js", ".jsx"))
        ]

        if not ts_cases:
            return TestSuite(layer=TestLayer.UNIT)

        by_module: dict[str, list] = {}
        for tc in ts_cases:
            by_module.setdefault(tc.target_module, []).append(tc)

        for module_path, cases in by_module.items():
            module_name = Path(module_path).stem
            ext = ".test.ts" if module_path.endswith((".ts", ".tsx")) else ".test.js"
            out_file = output_dir / f"{module_name}{ext}"

            if self._ai and hasattr(self._ai, "generate_test_code"):
                content = self._generate_with_ai(module_path, cases)
            else:
                content = self._generate_with_template(module_path, module_name, cases)

            out_file.write_text(content, encoding="utf-8")

        return TestSuite(layer=TestLayer.UNIT, test_cases=tuple(ts_cases))

    def _generate_with_ai(self, module_path: str, cases: list) -> str:
        """Use AI to generate real Jest/Vitest test implementations."""
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
        """Generate test scaffold using Jinja2 template."""
        template = self._env.get_template("jest_unit.ts.j2")
        return template.render(
            module_path=module_path,
            module_name=module_name,
            test_cases=cases,
            framework=self._framework,
        )

    def _read_source(self, module_path: str) -> str:
        if not self._source_root:
            return "// Source code not available"
        source_file = self._source_root / module_path
        if source_file.exists():
            try:
                return source_file.read_text(encoding="utf-8")
            except Exception:
                pass
        return "// Source code not available"

    def _build_imports_hint(self, module_path: str, cases: list) -> str:
        mod = module_path.replace("\\", "/")
        if mod.endswith((".ts", ".tsx", ".js", ".jsx")):
            mod = "./" + mod.rsplit(".", 1)[0]
        functions = list({c.target_function for c in cases})
        return f"import {{ {', '.join(functions)} }} from '{mod}';"
