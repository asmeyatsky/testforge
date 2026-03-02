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
        prd_content: str | None = None,
    ) -> TestStrategy:
        if layers is None:
            layers = [TestLayer.UNIT]

        # Extract keywords from PRD to boost priority of matching functions
        prd_keywords = self._extract_prd_keywords(prd_content) if prd_content else set()

        suites: list[TestSuite] = []
        for layer in layers:
            cases = self._generate_cases_for_layer(analysis, layer)
            if prd_keywords:
                cases = self._boost_prd_matches(cases, prd_keywords)
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
                        external_calls=func.external_calls,
                        fixtures_needed=func.fixtures_needed,
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
                            external_calls=method.external_calls,
                            fixtures_needed=method.fixtures_needed,
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

    @staticmethod
    def _extract_prd_keywords(prd_content: str) -> set[str]:
        """Extract meaningful keywords from PRD for matching against function names."""
        import re
        # Lowercase words, filter short/common ones
        words = re.findall(r"[a-zA-Z_]\w{2,}", prd_content.lower())
        stopwords = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "had", "her", "was", "one", "our", "out", "has", "have", "that",
            "this", "with", "from", "they", "will", "would", "should", "must",
            "shall", "each", "which", "their", "when", "what", "been", "make",
        }
        return {w for w in words if w not in stopwords}

    @staticmethod
    def _boost_prd_matches(cases: list[TestCase], prd_keywords: set[str]) -> list[TestCase]:
        """Boost priority of test cases whose target functions match PRD keywords."""
        import re
        boosted: list[TestCase] = []
        for tc in cases:
            # Split function name into words (e.g., "get_user_profile" -> {"get", "user", "profile"})
            func_words = set(re.findall(r"[a-z]+", tc.target_function.lower()))
            overlap = func_words & prd_keywords
            if overlap and tc.priority > 1:
                # Boost priority by 1 level
                from dataclasses import replace
                boosted.append(replace(tc, priority=max(1, tc.priority - 1)))
            else:
                boosted.append(tc)
        return boosted


class TestPrioritizationService:
    """Re-orders test cases by risk-based priority."""

    def prioritize(self, cases: list[TestCase]) -> list[TestCase]:
        return sorted(cases, key=lambda c: c.priority)
