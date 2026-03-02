"""Tests for DTOs and query objects."""

from testforge.application.dtos import (
    AnalysisDTO,
    ModuleDTO,
    StrategyDTO,
    TestCaseDTO,
    TestSuiteDTO,
)
from testforge.application.queries import GetAnalysis, GetStrategy
from testforge.domain.entities import (
    CodebaseAnalysis,
    TestCase,
    TestStrategy,
    TestSuite,
)
from testforge.domain.value_objects import (
    APIEndpoint,
    FilePath,
    FunctionSignature,
    ModuleInfo,
    TestLayer,
)


def _sample_analysis() -> CodebaseAnalysis:
    return CodebaseAnalysis(
        id="a1",
        root_path="/proj",
        modules=(
            ModuleInfo(
                file_path=FilePath("mod.py"),
                functions=(FunctionSignature(name="f", parameters=("x",)),),
                classes=(),
                endpoints=(
                    APIEndpoint(method="GET", path="/x", handler_name="f", file_path="mod.py"),
                ),
            ),
        ),
        languages=("python",),
    )


def _sample_strategy() -> TestStrategy:
    return TestStrategy(
        id="s1",
        analysis_id="a1",
        suites=(
            TestSuite(
                layer=TestLayer.UNIT,
                test_cases=(
                    TestCase(name="test_f", description="test f", layer=TestLayer.UNIT,
                             target_function="f", target_module="mod.py", priority=1,),
                ),
            ),
            TestSuite(
                layer=TestLayer.INTEGRATION,
                test_cases=(
                    TestCase(name="test_api", description="api test", layer=TestLayer.INTEGRATION,
                             target_function="f", target_module="mod.py", priority=2),
                ),
            ),
        ),
    )


class TestModuleDTO:
    def test_creation(self):
        dto = ModuleDTO(file_path="a.py", function_count=2, class_count=1, endpoint_count=0)
        assert dto.file_path == "a.py"
        assert dto.function_count == 2


class TestAnalysisDTO:
    def test_creation(self):
        dto = AnalysisDTO(
            id="a1", root_path="/p", modules=[], languages=["python"],
            total_functions=5, total_classes=2, total_modules=3,
        )
        assert dto.total_functions == 5


class TestTestCaseDTO:
    def test_creation(self):
        dto = TestCaseDTO(
            name="test_x", description="desc", layer="unit",
            target_function="x", target_module="m.py", priority=1,
        )
        assert dto.name == "test_x"


class TestTestSuiteDTO:
    def test_creation(self):
        dto = TestSuiteDTO(layer="unit", test_cases=[], size=0)
        assert dto.size == 0


class TestStrategyDTO:
    def test_creation(self):
        dto = StrategyDTO(
            id="s1", analysis_id="a1", suites=[], total_test_cases=0, layers_covered=[],
        )
        assert dto.total_test_cases == 0


class TestGetAnalysis:
    def test_converts_analysis_to_dto(self):
        query = GetAnalysis()
        dto = query.execute(_sample_analysis())
        assert dto.id == "a1"
        assert dto.root_path == "/proj"
        assert dto.total_modules == 1
        assert dto.total_functions == 1
        assert dto.total_classes == 0
        assert dto.languages == ["python"]
        assert len(dto.modules) == 1
        assert dto.modules[0].file_path == "mod.py"
        assert dto.modules[0].function_count == 1
        assert dto.modules[0].endpoint_count == 1


class TestGetStrategy:
    def test_converts_strategy_to_dto(self):
        query = GetStrategy()
        dto = query.execute(_sample_strategy())
        assert dto.id == "s1"
        assert dto.analysis_id == "a1"
        assert dto.total_test_cases == 2
        assert dto.layers_covered == ["unit", "integration"]
        assert len(dto.suites) == 2
        assert dto.suites[0].layer == "unit"
        assert dto.suites[0].size == 1
        assert dto.suites[0].test_cases[0].name == "test_f"
