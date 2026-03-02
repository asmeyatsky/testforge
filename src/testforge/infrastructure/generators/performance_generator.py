"""Performance test generator — stub for Phase 4."""

from __future__ import annotations

from pathlib import Path

from testforge.domain.entities import TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer


class PerformanceGenerator:
    layer = TestLayer.PERFORMANCE

    def generate(self, strategy: TestStrategy, output_dir: Path) -> TestSuite:
        output_dir.mkdir(parents=True, exist_ok=True)
        placeholder = output_dir / "README_performance.md"
        placeholder.write_text(
            "# Performance Tests\n\nPerformance test generation will be available in Phase 4.\n",
            encoding="utf-8",
        )
        suite = strategy.suite_for_layer(TestLayer.PERFORMANCE)
        return suite or TestSuite(layer=TestLayer.PERFORMANCE)
