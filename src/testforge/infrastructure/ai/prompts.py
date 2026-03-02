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

Test cases to generate:
{test_cases}

Requirements:
- Use pytest conventions (test_ prefix, fixtures, parametrize where appropriate)
- Include docstrings explaining each test
- Mock external dependencies
- Include both positive and negative test cases
- Use descriptive assertion messages

Return ONLY the Python code, no markdown fencing.
"""
