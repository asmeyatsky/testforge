"""Typer CLI application."""

from __future__ import annotations

import enum
import json as json_mod
import logging
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)


class OutputFormat(str, enum.Enum):
    rich = "rich"
    json = "json"
    yaml = "yaml"

from testforge.application.commands import (
    AnalyseCodebaseCommand,
    GenerateStrategyCommand,
    GenerateTestsCommand,
    RunPipelineCommand,
)
from testforge.application.queries import GetAnalysis, GetStrategy
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.container import Container

def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _version_callback(value: bool) -> None:
    if value:
        console.print("testforge 0.1.0")
        raise typer.Exit()


def _main_callback(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose logging")] = False,
) -> None:
    _configure_logging(verbose)


app = typer.Typer(
    name="testforge",
    help="AI-native testing framework — analyse codebases and generate multi-layered test strategies.",
    no_args_is_help=True,
    callback=_main_callback,
)
console = Console()


def _parse_layers(layers: str | None) -> list[TestLayer] | None:
    if not layers:
        return None
    return [TestLayer(l.strip()) for l in layers.split(",")]


def _enabled_layers(cfg: dict) -> list[TestLayer]:
    """Return layers that are enabled in config."""
    layers_cfg = cfg.get("layers", {})
    enabled = []
    for layer in TestLayer:
        layer_cfg = layers_cfg.get(layer.value, {})
        if layer_cfg.get("enabled", False):
            enabled.append(layer)
    return enabled


def _resolve_layers(explicit: list[TestLayer] | None, cfg: dict) -> list[TestLayer]:
    """Use explicit layers if provided, otherwise fall back to config-enabled layers."""
    if explicit:
        return explicit
    enabled = _enabled_layers(cfg)
    return enabled if enabled else [TestLayer.UNIT]


def _resolve_prd(explicit_prd: str | None, cfg: dict) -> str | None:
    """Load PRD content from explicit flag or config prd_path."""
    prd_path = explicit_prd or cfg.get("prd_path")
    if not prd_path:
        return None
    p = Path(prd_path)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def _get_container(config: str | None) -> Container:
    from testforge.infrastructure.config import ConfigAdapter

    cfg = ConfigAdapter().load(Path(config) if config else None)
    return Container(config=cfg)


@app.command()
def analyse(
    path: Annotated[Path, typer.Argument(help="Path to codebase root")] = Path("."),
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="Config file path")] = None,
    format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.rich,
) -> None:
    """Analyse a codebase and output a summary."""
    container = _get_container(config)
    scanner = container.scanner()
    cmd = AnalyseCodebaseCommand(scanner, container.event_bus)

    with console.status("[bold green]Scanning codebase..." if format == OutputFormat.rich else ""):
        analysis = cmd.execute(path.resolve())

    dto = GetAnalysis().execute(analysis)

    if format == OutputFormat.json:
        print(json_mod.dumps(dto.model_dump(), indent=2))
        return
    if format == OutputFormat.yaml:
        print(yaml.dump(dto.model_dump(), default_flow_style=False))
        return

    table = Table(title="Codebase Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Root Path", dto.root_path)
    table.add_row("Languages", ", ".join(dto.languages))
    table.add_row("Modules", str(dto.total_modules))
    table.add_row("Functions", str(dto.total_functions))
    table.add_row("Classes", str(dto.total_classes))
    console.print(table)

    if dto.modules:
        mod_table = Table(title="Modules")
        mod_table.add_column("File", style="cyan")
        mod_table.add_column("Functions", justify="right")
        mod_table.add_column("Classes", justify="right")
        mod_table.add_column("Endpoints", justify="right")
        for mod in dto.modules[:20]:
            mod_table.add_row(
                mod.file_path,
                str(mod.function_count),
                str(mod.class_count),
                str(mod.endpoint_count),
            )
        if len(dto.modules) > 20:
            mod_table.add_row(f"... and {len(dto.modules) - 20} more", "", "", "")
        console.print(mod_table)


@app.command()
def strategise(
    path: Annotated[Path, typer.Argument(help="Path to codebase root")] = Path("."),
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="Config file path")] = None,
    layers: Annotated[Optional[str], typer.Option("--layers", "-l", help="Comma-separated layers")] = None,
    prd: Annotated[Optional[str], typer.Option("--prd", help="Path to PRD file")] = None,
    format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.rich,
) -> None:
    """Generate a test strategy for a codebase."""
    container = _get_container(config)
    scanner = container.scanner()
    resolved_layers = _resolve_layers(_parse_layers(layers), container.config)

    with console.status("[bold green]Scanning codebase..." if format == OutputFormat.rich else ""):
        analysis = AnalyseCodebaseCommand(scanner).execute(path.resolve())

    prd_content = _resolve_prd(prd, container.config)

    ai = container.ai_strategy()
    cmd = GenerateStrategyCommand(ai, container.event_bus)

    with console.status("[bold green]Generating strategy..."):
        strategy = cmd.execute(analysis, resolved_layers, prd_content)

    dto = GetStrategy().execute(strategy)

    if format == OutputFormat.json:
        print(json_mod.dumps(dto.model_dump(), indent=2))
        return
    if format == OutputFormat.yaml:
        print(yaml.dump(dto.model_dump(), default_flow_style=False))
        return

    console.print(Panel(f"[bold]Test Strategy[/bold] — {dto.total_test_cases} test cases across {len(dto.layers_covered)} layers"))

    for suite in dto.suites:
        table = Table(title=f"{suite.layer.upper()} Layer ({suite.size} cases)")
        table.add_column("Test", style="cyan")
        table.add_column("Target", style="yellow")
        table.add_column("Priority", justify="right")
        for tc in suite.test_cases[:15]:
            table.add_row(tc.name, tc.target_function, str(tc.priority))
        if len(suite.test_cases) > 15:
            table.add_row(f"... and {len(suite.test_cases) - 15} more", "", "")
        console.print(table)


@app.command()
def generate(
    path: Annotated[Path, typer.Argument(help="Path to codebase root")] = Path("."),
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="Config file path")] = None,
    layers: Annotated[Optional[str], typer.Option("--layers", "-l", help="Comma-separated layers")] = None,
    prd: Annotated[Optional[str], typer.Option("--prd", help="Path to PRD file")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-o", help="Output directory")] = None,
    no_dedup: Annotated[bool, typer.Option("--no-dedup", help="Skip deduplication against existing tests")] = False,
) -> None:
    """Generate test files from a strategy."""
    from testforge.infrastructure.deduplicator import TestDeduplicator

    container = _get_container(config)
    scanner = container.scanner()
    resolved_layers = _resolve_layers(_parse_layers(layers), container.config)

    with console.status("[bold green]Scanning codebase..."):
        analysis = AnalyseCodebaseCommand(scanner).execute(path.resolve())

    prd_content = _resolve_prd(prd, container.config)
    ai = container.ai_strategy()

    with console.status("[bold green]Generating strategy..."):
        strategy = GenerateStrategyCommand(ai).execute(analysis, resolved_layers, prd_content)

    if not no_dedup:
        test_path = path.resolve() / "tests"
        if test_path.exists():
            dedup = TestDeduplicator(test_path)
            original_count = strategy.total_test_cases
            strategy = dedup.deduplicate(strategy)
            skipped = original_count - strategy.total_test_cases
            if skipped:
                console.print(f"[dim]Skipped {skipped} already-covered test cases[/dim]")

    out = Path(output_dir or container.config.get("output_dir", ".testforge_output"))
    generators = container.generators(source_root=path.resolve())
    cmd = GenerateTestsCommand(generators, container.event_bus)

    with console.status("[bold green]Generating tests..."):
        suites = cmd.execute(strategy, out, resolved_layers)

    for suite in suites:
        console.print(f"[green]✓[/green] Generated {suite.size} {suite.layer.value} test cases → {out}")


@app.command()
def run(
    path: Annotated[Path, typer.Argument(help="Path to codebase root")] = Path("."),
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="Config file path")] = None,
    layers: Annotated[Optional[str], typer.Option("--layers", "-l", help="Comma-separated layers")] = None,
    prd: Annotated[Optional[str], typer.Option("--prd", help="Path to PRD file")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-o", help="Output directory")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Run pipeline without generating files")] = False,
) -> None:
    """Run the full pipeline: analyse → strategise → generate."""
    container = _get_container(config)
    resolved_layers = _resolve_layers(_parse_layers(layers), container.config)

    prd_content = _resolve_prd(prd, container.config)
    out = Path(output_dir or container.config.get("output_dir", ".testforge_output"))

    cmd = RunPipelineCommand(
        scanner=container.scanner(),
        ai_strategy=container.ai_strategy(),
        generators=container.generators(source_root=path.resolve()),
        event_bus=container.event_bus,
    )

    with console.status("[bold green]Running pipeline..."):
        result = cmd.execute(
            root_path=path.resolve(),
            output_dir=out,
            layers=resolved_layers,
            prd_content=prd_content,
            dry_run=dry_run,
        )

    analysis = result["analysis"]
    strategy = result["strategy"]

    console.print(Panel(
        f"[bold]Pipeline Complete[/bold]\n"
        f"Modules scanned: {analysis.total_modules}\n"
        f"Functions found: {analysis.total_functions}\n"
        f"Test cases planned: {strategy.total_test_cases}\n"
        f"Dry run: {'yes' if dry_run else 'no'}",
        title="TestForge",
    ))

    if not dry_run:
        for suite in result["suites"]:
            console.print(f"[green]✓[/green] {suite.layer.value}: {suite.size} tests → {out}")
    else:
        console.print("[yellow]Dry run — no files generated[/yellow]")


@app.command()
def validate(
    path: Annotated[Path, typer.Argument(help="Path to generated test directory")] = Path(".testforge_output"),
    collect: Annotated[bool, typer.Option("--collect", help="Also run pytest --collect-only")] = False,
) -> None:
    """Validate generated test files for syntax and collection errors."""
    from testforge.infrastructure.validators import TestValidator

    validator = TestValidator()

    with console.status("[bold green]Validating tests..."):
        if collect:
            report = validator.validate_collection(path)
        else:
            report = validator.validate_syntax(path)

    table = Table(title="Validation Report")
    table.add_column("File", style="cyan")
    table.add_column("Status")
    table.add_column("Errors", style="red")

    for r in report.results:
        status = "[green]PASS[/green]" if r.valid else "[red]FAIL[/red]"
        errors = "; ".join(r.errors) if r.errors else ""
        table.add_row(r.file_path, status, errors)

    console.print(table)
    console.print(
        f"\n{report.passed}/{report.total} passed "
        f"({report.success_rate:.0%} success rate)"
    )


@app.command()
def gaps(
    path: Annotated[Path, typer.Argument(help="Path to codebase root")] = Path("."),
    test_dir: Annotated[Optional[str], typer.Option("--test-dir", "-t", help="Existing test directory")] = None,
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="Config file path")] = None,
    format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.rich,
) -> None:
    """Analyse coverage gaps — find untested functions."""
    from testforge.infrastructure.gap_analyser import GapAnalyser

    container = _get_container(config)
    scanner = container.scanner()

    with console.status("[bold green]Scanning codebase..." if format == OutputFormat.rich else ""):
        analysis = scanner.scan(path.resolve())

    test_path = Path(test_dir) if test_dir else path.resolve() / "tests"
    analyser = GapAnalyser()

    with console.status("[bold green]Analysing coverage gaps..." if format == OutputFormat.rich else ""):
        report = analyser.analyse(analysis, test_path)

    if format in (OutputFormat.json, OutputFormat.yaml):
        data = {
            "coverage_percent": report.coverage_percent,
            "tested": report.tested,
            "total": report.total,
            "untested": report.untested,
            "modules": [
                {"file_path": m.file_path, "tested": m.tested, "untested": m.untested}
                for m in report.modules if m.untested
            ],
        }
        if format == OutputFormat.json:
            print(json_mod.dumps(data, indent=2))
        else:
            print(yaml.dump(data, default_flow_style=False))
        return

    table = Table(title=f"Coverage Gap Analysis — {report.coverage_percent:.0f}% covered")
    table.add_column("Module", style="cyan")
    table.add_column("Untested Functions", style="red")
    table.add_column("Tested", style="green", justify="right")
    table.add_column("Total", justify="right")

    for module in report.modules:
        if module.untested:
            table.add_row(
                module.file_path,
                ", ".join(module.untested[:5]) + (f" +{len(module.untested)-5}" if len(module.untested) > 5 else ""),
                str(module.tested_count),
                str(module.total_count),
            )

    console.print(table)
    console.print(f"\nTotal: {report.tested}/{report.total} functions tested ({report.coverage_percent:.0f}%)")
    if report.untested:
        console.print(f"[yellow]{len(report.untested)} functions need tests[/yellow]")


@app.command()
def execute(
    path: Annotated[Path, typer.Argument(help="Path to generated test directory")] = Path(".testforge_output"),
    layers: Annotated[Optional[str], typer.Option("--layers", "-l", help="Comma-separated layers")] = None,
    format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.rich,
) -> None:
    """Execute generated tests and produce a report."""
    from testforge.infrastructure.test_runner import TestRunner

    runner = TestRunner()

    with console.status("[bold green]Running tests..."):
        report = runner.run_pytest_simple(path)

    if format == OutputFormat.json:
        import json as json_mod2
        data = {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "errors": report.errors,
            "skipped": report.skipped,
            "success_rate": report.success_rate,
            "failures": [
                {"name": f.name, "outcome": f.outcome, "message": f.longrepr[:500]}
                for f in report.failures
            ],
        }
        print(json_mod2.dumps(data, indent=2))
        return

    table = Table(title="Test Execution Report")
    table.add_column("Test", style="cyan")
    table.add_column("Status")
    table.add_column("Duration", justify="right")

    for r in report.results:
        status_style = {
            "passed": "[green]PASS[/green]",
            "failed": "[red]FAIL[/red]",
            "error": "[red]ERROR[/red]",
            "skipped": "[yellow]SKIP[/yellow]",
        }.get(r.outcome, r.outcome)
        table.add_row(r.name, status_style, f"{r.duration:.2f}s" if r.duration else "")

    console.print(table)
    console.print(
        f"\n[bold]{report.passed}[/bold]/{report.total} passed "
        f"({report.success_rate:.0%} success rate)"
    )

    if report.failures:
        console.print(f"\n[red]{len(report.failures)} failures:[/red]")
        for f in report.failures[:5]:
            console.print(f"  [red]- {f.name}[/red]")
            if f.longrepr:
                for line in f.longrepr.splitlines()[:3]:
                    console.print(f"    {line}")


@app.command()
def incremental(
    path: Annotated[Path, typer.Argument(help="Path to codebase root")] = Path("."),
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="Config file path")] = None,
    layers: Annotated[Optional[str], typer.Option("--layers", "-l", help="Comma-separated layers")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-o", help="Output directory")] = None,
    ref: Annotated[str, typer.Option("--ref", help="Git ref to diff against")] = "HEAD",
) -> None:
    """Incrementally generate tests only for changed files."""
    from testforge.infrastructure.diff_detector import DiffDetector

    container = _get_container(config)
    resolved_layers = _resolve_layers(_parse_layers(layers), container.config)
    out = Path(output_dir or container.config.get("output_dir", ".testforge_output"))

    detector = DiffDetector(path.resolve())

    with console.status("[bold green]Detecting changes..."):
        diff = detector.detect_git_changes(ref)

    if not diff.has_changes:
        console.print("[green]No source file changes detected.[/green]")
        return

    console.print(
        f"[yellow]Changes detected:[/yellow] {len(diff.modified)} modified, "
        f"{len(diff.added)} added, {len(diff.deleted)} deleted"
    )

    scanner = container.scanner()
    with console.status("[bold green]Scanning codebase..."):
        full_analysis = AnalyseCodebaseCommand(scanner).execute(path.resolve())

    # Filter analysis to only changed modules
    filtered = detector.filter_analysis_to_changed(full_analysis, diff)
    console.print(f"[dim]Generating tests for {filtered.total_modules} changed modules[/dim]")

    ai = container.ai_strategy()
    strategy = GenerateStrategyCommand(ai).execute(filtered, resolved_layers)

    generators = container.generators(source_root=path.resolve())
    cmd = GenerateTestsCommand(generators)

    with console.status("[bold green]Generating tests..."):
        suites = cmd.execute(strategy, out, resolved_layers)

    for suite in suites:
        console.print(f"[green]Generated {suite.size} {suite.layer.value} tests -> {out}[/green]")


@app.command()
def repair(
    path: Annotated[Path, typer.Argument(help="Path to test directory to repair")] = Path(".testforge_output"),
    source: Annotated[Optional[str], typer.Option("--source", "-s", help="Source code root")] = None,
    max_attempts: Annotated[int, typer.Option("--max-attempts", help="Max repair attempts per file")] = 3,
) -> None:
    """Auto-repair failing tests using LLM."""
    container = _get_container(None)
    ai = container.ai_strategy()

    if not ai:
        console.print("[red]Error: ANTHROPIC_API_KEY required for test repair[/red]")
        raise typer.Exit(1)

    from testforge.infrastructure.test_repairer import TestRepairer

    source_root = Path(source) if source else None
    repairer = TestRepairer(ai_adapter=ai, max_attempts=max_attempts, source_root=source_root)

    with console.status("[bold green]Repairing failing tests..."):
        results = repairer.repair_directory(path)

    if not results:
        console.print("[green]All tests passing — no repairs needed.[/green]")
        return

    table = Table(title="Repair Results")
    table.add_column("File", style="cyan")
    table.add_column("Status")
    table.add_column("Attempts", justify="right")

    for r in results:
        status = "[green]FIXED[/green]" if r.success else "[red]FAILED[/red]"
        table.add_row(Path(r.test_file).name, status, str(r.attempt))

    console.print(table)

    fixed = sum(1 for r in results if r.success)
    console.print(f"\n{fixed}/{len(results)} files repaired")


@app.command()
def mutate(
    source: Annotated[Path, typer.Argument(help="Source directory to mutate")] = Path("."),
    test_dir: Annotated[Path, typer.Option("--test-dir", "-t", help="Test directory")] = Path("tests"),
) -> None:
    """Run mutation testing to measure test quality."""
    from testforge.infrastructure.mutation_runner import MutationRunner

    runner = MutationRunner()

    if not runner.check_available():
        console.print("[red]mutmut not installed. Install with: pip install mutmut[/red]")
        raise typer.Exit(1)

    with console.status("[bold green]Running mutation testing (this may take a while)..."):
        report = runner.run(source, test_dir)

    if report.stderr and "not installed" in report.stderr:
        console.print(f"[red]{report.stderr}[/red]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]Mutation Score: {report.mutation_score:.1f}%[/bold]\n"
        f"Total mutants: {report.total}\n"
        f"Killed: {report.killed}\n"
        f"Survived: {report.survived}\n"
        f"Timeout: {report.timeout}",
        title="Mutation Testing Report",
    ))

    if report.survivors:
        console.print(f"\n[yellow]{len(report.survivors)} surviving mutants (tests didn't catch these):[/yellow]")
        for s in report.survivors[:10]:
            info = f"  - {s.source_file}" if s.source_file else f"  - mutant {s.id}"
            console.print(info)


@app.command()
def interactive(
    path: Annotated[Path, typer.Argument(help="Path to codebase root")] = Path("."),
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="Config file path")] = None,
) -> None:
    """Launch interactive TUI mode."""
    from testforge.presentation.tui import InteractiveTUI

    container = _get_container(config)
    tui = InteractiveTUI(container)
    tui.run(path)


@app.command()
def plugins(
) -> None:
    """List discovered plugins."""
    from testforge.infrastructure.plugin_manager import PluginManager

    pm = PluginManager()
    registry = pm.discover_all()

    if not registry.plugins:
        console.print("[dim]No plugins discovered.[/dim]")
        console.print("\nTo create a plugin, add entry points to your pyproject.toml:")
        console.print('  [project.entry-points."testforge.scanners"]')
        console.print('  my_scanner = "my_package.scanner:MyScanner"')
        return

    table = Table(title=f"TestForge Plugins ({registry.total_loaded} loaded)")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Module")
    table.add_column("Status")

    for p in registry.plugins:
        status = "[green]Loaded[/green]" if p.loaded else f"[red]Error: {p.error}[/red]"
        ptype = p.group.split(".")[-1]
        table.add_row(p.name, ptype, p.module, status)

    console.print(table)


@app.command()
def watch(
    path: Annotated[Path, typer.Argument(help="Path to codebase root")] = Path("."),
    config: Annotated[Optional[str], typer.Option("--config", "-c", help="Config file path")] = None,
    layers: Annotated[Optional[str], typer.Option("--layers", "-l", help="Comma-separated layers")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-o", help="Output directory")] = None,
    interval: Annotated[int, typer.Option("--interval", help="Polling interval in seconds")] = 2,
) -> None:
    """Watch for file changes and regenerate tests automatically."""
    import time

    container = _get_container(config)
    resolved_layers = _resolve_layers(_parse_layers(layers), container.config)
    out = Path(output_dir or container.config.get("output_dir", ".testforge_output"))

    console.print(f"[bold]Watching[/bold] {path.resolve()} for changes (Ctrl+C to stop)")
    console.print(f"Layers: {', '.join(l.value for l in resolved_layers)}")
    console.print(f"Output: {out}\n")

    last_mtimes: dict[str, float] = {}

    def _get_mtimes() -> dict[str, float]:
        mtimes: dict[str, float] = {}
        for ext in ("*.py", "*.ts", "*.tsx", "*.js", "*.jsx"):
            for f in path.resolve().rglob(ext):
                if any(p in str(f) for p in ("__pycache__", "node_modules", ".venv", ".testforge_output")):
                    continue
                mtimes[str(f)] = f.stat().st_mtime
        return mtimes

    last_mtimes = _get_mtimes()

    try:
        while True:
            time.sleep(interval)
            current_mtimes = _get_mtimes()

            changed = {
                f for f in current_mtimes
                if f not in last_mtimes or current_mtimes[f] != last_mtimes[f]
            }
            new_files = set(current_mtimes) - set(last_mtimes)
            deleted = set(last_mtimes) - set(current_mtimes)

            if changed or new_files or deleted:
                console.print(f"[yellow]Changes detected[/yellow]: {len(changed)} modified, {len(new_files)} new, {len(deleted)} deleted")

                cmd = RunPipelineCommand(
                    scanner=container.scanner(),
                    ai_strategy=container.ai_strategy(),
                    generators=container.generators(source_root=path.resolve()),
                    event_bus=container.event_bus,
                )

                try:
                    result = cmd.execute(
                        root_path=path.resolve(),
                        output_dir=out,
                        layers=resolved_layers,
                    )
                    strategy = result["strategy"]
                    console.print(f"[green]Regenerated[/green] {strategy.total_test_cases} test cases")
                except Exception as e:
                    console.print(f"[red]Error[/red]: {e}")

                last_mtimes = current_mtimes

    except KeyboardInterrupt:
        console.print("\n[bold]Watch stopped[/bold]")


if __name__ == "__main__":
    app()
