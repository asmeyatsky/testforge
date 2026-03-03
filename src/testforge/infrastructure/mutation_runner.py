"""Mutation testing integration — measures test quality using mutmut."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MutantResult:
    """Result of a single mutant."""
    id: str
    status: str  # "killed", "survived", "timeout", "suspicious"
    source_file: str = ""
    line_number: int = 0
    description: str = ""


@dataclass
class MutationReport:
    """Aggregate mutation testing report."""
    results: list[MutantResult] = field(default_factory=list)
    total_duration: float = 0.0
    stdout: str = ""
    stderr: str = ""

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def killed(self) -> int:
        return sum(1 for r in self.results if r.status == "killed")

    @property
    def survived(self) -> int:
        return sum(1 for r in self.results if r.status == "survived")

    @property
    def timeout(self) -> int:
        return sum(1 for r in self.results if r.status == "timeout")

    @property
    def mutation_score(self) -> float:
        """Percentage of mutants killed (higher = better tests)."""
        if self.total == 0:
            return 100.0
        return (self.killed / self.total) * 100.0

    @property
    def survivors(self) -> list[MutantResult]:
        return [r for r in self.results if r.status == "survived"]


class MutationRunner:
    """Runs mutation testing using mutmut to measure test quality."""

    def __init__(self, timeout: int = 300) -> None:
        self._timeout = timeout

    def run(
        self,
        source_dir: Path,
        test_dir: Path,
        paths_to_mutate: tuple[str, ...] = (),
    ) -> MutationReport:
        """Run mutmut mutation testing."""
        cmd = [
            sys.executable, "-m", "mutmut", "run",
            "--paths-to-mutate", str(source_dir),
            "--tests-dir", str(test_dir),
            "--no-progress",
        ]

        if paths_to_mutate:
            cmd = [
                sys.executable, "-m", "mutmut", "run",
                "--paths-to-mutate", ",".join(paths_to_mutate),
                "--tests-dir", str(test_dir),
                "--no-progress",
            ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=source_dir.parent,
            )
        except FileNotFoundError:
            return MutationReport(
                stderr="mutmut not installed. Install with: pip install mutmut",
            )
        except subprocess.TimeoutExpired:
            return MutationReport(stderr="Mutation testing timed out")

        # Parse results
        return self._parse_results(proc, source_dir)

    def _parse_results(
        self, proc: subprocess.CompletedProcess, source_dir: Path
    ) -> MutationReport:
        """Parse mutmut output to extract mutation results."""
        results: list[MutantResult] = []

        # Try to get results via mutmut results command
        try:
            results_proc = subprocess.run(
                [sys.executable, "-m", "mutmut", "results"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=source_dir.parent,
            )
            results = self._parse_results_output(results_proc.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            results = self._parse_run_output(proc.stdout)

        return MutationReport(
            results=results,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    def _parse_results_output(self, output: str) -> list[MutantResult]:
        """Parse `mutmut results` output."""
        results: list[MutantResult] = []
        current_status = ""

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Survived"):
                current_status = "survived"
            elif line.startswith("Killed"):
                current_status = "killed"
            elif line.startswith("Timeout"):
                current_status = "timeout"
            elif line.startswith("Suspicious"):
                current_status = "suspicious"
            elif line and current_status:
                # Lines like "---- module.py (1, 2, 3)"
                match = re.match(r"----\s+(.+?)\s*\((.+)\)", line)
                if match:
                    source_file = match.group(1)
                    mutant_ids = [m.strip() for m in match.group(2).split(",")]
                    for mid in mutant_ids:
                        results.append(MutantResult(
                            id=mid,
                            status=current_status,
                            source_file=source_file,
                        ))

        return results

    def _parse_run_output(self, output: str) -> list[MutantResult]:
        """Parse mutmut run output as fallback."""
        results: list[MutantResult] = []

        # Parse summary line like "292 killed, 5 survived, 2 timeout"
        killed_match = re.search(r"(\d+)\s+killed", output)
        survived_match = re.search(r"(\d+)\s+survived", output)
        timeout_match = re.search(r"(\d+)\s+timeout", output)

        if killed_match:
            for i in range(int(killed_match.group(1))):
                results.append(MutantResult(id=f"k{i}", status="killed"))
        if survived_match:
            for i in range(int(survived_match.group(1))):
                results.append(MutantResult(id=f"s{i}", status="survived"))
        if timeout_match:
            for i in range(int(timeout_match.group(1))):
                results.append(MutantResult(id=f"t{i}", status="timeout"))

        return results

    def check_available(self) -> bool:
        """Check if mutmut is installed."""
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "mutmut", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return proc.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
