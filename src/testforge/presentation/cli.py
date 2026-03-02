"""Typer CLI application."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from testforge.application.commands import (
    AnalyseCodebaseCommand,
    GenerateStrategyCommand,
    GenerateTestsCommand,
    RunPipelineCommand,
)
from testforge.application.queries import GetAnalysis, GetStrategy
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.container import Container

app = typer.Typer(
    name="testforge",
    help="AI-native testing framework — analyse codebases and generate multi-layered test strategies.",
    no_args_is_help=True,
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
) -> None:
    """Analyse a codebase and output a summary."""
    container = _get_container(config)
    scanner = container.scanner()
    cmd = AnalyseCodebaseCommand(scanner, container.event_bus)

    with console.status("[bold green]Scanning codebase..."):
        analysis = cmd.execute(path.resolve())

    dto = GetAnalysis().execute(analysis)

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
) -> None:
    """Generate a test strategy for a codebase."""
    container = _get_container(config)
    scanner = container.scanner()
    resolved_layers = _resolve_layers(_parse_layers(layers), container.config)

    with console.status("[bold green]Scanning codebase..."):
        analysis = AnalyseCodebaseCommand(scanner).execute(path.resolve())

    prd_content = _resolve_prd(prd, container.config)

    ai = container.ai_strategy()
    cmd = GenerateStrategyCommand(ai, container.event_bus)

    with console.status("[bold green]Generating strategy..."):
        strategy = cmd.execute(analysis, resolved_layers, prd_content)

    dto = GetStrategy().execute(strategy)

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
) -> None:
    """Generate test files from a strategy."""
    container = _get_container(config)
    scanner = container.scanner()
    resolved_layers = _resolve_layers(_parse_layers(layers), container.config)

    with console.status("[bold green]Scanning codebase..."):
        analysis = AnalyseCodebaseCommand(scanner).execute(path.resolve())

    prd_content = _resolve_prd(prd, container.config)
    ai = container.ai_strategy()

    with console.status("[bold green]Generating strategy..."):
        strategy = GenerateStrategyCommand(ai).execute(analysis, resolved_layers, prd_content)

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


if __name__ == "__main__":
    app()
