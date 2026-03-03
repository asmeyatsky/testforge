"""Tests for the agentic chat interface."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from testforge.domain.entities import CodebaseAnalysis, TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import (
    ClassInfo,
    FilePath,
    FunctionSignature,
    ModuleInfo,
    TestLayer,
)
from testforge.infrastructure.container import Container
from testforge.presentation.agent import (
    CONFIRMATION_REQUIRED,
    MAX_MESSAGES,
    TOOLS,
    AgentChat,
    AgentSession,
    _HANDLERS,
    _trim_messages,
    build_system_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_analysis(root: str = "/tmp/proj") -> CodebaseAnalysis:
    return CodebaseAnalysis(
        root_path=root,
        languages=("python",),
        modules=(
            ModuleInfo(
                file_path=FilePath("app.py"),
                functions=(
                    FunctionSignature(name="hello", parameters=()),
                    FunctionSignature(name="goodbye", parameters=("name",)),
                ),
                classes=(ClassInfo(name="App", methods=()),),
            ),
        ),
    )


def _make_strategy(analysis_id: str = "") -> TestStrategy:
    return TestStrategy(
        analysis_id=analysis_id,
        suites=(
            TestSuite(
                layer=TestLayer.UNIT,
                test_cases=(
                    TestCase(name="test_hello", target_function="hello", priority=1),
                    TestCase(name="test_goodbye", target_function="goodbye", priority=2),
                ),
            ),
        ),
    )


def _make_session(tmp_path: Path) -> AgentSession:
    (tmp_path / "app.py").write_text("def hello(): pass\ndef goodbye(name): pass\n")
    container = Container()
    return AgentSession(
        project_path=tmp_path,
        container=container,
        output_dir=tmp_path / "output",
    )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestToolSchemas:
    def test_all_tools_have_required_fields(self):
        for tool in TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "input_schema" in tool, f"Tool {tool['name']} missing 'input_schema'"
            schema = tool["input_schema"]
            assert schema.get("type") == "object", f"Tool {tool['name']} schema type must be 'object'"

    def test_tool_count(self):
        assert len(TOOLS) == 11

    def test_schema_names_match_handlers(self):
        tool_names = {t["name"] for t in TOOLS}
        handler_names = set(_HANDLERS.keys())
        assert tool_names == handler_names, (
            f"Mismatch — tools without handlers: {tool_names - handler_names}, "
            f"handlers without tools: {handler_names - tool_names}"
        )


# ---------------------------------------------------------------------------
# Confirmation logic
# ---------------------------------------------------------------------------

class TestConfirmation:
    def test_read_only_tools_no_confirmation(self):
        read_only = {"analyse_codebase", "show_analysis", "show_strategy", "find_gaps", "validate_tests"}
        for name in read_only:
            assert name not in CONFIRMATION_REQUIRED, f"{name} should not require confirmation"

    def test_write_tools_require_confirmation(self):
        write_tools = {
            "generate_strategy", "generate_tests", "execute_tests",
            "repair_tests", "incremental_generate", "run_mutation_testing",
        }
        for name in write_tools:
            assert name in CONFIRMATION_REQUIRED, f"{name} should require confirmation"

    def test_confirmation_set_matches_expected_size(self):
        assert len(CONFIRMATION_REQUIRED) == 6


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

class TestHandlers:
    def test_analyse_sets_session_state(self, tmp_path: Path):
        session = _make_session(tmp_path)
        assert session.analysis is None

        result = session.execute_tool("analyse_codebase", {})

        assert session.analysis is not None
        assert session.analysis.total_functions > 0
        assert "Analysis complete" in result
        assert "hello" in result or "Functions: 2" in result

    def test_show_analysis_without_analysis_returns_error(self, tmp_path: Path):
        session = _make_session(tmp_path)
        result = session.execute_tool("show_analysis", {})
        assert "No analysis available" in result

    def test_show_analysis_with_analysis(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.analysis = _make_analysis(str(tmp_path))
        result = session.execute_tool("show_analysis", {})
        assert "app.py" in result
        assert "2 funcs" in result

    def test_generate_strategy_without_analysis_returns_error(self, tmp_path: Path):
        session = _make_session(tmp_path)
        result = session.execute_tool("generate_strategy", {})
        assert "No analysis available" in result

    def test_generate_strategy_with_analysis(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.analysis = _make_analysis(str(tmp_path))
        result = session.execute_tool("generate_strategy", {"layers": "unit"})
        assert session.strategy is not None
        assert "Strategy generated" in result

    def test_show_strategy_without_strategy_returns_error(self, tmp_path: Path):
        session = _make_session(tmp_path)
        result = session.execute_tool("show_strategy", {})
        assert "No strategy available" in result

    def test_show_strategy_with_strategy(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.strategy = _make_strategy()
        result = session.execute_tool("show_strategy", {})
        assert "test_hello" in result
        assert "UNIT" in result

    def test_generate_tests_without_strategy_returns_error(self, tmp_path: Path):
        session = _make_session(tmp_path)
        result = session.execute_tool("generate_tests", {})
        assert "No strategy available" in result

    def test_execute_tests(self, tmp_path: Path):
        test_file = tmp_path / "test_ok.py"
        test_file.write_text("def test_pass(): assert True\n")
        session = _make_session(tmp_path)
        result = session.execute_tool("execute_tests", {"test_dir": str(tmp_path)})
        assert "1/1 passed" in result

    def test_validate_tests(self, tmp_path: Path):
        test_dir = tmp_path / "tests_out"
        test_dir.mkdir()
        (test_dir / "test_ok.py").write_text("def test_pass(): assert True\n")
        session = _make_session(tmp_path)
        result = session.execute_tool("validate_tests", {"test_dir": str(test_dir)})
        assert "1/1 passed" in result

    def test_find_gaps(self, tmp_path: Path):
        (tmp_path / "utils.py").write_text("def foo(): pass\ndef bar(): pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_utils.py").write_text("def test_foo(): pass\n")
        session = _make_session(tmp_path)
        result = session.execute_tool("find_gaps", {"test_dir": str(tests)})
        assert "Coverage" in result

    def test_unknown_tool_returns_error(self, tmp_path: Path):
        session = _make_session(tmp_path)
        result = session.execute_tool("nonexistent_tool", {})
        assert "Unknown tool" in result

    def test_handler_exception_returns_error_string(self, tmp_path: Path):
        session = _make_session(tmp_path)
        # Force handler to raise by using a broken container
        session.container = MagicMock()
        session.container.scanner.side_effect = RuntimeError("boom")
        result = session.execute_tool("analyse_codebase", {})
        assert "Error running" in result


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

class TestSystemPrompt:
    def test_includes_project_path(self, tmp_path: Path):
        session = _make_session(tmp_path)
        prompt = build_system_prompt(session)
        assert str(tmp_path.resolve()) in prompt

    def test_includes_analysis_when_available(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.analysis = _make_analysis(str(tmp_path))
        prompt = build_system_prompt(session)
        assert "Current analysis" in prompt
        assert "app.py" in prompt

    def test_no_analysis_section_without_analysis(self, tmp_path: Path):
        session = _make_session(tmp_path)
        prompt = build_system_prompt(session)
        assert "Current analysis" not in prompt

    def test_includes_strategy_when_available(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.strategy = _make_strategy()
        prompt = build_system_prompt(session)
        assert "Current strategy" in prompt

    def test_includes_workflow_guidance(self, tmp_path: Path):
        session = _make_session(tmp_path)
        prompt = build_system_prompt(session)
        assert "Workflow guidance" in prompt


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

class TestChatCommand:
    def test_chat_command_registered(self):
        from typer.testing import CliRunner
        from testforge.presentation.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert "chat" in result.output

    def test_agent_chat_init(self):
        container = Container()
        agent = AgentChat(container, model_override="claude-haiku-4-5-20251001")
        assert agent._model == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Message trimming
# ---------------------------------------------------------------------------

class TestTrimMessages:
    def test_under_limit_returns_unchanged(self):
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        result = _trim_messages(messages)
        assert result == messages
        assert len(result) == 10

    def test_at_limit_returns_unchanged(self):
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(MAX_MESSAGES)]
        result = _trim_messages(messages)
        assert result == messages

    def test_over_limit_trims_with_marker(self):
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(60)]
        result = _trim_messages(messages)
        assert len(result) == MAX_MESSAGES
        # First message preserved
        assert result[0] == messages[0]
        # Trim marker inserted
        assert "trimmed" in result[1]["content"].lower()
        # Last messages preserved
        assert result[-1] == messages[-1]


# ---------------------------------------------------------------------------
# find_gaps caching
# ---------------------------------------------------------------------------

class TestFindGapsCaching:
    def test_reuses_cached_analysis(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("def foo(): pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_app.py").write_text("def test_foo(): pass\n")

        session = _make_session(tmp_path)
        session.analysis = _make_analysis(str(tmp_path))

        # Mock scanner to verify it's NOT called
        session.container = MagicMock()
        result = session.execute_tool("find_gaps", {"test_dir": str(tests)})

        session.container.scanner.assert_not_called()
        assert "Coverage" in result

    def test_scans_when_no_cached_analysis(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("def foo(): pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_app.py").write_text("def test_foo(): pass\n")

        session = _make_session(tmp_path)
        assert session.analysis is None

        result = session.execute_tool("find_gaps", {"test_dir": str(tests)})
        assert "Coverage" in result


# ---------------------------------------------------------------------------
# generate_strategy layer defaults
# ---------------------------------------------------------------------------

class TestGenerateStrategyLayers:
    def test_empty_string_defaults_to_unit(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.analysis = _make_analysis(str(tmp_path))
        result = session.execute_tool("generate_strategy", {"layers": ""})
        assert session.strategy is not None
        assert "Strategy generated" in result

    def test_whitespace_only_defaults_to_unit(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.analysis = _make_analysis(str(tmp_path))
        result = session.execute_tool("generate_strategy", {"layers": "   "})
        assert session.strategy is not None
        assert "Strategy generated" in result
