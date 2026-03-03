"""Interactive TUI mode — Rich-powered terminal UI for browsing and selecting tests."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.tree import Tree

from testforge.application.commands import (
    AnalyseCodebaseCommand,
    GenerateStrategyCommand,
    GenerateTestsCommand,
)
from testforge.domain.entities import CodebaseAnalysis, TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.container import Container


class InteractiveTUI:
    """Rich-powered terminal UI for interactive test generation."""

    def __init__(self, container: Container) -> None:
        self._container = container
        self._console = Console()
        self._analysis: CodebaseAnalysis | None = None
        self._strategy: TestStrategy | None = None

    def run(self, path: Path) -> None:
        """Main TUI loop."""
        self._console.print(Panel(
            "[bold cyan]TestForge Interactive Mode[/bold cyan]\n"
            "Browse your codebase, select tests, preview and generate.",
            title="Welcome",
        ))

        # Step 1: Analyse
        self._analyse(path)
        if not self._analysis or self._analysis.total_modules == 0:
            self._console.print("[yellow]No modules found. Exiting.[/yellow]")
            return

        while True:
            choice = self._main_menu()
            if choice == "1":
                self._browse_modules()
            elif choice == "2":
                self._generate_strategy()
            elif choice == "3":
                self._browse_strategy()
            elif choice == "4":
                self._select_and_generate(path)
            elif choice == "5":
                self._preview_tests()
            elif choice == "q":
                self._console.print("[bold]Goodbye![/bold]")
                break

    def _main_menu(self) -> str:
        self._console.print()
        table = Table(title="Main Menu", show_header=False, box=None)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Action")
        table.add_row("1", "Browse modules")
        table.add_row("2", "Generate test strategy")
        table.add_row("3", "Browse strategy")
        table.add_row("4", "Select tests & generate")
        table.add_row("5", "Preview generated tests")
        table.add_row("q", "Quit")
        self._console.print(table)
        return Prompt.ask("Choose", choices=["1", "2", "3", "4", "5", "q"], default="1")

    def _analyse(self, path: Path) -> None:
        scanner = self._container.scanner()
        with self._console.status("[bold green]Scanning codebase..."):
            self._analysis = AnalyseCodebaseCommand(scanner).execute(path.resolve())

        self._console.print(Panel(
            f"[green]Scanned {self._analysis.total_modules} modules, "
            f"{self._analysis.total_functions} functions, "
            f"{self._analysis.total_classes} classes[/green]",
            title="Analysis Complete",
        ))

    def _browse_modules(self) -> None:
        if not self._analysis:
            return

        tree = Tree("[bold]Codebase Modules[/bold]")
        for mod in self._analysis.modules:
            branch = tree.add(f"[cyan]{mod.file_path}[/cyan]")
            for func in mod.functions:
                params = ", ".join(func.parameters)
                style = "green" if not func.name.startswith("_") else "dim"
                async_tag = "[yellow]async[/yellow] " if func.is_async else ""
                branch.add(f"{async_tag}[{style}]{func.name}[/{style}]({params})")
            for cls in mod.classes:
                cls_branch = branch.add(f"[bold magenta]class {cls.name}[/bold magenta]")
                for method in cls.methods:
                    cls_branch.add(f"  {method.name}({', '.join(method.parameters)})")

        self._console.print(tree)

    def _generate_strategy(self) -> None:
        if not self._analysis:
            return

        # Ask which layers
        self._console.print("\n[bold]Available layers:[/bold]")
        for i, layer in enumerate(TestLayer, 1):
            self._console.print(f"  {i}. {layer.value}")

        layer_input = Prompt.ask(
            "Select layers (comma-separated numbers)",
            default="1",
        )
        selected_layers: list[TestLayer] = []
        for num in layer_input.split(","):
            num = num.strip()
            if num.isdigit():
                idx = int(num) - 1
                layers_list = list(TestLayer)
                if 0 <= idx < len(layers_list):
                    selected_layers.append(layers_list[idx])

        if not selected_layers:
            selected_layers = [TestLayer.UNIT]

        ai = self._container.ai_strategy()
        cmd = GenerateStrategyCommand(ai)
        with self._console.status("[bold green]Generating strategy..."):
            self._strategy = cmd.execute(self._analysis, selected_layers)

        self._console.print(Panel(
            f"[green]Generated {self._strategy.total_test_cases} test cases "
            f"across {len(self._strategy.layers_covered)} layers[/green]",
            title="Strategy Ready",
        ))

    def _browse_strategy(self) -> None:
        if not self._strategy:
            self._console.print("[yellow]No strategy generated yet. Use option 2 first.[/yellow]")
            return

        for suite in self._strategy.suites:
            table = Table(title=f"{suite.layer.value.upper()} Layer ({suite.size} cases)")
            table.add_column("#", style="dim", width=4)
            table.add_column("Test", style="cyan")
            table.add_column("Target", style="yellow")
            table.add_column("Module")
            table.add_column("Priority", justify="right")
            for i, tc in enumerate(suite.test_cases, 1):
                table.add_row(
                    str(i), tc.name, tc.target_function,
                    tc.target_module, str(tc.priority),
                )
            self._console.print(table)

    def _select_and_generate(self, path: Path) -> None:
        if not self._strategy:
            self._console.print("[yellow]No strategy yet. Generating default...[/yellow]")
            self._generate_strategy()

        if not self._strategy or self._strategy.total_test_cases == 0:
            self._console.print("[yellow]No test cases to generate.[/yellow]")
            return

        # Show test cases and let user exclude some
        self._browse_strategy()

        if not Confirm.ask("\nGenerate all test cases?", default=True):
            self._console.print("[dim]Selective generation: enter test numbers to exclude (comma-separated)[/dim]")
            exclude_input = Prompt.ask("Exclude (or Enter to skip)", default="")
            # For now, generate all — selective exclusion is a future enhancement
            self._console.print("[dim]Generating all tests...[/dim]")

        output_dir = Path(Prompt.ask(
            "Output directory",
            default=str(self._container.config.get("output_dir", ".testforge_output")),
        ))

        generators = self._container.generators(source_root=path.resolve())
        cmd = GenerateTestsCommand(generators)

        with self._console.status("[bold green]Generating tests..."):
            suites = cmd.execute(self._strategy, output_dir)

        for suite in suites:
            self._console.print(
                f"[green]Generated {suite.size} {suite.layer.value} tests -> {output_dir}[/green]"
            )

    def _preview_tests(self) -> None:
        output_dir = Path(Prompt.ask(
            "Test output directory to preview",
            default=".testforge_output",
        ))

        if not output_dir.exists():
            self._console.print("[yellow]Directory does not exist.[/yellow]")
            return

        test_files = sorted(output_dir.rglob("test_*"))
        if not test_files:
            test_files = sorted(output_dir.rglob("*.test.*"))

        if not test_files:
            self._console.print("[yellow]No test files found.[/yellow]")
            return

        self._console.print(f"\n[bold]Found {len(test_files)} test files:[/bold]")
        for i, f in enumerate(test_files, 1):
            self._console.print(f"  {i}. {f.relative_to(output_dir)}")

        choice = IntPrompt.ask("Preview file number", default=1)
        if 1 <= choice <= len(test_files):
            content = test_files[choice - 1].read_text()
            self._console.print(Panel(
                content,
                title=str(test_files[choice - 1].name),
                border_style="green",
            ))
