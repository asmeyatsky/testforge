"""UAT test pack generator — stub for Phase 3."""

from __future__ import annotations

from pathlib import Path

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer


class UATGenerator:
    layer = TestLayer.UAT

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite:
        output_dir.mkdir(parents=True, exist_ok=True)
        placeholder = output_dir / "README_uat.md"
        placeholder.write_text(
            "# UAT Test Packs\n\nUAT test pack generation will be available in Phase 3.\n",
            encoding="utf-8",
        )
        suite = strategy.suite_for_layer(TestLayer.UAT)
        return suite or TestSuite(layer=TestLayer.UAT)
