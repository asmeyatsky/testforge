"""Claude API adapter — implements AIStrategyPort."""

from __future__ import annotations

import json
import logging

from testforge.domain.entities import CodebaseAnalysis, TestCase, TestStrategy, TestSuite
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.ai.prompts import STRATEGY_GENERATION_PROMPT

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
