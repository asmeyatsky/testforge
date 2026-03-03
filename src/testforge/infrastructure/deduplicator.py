"""Test deduplication — detects existing tests and filters already-covered functions."""

from __future__ import annotations

import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from testforge.domain.entities import TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer


class TestDeduplicator:
    __test__ = False

    """Removes test cases that already have corresponding tests in existing test files."""

    def __init__(self, test_dir: Path) -> None:
        self._existing_targets = self._scan_existing_tests(test_dir)

    def deduplicate(self, strategy: TestStrategy) -> TestStrategy:
        """Return a new strategy with already-covered test cases removed."""
        logger.info("Deduplicating strategy with %d test cases", strategy.total_test_cases)
        new_suites: list[TestSuite] = []

        for suite in strategy.suites:
            filtered = [
                tc for tc in suite.test_cases
                if not self._is_covered(tc)
            ]
            if filtered:
                new_suites.append(TestSuite(
                    id=suite.id,
                    layer=suite.layer,
                    test_cases=tuple(filtered),
                    created_at=suite.created_at,
                ))

        return TestStrategy(
            id=strategy.id,
            analysis_id=strategy.analysis_id,
            suites=tuple(new_suites),
            created_at=strategy.created_at,
        )

    def _is_covered(self, tc: TestCase) -> bool:
        """Check if a test case's target is already tested."""
        target = tc.target_function.lower().replace(".", "_")
        name = tc.name.lower()

        for existing in self._existing_targets:
            existing_lower = existing.lower()
            if target and target in existing_lower:
                return True
            if name == existing_lower:
                return True

        return False

    @staticmethod
    def _scan_existing_tests(test_dir: Path) -> set[str]:
        """Scan existing test files and return all test function names."""
        targets: set[str] = set()

        if not test_dir.exists():
            return targets

        for test_file in test_dir.rglob("test_*.py"):
            try:
                source = test_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    targets.add(node.name)

        return targets
