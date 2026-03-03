"""AI prompt templates for each phase."""

from __future__ import annotations

ANALYSIS_INTERPRETATION_PROMPT = """\
You are a senior test architect. Given the following codebase analysis, identify:
1. Critical paths that need thorough testing
2. Areas with high complexity or risk
3. Integration points between modules
4. Public API surfaces

Codebase Analysis:
- Modules: {module_count}
- Functions: {function_count}
- Classes: {class_count}
- API Endpoints: {endpoint_count}
- Languages: {languages}

Module details:
{module_details}

{prd_section}

Respond with a JSON object containing:
{{
  "critical_paths": [list of critical module/function paths],
  "risk_areas": [list of high-risk areas with rationale],
  "integration_points": [list of module pairs that interact],
  "api_surfaces": [list of public API descriptions]
}}
"""

STRATEGY_GENERATION_PROMPT = """\
You are a senior test architect. Based on the following codebase analysis, generate a \
comprehensive test strategy for the requested layers: {layers}.

Codebase Analysis:
{analysis_summary}

{prd_section}

For each requested layer, generate test cases with the following JSON structure:
{{
  "suites": [
    {{
      "layer": "unit|integration|uat|soak|performance",
      "test_cases": [
        {{
          "name": "test_descriptive_name",
          "description": "What this test verifies",
          "target_function": "function_or_method_name",
          "target_module": "module/path.py",
          "priority": 1,
          "tags": ["tag1", "tag2"]
        }}
      ]
    }}
  ]
}}

Prioritize test cases by risk (1 = highest priority). Focus on:
- Core business logic for unit tests
- API contract verification for integration tests
- User journey coverage for UAT
- Stability under load for soak tests
- Throughput and latency for performance tests
"""

TEST_CASE_GENERATION_PROMPT = """\
You are a senior Python developer. Generate a complete pytest test file for the following \
test cases targeting module: {target_module}

Source code of the module under test:
```python
{source_code}
```

Test cases to generate:
{test_cases}

{imports_hint}

Requirements:
- Use pytest conventions (test_ prefix, fixtures, parametrize where appropriate)
- Include docstrings explaining each test
- Mock external dependencies using unittest.mock.patch
- Include both positive and negative test cases
- Use descriptive assertion messages
- Import the module under test correctly based on the source code
- Generate real, runnable assertions — not NotImplementedError stubs

Return ONLY the Python code, no markdown fencing.
"""

INTEGRATION_TEST_PROMPT = """\
You are a senior Python developer. Generate integration tests for the following API endpoints \
using a test client.

Framework detected: {framework}
Endpoints:
{endpoints}

Source code:
```python
{source_code}
```

Requirements:
- Use the {framework} test client
- Test successful responses (2xx)
- Test error cases (4xx, 5xx)
- Validate response structure
- Use fixtures for test setup

Return ONLY the Python code, no markdown fencing.
"""

TEST_REPAIR_PROMPT = """\
You are a senior Python developer. The following test file has failures. Fix the test code \
so all tests pass.

Test file path: {test_file}

Current test code:
```python
{test_code}
```

Source code of the module under test:
```python
{source_code}
```

Error output from pytest:
```
{error_output}
```

Requirements:
- Fix the failing tests so they pass
- Do not remove tests — fix them
- Keep all existing passing tests intact
- Use proper imports and mocking where needed

Return ONLY the corrected Python code, no markdown fencing.
"""

UAT_GENERATION_PROMPT = """\
You are a senior QA engineer. Generate a UAT (User Acceptance Test) pack in markdown format \
for the following application.

Application endpoints:
{endpoints}

{prd_section}

For each user-facing feature, generate:
1. Scenario name
2. Preconditions
3. Step-by-step test instructions
4. Expected results
5. Pass/Fail criteria

Format as a structured markdown document with tables.
"""
