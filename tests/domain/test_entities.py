"""Tests for domain entities."""

from testforge.domain.entities import (
    CodebaseAnalysis,
    TestCase,
    TestStrategy,
    TestSuite,
)
from testforge.domain.value_objects import (
    DependencyGraph,
    FilePath,
    FunctionSignature,
    ModuleInfo,
    TestLayer,
)


class TestCodebaseAnalysis:
    def test_creation_defaults(self):
        analysis = CodebaseAnalysis()
        assert analysis.total_functions == 0
        assert analysis.total_classes == 0
        assert analysis.total_modules == 0
        assert analysis.languages == ()

    def test_total_functions(self):
        modules = (
            ModuleInfo(
                file_path=FilePath("a.py"),
                functions=(
                    FunctionSignature(name="foo", parameters=()),
                    FunctionSignature(name="bar", parameters=()),
                ),
            ),
            ModuleInfo(
                file_path=FilePath("b.py"),
                functions=(FunctionSignature(name="baz", parameters=()),),
            ),
        )
        analysis = CodebaseAnalysis(modules=modules)
        assert analysis.total_functions == 3
        assert analysis.total_modules == 2

    def test_is_frozen(self):
        analysis = CodebaseAnalysis()
        try:
            analysis.root_path = "new"  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass


class TestTestCase:
    def test_defaults(self):
        tc = TestCase(name="test_foo")
        assert tc.layer == TestLayer.UNIT
        assert tc.priority == 1

    def test_is_frozen(self):
        tc = TestCase()
        try:
            tc.name = "changed"  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass


class TestTestSuite:
    def test_size(self):
        cases = (TestCase(name="a"), TestCase(name="b"))
        suite = TestSuite(test_cases=cases)
        assert suite.size == 2

    def test_empty(self):
        suite = TestSuite()
        assert suite.size == 0


class TestTestStrategy:
    def test_suite_for_layer(self):
        unit_suite = TestSuite(layer=TestLayer.UNIT, test_cases=(TestCase(),))
        strategy = TestStrategy(suites=(unit_suite,))
        assert strategy.suite_for_layer(TestLayer.UNIT) is unit_suite
        assert strategy.suite_for_layer(TestLayer.INTEGRATION) is None

    def test_total_test_cases(self):
        s1 = TestSuite(layer=TestLayer.UNIT, test_cases=(TestCase(), TestCase()))
        s2 = TestSuite(layer=TestLayer.INTEGRATION, test_cases=(TestCase(),))
        strategy = TestStrategy(suites=(s1, s2))
        assert strategy.total_test_cases == 3

    def test_layers_covered(self):
        s1 = TestSuite(layer=TestLayer.UNIT)
        s2 = TestSuite(layer=TestLayer.UAT)
        strategy = TestStrategy(suites=(s1, s2))
        assert strategy.layers_covered == (TestLayer.UNIT, TestLayer.UAT)
