# TestForge Audit Log

## 2026-03-05 — End-to-End Audit

**Scope:** Architecture, E2E Pipeline, Test Coverage, Security, Code Quality
**Test Suite:** 252 passed, 0 failed (9.47s) | **Overall Coverage: 77%**

---

### 1. Architecture — Score: 9.5/10

TestForge follows **hexagonal/clean architecture** with excellent layer separation.

**Layer Compliance:**
| Layer | Violation Count | Assessment |
|---|---|---|
| Domain (entities, VOs, services, ports, events) | 0 | ZERO imports from infrastructure or presentation |
| Application (commands, queries, DTOs) | 0 | Depends only on domain ports |
| Infrastructure (adapters, scanners, generators) | 0 | Implements domain ports correctly |
| Presentation (CLI, TUI, API, agent) | 0 | Uses application commands only |

**Domain Model Quality:**
- All 12 domain dataclasses use `@dataclass(frozen=True)` — full immutability
- Business rules concentrated in `TestStrategyService` and `TestPrioritizationService`
- Value objects used properly: `FilePath`, `FunctionSignature`, `ClassInfo`, `APIEndpoint`, `DependencyGraph`, `TestLayer`
- Domain events are immutable, published in commands, dispatched via `SimpleEventBus`

**Port/Adapter Pattern:**
- 6 ports defined as `@runtime_checkable` Protocols in `domain/ports.py`: `CodeScannerPort`, `AIStrategyPort`, `TestGeneratorPort`, `ConfigPort`, `FileSystemPort`, `EventBusPort`
- All external dependencies abstracted behind ports
- Composition root in `infrastructure/container.py` wires implementations

**Design Patterns:** DI Container, Port/Adapter, CQRS, Strategy, Plugin Architecture, Template Method

---

### 2. E2E Pipeline — Score: 8.5/10

**Pipeline Flow:**
```
Entry Points (CLI/TUI/API/Agent)
  |
  v
RunPipelineCommand (application/commands.py:113-147)
  |
  +-- Phase 1: AnalyseCodebaseCommand
  |     MultiScanner -> PythonScanner/TypeScriptScanner (AST-based)
  |     Output: CodebaseAnalysis (modules, functions, classes, endpoints)
  |
  +-- Phase 2: GenerateStrategyCommand
  |     Path A: ClaudeAdapter.generate_strategy() (AI via STRATEGY_GENERATION_PROMPT)
  |     Path B: TestStrategyService.build_strategy() (local fallback)
  |     Output: TestStrategy with suites/test_cases
  |
  +-- Phase 3: GenerateTestsCommand
  |     Per-layer generators (unit, integration, UAT, soak, performance)
  |     Path A: AI adapter -> real test code
  |     Path B: Jinja2 templates -> scaffold stubs
  |     Output: .testforge_output/{test files}
  |
  +-- Events: AnalysisCompleted -> StrategyGenerated -> TestsGenerated
```

**Additional Pipeline Features:**
- Validation: AST parse + `pytest --collect-only`
- Execution: subprocess pytest with JSON report parsing
- Repair: Run failing test -> extract error -> Claude fix -> retry (3 attempts)
- Gap Analysis: Compare source functions vs test AST
- Incremental: `git diff HEAD` to regenerate only changed modules
- Mutation Testing: `mutmut` wrapper with kill/survival scoring
- Deduplication: Compare new cases against existing tests

**Error Handling / Fallbacks:**
| Failure Point | Handling |
|---|---|
| Scanner fails on file | Silent skip, continues scanning |
| AI strategy generation fails | Returns empty TestStrategy (logs WARNING) |
| AI test code generation fails | Falls back to Jinja2 template scaffold |
| Test execution fails | Returns ExecutionReport with failure details |
| Test repair fails | Restores original code after max retries |
| Missing API key | Falls back to local strategy service |

**Pipeline Issues Found:**
1. **No retry logic** for transient AI API failures (rate limits, network timeouts)
2. **JSON parsing is fragile** — assumes well-formed JSON from Claude; malformed responses silently produce empty strategy
3. **Markdown-stripping duplicated** in 3 files (claude_adapter.py, jest_generator.py, integration_generator.py)
4. **Scanner file errors not aggregated** — individual failures silently skipped, no summary report
5. **Error truncation in repair** — output truncated to 3000 chars, may lose critical debug info

---

### 3. Test Coverage — Score: 8/10

**Results: 252 passed, 0 failed | 77% line coverage (CI threshold: 70%)**

**Coverage by Layer:**
| Layer | Coverage | Key Gaps |
|---|---|---|
| Domain | 97-100% | `services.py` at 92% (5 uncovered lines) |
| Application | 97-100% | `commands.py` 98%, `orchestrator.py` 97% |
| Infrastructure | 0-100% | `gemini_adapter.py` 0%, `test_runner.py` 55%, `mutation_runner.py` 59% |
| Presentation | 52-65% | `agent.py` 52%, `cli.py` 65% (API/TUI excluded by config) |

**Modules with ZERO coverage:**
| Module | Lines | Risk | Action Needed |
|---|---|---|---|
| `gemini_adapter.py` | 51 stmts | HIGH | Mirror `test_claude_adapter.py` (22 tests exist for Claude) |

**Modules with LOW coverage (<70%):**
| Module | Coverage | Reason |
|---|---|---|
| `test_runner.py` | 55% | Subprocess execution paths untested |
| `mutation_runner.py` | 59% | Mutmut integration paths untested |
| `diff_detector.py` | 63% | Git diff parsing paths untested |
| `integration_generator.py` | 53% | AI-powered paths untested |
| `agent.py` | 52% | Agent tool execution loops untested |
| `cli.py` | 65% | watch/repair/mutate commands untested |
| `test_repairer.py` | 68% | Repair loop paths partially untested |

**Test Quality: HIGH**
- Domain tests: pure logic, zero mocks
- Application tests: mock ports correctly (not domain logic)
- Infrastructure tests: real I/O via `tmp_path`
- AI adapter tests: mock at SDK boundary (`anthropic.Anthropic`)
- CLI tests: genuine E2E via `typer.testing.CliRunner`
- All 252 tests have concrete assertions — no stubs/placeholders

**Test Pattern Gaps:**
- `@pytest.mark.parametrize` not used (several data-driven tests would benefit)
- No `conftest.py` — 15+ duplicate helper builders across files
- Duplicate TypeScriptScanner tests in `test_generators.py` (lines 188-234)

---

### 4. Security — Score: 9/10

**Overall Risk: LOW** — appropriate for a local development tool.

| # | Finding | Location | Severity |
|---|---|---|---|
| S1 | CORS `allow_origins=["*"]` | `presentation/api/app.py:40-43` | Medium (local-only OK) |
| S2 | In-memory sessions without expiration | `presentation/api/dependencies.py:25` | Low |
| S3 | Bare `os.environ[]` access (KeyError risk) | `presentation/api/routes/chat.py:52` | Low |
| S4 | Git clone accepts any URL, no size limits | `presentation/api/routes/settings.py:60-65` | Low |
| S5 | Silent `except Exception: pass` in JSON parsing | `infrastructure/test_runner.py:106-107` | Low |

**Positive Findings:**
- No hardcoded secrets — API keys via environment variables only
- All subprocess calls use list-based commands (no shell injection)
- Safe YAML: `yaml.safe_load()` everywhere
- No `eval`/`exec`/`pickle` usage
- Jinja2 uses `autoescape`
- Pydantic validates all API request schemas
- CI includes `pip-audit` security check
- React frontend: no `dangerouslySetInnerHTML`, proper DOM escaping
- Dependencies all current, no known vulnerabilities

---

### 5. Code Quality — Score: 8.5/10

**Strengths:**
- Clean architecture well-executed across all layers
- No circular imports
- Comprehensive type annotations
- Proper error hierarchy (`DomainError` base)
- Consistent naming (PEP 8)
- Proper logging throughout (no print statements in library code)

**Issues:**
| # | Finding | Location | Severity |
|---|---|---|---|
| Q1 | `watch()` function 68 lines — should extract helpers | `cli.py:628` | Low |
| Q2 | Markdown-stripping duplicated in 3 files | claude/jest/integration generators | Low |
| Q3 | Container returns `object` instead of typed ports | `container.py:70,80` | Low |
| Q4 | Missing docstrings on domain entities | `entities.py`, `events.py` | Low |
| Q5 | 7 `# type: ignore` comments in generators | Various | Info |

---

### Overall Verdict

| Dimension | Score | Confidence Level |
|---|---|---|
| Architecture | 9.5/10 | Production-grade hexagonal architecture |
| E2E Pipeline | 8.5/10 | Functional with good fallbacks, needs retry logic |
| Test Coverage | 8/10 | 77% coverage, quality is high, gemini_adapter gap |
| Security | 9/10 | Solid for local dev tool, minor hardening needed |
| Code Quality | 8.5/10 | Clean, consistent, minor duplication |
| **OVERALL** | **8.7/10** | **Ready for use — high confidence** |

### Priority Action Items

| Priority | Action | Impact |
|---|---|---|
| HIGH | Add tests for `gemini_adapter.py` (0% coverage, real parsing logic) | Closes biggest coverage gap |
| HIGH | Add retry logic with exponential backoff for AI API calls | Prevents silent failures on transient errors |
| MEDIUM | Extract `strip_markdown_fences()` into shared utility | Removes 3-way duplication |
| MEDIUM | Add `conftest.py` with shared test fixtures | Reduces 15+ duplicate builders |
| MEDIUM | Improve `test_runner.py` coverage (55%) | Core execution path undertested |
| LOW | Add session expiration to API (TTL-based cleanup) | Prevents memory leak in long runs |
| LOW | Validate API key format before storing in env | Input validation at boundary |
| LOW | Aggregate scanner file errors into summary report | Better user feedback |

---

## 2026-03-05 — Test Suite Audit

**Scope:** Test coverage, test structure, test quality, missing coverage, test patterns
**Test Files:** 29 test files containing 290 test functions

---

### 1. Test Coverage

**CI configuration** (`ci.yml`): `pytest --cov=testforge --cov-report=term-missing --cov-fail-under=70`
**Coverage omissions** (`pyproject.toml [tool.coverage.run].omit`):
- `src/testforge/presentation/api/*` (FastAPI routes — 12 files excluded)
- `src/testforge/presentation/tui.py` (interactive TUI excluded)

Previous audit (2026-03-03) reported: **203 tests passed, 0 failed**. Current test count has grown to **290 test functions across 29 files**.

---

### 2. Test Structure

The test directory mirrors the source architecture well:

| Source Layer | Source Path | Test Path | Test Files |
|---|---|---|---|
| **Domain** | `src/testforge/domain/` | `tests/domain/` | 4 files: `test_entities.py`, `test_value_objects.py`, `test_services.py`, `test_services_prd.py`, `test_errors.py` |
| **Application** | `src/testforge/application/` | `tests/application/` | 3 files: `test_commands.py`, `test_orchestrator.py`, `test_dtos_and_queries.py` |
| **Infrastructure** | `src/testforge/infrastructure/` | `tests/infrastructure/` | 18 files covering scanners, generators, validators, runners, adapters, etc. |
| **Presentation** | `src/testforge/presentation/` | `tests/` (root) | 3 files: `test_cli.py`, `test_agent.py`, `test_config_layers.py` |

**Structural coverage by test file count:**
- Domain: 5 source modules (entities, value_objects, services, errors, ports, events) → 5 test files (ports and events tested indirectly)
- Application: 4 source modules (commands, orchestrator, dtos, queries) → 3 test files (dtos+queries combined)
- Infrastructure: 17 source modules → 18 test files (good coverage)
- Presentation: 4 source modules (cli, tui, agent, api/*) → 3 test files (tui and api excluded from coverage)

---

### 3. Test Quality Assessment

**Verdict: HIGH QUALITY — Tests verify real behavior, not stubs.**

#### Strengths

1. **Domain tests are pure** — `test_entities.py`, `test_value_objects.py`, `test_services.py` use zero mocks. They test domain logic with real domain objects. This is the correct approach for domain layer testing.

2. **Application tests mock ports correctly** — `test_commands.py` mocks `scanner`, `ai`, and `gen` (port interfaces), not domain services. For example:
   - `scanner = MagicMock(); scanner.scan.return_value = analysis` — mocks the CodeScannerPort
   - `ai = MagicMock(); ai.generate_strategy.return_value = expected` — mocks AIStrategyPort
   - This follows hexagonal architecture mocking best practices.

3. **Infrastructure tests use real I/O** — `test_python_scanner.py`, `test_typescript_scanner.py`, `test_filesystem.py`, `test_config.py`, `test_test_runner.py` all use `tmp_path` fixtures to create real files and run real scanning/parsing logic.

4. **AI adapter tests mock at the right boundary** — `test_claude_adapter.py` mocks `anthropic.Anthropic` (the external SDK), not internal logic. Tests verify JSON parsing, markdown fence stripping, and strategy construction with 22 test functions.

5. **CLI tests are genuine integration tests** — `test_cli.py` (23 tests) uses `typer.testing.CliRunner` with real temporary files, exercising the full CLI flow end-to-end.

6. **Agent tests are thorough** — `test_agent.py` (38 tests) covers tool schemas, confirmation logic, all handler paths (including error states), system prompt generation, message trimming, and gap-finding caching.

7. **Concrete assertions throughout** — Every test has specific assertions (e.g., `assert suite.size == 3`, `assert "format_name" in func_names`, `assert report.coverage_percent == 100.0`). No `assert True` stubs or placeholder tests found.

#### Minor Issues

1. **Frozen immutability tests use try/except instead of `pytest.raises`** — `test_entities.py` lines 44-50 and `test_value_objects.py` lines 42-48 use manual try/except blocks instead of `with pytest.raises(AttributeError)`. This is functional but not idiomatic pytest.

2. **Some test duplication** — `test_generators.py` contains TypeScriptScanner tests (lines 188-234) that duplicate tests in `test_typescript_scanner.py`. The file tests 6 generator classes plus redundant scanner tests.

---

### 4. Missing Coverage

#### Source modules with NO dedicated test file

| Module | Lines | Risk | Notes |
|---|---|---|---|
| `domain/ports.py` | 53 | None | Protocol interfaces only (ABCs). Tested via implementations. No logic to test. |
| `domain/events.py` | 53 | Low | Frozen dataclasses. Indirectly tested via `test_container.py` (imports `AnalysisCompleted`). |
| `infrastructure/ai/prompts.py` | 166 | Low | Static string templates. No logic. Could add format-string validation tests. |
| `infrastructure/ai/gemini_adapter.py` | 128 | **Medium** | Full adapter with parsing logic. Has `_parse_strategy_response()` and `_build_analysis_summary()` methods with real logic. Zero tests. |
| `presentation/tui.py` | ~150+ | Medium | Excluded from coverage in `pyproject.toml`. Interactive UI code. |
| `presentation/api/*` | ~12 files | Medium | Excluded from coverage in `pyproject.toml`. FastAPI routes. |
| `presentation/cli.py` | ~300+ | Low | Partially tested via `test_cli.py` (23 tests) and `test_config_layers.py` (4 tests). Some code paths (e.g., `watch`, `repair`, `mutate`) may have lower coverage. |

**Key gap:** `gemini_adapter.py` has real parsing logic (JSON deserialization, markdown stripping, strategy construction) identical in complexity to `claude_adapter.py` (which has 22 tests), but has zero tests.

#### Modules with potentially low line coverage (based on code complexity vs test count)

| Module | Test Count | Estimated Risk |
|---|---|---|
| `infrastructure/test_repairer.py` | 13 tests | Good — covers repair flow, retries, directory scanning |
| `presentation/agent.py` | 38 tests | Excellent |
| `presentation/cli.py` | 27 tests (across 2 files) | Good but `watch`, `repair`, `mutate` CLI commands may lack coverage |

---

### 5. Test Patterns

#### Fixtures
- **`@pytest.fixture`**: Used only once (`test_python_scanner.py:11` — `sample_project` fixture)
- **`tmp_path`**: Used extensively (pytest built-in) — 40+ test methods use it for file I/O isolation
- **`monkeypatch`**: Used in `test_config.py` for `chdir()`
- **No `conftest.py`**: There are no shared conftest files in the test directory. Each test file is self-contained.
- **Helper builders**: Reusable factory functions (`_sample_analysis()`, `_mock_analysis()`, `_strategy_with_unit_tests()`, `_make_session()`, etc.) are used consistently instead of fixtures — 15+ such helpers across test files.

#### Parametrize
- **`@pytest.mark.parametrize` is not used anywhere.** Several tests would benefit from it:
  - `test_value_objects.py::TestTestLayer::test_values` — iterates 5 enum values in one test
  - `test_errors.py::test_all_inherit_from_domain_error` — checks 6 error classes in a loop
  - `test_diff_detector.py::test_is_source_file` — checks 4 file extensions inline
  - `test_fixture_inferrer.py` — 3 similar mock-inference tests (HTTP, DB, subprocess) could share logic

#### Test Independence
- Tests are fully independent — no shared mutable state, no test ordering dependencies
- Each test method creates its own objects or uses `tmp_path` for isolation
- No `setUp`/`tearDown` or `@pytest.fixture(autouse=True)` patterns that could cause coupling

#### Test Organization
- Consistent use of test classes to group related tests (e.g., `TestPythonScanner`, `TestConfigAdapter`)
- Descriptive test method names following `test_<behavior>` pattern
- Docstrings used in approximately 30% of tests (primarily in `test_test_repairer.py`, `test_generators.py`)

---

### Summary & Recommendations

| Priority | Action | Impact |
|---|---|---|
| **High** | Add tests for `infrastructure/ai/gemini_adapter.py` (mirror `test_claude_adapter.py` approach) | Closes the biggest logic-coverage gap |
| **Medium** | Add `@pytest.mark.parametrize` to data-driven tests (errors, value objects, file type checks) | Improves readability and catches regressions |
| **Medium** | Add a `conftest.py` with shared fixtures (e.g., `sample_analysis`, `sample_strategy`) to reduce duplication across 15+ builder functions | Reduces maintenance burden |
| **Low** | Replace try/except immutability tests with `pytest.raises(AttributeError)` | Idiomatic pytest |
| **Low** | Remove duplicate TypeScriptScanner tests from `test_generators.py` (lines 188-234) | Reduces redundancy |
| **Low** | Add minimal tests for `domain/events.py` (creation, frozen check, field defaults) | Completes domain layer coverage |
| **Info** | Presentation layer (`tui.py`, `api/*`) is intentionally excluded from coverage — this is acceptable for CI but should be revisited if those layers grow in complexity | No action needed now |

## 2026-03-03 — Full Project Audit

**Scope:** Security, Code Quality, Test Coverage, Architecture
**Test Suite:** 203 passed, 0 failed (6.13s)

---

### Security Audit

**Overall Risk: LOW** — No critical or high-priority vulnerabilities found.

| # | Finding | Location | Severity | Status |
|---|---------|----------|----------|--------|
| S1 | `subprocess.run()` with user-provided `extra_args` | `infrastructure/test_runner.py:71-92` | Low | Mitigated (list-based commands) |
| S2 | `paths_to_mutate` joined into command args | `infrastructure/mutation_runner.py:85` | Low | Mitigated (list-based commands) |
| S3 | API key read from env var | `infrastructure/container.py:72` | Info | Correct — no hardcoded secrets |

**Positive findings:**
- Safe YAML: `yaml.safe_load()` used everywhere
- No `eval`/`exec`/`pickle` usage
- All subprocess calls use list-based commands (no shell injection)
- No hardcoded secrets; credentials via env vars
- Jinja2 uses `autoescape`
- File operations use `pathlib` (no path traversal risk)
- Plugin loading via standard `importlib.metadata.entry_points()`

**Recommendations:**
- Add `pip audit` to CI pipeline for dependency vulnerability scanning
- Add path validation for `paths_to_mutate` in mutation_runner.py

---

### Code Quality Audit

**Overall Quality: HIGH (85/100)**

#### Strengths
- Clean Architecture (Domain/Application/Infrastructure/Presentation) well-executed
- No circular imports
- PEP 8 naming conventions followed consistently
- Proper use of Protocol/ABC for ports
- Frozen dataclasses for value objects (immutability)
- Good error handling with specific exception types

#### Issues Found

| # | Finding | Location | Severity |
|---|---------|----------|----------|
| Q1 | `watch()` function is 68 lines — could extract helpers | `presentation/cli.py:628` | Low |
| Q2 | Markdown-stripping logic duplicated in 3 generators | `claude_adapter.py`, `jest_generator.py`, `integration_generator.py` | Low |
| Q3 | Some `# type: ignore` comments (7 total) | Various generator files | Info |
| Q4 | Return type `object` could be more specific | `infrastructure/container.py:70,80` | Low |
| Q5 | Missing docstrings on public domain entities | `domain/entities.py` (CodebaseAnalysis, TestCase, TestSuite, TestStrategy) | Low |
| Q6 | Missing docstrings on domain events | `domain/events.py` | Low |

---

### Test Coverage Audit

**Coverage: 31/35 modules have dedicated tests (88.6%)**
**Test Results: 203 passed, 0 failed**

#### Modules WITHOUT test coverage

| Module | Risk | Reason | Recommendation |
|--------|------|--------|----------------|
| `infrastructure/ai/claude_adapter.py` | Medium | Requires API key | Add mock-based unit tests |
| `infrastructure/ai/prompts.py` | Low | Static templates | Add format validation tests |
| `presentation/tui.py` | Medium | Interactive UI | Consider snapshot tests |
| `domain/events.py` | Low | Tested indirectly via commands | Acceptable |
| `domain/ports.py` | Low | Abstract interfaces | Tested via implementations |

#### Test Quality Assessment
- Tests are **meaningful** — they verify real behavior with concrete assertions, not stubs
- Proper mocking: `MagicMock`, `@patch` used for external dependencies
- Reusable test data builders (`_sample_analysis()`, `_strategy_with_unit_tests()`)
- CLI integration tests exercise end-to-end flows with real file I/O
- Test layering mirrors source architecture (domain/application/infrastructure)

---

### Architecture Audit

**Pattern: Clean Architecture (Hexagonal) — well implemented**

```
Presentation (CLI, TUI)
    └── Application (Commands, Queries, Orchestrator)
         └── Domain (Entities, Services, Ports, Value Objects)
              └── Infrastructure (Adapters: AI, Scanners, Generators, Runners)
```

**Design patterns in use:**
- Dependency Injection (Container)
- Port/Adapter (Protocol-based interfaces)
- CQRS (Commands + Queries)
- Strategy (per test layer)
- Plugin Architecture (entry points)
- Template Method (Jinja2 + AI enhancement)

**Pipeline flow:** Analyse → Strategise → Generate → Validate → Execute

---

### Summary & Recommended Next Steps

| Priority | Action |
|----------|--------|
| High | Add mock-based tests for `claude_adapter.py` |
| Medium | Add `pip audit` to CI workflow |
| Medium | Extract markdown-stripping into a shared utility |
| Low | Add docstrings to public domain entities |
| Low | Refactor `watch()` into smaller helper functions |
| Low | Consider TUI snapshot tests |
