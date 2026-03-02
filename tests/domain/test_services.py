"""Tests for domain services — no mocks, pure domain objects."""

from testforge.domain.entities import CodebaseAnalysis, TestCase
from testforge.domain.services import TestPrioritizationService, TestStrategyService
from testforge.domain.value_objects import (
    APIEndpoint,
    FilePath,
    FunctionSignature,
    ModuleInfo,
    TestLayer,
)


def _sample_analysis() -> CodebaseAnalysis:
    return CodebaseAnalysis(
        root_path="/project",
        modules=(
            ModuleInfo(
                file_path=FilePath("app.py"),
                functions=(
                    FunctionSignature(name="get_users", parameters=("db",), decorators=("app.get",)),
                    FunctionSignature(name="_helper", parameters=()),
                ),
            ),
            ModuleInfo(
                file_path=FilePath("utils.py"),
                functions=(
                    FunctionSignature(name="format_name", parameters=("name",)),
                ),
            ),
        ),
        endpoints=(
            APIEndpoint(method="GET", path="/users", handler_name="get_users", file_path="app.py"),
        ),
    )


class TestTestStrategyService:
    def test_build_unit_strategy(self):
        svc = TestStrategyService()
        strategy = svc.build_strategy(_sample_analysis(), [TestLayer.UNIT])
        assert len(strategy.suites) == 1
        suite = strategy.suite_for_layer(TestLayer.UNIT)
        assert suite is not None
        assert suite.size >= 2  # at least get_users and format_name

    def test_build_integration_strategy(self):
        svc = TestStrategyService()
        strategy = svc.build_strategy(_sample_analysis(), [TestLayer.INTEGRATION])
        suite = strategy.suite_for_layer(TestLayer.INTEGRATION)
        assert suite is not None
        assert suite.size == 1  # one endpoint

    def test_build_multi_layer(self):
        svc = TestStrategyService()
        strategy = svc.build_strategy(
            _sample_analysis(), [TestLayer.UNIT, TestLayer.INTEGRATION]
        )
        assert len(strategy.suites) == 2

    def test_route_handlers_get_highest_priority(self):
        svc = TestStrategyService()
        strategy = svc.build_strategy(_sample_analysis(), [TestLayer.UNIT])
        suite = strategy.suite_for_layer(TestLayer.UNIT)
        assert suite is not None
        cases_by_name = {c.name: c for c in suite.test_cases}
        assert cases_by_name["test_get_users"].priority == 1
        assert cases_by_name["test_format_name"].priority == 2

    def test_empty_analysis(self):
        svc = TestStrategyService()
        strategy = svc.build_strategy(CodebaseAnalysis(), [TestLayer.UNIT])
        # No modules means no test cases, so no suites
        assert len(strategy.suites) == 0


class TestTestPrioritizationService:
    def test_prioritize_sorts_by_priority(self):
        svc = TestPrioritizationService()
        cases = [
            TestCase(name="low", priority=3),
            TestCase(name="high", priority=1),
            TestCase(name="med", priority=2),
        ]
        result = svc.prioritize(cases)
        assert [c.name for c in result] == ["high", "med", "low"]
