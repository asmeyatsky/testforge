"""LLM-powered test repair — auto-fix failing tests by feeding errors back to Claude."""

from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_REPAIR_PROMPT = """\
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
- Return ONLY the corrected Python code, no markdown fencing
"""


@dataclass
class RepairResult:
    test_file: str
    original_code: str
    repaired_code: str
    attempt: int
    success: bool
    error: str = ""


class TestRepairer:
    """Auto-fixes failing tests using LLM feedback loop."""

    def __init__(
        self,
        ai_adapter: object,
        max_attempts: int = 3,
        source_root: Path | None = None,
    ) -> None:
        self._ai = ai_adapter
        self._max_attempts = max_attempts
        self._source_root = source_root

    def repair_file(self, test_file: Path) -> RepairResult:
        """Attempt to repair a failing test file."""
        original_code = test_file.read_text(encoding="utf-8")
        current_code = original_code
        source_code = self._find_source_code(test_file)

        for attempt in range(1, self._max_attempts + 1):
            # Run the test to get errors
            error_output = self._run_test(test_file)
            if not error_output:
                # Tests pass — no repair needed
                return RepairResult(
                    test_file=str(test_file),
                    original_code=original_code,
                    repaired_code=current_code,
                    attempt=attempt,
                    success=True,
                )

            # Ask LLM to fix
            logger.info("Repair attempt %d/%d for %s", attempt, self._max_attempts, test_file.name)
            try:
                repaired = self._ask_llm_to_fix(
                    test_file=str(test_file),
                    test_code=current_code,
                    source_code=source_code,
                    error_output=error_output,
                )
            except Exception as e:
                return RepairResult(
                    test_file=str(test_file),
                    original_code=original_code,
                    repaired_code=current_code,
                    attempt=attempt,
                    success=False,
                    error=f"LLM error: {e}",
                )

            # Write repaired code
            test_file.write_text(repaired, encoding="utf-8")
            current_code = repaired

        # Final check after all attempts
        error_output = self._run_test(test_file)
        success = not error_output
        if not success:
            # Restore original code on failure
            test_file.write_text(original_code, encoding="utf-8")

        return RepairResult(
            test_file=str(test_file),
            original_code=original_code,
            repaired_code=current_code if success else original_code,
            attempt=self._max_attempts,
            success=success,
            error=error_output or "",
        )

    def repair_directory(self, test_dir: Path) -> list[RepairResult]:
        """Repair all failing test files in a directory."""
        results: list[RepairResult] = []
        for test_file in sorted(test_dir.rglob("test_*.py")):
            error = self._run_test(test_file)
            if error:
                result = self.repair_file(test_file)
                results.append(result)
        return results

    def _run_test(self, test_file: Path) -> str:
        """Run a single test file and return error output (empty string = pass)."""
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-x", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode == 0:
                return ""
            return proc.stdout + proc.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return "Test execution failed"

    def _ask_llm_to_fix(
        self,
        test_file: str,
        test_code: str,
        source_code: str,
        error_output: str,
    ) -> str:
        """Ask the AI adapter to fix the test code."""
        prompt = _REPAIR_PROMPT.format(
            test_file=test_file,
            test_code=test_code,
            source_code=source_code,
            error_output=error_output[:3000],  # Truncate long errors
        )

        # Use the AI adapter's message API
        if hasattr(self._ai, "_client"):
            message = self._ai._client.messages.create(
                model=self._ai._model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            code = message.content[0].text.strip()
        else:
            raise RuntimeError("AI adapter does not support message generation")

        # Strip markdown fencing
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        return code

    def _find_source_code(self, test_file: Path) -> str:
        """Try to find the source module corresponding to a test file."""
        if not self._source_root:
            return "# Source not available"

        # test_utils.py -> utils.py
        test_name = test_file.stem
        if test_name.startswith("test_"):
            source_name = test_name[5:] + ".py"
        else:
            return "# Source not available"

        # Search source root
        for source_file in self._source_root.rglob(source_name):
            try:
                return source_file.read_text(encoding="utf-8")
            except Exception:
                continue

        return "# Source not available"
