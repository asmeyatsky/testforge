"""Tests for Jest/Vitest generator."""

from pathlib import Path
from unittest.mock import MagicMock

from testforge.domain.entities import TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.generators.jest_generator import JestGenerator


def _ts_strategy() -> TestStrategy:
    return TestStrategy(
        suites=(
            TestSuite(
                layer=TestLayer.UNIT,
                test_cases=(
                    TestCase(
                        name="test_greet",
                        description="Test greet function",
                        layer=TestLayer.UNIT,
                        target_function="greet",
                        target_module="app.ts",
                        priority=1,
                    ),
                    TestCase(
                        name="test_add",
                        description="Test add function",
                        layer=TestLayer.UNIT,
                        target_function="add",
                        target_module="utils.ts",
                        priority=2,
                    ),
                ),
            ),
        ),
    )


class TestJestGenerator:
    def test_generates_test_files(self, tmp_path: Path):
        gen = JestGenerator()
        suite = gen.generate(_ts_strategy(), tmp_path)
        assert suite.size == 2
        assert (tmp_path / "app.test.ts").exists()
        assert (tmp_path / "utils.test.ts").exists()

    def test_file_content(self, tmp_path: Path):
        gen = JestGenerator()
        gen.generate(_ts_strategy(), tmp_path)
        content = (tmp_path / "app.test.ts").read_text()
        assert "greet" in content
        assert "describe" in content
        assert "expect" in content

    def test_empty_strategy(self, tmp_path: Path):
        gen = JestGenerator()
        suite = gen.generate(TestStrategy(), tmp_path)
        assert suite.size == 0

    def test_skips_python_targets(self, tmp_path: Path):
        strategy = TestStrategy(
            suites=(
                TestSuite(layer=TestLayer.UNIT, test_cases=(
                    TestCase(name="test_py", target_function="foo", target_module="app.py"),
                )),
            ),
        )
        gen = JestGenerator()
        suite = gen.generate(strategy, tmp_path)
        assert suite.size == 0

    def test_vitest_framework(self, tmp_path: Path):
        gen = JestGenerator(framework="vitest")
        gen.generate(_ts_strategy(), tmp_path)
        content = (tmp_path / "app.test.ts").read_text()
        assert "vitest" in content

    def test_js_files_get_js_extension(self, tmp_path: Path):
        strategy = TestStrategy(
            suites=(
                TestSuite(layer=TestLayer.UNIT, test_cases=(
                    TestCase(name="test_foo", target_function="foo", target_module="app.js"),
                )),
            ),
        )
        gen = JestGenerator()
        gen.generate(strategy, tmp_path)
        assert (tmp_path / "app.test.js").exists()

    def test_ai_generation_fallback(self, tmp_path: Path):
        ai = MagicMock()
        ai.generate_test_code.side_effect = RuntimeError("fail")
        gen = JestGenerator(ai_adapter=ai)
        suite = gen.generate(_ts_strategy(), tmp_path)
        assert suite.size == 2
