"""Tests for domain value objects."""

from pathlib import Path

from testforge.domain.value_objects import (
    APIEndpoint,
    ClassInfo,
    DependencyGraph,
    FilePath,
    FunctionSignature,
    ModuleInfo,
    TestLayer,
)


class TestTestLayer:
    def test_values(self):
        assert TestLayer.UNIT.value == "unit"
        assert TestLayer.INTEGRATION.value == "integration"
        assert TestLayer.UAT.value == "uat"
        assert TestLayer.SOAK.value == "soak"
        assert TestLayer.PERFORMANCE.value == "performance"

    def test_from_string(self):
        assert TestLayer("unit") == TestLayer.UNIT


class TestFilePath:
    def test_creation(self):
        fp = FilePath("src/foo.py")
        assert fp.suffix == ".py"
        assert fp.stem == "foo"

    def test_str(self):
        fp = FilePath("src/foo.py")
        assert str(fp) == "src/foo.py"

    def test_equality(self):
        assert FilePath("a.py") == FilePath("a.py")
        assert FilePath("a.py") != FilePath("b.py")

    def test_frozen(self):
        fp = FilePath("a.py")
        try:
            fp.path = Path("b.py")  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass


class TestFunctionSignature:
    def test_creation(self):
        sig = FunctionSignature(name="foo", parameters=("a", "b"), return_type="int")
        assert sig.name == "foo"
        assert sig.parameters == ("a", "b")
        assert sig.return_type == "int"
        assert sig.is_async is False

    def test_equality(self):
        a = FunctionSignature(name="foo", parameters=("x",))
        b = FunctionSignature(name="foo", parameters=("x",))
        assert a == b


class TestDependencyGraph:
    def test_empty(self):
        g = DependencyGraph()
        assert g.modules == frozenset()

    def test_modules(self):
        g = DependencyGraph(edges=(("a", "b"), ("b", "c")))
        assert g.modules == frozenset({"a", "b", "c"})

    def test_dependents_of(self):
        g = DependencyGraph(edges=(("a", "b"), ("c", "b")))
        assert g.dependents_of("b") == frozenset({"a", "c"})

    def test_dependencies_of(self):
        g = DependencyGraph(edges=(("a", "b"), ("a", "c")))
        assert g.dependencies_of("a") == frozenset({"b", "c"})


class TestAPIEndpoint:
    def test_creation(self):
        ep = APIEndpoint(method="GET", path="/users", handler_name="get_users", file_path="app.py")
        assert ep.method == "GET"
        assert ep.path == "/users"
