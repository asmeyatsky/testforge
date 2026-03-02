"""Domain services — pure business logic."""

from __future__ import annotations

from testforge.domain.entities import CodebaseAnalysis, TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer


class TestStrategyService:
    """Maps analysis findings to test cases per layer using pure domain logic."""

    def build_strategy(
        self,
        analysis: CodebaseAnalysis,
        layers: list[TestLayer] | None = None,
    ) -> TestStrategy:
        if layers is None:
            layers = [TestLayer.UNIT]

        suites: list[TestSuite] = []
        for layer in layers:
            cases = self._generate_cases_for_layer(analysis, layer)
            if cases:
                suites.append(TestSuite(layer=layer, test_cases=tuple(cases)))

        return TestStrategy(
            analysis_id=analysis.id,
            suites=tuple(suites),
        )

    def _generate_cases_for_layer(
        self,
        analysis: CodebaseAnalysis,
        layer: TestLayer,
    ) -> list[TestCase]:
        if layer == TestLayer.UNIT:
            return self._unit_cases(analysis)
        if layer == TestLayer.INTEGRATION:
            return self._integration_cases(analysis)
        if layer == TestLayer.UAT:
            return self._uat_cases(analysis)
        return []

    def _unit_cases(self, analysis: CodebaseAnalysis) -> list[TestCase]:
        cases: list[TestCase] = []
        for module in analysis.modules:
            for func in module.functions:
                cases.append(
                    TestCase(
                        name=f"test_{func.name}",
                        description=f"Unit test for {func.name}",
                        layer=TestLayer.UNIT,
                        target_function=func.name,
                        target_module=str(module.file_path),
                        priority=self._function_priority(func.name, func.decorators),
                    )
                )
            for cls in module.classes:
                for method in cls.methods:
                    if method.name.startswith("_") and method.name != "__init__":
                        continue
                    cases.append(
                        TestCase(
                            name=f"test_{cls.name}_{method.name}",
                            description=f"Unit test for {cls.name}.{method.name}",
                            layer=TestLayer.UNIT,
                            target_function=f"{cls.name}.{method.name}",
                            target_module=str(module.file_path),
                            priority=self._function_priority(
                                method.name, method.decorators
                            ),
                        )
                    )
        return cases

    def _integration_cases(self, analysis: CodebaseAnalysis) -> list[TestCase]:
        cases: list[TestCase] = []
        for endpoint in analysis.endpoints:
            cases.append(
                TestCase(
                    name=f"test_{endpoint.method.lower()}_{endpoint.handler_name}",
                    description=f"Integration test for {endpoint.method} {endpoint.path}",
                    layer=TestLayer.INTEGRATION,
                    target_function=endpoint.handler_name,
                    target_module=endpoint.file_path,
                    priority=1,
                    tags=("api", endpoint.method.lower()),
                )
            )
        return cases

    def _uat_cases(self, analysis: CodebaseAnalysis) -> list[TestCase]:
        cases: list[TestCase] = []
        for endpoint in analysis.endpoints:
            cases.append(
                TestCase(
                    name=f"uat_{endpoint.handler_name}",
                    description=f"UAT scenario for {endpoint.method} {endpoint.path}",
                    layer=TestLayer.UAT,
                    target_function=endpoint.handler_name,
                    target_module=endpoint.file_path,
                    priority=1,
                )
            )
        return cases

    @staticmethod
    def _function_priority(name: str, decorators: tuple[str, ...]) -> int:
        # Public API / route handlers get highest priority
        route_decorators = {"app.route", "app.get", "app.post", "router.get", "router.post"}
        if any(d in route_decorators for d in decorators):
            return 1
        if name.startswith("_"):
            return 3
        return 2


class TestPrioritizationService:
    """Re-orders test cases by risk-based priority."""

    def prioritize(self, cases: list[TestCase]) -> list[TestCase]:
        return sorted(cases, key=lambda c: c.priority)
