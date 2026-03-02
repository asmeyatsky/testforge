"""Tests for test deduplicator."""

from pathlib import Path

from testforge.domain.entities import TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.deduplicator import TestDeduplicator


def _strategy() -> TestStrategy:
    return TestStrategy(
        suites=(
            TestSuite(
                layer=TestLayer.UNIT,
                test_cases=(
                    TestCase(name="test_format_name", target_function="format_name", target_module="utils.py"),
                    TestCase(name="test_parse_data", target_function="parse_data", target_module="utils.py"),
                    TestCase(name="test_new_func", target_function="new_func", target_module="utils.py"),
                ),
            ),
        ),
    )


class TestDedup:
    def test_removes_covered_tests(self, tmp_path: Path):
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_utils.py").write_text(
            "def test_format_name(): pass\ndef test_parse_data(): pass\n"
        )
        dedup = TestDeduplicator(test_dir)
        result = dedup.deduplicate(_strategy())
        suite = result.suite_for_layer(TestLayer.UNIT)
        assert suite is not None
        names = [tc.name for tc in suite.test_cases]
        assert "test_new_func" in names
        assert "test_format_name" not in names
        assert "test_parse_data" not in names

    def test_keeps_all_when_no_existing_tests(self, tmp_path: Path):
        dedup = TestDeduplicator(tmp_path)  # empty dir
        result = dedup.deduplicate(_strategy())
        suite = result.suite_for_layer(TestLayer.UNIT)
        assert suite is not None
        assert suite.size == 3

    def test_removes_entire_suite_if_all_covered(self, tmp_path: Path):
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_all.py").write_text(
            "def test_format_name(): pass\n"
            "def test_parse_data(): pass\n"
            "def test_new_func(): pass\n"
        )
        dedup = TestDeduplicator(test_dir)
        result = dedup.deduplicate(_strategy())
        assert result.total_test_cases == 0
