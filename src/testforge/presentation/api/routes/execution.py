"""Test execution routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from testforge.infrastructure.test_runner import TestRunner
from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import ExecuteRequest

router = APIRouter(prefix="/api", tags=["execution"])


@router.post("/execute")
def execute_tests(
    body: ExecuteRequest,
    session: WebSession = Depends(get_or_create_session),
):
    test_dir = Path(body.test_dir or str(session.agent.output_dir))
    runner = TestRunner()
    report = runner.run_pytest_simple(test_dir)

    return {
        "session_id": session.id,
        "results": {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "errors": report.errors,
            "skipped": report.skipped,
            "success_rate": report.success_rate,
            "tests": [
                {
                    "name": r.name,
                    "outcome": r.outcome,
                    "duration": r.duration,
                    "message": r.longrepr[:500] if r.longrepr else None,
                }
                for r in report.results
            ],
        },
    }
