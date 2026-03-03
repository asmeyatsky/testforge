"""Test quality validation — checks generated tests for syntax/import errors."""

from __future__ import annotations

import ast
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    file_path: str
    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.valid)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total else 1.0


class TestValidator:
    """Validates generated test files for syntax and collection errors."""

    def validate_syntax(self, output_dir: Path) -> ValidationReport:
        """Check all .py files in output_dir for Python syntax errors."""
        logger.info("Validating syntax in %s", output_dir)
        results: list[ValidationResult] = []

        for py_file in sorted(output_dir.rglob("*.py")):
            try:
                source = py_file.read_text(encoding="utf-8")
                ast.parse(source, filename=str(py_file))
                results.append(ValidationResult(
                    file_path=str(py_file.relative_to(output_dir)),
                    valid=True,
                ))
            except SyntaxError as e:
                results.append(ValidationResult(
                    file_path=str(py_file.relative_to(output_dir)),
                    valid=False,
                    errors=[f"SyntaxError at line {e.lineno}: {e.msg}"],
                ))

        return ValidationReport(results=results)

    def validate_collection(self, output_dir: Path) -> ValidationReport:
        """Run pytest --collect-only on generated tests to check imports and structure."""
        results: list[ValidationResult] = []

        py_files = sorted(output_dir.rglob("test_*.py"))
        if not py_files:
            return ValidationReport()

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", str(output_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if proc.returncode == 0:
                # All tests collected successfully
                for f in py_files:
                    results.append(ValidationResult(
                        file_path=str(f.relative_to(output_dir)),
                        valid=True,
                    ))
            else:
                # Parse errors from output
                error_lines = proc.stderr.strip().split("\n") if proc.stderr else []
                stdout_lines = proc.stdout.strip().split("\n") if proc.stdout else []

                for f in py_files:
                    fname = str(f.relative_to(output_dir))
                    file_errors = [
                        line for line in error_lines + stdout_lines
                        if fname in line or f.stem in line
                    ]
                    if file_errors:
                        results.append(ValidationResult(
                            file_path=fname, valid=False, errors=file_errors,
                        ))
                    else:
                        results.append(ValidationResult(file_path=fname, valid=True))

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Can't run pytest — fall back to syntax check only
            return self.validate_syntax(output_dir)

        return ValidationReport(results=results)
