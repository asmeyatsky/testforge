# TestForge

AI-native testing framework that analyses codebases and generates multi-layered test strategies using Claude as the AI backbone.

TestForge scans your Python and TypeScript/JavaScript projects, builds a dependency-aware model of the codebase, and produces comprehensive test suites across five layers: unit, integration, UAT, soak, and performance.

## Features

### Code Analysis
- **AST-based Python scanning** — parses modules, functions, classes, imports, and external calls
- **Regex-based TypeScript/JavaScript scanning** — extracts exports, functions, classes, and React components
- **Polyglot support** — auto-detects and scans mixed-language projects via the multi-scanner

### Test Generation
- **AI-powered generation** — Claude produces context-aware test code with realistic mocks and assertions
- **Template fallback** — Jinja2 templates generate scaffold tests when AI is unavailable
- **Multi-layer strategies** — unit, integration, UAT, soak, and performance test generation
- **Jest/Vitest support** — generates TypeScript test files alongside Python pytest tests
- **Fixture inference** — detects external calls (HTTP, DB, filesystem) and generates appropriate mocks
- **PRD-aware strategies** — reads Product Requirements Documents to prioritise user-facing flows

### Workflow
- **Incremental mode** — only regenerates tests for files changed since a git ref
- **Test deduplication** — skips generating tests that already exist in your test suite
- **Coverage gap analysis** — identifies untested functions and methods
- **Mutation testing** — integrates with mutmut to measure test effectiveness
- **Auto-repair** — feeds failing test output back to the LLM for iterative fixes
- **Watch mode** — monitors file changes and regenerates tests automatically
- **Validation** — syntax checking and pytest collection verification before committing tests

### Interface
- **13 CLI commands** — Typer-based command-line interface with rich output
- **Interactive TUI** — Rich-powered terminal UI for browsing modules and selecting tests
- **Multiple output formats** — Rich tables, JSON, and YAML export
- **Plugin system** — extend with custom scanners, generators, and exporters via entry points

## Installation

```bash
pip install testforge
```

For development:

```bash
git clone <repo-url>
cd testforge
pip install -e ".[dev]"
```

Requires Python 3.11+.

## Quick Start

```bash
# Set your Anthropic API key for AI-powered features
export ANTHROPIC_API_KEY=sk-ant-...

# Analyse a codebase
testforge analyse /path/to/project

# Generate a test strategy
testforge strategise /path/to/project

# Generate test files
testforge generate /path/to/project -o tests_output

# Run the full pipeline (analyse -> strategise -> generate)
testforge run /path/to/project

# Only regenerate tests for recently changed files
testforge incremental /path/to/project --since HEAD~5

# Find untested functions
testforge gaps /path/to/project

# Auto-repair failing tests
testforge repair tests_output/

# Run mutation testing
testforge mutate /path/to/project --test-dir tests_output/

# Launch the interactive TUI
testforge interactive /path/to/project
```

## CLI Commands

| Command | Description |
|---|---|
| `analyse` | Scan a codebase and output modules, functions, classes, and endpoints |
| `strategise` | Generate a test strategy with prioritised test cases per layer |
| `generate` | Generate test files from a strategy |
| `run` | Full pipeline: analyse, strategise, generate |
| `execute` | Run generated tests and produce a pass/fail report |
| `incremental` | Generate tests only for files changed since a git ref |
| `gaps` | Find untested functions and methods |
| `repair` | Auto-repair failing tests using LLM feedback |
| `mutate` | Run mutation testing to measure test quality |
| `validate` | Check generated tests for syntax and collection errors |
| `interactive` | Launch the Rich-powered TUI |
| `watch` | Watch for file changes and regenerate automatically |
| `plugins` | List discovered plugins |

### Common Options

- `--config / -c` — path to config file
- `--layers / -l` — comma-separated layers (e.g. `unit,integration`)
- `--output-dir / -o` — output directory for generated tests
- `--format / -f` — output format: `rich`, `json`, or `yaml`
- `--verbose / -v` — enable debug logging
- `--prd` — path to a Product Requirements Document for PRD-aware strategy generation

## Configuration

Create a `testforge.yml` in your project root (also accepts `testforge.yaml` or `.testforge.yml`):

```yaml
project:
  name: my-project
  languages:
    - python
  test_framework: pytest

layers:
  unit:
    enabled: true
    output_dir: tests/unit
  integration:
    enabled: true
    output_dir: tests/integration
  uat:
    enabled: true
    output_dir: tests/uat
  soak:
    enabled: false
  performance:
    enabled: false

ai:
  provider: claude
  model: claude-sonnet-4-6-20250514

prd_path: docs/prd.md
output_dir: .testforge_output
```

## Architecture

TestForge follows clean architecture (hexagonal) with strict layer separation:

```
src/testforge/
├── domain/              # Pure business logic — no external dependencies
│   ├── entities.py      # CodebaseAnalysis, TestCase, TestSuite, TestStrategy
│   ├── value_objects.py # TestLayer, ModuleInfo, FunctionSignature, APIEndpoint
│   ├── services.py      # TestStrategyService — maps analysis to test cases
│   ├── ports.py         # Protocol interfaces for adapters
│   ├── events.py        # Domain events (AnalysisCompleted, StrategyGenerated, etc.)
│   └── errors.py        # Domain exception hierarchy
├── application/         # Use cases and orchestration
│   ├── commands.py      # CQRS command handlers
│   ├── queries.py       # Read-side DTOs
│   ├── dtos.py          # Data transfer objects
│   └── orchestrator.py  # DAG-based pipeline execution
├── infrastructure/      # Adapter implementations
│   ├── ai/              # Claude adapter with prompt templates
│   ├── scanners/        # Python (AST), TypeScript (regex), multi-language
│   ├── generators/      # Unit, integration, Jest, UAT, soak, performance
│   ├── templates/       # Jinja2 test scaffolds (.py.j2, .ts.j2, .js.j2, .md.j2)
│   ├── config.py        # YAML config with defaults
│   ├── container.py     # Dependency injection composition root
│   ├── test_runner.py   # pytest/Jest execution with result parsing
│   ├── test_repairer.py # LLM-powered auto-repair
│   ├── diff_detector.py # Git-based incremental detection
│   ├── fixture_inferrer.py  # Mock/fixture inference from external calls
│   ├── mutation_runner.py   # mutmut integration
│   ├── gap_analyser.py      # Coverage gap detection
│   ├── deduplicator.py      # Existing test deduplication
│   ├── validators.py        # Syntax and collection validation
│   ├── filesystem.py        # File I/O adapter
│   └── plugin_manager.py   # Entry-point plugin discovery
└── presentation/        # User interfaces
    ├── cli.py           # Typer CLI (13 commands)
    └── tui.py           # Rich interactive TUI
```

### Design Patterns

- **Dependency Injection** — `Container` composes all adapters at startup
- **Port/Adapter** — Protocol-based interfaces decouple domain from infrastructure
- **CQRS** — separate command and query paths
- **Strategy** — per-layer test generation strategies
- **Plugin Architecture** — `importlib.metadata.entry_points()` for extensibility

### Pipeline Flow

```
Analyse (scanner) → Strategise (AI/rules) → Generate (template/AI) → Validate → Execute
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=testforge --cov-report=term-missing

# CLI smoke test
testforge --help
testforge analyse src/testforge
```

CI runs on GitHub Actions across Python 3.11, 3.12, and 3.13 with dependency auditing via `pip-audit`.

## Dependencies

| Package | Purpose |
|---------|---------|
| `typer` | CLI framework |
| `rich` | Terminal UI, tables, progress bars |
| `anthropic` | Claude API client |
| `jinja2` | Test scaffold templates |
| `pyyaml` | Configuration parsing |
| `pydantic` | Data validation |

## License

MIT
