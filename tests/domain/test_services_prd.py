"""Tests for PRD-aware strategy generation."""

from testforge.domain.entities import CodebaseAnalysis
from testforge.domain.services import TestStrategyService
from testforge.domain.value_objects import (
    FilePath,
    FunctionSignature,
    ModuleInfo,
    TestLayer,
)


def _analysis_with_functions() -> CodebaseAnalysis:
    return CodebaseAnalysis(
        modules=(
            ModuleInfo(
                file_path=FilePath("auth.py"),
                functions=(
                    FunctionSignature(name="login", parameters=("username", "password")),
                    FunctionSignature(name="logout", parameters=()),
                    FunctionSignature(name="validate_token", parameters=("token",)),
                ),
            ),
            ModuleInfo(
                file_path=FilePath("billing.py"),
                functions=(
                    FunctionSignature(name="process_payment", parameters=("amount",)),
                    FunctionSignature(name="generate_invoice", parameters=("order_id",)),
                ),
            ),
        ),
    )


class TestPRDAwareStrategy:
    def test_prd_boosts_matching_functions(self):
        svc = TestStrategyService()
        prd = "The authentication system must support secure login and logout. Token validation is critical."
        strategy = svc.build_strategy(_analysis_with_functions(), [TestLayer.UNIT], prd_content=prd)

        suite = strategy.suite_for_layer(TestLayer.UNIT)
        assert suite is not None
        cases_by_name = {c.name: c for c in suite.test_cases}

        # login/logout/validate_token should be boosted (priority 2 → 1)
        assert cases_by_name["test_login"].priority == 1
        assert cases_by_name["test_logout"].priority == 1
        assert cases_by_name["test_validate_token"].priority == 1

    def test_no_prd_preserves_default_priority(self):
        svc = TestStrategyService()
        strategy = svc.build_strategy(_analysis_with_functions(), [TestLayer.UNIT])

        suite = strategy.suite_for_layer(TestLayer.UNIT)
        assert suite is not None
        cases_by_name = {c.name: c for c in suite.test_cases}
        # Default priority for non-route functions is 2
        assert cases_by_name["test_login"].priority == 2

    def test_prd_keyword_extraction(self):
        svc = TestStrategyService()
        keywords = svc._extract_prd_keywords("The user must login and process payment securely.")
        assert "login" in keywords
        assert "process" in keywords
        assert "payment" in keywords
        assert "the" not in keywords  # stopword filtered
