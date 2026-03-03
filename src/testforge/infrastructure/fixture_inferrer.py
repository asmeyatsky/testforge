"""Fixture and mock inference — analyses function bodies to auto-generate realistic mocks."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MockSpec:
    """Specification for an auto-generated mock."""
    target: str  # e.g. "requests.get"
    mock_name: str  # e.g. "mock_requests_get"
    return_value: str  # e.g. "MagicMock(status_code=200, json=lambda: {})"
    category: str  # "http", "db", "file", "env", "subprocess", "other"


@dataclass(frozen=True)
class FixtureSpec:
    """Specification for an auto-generated pytest fixture."""
    name: str  # e.g. "sample_user"
    code: str  # Fixture body
    scope: str = "function"


@dataclass
class InferredFixtures:
    """All inferred fixtures and mocks for a function."""
    mocks: list[MockSpec] = field(default_factory=list)
    fixtures: list[FixtureSpec] = field(default_factory=list)
    patch_decorators: list[str] = field(default_factory=list)


# Maps external call patterns to realistic mock return values
_MOCK_TEMPLATES: dict[str, tuple[str, str]] = {
    # HTTP clients
    "requests.get": ("MagicMock(status_code=200, json=lambda: {}, text='')", "http"),
    "requests.post": ("MagicMock(status_code=201, json=lambda: {'id': 1}, text='')", "http"),
    "requests.put": ("MagicMock(status_code=200, json=lambda: {}, text='')", "http"),
    "requests.delete": ("MagicMock(status_code=204)", "http"),
    "requests.patch": ("MagicMock(status_code=200, json=lambda: {}, text='')", "http"),
    "httpx.get": ("MagicMock(status_code=200, json=lambda: {}, text='')", "http"),
    "httpx.post": ("MagicMock(status_code=201, json=lambda: {'id': 1})", "http"),
    "aiohttp": ("MagicMock()", "http"),
    # Database
    "sqlite3.connect": ("MagicMock()", "db"),
    "psycopg2.connect": ("MagicMock()", "db"),
    "pymongo.MongoClient": ("MagicMock()", "db"),
    "sqlalchemy.create_engine": ("MagicMock()", "db"),
    "redis.Redis": ("MagicMock()", "db"),
    # File system
    "open": ("MagicMock(read=MagicMock(return_value=''), write=MagicMock())", "file"),
    "os.remove": ("None", "file"),
    "os.makedirs": ("None", "file"),
    "shutil.rmtree": ("None", "file"),
    "shutil.copy": ("None", "file"),
    # Subprocess
    "subprocess.run": ("MagicMock(returncode=0, stdout='', stderr='')", "subprocess"),
    "subprocess.Popen": ("MagicMock(returncode=0, communicate=MagicMock(return_value=('', '')))", "subprocess"),
    # Cloud/External
    "boto3.client": ("MagicMock()", "cloud"),
    "smtplib.SMTP": ("MagicMock()", "email"),
    # Time
    "time.sleep": ("None", "other"),
}

# Parameter type hints that suggest fixture generation
_PARAM_FIXTURE_MAP: dict[str, tuple[str, str]] = {
    "db": ("db_session", "@pytest.fixture\ndef db_session():\n    \"\"\"Mock database session.\"\"\"\n    return MagicMock()"),
    "session": ("db_session", "@pytest.fixture\ndef db_session():\n    \"\"\"Mock database session.\"\"\"\n    return MagicMock()"),
    "conn": ("db_connection", "@pytest.fixture\ndef db_connection():\n    \"\"\"Mock database connection.\"\"\"\n    return MagicMock()"),
    "client": ("http_client", "@pytest.fixture\ndef http_client():\n    \"\"\"Mock HTTP client.\"\"\"\n    return MagicMock()"),
    "config": ("app_config", "@pytest.fixture\ndef app_config():\n    \"\"\"Sample application config.\"\"\"\n    return {'debug': False, 'host': 'localhost', 'port': 8080}"),
    "user": ("sample_user", "@pytest.fixture\ndef sample_user():\n    \"\"\"Sample user object.\"\"\"\n    return {'id': 1, 'name': 'Test User', 'email': 'test@example.com'}"),
    "path": ("tmp_path", ""),  # Built-in pytest fixture
    "file_path": ("tmp_path", ""),
}


class FixtureInferrer:
    """Analyses function bodies to infer required mocks and fixtures."""

    def infer_for_function(
        self,
        source_code: str,
        function_name: str,
    ) -> InferredFixtures:
        """Analyse a function's source to infer mocks and fixtures."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return InferredFixtures()

        func_node = self._find_function(tree, function_name)
        if func_node is None:
            return InferredFixtures()

        mocks = self._infer_mocks(func_node, source_code)
        fixtures = self._infer_fixtures_from_params(func_node)
        patch_decorators = [
            f'@patch("{m.target}")' for m in mocks
        ]

        return InferredFixtures(
            mocks=mocks,
            fixtures=fixtures,
            patch_decorators=patch_decorators,
        )

    def infer_for_module(self, source_path: Path) -> dict[str, InferredFixtures]:
        """Analyse all functions in a module."""
        logger.info("Inferring fixtures for %s", source_path)
        try:
            source_code = source_path.read_text(encoding="utf-8")
            tree = ast.parse(source_code)
        except (SyntaxError, OSError):
            return {}

        result: dict[str, InferredFixtures] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                inferred = self.infer_for_function(source_code, node.name)
                if inferred.mocks or inferred.fixtures:
                    result[node.name] = inferred

        return result

    def _find_function(self, tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        """Find a function node by name (including class methods)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
                return node
        return None

    def _infer_mocks(self, func_node: ast.AST, source_code: str) -> list[MockSpec]:
        """Walk function body to find external calls that should be mocked."""
        mocks: list[MockSpec] = []
        seen: set[str] = set()

        for child in ast.walk(func_node):
            if isinstance(child, ast.Call):
                call_name = self._call_name(child)
                if call_name and call_name not in seen:
                    # Check exact matches
                    if call_name in _MOCK_TEMPLATES:
                        return_value, category = _MOCK_TEMPLATES[call_name]
                        mock_name = "mock_" + call_name.replace(".", "_")
                        mocks.append(MockSpec(
                            target=call_name,
                            mock_name=mock_name,
                            return_value=return_value,
                            category=category,
                        ))
                        seen.add(call_name)
                    else:
                        # Check prefix matches
                        for pattern, (return_value, category) in _MOCK_TEMPLATES.items():
                            if call_name.startswith(pattern + ".") or call_name.startswith(pattern.split(".")[0] + "."):
                                mock_name = "mock_" + call_name.replace(".", "_")
                                mocks.append(MockSpec(
                                    target=call_name,
                                    mock_name=mock_name,
                                    return_value=return_value,
                                    category=category,
                                ))
                                seen.add(call_name)
                                break

        return mocks

    def _infer_fixtures_from_params(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[FixtureSpec]:
        """Infer fixtures from function parameter names."""
        fixtures: list[FixtureSpec] = []
        seen: set[str] = set()

        for arg in func_node.args.args:
            param_name = arg.arg
            if param_name == "self":
                continue
            for hint, (fixture_name, fixture_code) in _PARAM_FIXTURE_MAP.items():
                if hint in param_name.lower() and fixture_name not in seen:
                    if fixture_code:  # Skip built-in fixtures
                        fixtures.append(FixtureSpec(name=fixture_name, code=fixture_code))
                    seen.add(fixture_name)

        return fixtures

    @staticmethod
    def _call_name(node: ast.Call) -> str | None:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            try:
                return ast.unparse(func)
            except Exception:
                return None
        return None
