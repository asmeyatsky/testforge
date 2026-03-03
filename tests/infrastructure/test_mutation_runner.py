"""Tests for mutation testing integration."""

from unittest.mock import MagicMock

from testforge.infrastructure.mutation_runner import MutationReport, MutantResult, MutationRunner


class TestMutantResult:
    def test_creation(self):
        r = MutantResult(id="1", status="killed", source_file="app.py")
        assert r.id == "1"
        assert r.status == "killed"


class TestMutationReport:
    def test_mutation_score(self):
        report = MutationReport(results=[
            MutantResult(id="1", status="killed"),
            MutantResult(id="2", status="killed"),
            MutantResult(id="3", status="survived"),
            MutantResult(id="4", status="timeout"),
        ])
        assert report.total == 4
        assert report.killed == 2
        assert report.survived == 1
        assert report.timeout == 1
        assert report.mutation_score == 50.0

    def test_empty_report(self):
        report = MutationReport()
        assert report.mutation_score == 100.0
        assert report.total == 0

    def test_survivors(self):
        report = MutationReport(results=[
            MutantResult(id="1", status="killed"),
            MutantResult(id="2", status="survived"),
        ])
        assert len(report.survivors) == 1
        assert report.survivors[0].id == "2"


class TestMutationRunner:
    def test_parse_run_output(self):
        runner = MutationRunner()
        output = "10 killed, 2 survived, 1 timeout"
        results = runner._parse_run_output(output)
        killed = sum(1 for r in results if r.status == "killed")
        survived = sum(1 for r in results if r.status == "survived")
        assert killed == 10
        assert survived == 2
