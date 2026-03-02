"""Use case command classes."""

from __future__ import annotations

from pathlib import Path

from testforge.domain.entities import CodebaseAnalysis, TestStrategy, TestSuite
from testforge.domain.events import AnalysisCompleted, StrategyGenerated, TestsGenerated
from testforge.domain.ports import (
    AIStrategyPort,
    CodeScannerPort,
    EventBusPort,
    TestGeneratorPort,
)
from testforge.domain.services import TestStrategyService
from testforge.domain.value_objects import TestLayer


class AnalyseCodebaseCommand:
    def __init__(
        self,
        scanner: CodeScannerPort,
        event_bus: EventBusPort | None = None,
    ) -> None:
        self._scanner = scanner
        self._event_bus = event_bus

    def execute(self, root_path: Path) -> CodebaseAnalysis:
        analysis = self._scanner.scan(root_path)
        if self._event_bus:
            self._event_bus.publish(
                AnalysisCompleted(
                    aggregate_id=analysis.id,
                    root_path=str(root_path),
                    module_count=analysis.total_modules,
                    function_count=analysis.total_functions,
                )
            )
        return analysis


class GenerateStrategyCommand:
    def __init__(
        self,
        ai_strategy: AIStrategyPort | None = None,
        event_bus: EventBusPort | None = None,
    ) -> None:
        self._ai_strategy = ai_strategy
        self._strategy_service = TestStrategyService()
        self._event_bus = event_bus

    def execute(
        self,
        analysis: CodebaseAnalysis,
        layers: list[TestLayer] | None = None,
        prd_content: str | None = None,
    ) -> TestStrategy:
        if layers is None:
            layers = [TestLayer.UNIT]

        if self._ai_strategy:
            strategy = self._ai_strategy.generate_strategy(analysis, layers, prd_content)
        else:
            strategy = self._strategy_service.build_strategy(analysis, layers, prd_content)

        if self._event_bus:
            self._event_bus.publish(
                StrategyGenerated(
                    aggregate_id=strategy.id,
                    layers=strategy.layers_covered,
                    total_test_cases=strategy.total_test_cases,
                )
            )
        return strategy


class GenerateTestsCommand:
    def __init__(
        self,
        generators: dict[TestLayer, TestGeneratorPort],
        event_bus: EventBusPort | None = None,
    ) -> None:
        self._generators = generators
        self._event_bus = event_bus

    def execute(
        self,
        strategy: TestStrategy,
        output_dir: Path,
        layers: list[TestLayer] | None = None,
    ) -> list[TestSuite]:
        results: list[TestSuite] = []
        target_layers = layers or [s.layer for s in strategy.suites]

        for layer in target_layers:
            generator = self._generators.get(layer)
            if generator is None:
                continue
            suite = generator.generate(strategy, output_dir)
            results.append(suite)
            if self._event_bus:
                self._event_bus.publish(
                    TestsGenerated(
                        aggregate_id=suite.id,
                        layer=layer,
                        test_count=suite.size,
                        output_dir=str(output_dir),
                    )
                )
        return results


class RunPipelineCommand:
    """Full pipeline: analyse → strategise → generate."""

    def __init__(
        self,
        scanner: CodeScannerPort,
        ai_strategy: AIStrategyPort | None = None,
        generators: dict[TestLayer, TestGeneratorPort] | None = None,
        event_bus: EventBusPort | None = None,
    ) -> None:
        self._analyse = AnalyseCodebaseCommand(scanner, event_bus)
        self._strategise = GenerateStrategyCommand(ai_strategy, event_bus)
        self._generate = GenerateTestsCommand(generators or {}, event_bus)

    def execute(
        self,
        root_path: Path,
        output_dir: Path,
        layers: list[TestLayer] | None = None,
        prd_content: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        analysis = self._analyse.execute(root_path)
        strategy = self._strategise.execute(analysis, layers, prd_content)

        suites: list[TestSuite] = []
        if not dry_run:
            suites = self._generate.execute(strategy, output_dir, layers)

        return {
            "analysis": analysis,
            "strategy": strategy,
            "suites": suites,
            "dry_run": dry_run,
        }
