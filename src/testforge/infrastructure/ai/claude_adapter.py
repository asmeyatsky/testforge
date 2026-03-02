"""Claude API adapter — implements AIStrategyPort."""

from __future__ import annotations

import json
import logging

from testforge.domain.entities import CodebaseAnalysis, TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.ai.prompts import (
    INTEGRATION_TEST_PROMPT,
    STRATEGY_GENERATION_PROMPT,
    TEST_CASE_GENERATION_PROMPT,
    UAT_GENERATION_PROMPT,
)

logger = logging.getLogger(__name__)


class ClaudeAdapter:
    """Implements AIStrategyPort using the Anthropic SDK."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514") -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate_strategy(
        self,
        analysis: CodebaseAnalysis,
        layers: list[TestLayer],
        prd_content: str | None = None,
    ) -> TestStrategy:
        analysis_summary = self._build_analysis_summary(analysis)
        prd_section = f"Product Requirements:\n{prd_content}" if prd_content else ""

        prompt = STRATEGY_GENERATION_PROMPT.format(
            layers=", ".join(l.value for l in layers),
            analysis_summary=analysis_summary,
            prd_section=prd_section,
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        return self._parse_strategy_response(response_text, analysis.id)

    def _build_analysis_summary(self, analysis: CodebaseAnalysis) -> str:
        lines = [
            f"Root: {analysis.root_path}",
            f"Languages: {', '.join(analysis.languages)}",
            f"Modules: {analysis.total_modules}",
            f"Functions: {analysis.total_functions}",
            f"Classes: {analysis.total_classes}",
            f"Endpoints: {len(analysis.endpoints)}",
            "",
            "Modules:",
        ]
        for mod in analysis.modules:
            lines.append(f"  - {mod.file_path}: {len(mod.functions)} functions, {len(mod.classes)} classes")
            for func in mod.functions:
                lines.append(f"    - {func.name}({', '.join(func.parameters)})")
            for cls in mod.classes:
                lines.append(f"    - class {cls.name}: {len(cls.methods)} methods")

        return "\n".join(lines)

    def _parse_strategy_response(self, response_text: str, analysis_id: str) -> TestStrategy:
        # Extract JSON from response (may be wrapped in markdown)
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI response as JSON, returning empty strategy")
            return TestStrategy(analysis_id=analysis_id)

        suites: list[TestSuite] = []
        for suite_data in data.get("suites", []):
            layer = TestLayer(suite_data["layer"])
            cases = [
                TestCase(
                    name=tc["name"],
                    description=tc.get("description", ""),
                    layer=layer,
                    target_function=tc.get("target_function", ""),
                    target_module=tc.get("target_module", ""),
                    priority=tc.get("priority", 2),
                    tags=tuple(tc.get("tags", [])),
                )
                for tc in suite_data.get("test_cases", [])
            ]
            suites.append(TestSuite(layer=layer, test_cases=tuple(cases)))

        return TestStrategy(analysis_id=analysis_id, suites=tuple(suites))

    def generate_test_code(
        self,
        target_module: str,
        source_code: str,
        test_cases: list[TestCase],
        imports_hint: str = "",
    ) -> str:
        """Generate actual test implementation code using AI."""
        cases_desc = "\n".join(
            f"- {tc.name}: {tc.description} (target: {tc.target_function}, priority: {tc.priority})"
            for tc in test_cases
        )
        imports_section = f"Import hints:\n{imports_hint}" if imports_hint else ""

        prompt = TEST_CASE_GENERATION_PROMPT.format(
            target_module=target_module,
            source_code=source_code,
            test_cases=cases_desc,
            imports_hint=imports_section,
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        code = message.content[0].text.strip()
        # Strip markdown fencing if present
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()
        return code

    def generate_integration_tests(
        self,
        framework: str,
        endpoints: list,
        source_code: str,
    ) -> str:
        """Generate integration test code for API endpoints."""
        endpoints_desc = "\n".join(
            f"- {ep.method} {ep.path} → {ep.handler_name} ({ep.file_path})"
            for ep in endpoints
        )

        prompt = INTEGRATION_TEST_PROMPT.format(
            framework=framework,
            endpoints=endpoints_desc,
            source_code=source_code,
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        code = message.content[0].text.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()
        return code

    def generate_uat_pack(
        self,
        endpoints: list,
        prd_content: str | None = None,
    ) -> str:
        """Generate UAT test pack in markdown."""
        endpoints_desc = "\n".join(
            f"- {ep.method} {ep.path} → {ep.handler_name}"
            for ep in endpoints
        )
        prd_section = f"Product Requirements Document:\n{prd_content}" if prd_content else "No PRD provided."

        prompt = UAT_GENERATION_PROMPT.format(
            endpoints=endpoints_desc,
            prd_section=prd_section,
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text.strip()
