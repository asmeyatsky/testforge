"""Google Gemini adapter — implements AIStrategyPort."""

from __future__ import annotations

import json
import logging

from testforge.domain.entities import CodebaseAnalysis, TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.ai.claude_adapter import strip_markdown_fences
from testforge.infrastructure.ai.prompts import (
    STRATEGY_GENERATION_PROMPT,
    TEST_CASE_GENERATION_PROMPT,
)

logger = logging.getLogger(__name__)


class GeminiAdapter:
    """Implements AIStrategyPort using the Google Generative AI SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
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

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )

        return self._parse_strategy_response(response.text, analysis.id)

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
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini response as JSON, returning empty strategy")
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

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )

        return strip_markdown_fences(response.text)
