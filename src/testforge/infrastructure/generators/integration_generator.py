"""Integration test generator — stub for Phase 2."""

from __future__ import annotations

from pathlib import Path

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer


class IntegrationTestGenerator:
    layer = TestLayer.INTEGRATION

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite:
        output_dir.mkdir(parents=True, exist_ok=True)
        placeholder = output_dir / "README_integration.md"
        placeholder.write_text(
            "# Integration Tests\n\nIntegration test generation will be available in Phase 2.\n",
            encoding="utf-8",
        )
        suite = strategy.suite_for_layer(TestLayer.INTEGRATION)
        return suite or TestSuite(layer=TestLayer.INTEGRATION)
