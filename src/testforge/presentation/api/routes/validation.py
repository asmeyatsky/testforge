"""Test validation routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from testforge.infrastructure.validators import TestValidator
from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import ValidateRequest

router = APIRouter(prefix="/api", tags=["validation"])


@router.post("/validate")
def validate_tests(
    body: ValidateRequest,
    session: WebSession = Depends(get_or_create_session),
):
    test_dir = Path(body.test_dir or str(session.agent.output_dir))
    validator = TestValidator()
    report = validator.validate_syntax(test_dir)

    return {
        "session_id": session.id,
        "validation": {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "success_rate": report.success_rate,
            "results": [
                {
                    "file_path": r.file_path,
                    "valid": r.valid,
                    "errors": r.errors,
                }
                for r in report.results
            ],
        },
    }
