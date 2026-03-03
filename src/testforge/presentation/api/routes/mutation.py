"""Mutation testing routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from testforge.infrastructure.mutation_runner import MutationRunner
from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import MutateRequest

router = APIRouter(prefix="/api", tags=["mutation"])


@router.post("/mutate")
def run_mutation(
    body: MutateRequest,
    session: WebSession = Depends(get_or_create_session),
):
    runner = MutationRunner()
    if not runner.check_available():
        return {"error": "mutmut not installed. Install with: pip install mutmut"}

    report = runner.run(Path(body.source), Path(body.test_dir))

    if report.stderr and "not installed" in report.stderr:
        return {"error": report.stderr}

    return {
        "session_id": session.id,
        "mutation": {
            "mutation_score": report.mutation_score,
            "total": report.total,
            "killed": report.killed,
            "survived": report.survived,
            "timeout": report.timeout,
            "survivors": [
                {
                    "id": s.id,
                    "source_file": s.source_file,
                }
                for s in report.survivors[:20]
            ],
        },
    }
