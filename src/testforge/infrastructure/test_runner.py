"""Test execution and reporting — runs generated tests and captures results."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestResult:
    name: str
    outcome: str  # "passed", "failed", "error", "skipped"
    duration: float = 0.0
    message: str = ""
    longrepr: str = ""


@dataclass
class ExecutionReport:
    results: list[TestResult] = field(default_factory=list)
    total_duration: float = 0.0
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.outcome == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.outcome == "failed")

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.outcome == "error")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.outcome == "skipped")

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def failures(self) -> list[TestResult]:
        return [r for r in self.results if r.outcome in ("failed", "error")]


class TestRunner:
    """Runs generated test files and captures structured results."""

    def __init__(self, timeout: int = 120) -> None:
        self._timeout = timeout

    def run_pytest(self, test_dir: Path, extra_args: tuple[str, ...] = ()) -> ExecutionReport:
        """Run pytest on a directory and parse results via JSON report."""
        json_report = test_dir / ".testforge_results.json"
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_dir),
            f"--json-report-file={json_report}",
            "--json-report",
            "-q",
            *extra_args,
        ]

        # Try with json-report plugin first, fall back to parsing stdout
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=test_dir.parent,
            )
        except FileNotFoundError:
            return ExecutionReport(stderr="pytest not found", return_code=1)
        except subprocess.TimeoutExpired:
            return ExecutionReport(stderr="Test execution timed out", return_code=1)

        # Try parsing JSON report
        if json_report.exists():
            try:
                report = self._parse_json_report(json_report)
                report.stdout = proc.stdout
                report.stderr = proc.stderr
                report.return_code = proc.returncode
                return report
            except Exception:
                pass
            finally:
                json_report.unlink(missing_ok=True)

        # Fall back to parsing stdout
        return self._parse_stdout(proc)

    def run_pytest_simple(self, test_dir: Path, extra_args: tuple[str, ...] = ()) -> ExecutionReport:
        """Run pytest with verbose output and parse results from stdout."""
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_dir),
            "-v",
            "--tb=short",
            *extra_args,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=test_dir.parent if test_dir.parent.exists() else None,
            )
        except FileNotFoundError:
            return ExecutionReport(stderr="pytest not found", return_code=1)
        except subprocess.TimeoutExpired:
            return ExecutionReport(stderr="Test execution timed out", return_code=1)

        return self._parse_stdout(proc)

    def run_jest(self, test_dir: Path, extra_args: tuple[str, ...] = ()) -> ExecutionReport:
        """Run Jest on a directory and parse results."""
        cmd = [
            "npx", "jest",
            str(test_dir),
            "--json",
            "--no-coverage",
            *extra_args,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=test_dir.parent,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ExecutionReport(stderr="Jest not found or timed out", return_code=1)

        return self._parse_jest_output(proc)

    def _parse_json_report(self, report_path: Path) -> ExecutionReport:
        """Parse pytest-json-report output."""
        data = json.loads(report_path.read_text())
        results: list[TestResult] = []

        for test in data.get("tests", []):
            outcome = test.get("outcome", "unknown")
            longrepr = ""
            if outcome in ("failed", "error"):
                call = test.get("call", {})
                longrepr = call.get("longrepr", "")

            results.append(TestResult(
                name=test.get("nodeid", ""),
                outcome=outcome,
                duration=test.get("duration", 0.0),
                longrepr=longrepr,
            ))

        return ExecutionReport(
            results=results,
            total_duration=data.get("duration", 0.0),
        )

    def _parse_stdout(self, proc: subprocess.CompletedProcess) -> ExecutionReport:
        """Parse pytest verbose stdout to extract test results."""
        results: list[TestResult] = []

        for line in proc.stdout.splitlines():
            line = line.strip()
            if " PASSED" in line:
                name = line.split(" PASSED")[0].strip()
                results.append(TestResult(name=name, outcome="passed"))
            elif " FAILED" in line:
                name = line.split(" FAILED")[0].strip()
                results.append(TestResult(name=name, outcome="failed"))
            elif " ERROR" in line and "::" in line:
                name = line.split(" ERROR")[0].strip()
                results.append(TestResult(name=name, outcome="error"))
            elif " SKIPPED" in line:
                name = line.split(" SKIPPED")[0].strip()
                results.append(TestResult(name=name, outcome="skipped"))

        # Extract failure details
        failure_section = False
        current_failure = ""
        for line in proc.stdout.splitlines():
            if line.startswith("FAILURES") or line.startswith("=== FAILURES"):
                failure_section = True
                continue
            if failure_section and line.startswith("==="):
                failure_section = False
                continue
            if failure_section:
                current_failure += line + "\n"

        # Attach failure info to failed results
        if current_failure:
            for r in results:
                if r.outcome == "failed":
                    r.longrepr = current_failure

        return ExecutionReport(
            results=results,
            stdout=proc.stdout,
            stderr=proc.stderr,
            return_code=proc.returncode,
        )

    def _parse_jest_output(self, proc: subprocess.CompletedProcess) -> ExecutionReport:
        """Parse Jest JSON output."""
        results: list[TestResult] = []
        try:
            data = json.loads(proc.stdout)
            for suite in data.get("testResults", []):
                for test in suite.get("testResults", []):
                    status_map = {"passed": "passed", "failed": "failed", "pending": "skipped"}
                    outcome = status_map.get(test.get("status", ""), "error")
                    results.append(TestResult(
                        name=test.get("fullName", ""),
                        outcome=outcome,
                        duration=test.get("duration", 0) / 1000.0,
                        message="\n".join(test.get("failureMessages", [])),
                    ))
        except (json.JSONDecodeError, KeyError):
            pass

        return ExecutionReport(
            results=results,
            stdout=proc.stdout,
            stderr=proc.stderr,
            return_code=proc.returncode,
        )
