"""Query objects for read-side operations."""

from __future__ import annotations

from testforge.domain.entities import CodebaseAnalysis, TestStrategy
from testforge.application.dtos import (
    AnalysisDTO,
    ModuleDTO,
    StrategyDTO,
    TestCaseDTO,
    TestSuiteDTO,
)


class GetAnalysis:
    """Converts a CodebaseAnalysis entity to a DTO."""

    def execute(self, analysis: CodebaseAnalysis) -> AnalysisDTO:
        modules = [
            ModuleDTO(
                file_path=str(m.file_path),
                function_count=len(m.functions),
                class_count=len(m.classes),
                endpoint_count=len(m.endpoints),
            )
            for m in analysis.modules
        ]
        return AnalysisDTO(
            id=analysis.id,
            root_path=analysis.root_path,
            modules=modules,
            languages=list(analysis.languages),
            total_functions=analysis.total_functions,
            total_classes=analysis.total_classes,
            total_modules=analysis.total_modules,
        )


class GetStrategy:
    """Converts a TestStrategy entity to a DTO."""

    def execute(self, strategy: TestStrategy) -> StrategyDTO:
        suites = [
            TestSuiteDTO(
                layer=s.layer.value,
                test_cases=[
                    TestCaseDTO(
                        name=tc.name,
                        description=tc.description,
                        layer=tc.layer.value,
                        target_function=tc.target_function,
                        target_module=tc.target_module,
                        priority=tc.priority,
                    )
                    for tc in s.test_cases
                ],
                size=s.size,
            )
            for s in strategy.suites
        ]
        return StrategyDTO(
            id=strategy.id,
            analysis_id=strategy.analysis_id,
            suites=suites,
            total_test_cases=strategy.total_test_cases,
            layers_covered=[l.value for l in strategy.layers_covered],
        )
