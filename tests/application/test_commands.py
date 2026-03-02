"""Tests for application commands — with mocked ports."""

from pathlib import Path
from unittest.mock import MagicMock

from testforge.application.commands import (
    AnalyseCodebaseCommand,
    GenerateStrategyCommand,
    GenerateTestsCommand,
    RunPipelineCommand,
)
from testforge.domain.entities import CodebaseAnalysis, TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import FilePath, FunctionSignature, ModuleInfo, TestLayer


def _mock_analysis() -> CodebaseAnalysis:
    return CodebaseAnalysis(
        root_path="/test",
        modules=(
            ModuleInfo(
                file_path=FilePath("mod.py"),
                functions=(FunctionSignature(name="func", parameters=()),),
            ),
        ),
    )


class TestAnalyseCodebaseCommand:
    def test_execute_calls_scanner(self):
        scanner = MagicMock()
        analysis = _mock_analysis()
        scanner.scan.return_value = analysis

        cmd = AnalyseCodebaseCommand(scanner)
        result = cmd.execute(Path("/test"))

        scanner.scan.assert_called_once_with(Path("/test"))
        assert result is analysis

    def test_publishes_event(self):
        scanner = MagicMock()
        scanner.scan.return_value = _mock_analysis()
        bus = MagicMock()

        cmd = AnalyseCodebaseCommand(scanner, bus)
        cmd.execute(Path("/test"))

        bus.publish.assert_called_once()


class TestGenerateStrategyCommand:
    def test_without_ai_uses_domain_service(self):
        cmd = GenerateStrategyCommand()
        analysis = _mock_analysis()
        strategy = cmd.execute(analysis, [TestLayer.UNIT])
        assert strategy.total_test_cases >= 1

    def test_with_ai_adapter(self):
        ai = MagicMock()
        expected = TestStrategy(suites=(TestSuite(layer=TestLayer.UNIT, test_cases=(TestCase(),)),))
        ai.generate_strategy.return_value = expected

        cmd = GenerateStrategyCommand(ai)
        result = cmd.execute(_mock_analysis(), [TestLayer.UNIT])
        assert result is expected


class TestGenerateTestsCommand:
    def test_calls_generator_for_layer(self, tmp_path):
        gen = MagicMock()
        gen.generate.return_value = TestSuite(layer=TestLayer.UNIT, test_cases=(TestCase(),))

        cmd = GenerateTestsCommand({TestLayer.UNIT: gen})
        strategy = TestStrategy(suites=(TestSuite(layer=TestLayer.UNIT),))
        results = cmd.execute(strategy, tmp_path, [TestLayer.UNIT])

        gen.generate.assert_called_once()
        assert len(results) == 1

    def test_skips_missing_generator(self, tmp_path):
        cmd = GenerateTestsCommand({})
        strategy = TestStrategy(suites=(TestSuite(layer=TestLayer.UNIT),))
        results = cmd.execute(strategy, tmp_path, [TestLayer.UNIT])
        assert len(results) == 0


class TestRunPipelineCommand:
    def test_dry_run(self, tmp_path):
        scanner = MagicMock()
        scanner.scan.return_value = _mock_analysis()

        cmd = RunPipelineCommand(scanner=scanner)
        result = cmd.execute(
            root_path=Path("/test"),
            output_dir=tmp_path,
            layers=[TestLayer.UNIT],
            dry_run=True,
        )

        assert result["dry_run"] is True
        assert result["suites"] == []
        assert result["analysis"] is not None
        assert result["strategy"] is not None
