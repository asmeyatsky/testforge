"""Tests for test generators."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from testforge.domain.entities import TestCase, TestStrategy, TestSuite
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


def _strategy_with_integration_tests() -> TestStrategy:
    return TestStrategy(
        suites=(
            TestSuite(
                layer=TestLayer.INTEGRATION,
                test_cases=(
                    TestCase(name="test_get_users", description="Test GET /users",
                             layer=TestLayer.INTEGRATION, target_function="get_users",
                             target_module="app.py", priority=1, tags=("api", "get")),
                ),
            ),
        ),
    )


def _strategy_with_uat_tests() -> TestStrategy:
    return TestStrategy(
        suites=(
            TestSuite(
                layer=TestLayer.UAT,
                test_cases=(
                    TestCase(name="uat_login", description="UAT for login flow",
                             layer=TestLayer.UAT, target_function="login",
                             target_module="auth.py", priority=1),
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

    def test_ai_generation_fallback(self, tmp_path: Path):
        """When AI adapter fails, falls back to template."""
        ai = MagicMock()
        ai.generate_test_code.side_effect = RuntimeError("API error")
        gen = UnitTestGenerator(ai_adapter=ai)
        suite = gen.generate(_strategy_with_unit_tests(), tmp_path)
        assert suite.size == 3
        assert (tmp_path / "test_mymod.py").exists()

    def test_ai_generation_success(self, tmp_path: Path):
        """When AI adapter succeeds, uses AI-generated code."""
        ai = MagicMock()
        ai.generate_test_code.return_value = "# AI generated\ndef test_foo(): pass\n"
        gen = UnitTestGenerator(ai_adapter=ai, source_root=tmp_path)
        suite = gen.generate(_strategy_with_unit_tests(), tmp_path)
        assert suite.size == 3
        content = (tmp_path / "test_mymod.py").read_text()
        assert "AI generated" in content


class TestIntegrationGenerator:
    def test_generates_integration_file(self, tmp_path: Path):
        gen = IntegrationTestGenerator()
        suite = gen.generate(_strategy_with_integration_tests(), tmp_path)
        assert suite.size == 1
        assert (tmp_path / "test_integration_app.py").exists()

    def test_empty_strategy(self, tmp_path: Path):
        gen = IntegrationTestGenerator()
        strategy = TestStrategy()
        suite = gen.generate(strategy, tmp_path)
        assert suite.size == 0


class TestUATGenerator:
    def test_generates_uat_file(self, tmp_path: Path):
        gen = UATGenerator()
        suite = gen.generate(_strategy_with_uat_tests(), tmp_path)
        assert suite.size == 1
        assert (tmp_path / "uat_testpack.md").exists()
        content = (tmp_path / "uat_testpack.md").read_text()
        assert "uat_login" in content

    def test_empty_strategy(self, tmp_path: Path):
        gen = UATGenerator()
        strategy = TestStrategy()
        suite = gen.generate(strategy, tmp_path)
        assert suite.size == 0


class TestSoakGenerator:
    def test_generates_k6_script(self, tmp_path: Path):
        strategy = TestStrategy(
            suites=(
                TestSuite(layer=TestLayer.INTEGRATION, test_cases=(
                    TestCase(name="test_get_users", target_function="get_users",
                             target_module="app.py", layer=TestLayer.INTEGRATION, tags=("api", "get")),
                )),
            ),
        )
        gen = SoakGenerator()
        gen.generate(strategy, tmp_path)
        assert (tmp_path / "soak_test.js").exists()
        content = (tmp_path / "soak_test.js").read_text()
        assert "k6/http" in content
        assert "get_users" in content

    def test_empty_returns_empty_suite(self, tmp_path: Path):
        gen = SoakGenerator()
        suite = gen.generate(TestStrategy(), tmp_path)
        assert suite.size == 0


class TestPerformanceGenerator:
    def test_generates_k6_script(self, tmp_path: Path):
        strategy = TestStrategy(
            suites=(
                TestSuite(layer=TestLayer.INTEGRATION, test_cases=(
                    TestCase(name="test_get_users", target_function="get_users",
                             target_module="app.py", layer=TestLayer.INTEGRATION, tags=("api", "get")),
                )),
            ),
        )
        gen = PerformanceGenerator()
        gen.generate(strategy, tmp_path)
        assert (tmp_path / "performance_test.js").exists()
        content = (tmp_path / "performance_test.js").read_text()
        assert "k6/http" in content
        assert "p(95)" in content

    def test_empty_returns_empty_suite(self, tmp_path: Path):
        gen = PerformanceGenerator()
        suite = gen.generate(TestStrategy(), tmp_path)
        assert suite.size == 0


class TestTypeScriptScanner:
    def test_scan_empty_dir(self, tmp_path: Path):
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        assert analysis.total_modules == 0

    def test_scan_ts_file(self, tmp_path: Path):
        (tmp_path / "app.ts").write_text(
            'import express from "express";\n'
            "export function greet(name: string): string {\n"
            "  return `Hello ${name}`;\n"
            "}\n"
            'const add = (a: number, b: number): number => a + b;\n'
        )
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        assert analysis.total_modules == 1
        assert analysis.total_functions >= 2

    def test_scan_extracts_classes(self, tmp_path: Path):
        (tmp_path / "service.ts").write_text(
            "export class UserService extends BaseService {\n"
            "  async getUser(id: string): Promise<User> {\n"
            "    return this.db.find(id);\n"
            "  }\n"
            "  deleteUser(id: string): void {\n"
            "    this.db.remove(id);\n"
            "  }\n"
            "}\n"
        )
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        classes = analysis.modules[0].classes
        assert len(classes) == 1
        assert classes[0].name == "UserService"
        assert classes[0].bases == ("BaseService",)
        assert len(classes[0].methods) >= 2

    def test_scan_extracts_routes(self, tmp_path: Path):
        (tmp_path / "routes.ts").write_text(
            'app.get("/users", getUsers);\n'
            'app.post("/users", createUser);\n'
        )
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        assert len(analysis.endpoints) == 2
