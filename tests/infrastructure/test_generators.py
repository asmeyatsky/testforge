"""Tests for test generators."""

from pathlib import Path

import pytest

from testforge.domain.entities import TestCase, TestStrategy, TestSuite
from testforge.domain.errors import UnsupportedLanguageError
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.generators.integration_generator import IntegrationTestGenerator
from testforge.infrastructure.generators.performance_generator import PerformanceGenerator
from testforge.infrastructure.generators.soak_generator import SoakGenerator
from testforge.infrastructure.generators.uat_generator import UATGenerator
from testforge.infrastructure.generators.unit_generator import UnitTestGenerator
from testforge.infrastructure.scanners.typescript_scanner import TypeScriptScanner


def _strategy_with_unit_tests() -> TestStrategy:
    return TestStrategy(
        suites=(
            TestSuite(
                layer=TestLayer.UNIT,
                test_cases=(
                    TestCase(name="test_foo", description="Test foo", layer=TestLayer.UNIT,
                             target_function="foo", target_module="mymod.py", priority=1),
                    TestCase(name="test_bar", description="Test bar", layer=TestLayer.UNIT,
                             target_function="bar", target_module="mymod.py", priority=2),
                    TestCase(name="test_baz", description="Test baz", layer=TestLayer.UNIT,
                             target_function="baz", target_module="other.py", priority=1),
                ),
            ),
        ),
    )


class TestUnitTestGenerator:
    def test_generates_files(self, tmp_path: Path):
        gen = UnitTestGenerator()
        strategy = _strategy_with_unit_tests()
        suite = gen.generate(strategy, tmp_path)

        assert suite.size == 3
        assert (tmp_path / "test_mymod.py").exists()
        assert (tmp_path / "test_other.py").exists()

        content = (tmp_path / "test_mymod.py").read_text()
        assert "test_foo" in content
        assert "test_bar" in content

    def test_empty_strategy(self, tmp_path: Path):
        gen = UnitTestGenerator()
        strategy = TestStrategy()
        suite = gen.generate(strategy, tmp_path)
        assert suite.size == 0

    def test_creates_output_dir(self, tmp_path: Path):
        out = tmp_path / "new" / "dir"
        gen = UnitTestGenerator()
        gen.generate(_strategy_with_unit_tests(), out)
        assert out.is_dir()


class TestIntegrationGenerator:
    def test_generates_placeholder(self, tmp_path: Path):
        gen = IntegrationTestGenerator()
        strategy = TestStrategy(suites=(TestSuite(layer=TestLayer.INTEGRATION),))
        gen.generate(strategy, tmp_path)
        assert (tmp_path / "README_integration.md").exists()


class TestUATGenerator:
    def test_generates_placeholder(self, tmp_path: Path):
        gen = UATGenerator()
        strategy = TestStrategy(suites=(TestSuite(layer=TestLayer.UAT),))
        gen.generate(strategy, tmp_path)
        assert (tmp_path / "README_uat.md").exists()


class TestSoakGenerator:
    def test_generates_placeholder(self, tmp_path: Path):
        gen = SoakGenerator()
        strategy = TestStrategy(suites=(TestSuite(layer=TestLayer.SOAK),))
        gen.generate(strategy, tmp_path)
        assert (tmp_path / "README_soak.md").exists()


class TestPerformanceGenerator:
    def test_generates_placeholder(self, tmp_path: Path):
        gen = PerformanceGenerator()
        strategy = TestStrategy(suites=(TestSuite(layer=TestLayer.PERFORMANCE),))
        gen.generate(strategy, tmp_path)
        assert (tmp_path / "README_performance.md").exists()


class TestTypeScriptScanner:
    def test_raises_unsupported(self, tmp_path: Path):
        scanner = TypeScriptScanner()
        with pytest.raises(UnsupportedLanguageError, match="typescript"):
            scanner.scan(tmp_path)
