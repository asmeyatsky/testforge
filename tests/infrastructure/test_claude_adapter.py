"""Tests for ClaudeAdapter — all Anthropic API calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from testforge.domain.entities import CodebaseAnalysis, TestCase
from testforge.domain.value_objects import (
    APIEndpoint,
    FunctionSignature,
    ModuleInfo,
    TestLayer,
)
from testforge.infrastructure.ai.claude_adapter import strip_markdown_fences


# ---------------------------------------------------------------------------
# strip_markdown_fences
# ---------------------------------------------------------------------------

class TestStripMarkdownFences:
    def test_plain_code(self):
        assert strip_markdown_fences("print('hi')") == "print('hi')"

    def test_python_fenced(self):
        text = "```python\nprint('hi')\n```"
        assert strip_markdown_fences(text) == "print('hi')"

    def test_generic_fenced(self):
        text = "```\nprint('hi')\n```"
        assert strip_markdown_fences(text) == "print('hi')"

    def test_custom_language(self):
        text = "```typescript\nconsole.log('hi')\n```"
        assert strip_markdown_fences(text, language="typescript") == "console.log('hi')"

    def test_trailing_fence_only(self):
        text = "print('hi')\n```"
        assert strip_markdown_fences(text) == "print('hi')"

    def test_whitespace_around(self):
        text = "  \n```python\n  code  \n```\n  "
        assert strip_markdown_fences(text) == "code"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _mock_message(text: str) -> MagicMock:
    """Build a mock Anthropic Message with the given text."""
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


def _sample_analysis() -> CodebaseAnalysis:
    return CodebaseAnalysis(
        root_path="/app",
        languages=("python",),
        modules=(
            ModuleInfo(
                file_path="app/utils.py",
                functions=(FunctionSignature(name="add", parameters=("a", "b")),),
            ),
        ),
    )


def _sample_test_cases() -> list[TestCase]:
    return [
        TestCase(
            name="test_add",
            description="Verify addition",
            target_function="add",
            target_module="app/utils.py",
        ),
    ]


def _make_adapter() -> tuple:
    """Create a ClaudeAdapter with a mocked Anthropic client."""
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        from testforge.infrastructure.ai.claude_adapter import ClaudeAdapter
        adapter = ClaudeAdapter(api_key="test-key")
    return adapter, mock_client


# ---------------------------------------------------------------------------
# ClaudeAdapter
# ---------------------------------------------------------------------------

class TestClaudeAdapter:

    # -- generate_strategy ---------------------------------------------------

    def test_generate_strategy_parses_json(self):
        adapter, client = _make_adapter()

        strategy_json = json.dumps({
            "suites": [{
                "layer": "unit",
                "test_cases": [{
                    "name": "test_add",
                    "description": "Test addition",
                    "target_function": "add",
                    "target_module": "app/utils.py",
                    "priority": 1,
                    "tags": ["math"],
                }],
            }],
        })
        client.messages.create.return_value = _mock_message(strategy_json)

        result = adapter.generate_strategy(_sample_analysis(), [TestLayer.UNIT])
        assert len(result.suites) == 1
        assert result.suites[0].layer == TestLayer.UNIT
        assert result.suites[0].test_cases[0].name == "test_add"
        assert result.suites[0].test_cases[0].tags == ("math",)

    def test_generate_strategy_strips_json_fences(self):
        adapter, client = _make_adapter()

        raw = '```json\n{"suites": []}\n```'
        client.messages.create.return_value = _mock_message(raw)

        result = adapter.generate_strategy(_sample_analysis(), [TestLayer.UNIT])
        assert result.suites == ()

    def test_generate_strategy_invalid_json_returns_empty(self):
        adapter, client = _make_adapter()
        client.messages.create.return_value = _mock_message("not json at all")

        result = adapter.generate_strategy(_sample_analysis(), [TestLayer.UNIT])
        assert result.suites == ()

    def test_generate_strategy_with_prd(self):
        adapter, client = _make_adapter()
        client.messages.create.return_value = _mock_message('{"suites": []}')

        adapter.generate_strategy(
            _sample_analysis(), [TestLayer.UNIT], prd_content="Users can log in",
        )
        call_kwargs = client.messages.create.call_args[1]
        prompt_sent = call_kwargs["messages"][0]["content"]
        assert "Product Requirements:" in prompt_sent
        assert "Users can log in" in prompt_sent

    # -- generate_test_code --------------------------------------------------

    def test_generate_test_code(self):
        adapter, client = _make_adapter()
        client.messages.create.return_value = _mock_message(
            "```python\ndef test_add():\n    assert add(1, 2) == 3\n```"
        )

        code = adapter.generate_test_code(
            target_module="app/utils.py",
            source_code="def add(a, b): return a + b",
            test_cases=_sample_test_cases(),
        )
        assert "def test_add" in code
        assert "```" not in code

    def test_generate_test_code_plain_response(self):
        adapter, client = _make_adapter()
        client.messages.create.return_value = _mock_message("def test_add(): pass")

        code = adapter.generate_test_code(
            target_module="app/utils.py",
            source_code="def add(a, b): return a + b",
            test_cases=_sample_test_cases(),
            imports_hint="from app.utils import add",
        )
        assert code == "def test_add(): pass"

    # -- generate_integration_tests ------------------------------------------

    def test_generate_integration_tests(self):
        adapter, client = _make_adapter()
        client.messages.create.return_value = _mock_message(
            "```python\ndef test_get_users(): pass\n```"
        )

        endpoints = [
            APIEndpoint(method="GET", path="/users", handler_name="get_users", file_path="app/api.py"),
        ]
        code = adapter.generate_integration_tests(
            framework="fastapi", endpoints=endpoints, source_code="# api code",
        )
        assert "def test_get_users" in code
        assert "```" not in code

    # -- generate_uat_pack ---------------------------------------------------

    def test_generate_uat_pack(self):
        adapter, client = _make_adapter()
        client.messages.create.return_value = _mock_message("# UAT Test Pack\n\n| Scenario | Steps |")

        endpoints = [
            APIEndpoint(method="POST", path="/login", handler_name="login", file_path="app/auth.py"),
        ]
        result = adapter.generate_uat_pack(endpoints=endpoints, prd_content="Users must log in")
        assert "UAT Test Pack" in result

    def test_generate_uat_pack_no_prd(self):
        adapter, client = _make_adapter()
        client.messages.create.return_value = _mock_message("# UAT Pack")

        endpoints = [
            APIEndpoint(method="GET", path="/", handler_name="index", file_path="app/main.py"),
        ]
        adapter.generate_uat_pack(endpoints=endpoints)
        call_kwargs = client.messages.create.call_args[1]
        prompt_sent = call_kwargs["messages"][0]["content"]
        assert "No PRD provided." in prompt_sent

    # -- _build_analysis_summary ---------------------------------------------

    def test_build_analysis_summary(self):
        adapter, _ = _make_adapter()
        summary = adapter._build_analysis_summary(_sample_analysis())
        assert "Root: /app" in summary
        assert "python" in summary
        assert "add(a, b)" in summary
