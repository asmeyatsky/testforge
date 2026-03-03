"""Tests for test execution and reporting."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from testforge.infrastructure.test_runner import ExecutionReport, TestResult, TestRunner


class TestTestResult:
    def test_creation(self):
        r = TestResult(name="test_foo", outcome="passed", duration=0.5)
        assert r.name == "test_foo"
        assert r.outcome == "passed"


class TestExecutionReport:
    def test_counts(self):
        report = ExecutionReport(results=[
            TestResult(name="t1", outcome="passed"),
            TestResult(name="t2", outcome="passed"),
            TestResult(name="t3", outcome="failed"),
            TestResult(name="t4", outcome="skipped"),
        ])
        assert report.total == 4
        assert report.passed == 2
        assert report.failed == 1
        assert report.skipped == 1
        assert report.success_rate == 0.5

    def test_failures(self):
        report = ExecutionReport(results=[
            TestResult(name="t1", outcome="passed"),
            TestResult(name="t2", outcome="failed", longrepr="AssertionError"),
        ])
        assert len(report.failures) == 1
        assert report.failures[0].name == "t2"

    def test_empty(self):
        report = ExecutionReport()
        assert report.total == 0
        assert report.success_rate == 0.0


class TestTestRunner:
    def test_run_pytest_simple(self, tmp_path: Path):
        (tmp_path / "test_ok.py").write_text("def test_pass(): assert True\n")
        runner = TestRunner()
        report = runner.run_pytest_simple(tmp_path)
        assert report.passed >= 1

    def test_run_pytest_simple_failure(self, tmp_path: Path):
        (tmp_path / "test_fail.py").write_text("def test_fail(): assert False\n")
        runner = TestRunner()
        report = runner.run_pytest_simple(tmp_path)
        assert report.failed >= 1

    def test_parse_stdout(self):
        runner = TestRunner()
        mock_proc = MagicMock()
        mock_proc.stdout = "test_a.py::test_foo PASSED\ntest_a.py::test_bar FAILED\n"
        mock_proc.stderr = ""
        mock_proc.returncode = 1
        report = runner._parse_stdout(mock_proc)
        assert report.passed == 1
        assert report.failed == 1
