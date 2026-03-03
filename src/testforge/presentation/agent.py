"""Agentic chat interface — tool-use loop over TestForge commands."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from testforge.infrastructure.container import Container

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas (Claude tool-use format)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "analyse_codebase",
        "description": "Scan the project and return a summary of modules, functions, classes, and languages.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "show_analysis",
        "description": "Show the most recent codebase analysis (must analyse first).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "generate_strategy",
        "description": "Generate a test strategy from the current analysis. Requires prior analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "layers": {
                    "type": "string",
                    "description": "Comma-separated test layers: unit, integration, uat, soak, performance. Defaults to 'unit'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "show_strategy",
        "description": "Show the most recent test strategy (must generate strategy first).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "generate_tests",
        "description": "Generate test files from the current strategy. Requires prior strategy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "layers": {
                    "type": "string",
                    "description": "Comma-separated test layers. Defaults to layers in strategy.",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Output directory for generated tests. Defaults to '.testforge_output'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "execute_tests",
        "description": "Run pytest on generated tests and return results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_dir": {
                    "type": "string",
                    "description": "Path to test directory. Defaults to output_dir.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "find_gaps",
        "description": "Find untested functions by comparing source code against existing tests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_dir": {
                    "type": "string",
                    "description": "Path to existing test directory. Defaults to '<project>/tests'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "validate_tests",
        "description": "Validate generated test files for syntax errors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_dir": {
                    "type": "string",
                    "description": "Path to test directory. Defaults to output_dir.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "repair_tests",
        "description": "Auto-repair failing tests using LLM. Requires ANTHROPIC_API_KEY.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_dir": {
                    "type": "string",
                    "description": "Path to test directory to repair. Defaults to output_dir.",
                },
                "max_attempts": {
                    "type": "integer",
                    "description": "Maximum repair attempts per file. Defaults to 3.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "incremental_generate",
        "description": "Detect changed files via git diff and generate tests only for those changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Git ref to diff against. Defaults to 'HEAD'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "run_mutation_testing",
        "description": "Run mutation testing to measure test quality. Requires mutmut.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_dir": {
                    "type": "string",
                    "description": "Test directory for mutation testing. Defaults to 'tests'.",
                },
            },
            "required": [],
        },
    },
]

# Tools that modify state or call external APIs — require user confirmation.
CONFIRMATION_REQUIRED: set[str] = {
    "generate_strategy",
    "generate_tests",
    "execute_tests",
    "repair_tests",
    "incremental_generate",
    "run_mutation_testing",
}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

@dataclass
class AgentSession:
    """Mutable state maintained across the chat loop."""

    project_path: Path = field(default_factory=lambda: Path("."))
    container: Container = field(default_factory=Container)
    analysis: Any = None  # CodebaseAnalysis | None
    strategy: Any = None  # TestStrategy | None
    output_dir: Path = field(default_factory=lambda: Path(".testforge_output"))

    def execute_tool(self, name: str, args: dict[str, Any]) -> str:
        """Dispatch a tool call to the matching handler."""
        handler = _HANDLERS.get(name)
        if handler is None:
            return f"Unknown tool: {name}"
        try:
            return handler(self, args)
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return f"Error running {name}: {exc}"


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def _handle_analyse_codebase(session: AgentSession, _args: dict) -> str:
    from testforge.application.commands import AnalyseCodebaseCommand

    scanner = session.container.scanner()
    cmd = AnalyseCodebaseCommand(scanner, session.container.event_bus)
    session.analysis = cmd.execute(session.project_path.resolve())

    a = session.analysis
    return (
        f"Analysis complete.\n"
        f"Root: {a.root_path}\n"
        f"Languages: {', '.join(a.languages)}\n"
        f"Modules: {a.total_modules}\n"
        f"Functions: {a.total_functions}\n"
        f"Classes: {a.total_classes}"
    )


def _handle_show_analysis(session: AgentSession, _args: dict) -> str:
    if session.analysis is None:
        return "No analysis available yet. Run analyse_codebase first."

    from testforge.application.queries import GetAnalysis

    dto = GetAnalysis().execute(session.analysis)
    lines = [
        f"Root: {dto.root_path}",
        f"Languages: {', '.join(dto.languages)}",
        f"Modules: {dto.total_modules}, Functions: {dto.total_functions}, Classes: {dto.total_classes}",
        "",
    ]
    for mod in dto.modules[:20]:
        lines.append(f"  {mod.file_path}: {mod.function_count} funcs, {mod.class_count} classes")
    if len(dto.modules) > 20:
        lines.append(f"  ... and {len(dto.modules) - 20} more")
    return "\n".join(lines)


def _handle_generate_strategy(session: AgentSession, args: dict) -> str:
    if session.analysis is None:
        return "No analysis available. Run analyse_codebase first."

    from testforge.application.commands import GenerateStrategyCommand
    from testforge.domain.value_objects import TestLayer

    layers_str = args.get("layers", "unit")
    layers = [TestLayer(l.strip()) for l in layers_str.split(",")]

    ai = session.container.ai_strategy()
    cmd = GenerateStrategyCommand(ai, session.container.event_bus)
    session.strategy = cmd.execute(session.analysis, layers)

    return (
        f"Strategy generated: {session.strategy.total_test_cases} test cases "
        f"across {len(session.strategy.layers_covered)} layer(s)."
    )


def _handle_show_strategy(session: AgentSession, _args: dict) -> str:
    if session.strategy is None:
        return "No strategy available yet. Run generate_strategy first."

    from testforge.application.queries import GetStrategy

    dto = GetStrategy().execute(session.strategy)
    lines = [f"Strategy: {dto.total_test_cases} test cases, layers: {', '.join(dto.layers_covered)}"]
    for suite in dto.suites:
        lines.append(f"\n  {suite.layer.upper()} ({suite.size} cases):")
        for tc in suite.test_cases[:10]:
            lines.append(f"    - {tc.name} -> {tc.target_function} (priority {tc.priority})")
        if len(suite.test_cases) > 10:
            lines.append(f"    ... and {len(suite.test_cases) - 10} more")
    return "\n".join(lines)


def _handle_generate_tests(session: AgentSession, args: dict) -> str:
    if session.strategy is None:
        return "No strategy available. Run generate_strategy first."

    from testforge.application.commands import GenerateTestsCommand
    from testforge.domain.value_objects import TestLayer

    out = Path(args.get("output_dir", str(session.output_dir)))
    session.output_dir = out

    layers_str = args.get("layers")
    if layers_str:
        layers = [TestLayer(l.strip()) for l in layers_str.split(",")]
    else:
        layers = list(session.strategy.layers_covered)

    generators = session.container.generators(source_root=session.project_path.resolve())
    cmd = GenerateTestsCommand(generators, session.container.event_bus)
    suites = cmd.execute(session.strategy, out, layers)

    parts = [f"Generated {s.size} {s.layer.value} tests -> {out}" for s in suites]
    return "\n".join(parts) if parts else "No test files generated."


def _handle_execute_tests(session: AgentSession, args: dict) -> str:
    from testforge.infrastructure.test_runner import TestRunner

    test_dir = Path(args.get("test_dir", str(session.output_dir)))
    runner = TestRunner()
    report = runner.run_pytest_simple(test_dir)

    lines = [
        f"Results: {report.passed}/{report.total} passed ({report.success_rate:.0%})",
        f"Failed: {report.failed}, Errors: {report.errors}, Skipped: {report.skipped}",
    ]
    if report.failures:
        lines.append("\nFailures:")
        for f in report.failures[:5]:
            lines.append(f"  - {f.name}")
            if f.longrepr:
                for ln in f.longrepr.splitlines()[:3]:
                    lines.append(f"    {ln}")
    return "\n".join(lines)


def _handle_find_gaps(session: AgentSession, args: dict) -> str:
    from testforge.infrastructure.gap_analyser import GapAnalyser

    scanner = session.container.scanner()
    analysis = scanner.scan(session.project_path.resolve())

    test_dir = Path(args.get("test_dir", str(session.project_path.resolve() / "tests")))
    analyser = GapAnalyser()
    report = analyser.analyse(analysis, test_dir)

    lines = [f"Coverage: {report.coverage_percent:.0f}% ({report.tested}/{report.total} functions tested)"]
    if report.untested:
        lines.append(f"\nUntested functions ({len(report.untested)}):")
        for func in report.untested[:20]:
            lines.append(f"  - {func}")
        if len(report.untested) > 20:
            lines.append(f"  ... and {len(report.untested) - 20} more")
    else:
        lines.append("All functions have tests!")
    return "\n".join(lines)


def _handle_repair_tests(session: AgentSession, args: dict) -> str:
    from testforge.infrastructure.test_repairer import TestRepairer

    ai = session.container.ai_strategy()
    if not ai:
        return "Error: ANTHROPIC_API_KEY required for test repair."

    test_dir = Path(args.get("test_dir", str(session.output_dir)))
    max_attempts = int(args.get("max_attempts", 3))
    repairer = TestRepairer(ai_adapter=ai, max_attempts=max_attempts)
    results = repairer.repair_directory(test_dir)

    if not results:
        return "All tests passing — no repairs needed."

    fixed = sum(1 for r in results if r.success)
    lines = [f"Repair results: {fixed}/{len(results)} files repaired"]
    for r in results:
        status = "FIXED" if r.success else "FAILED"
        lines.append(f"  - {Path(r.test_file).name}: {status} (attempt {r.attempt})")
    return "\n".join(lines)


def _handle_validate_tests(session: AgentSession, args: dict) -> str:
    from testforge.infrastructure.validators import TestValidator

    test_dir = Path(args.get("test_dir", str(session.output_dir)))
    validator = TestValidator()
    report = validator.validate_syntax(test_dir)

    lines = [f"Validation: {report.passed}/{report.total} passed ({report.success_rate:.0%})"]
    for r in report.results:
        if not r.valid:
            lines.append(f"  FAIL: {r.file_path} — {'; '.join(r.errors)}")
    return "\n".join(lines)


def _handle_incremental_generate(session: AgentSession, args: dict) -> str:
    from testforge.application.commands import (
        AnalyseCodebaseCommand,
        GenerateStrategyCommand,
        GenerateTestsCommand,
    )
    from testforge.infrastructure.diff_detector import DiffDetector

    ref = args.get("ref", "HEAD")
    detector = DiffDetector(session.project_path.resolve())
    diff = detector.detect_git_changes(ref)

    if not diff.has_changes:
        return "No source file changes detected."

    scanner = session.container.scanner()
    full_analysis = AnalyseCodebaseCommand(scanner).execute(session.project_path.resolve())
    filtered = detector.filter_analysis_to_changed(full_analysis, diff)

    ai = session.container.ai_strategy()
    strategy = GenerateStrategyCommand(ai).execute(filtered, None)

    generators = session.container.generators(source_root=session.project_path.resolve())
    cmd = GenerateTestsCommand(generators)
    suites = cmd.execute(strategy, session.output_dir, None)

    parts = [
        f"Changes: {len(diff.modified)} modified, {len(diff.added)} added, {len(diff.deleted)} deleted",
    ]
    for s in suites:
        parts.append(f"Generated {s.size} {s.layer.value} tests -> {session.output_dir}")
    return "\n".join(parts)


def _handle_run_mutation_testing(session: AgentSession, args: dict) -> str:
    from testforge.infrastructure.mutation_runner import MutationRunner

    runner = MutationRunner()
    if not runner.check_available():
        return "Error: mutmut not installed. Install with: pip install mutmut"

    test_dir = Path(args.get("test_dir", "tests"))
    report = runner.run(session.project_path.resolve(), test_dir)

    if report.stderr and "not installed" in report.stderr:
        return f"Error: {report.stderr}"

    lines = [
        f"Mutation score: {report.mutation_score:.1f}%",
        f"Total: {report.total}, Killed: {report.killed}, Survived: {report.survived}, Timeout: {report.timeout}",
    ]
    if report.survivors:
        lines.append(f"\n{len(report.survivors)} surviving mutants:")
        for s in report.survivors[:10]:
            info = f"  - {s.source_file}" if s.source_file else f"  - mutant {s.id}"
            lines.append(info)
    return "\n".join(lines)


_HANDLERS: dict[str, Any] = {
    "analyse_codebase": _handle_analyse_codebase,
    "show_analysis": _handle_show_analysis,
    "generate_strategy": _handle_generate_strategy,
    "show_strategy": _handle_show_strategy,
    "generate_tests": _handle_generate_tests,
    "execute_tests": _handle_execute_tests,
    "find_gaps": _handle_find_gaps,
    "repair_tests": _handle_repair_tests,
    "validate_tests": _handle_validate_tests,
    "incremental_generate": _handle_incremental_generate,
    "run_mutation_testing": _handle_run_mutation_testing,
}


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def build_system_prompt(session: AgentSession) -> str:
    """Build a context-aware system prompt for Claude."""
    parts = [
        "You are TestForge Assistant, an AI agent that helps developers generate "
        "and manage tests for their codebase.",
        "",
        "You have tools to analyse codebases, generate test strategies, generate "
        "test files, execute tests, find coverage gaps, repair failing tests, and "
        "run mutation testing.",
        "",
        f"Project path: {session.project_path.resolve()}",
    ]

    if session.analysis:
        a = session.analysis
        parts.append("")
        parts.append("Current analysis:")
        parts.append(f"  Languages: {', '.join(a.languages)}")
        parts.append(f"  Modules: {a.total_modules}, Functions: {a.total_functions}, Classes: {a.total_classes}")
        for mod in a.modules[:20]:
            parts.append(f"  - {mod.file_path}: {len(mod.functions)} funcs, {len(mod.classes)} classes")
        if len(a.modules) > 20:
            parts.append(f"  ... and {len(a.modules) - 20} more")

    if session.strategy:
        s = session.strategy
        parts.append("")
        parts.append(
            f"Current strategy: {s.total_test_cases} test cases across "
            f"{', '.join(l.value for l in s.layers_covered)}"
        )

    parts.extend([
        "",
        "Workflow guidance:",
        "1. Start by analysing the codebase if not yet done.",
        "2. Generate a strategy to plan test cases.",
        "3. Generate test files from the strategy.",
        "4. Validate and execute the tests.",
        "5. Repair any failures and re-run.",
        "",
        "Always explain what you're doing and why. If a tool requires a prior step, "
        "run that step first.",
    ])

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Chat REPL
# ---------------------------------------------------------------------------

class AgentChat:
    """Interactive tool-use chat loop with Claude."""

    def __init__(
        self,
        container: Container,
        model_override: str | None = None,
        console: Console | None = None,
    ) -> None:
        self._container = container
        self._model = model_override or container.config.get("ai", {}).get(
            "model", "claude-sonnet-4-6-20250514"
        )
        self._console = console or Console()

    def run(self, project_path: Path) -> None:
        import anthropic

        client = anthropic.Anthropic()
        session = AgentSession(
            project_path=project_path.resolve(),
            container=self._container,
            output_dir=Path(
                self._container.config.get("output_dir", ".testforge_output")
            ),
        )
        messages: list[dict[str, Any]] = []

        self._console.print(
            Panel(
                "[bold]TestForge Chat[/bold]\n"
                "Ask me to analyse your code, generate tests, find gaps, and more.\n"
                "Type [bold]quit[/bold] or [bold]exit[/bold] to leave.",
                title="TestForge",
                border_style="blue",
            )
        )

        while True:
            try:
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
            except (KeyboardInterrupt, EOFError):
                self._console.print("\n[bold]Goodbye![/bold]")
                break

            if user_input.strip().lower() in ("quit", "exit"):
                self._console.print("[bold]Goodbye![/bold]")
                break

            if not user_input.strip():
                continue

            messages.append({"role": "user", "content": user_input})

            # Inner tool-use loop
            while True:
                system_prompt = build_system_prompt(session)

                response = client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=messages,
                )

                # Process response content blocks
                assistant_content: list[dict[str, Any]] = []
                tool_results: list[dict[str, Any]] = []

                for block in response.content:
                    if block.type == "text":
                        self._console.print()
                        self._console.print(Markdown(block.text))
                        assistant_content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

                        # Confirmation for write operations
                        if block.name in CONFIRMATION_REQUIRED:
                            confirmed = Confirm.ask(
                                f"\n[yellow]Allow [bold]{block.name}[/bold]?[/yellow]",
                                default=True,
                            )
                            if not confirmed:
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": "User declined this operation.",
                                })
                                continue

                        with self._console.status(f"[bold green]Running {block.name}..."):
                            result = session.execute_tool(block.name, block.input)

                        self._console.print(f"[dim]{block.name} completed[/dim]")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "assistant", "content": assistant_content})

                if response.stop_reason == "end_turn":
                    break

                if response.stop_reason == "tool_use" and tool_results:
                    messages.append({"role": "user", "content": tool_results})
                else:
                    break
