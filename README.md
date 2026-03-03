# TestForge

AI-native testing framework that analyses codebases and generates multi-layered test strategies.

TestForge scans your Python and TypeScript/JavaScript projects, builds a dependency-aware model of the codebase, and produces comprehensive test suites — from unit tests through integration, UAT, soak, and performance layers — using Claude as the AI backbone.

## Features

- **Codebase analysis** — AST-based scanning for Python, regex-based for TypeScript/JavaScript, with auto-detection for polyglot projects
- **Multi-layer test strategies** — unit, integration, UAT, soak, and performance test generation
- **AI-powered generation** — uses Claude to produce context-aware test code with realistic mocks and fixtures
- **Fixture inference** — automatically detects external calls (HTTP, DB, filesystem) and generates appropriate mocks
- **Incremental mode** — only regenerates tests for files changed since a git ref
- **Test deduplication** — skips generating tests that already exist in your test suite
- **Coverage gap analysis** — identifies untested functions and methods
- **Mutation testing** — integrates with mutmut to measure test quality
- **Auto-repair** — feeds failing test output back to the LLM for iterative fixes
- **Interactive TUI** — Rich-powered terminal UI for browsing modules and selecting tests
- **Watch mode** — monitors file changes and regenerates tests automatically
- **Plugin system** — extend with custom scanners, generators, and exporters via entry points
- **Multiple output formats** — Rich tables, JSON, and YAML

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

# Run the full pipeline (analyse → strategise → generate)
testforge run /path/to/project
```

## CLI Commands

| Command | Description |
|---|---|
| `analyse` | Scan a codebase and output a summary of modules, functions, and classes |
| `strategise` | Generate a test strategy with prioritised test cases |
| `generate` | Generate test files from a strategy |
| `run` | Run the full pipeline: analyse, strategise, generate |
| `execute` | Run generated tests and produce a report |
| `incremental` | Only generate tests for files changed since a git ref |
| `gaps` | Analyse coverage gaps — find untested functions |
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

Create a `testforge.yml` in your project root:

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

TestForge searches for `testforge.yml`, `testforge.yaml`, or `.testforge.yml` in the current directory if no config is specified.

## Architecture

```
src/testforge/
├── domain/           # Entities, value objects, events, errors
│   ├── entities.py   # CodebaseAnalysis, TestCase, TestSuite, TestStrategy
│   ├── value_objects.py  # TestLayer, ModuleInfo, FunctionSignature, etc.
│   ├── events.py     # Domain events
│   └── errors.py     # Domain exceptions
├── application/      # Commands, queries, orchestrator
│   ├── commands.py   # AnalyseCodebase, GenerateStrategy, GenerateTests, RunPipeline
│   ├── queries.py    # Read-side DTOs
│   └── orchestrator.py  # DAG-based pipeline execution
├── infrastructure/   # Adapters and implementations
│   ├── ai/           # Claude adapter with prompt templates
│   ├── scanners/     # Python (AST), TypeScript (regex), multi-language
│   ├── generators/   # Unit, integration, UAT, soak, performance, Jest
│   ├── config.py     # YAML config loading
│   ├── container.py  # Dependency injection composition root
│   ├── test_runner.py    # pytest/Jest execution
│   ├── test_repairer.py  # LLM-powered auto-repair
│   ├── diff_detector.py  # Git-based incremental detection
│   ├── fixture_inferrer.py  # Mock/fixture inference
│   ├── mutation_runner.py   # mutmut integration
│   ├── gap_analyser.py     # Coverage gap detection
│   ├── deduplicator.py     # Test deduplication
│   ├── validators.py       # Syntax/collection validation
│   └── plugin_manager.py   # Entry-point plugin discovery
└── presentation/     # CLI and TUI
    ├── cli.py        # Typer CLI application
    └── tui.py        # Rich interactive TUI
```

## License

MIT
